"""
transcriber.py
Premium multi-engine Transcriber supporting Google Speech-to-Text, NVIDIA Canary daemon,
Groq Whisper, and Gemini 2.5 Flash. Fully integrates post-processing dictionary
corrections and LLM-based consensus reconciliation.
"""

import os
import json
import re
import uuid
import logging
import tempfile
import subprocess
from typing import Optional

from google.cloud import speech, storage

from models import TranscriptResult, TranscriptSegment
from corrections import CorrectionsApplier
from reconciler import TranscriptReconciler
from model_router import AI_STUDIO_ALLOWED, AI_STUDIO_API_KEY

logger = logging.getLogger(__name__)

TEMP_BUCKET = os.getenv("SPEECH_TEMP_BUCKET", "evolution-engine-speech-temp")
CANARY_URL = os.getenv("CANARY_URL", "http://127.0.0.1:5005/transcribe")


class Transcriber:
    """Orchestrates multi-engine transcription with fallbacks, corrections, and reconciliation."""

    def __init__(self, speaker_count: int = 1):
        self.speaker_count = max(1, min(speaker_count, 2))
        self.speaker_names = self._get_speaker_names()
        self.corrections_applier = CorrectionsApplier()
        self.reconciler = TranscriptReconciler()

        # Lazy initialize clients to allow running without specific credentials if unused
        self._speech_client = None
        self._storage_client = None

    @property
    def speech_client(self):
        if self._speech_client is None:
            self._speech_client = speech.SpeechClient()
        return self._speech_client

    @property
    def storage_client(self):
        if self._storage_client is None:
            self._storage_client = storage.Client()
        return self._storage_client

    def _get_speaker_names(self) -> list[str]:
        if self.speaker_count >= 2:
            return ["Andrew Scott", "Lance O'Sullivan"]
        return ["Andrew Scott"]

    def transcribe_video(
        self,
        video_path: str,
        engine: str = "auto",
        force_audit: bool = False,
        horse_name: str = "Unknown",
        venue: str = "Unknown",
        content_type: str = "update"
    ) -> TranscriptResult:
        """
        Transcribes a video/audio file.
        
        Args:
            video_path: Local path to the video file.
            engine: 'auto', 'google', 'canary', or 'groq'.
            force_audit: If True, run multiple backends and reconcile them with LLM.
            horse_name: Used for LLM reconciliation context and Gemini prompting.
            venue: Used for LLM reconciliation context.
            content_type: Used for LLM reconciliation context.
        """
        logger.info(f"Starting transcription: {video_path} (engine={engine}, force_audit={force_audit})")

        # Step 1: Handle direct video/audio model if AI Studio or Gemini is selected
        if engine == "aistudio":
            if not AI_STUDIO_ALLOWED or not AI_STUDIO_API_KEY:
                raise RuntimeError("AI Studio not configured. Set AI_STUDIO_API_KEY.")
            logger.info("Using AI Studio free-tier transcription.")
            audio_path = self._extract_audio(video_path)
            try:
                result_dict = self._transcribe_aistudio(audio_path, horse_name)
                result = TranscriptResult(**result_dict)
                return self.corrections_applier.apply_to_transcript_result(result)
            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)

        if engine == "gemini":
            if os.getenv("GEMINI_ALLOW_TRANSCRIPTION", "false").lower() != "true":
                raise RuntimeError(
                    "Gemini transcription is disabled. Set GEMINI_ALLOW_TRANSCRIPTION=true to enable."
                )
            logger.info("Using direct Gemini 2.5 Flash transcription (explicitly enabled).")
            result_dict = self._transcribe_gemini(video_path, horse_name)
            result = TranscriptResult(**result_dict)
            return self.corrections_applier.apply_to_transcript_result(result)

        # Step 1b: Auto engine — quota-aware fallback chain
        if engine == "auto":
            # Gate Google STT behind free-tier quota
            from model_router import get_tracker
            tracker = get_tracker()
            if tracker.check("google_stt_free"):
                engine = "google"
            elif AI_STUDIO_ALLOWED and AI_STUDIO_API_KEY and tracker.check("ai_studio_stt"):
                logger.info("Google STT quota exhausted — trying AI Studio free tier")
                engine = "aistudio"
            else:
                logger.info("Google + AI Studio STT quotas exhausted — falling back to Groq")
                engine = "groq"

        # Step 2: Extract audio for all other audio-based STT engines
        audio_path = self._extract_audio(video_path)
        
        try:
            transcripts: dict[str, TranscriptResult] = {}

            # Execute engines based on request
            if engine in ("auto", "google"):
                try:
                    logger.info("Running Google STT...")
                    gcs_uri = self._upload_to_gcs(audio_path)
                    try:
                        google_segments = self._transcribe_google_gcs(gcs_uri)
                        google_segments = self._map_speakers(google_segments)
                        full_text = " ".join(s.text for s in google_segments)
                        transcripts["google"] = TranscriptResult(
                            source="google_speech_v1",
                            model="latest_long",
                            full_text=full_text,
                            segments=google_segments,
                            speakers=[{"name": name, "label": f"spk{i}"} for i, name in enumerate(self.speaker_names)]
                        )
                        # Record quota usage after success
                        duration = google_segments[-1].end_time if google_segments else 0.0
                        if duration > 0:
                            from model_router import get_tracker
                            tracker = get_tracker()
                            tracker.consume("google_stt_free", amount=int(duration))
                            logger.info(f"Recorded Google STT usage: {int(duration)}s")
                    finally:
                        self._delete_from_gcs(gcs_uri)
                except Exception as e:
                    logger.error(f"Google STT failed: {e}")
                    if engine == "google":
                        raise

            # Gated Audits & Fallbacks
            # If primary failed or force_audit is requested, run alternative engines
            primary_failed = "google" not in transcripts or not transcripts["google"].full_text
            run_audits = force_audit or primary_failed

            if run_audits:
                # 1. Groq Whisper Fallback
                groq_key = os.getenv("GROQ_API_KEY")
                if groq_key:
                    try:
                        logger.info("Running Groq Whisper ASR...")
                        groq_result = self._transcribe_groq(audio_path)
                        if groq_result:
                            transcripts["groq"] = groq_result
                    except Exception as e:
                        logger.warning(f"Groq Whisper failed: {e}")
                else:
                    logger.debug("Groq key not configured, skipping Groq Whisper.")

                # 2. Local GPU Canary Fallback
                try:
                    logger.info("Running NVIDIA Canary ASR...")
                    canary_result = self._transcribe_canary(audio_path)
                    if canary_result:
                        transcripts["canary"] = canary_result
                except Exception as e:
                    logger.warning(f"Canary Daemon failed: {e}")

            # Step 3: Raise if no transcripts yet
            if not transcripts:
                raise RuntimeError("All transcription engines failed.")

            # Step 3: Apply corrections to all successful raw transcripts
            for key, t_res in transcripts.items():
                transcripts[key] = self.corrections_applier.apply_to_transcript_result(t_res)

            # Step 4: Perform Reconciliation if needed
            # If multiple transcripts exist, or force_audit is True, run the LLM reconciler
            if len(transcripts) > 1 or (len(transcripts) == 1 and force_audit):
                logger.info(f"Reconciling {len(transcripts)} transcripts with Ollama consensus LLM...")
                meta = {"horse": horse_name, "venue": venue, "content_type": content_type}
                
                # Format candidate texts for the reconciler
                texts_to_reconcile = {engine: r.full_text for engine, r in transcripts.items()}
                
                reconciled_raw = self.reconciler.reconcile(texts_to_reconcile, meta=meta)
                if reconciled_raw and reconciled_raw.get("finalText"):
                    # Use the primary/first available engine as structural base, and insert the reconciled text
                    base_engine = "google" if "google" in transcripts else list(transcripts.keys())[0]
                    base_res = transcripts[base_engine]
                    
                    # Construct clean, single-segment reconciled output (or map text onto base segments)
                    # For simplicity and clean UI display, we return a single segment with the LLM reconciled text,
                    # mimicking the legacy JavaScript pipeline.
                    reconciled_segments = [TranscriptSegment(
                        start_time=base_res.segments[0].start_time if base_res.segments else 0.0,
                        end_time=base_res.segments[-1].end_time if base_res.segments else 0.0,
                        speaker=base_res.segments[0].speaker if base_res.segments else self.speaker_names[0],
                        text=reconciled_raw["finalText"]
                    )]
                    
                    return TranscriptResult(
                        source="reconciled_llm",
                        model=f"reconciled_{reconciled_raw.get('reconciliation_model', 'unknown')}",
                        full_text=reconciled_raw["finalText"],
                        segments=reconciled_segments,
                        speakers=base_res.speakers,
                        confidence=reconciled_raw.get("confidence"),
                        needs_human_review=reconciled_raw.get("needsHumanReview"),
                        review_reason=reconciled_raw.get("reviewReason"),
                        reconciliation_changes=reconciled_raw.get("changes", [])
                    )

            # Return the single best transcript if no reconciliation took place
            best_engine = "google" if "google" in transcripts else list(transcripts.keys())[0]
            logger.info(f"Returning non-reconciled transcript from engine: {best_engine}")
            return transcripts[best_engine]

        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    def _extract_audio(self, video_path: str) -> str:
        """Extract mono 16kHz WAV audio from video using ffmpeg."""
        audio_path = os.path.join(
            tempfile.gettempdir(),
            f"email-ingest-{uuid.uuid4().hex[:8]}.wav",
        )
        logger.info(f"Extracting audio to: {audio_path}")

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            audio_path,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr.decode()}") from e

        return audio_path

    def _upload_to_gcs(self, local_path: str) -> str:
        bucket = self.storage_client.bucket(TEMP_BUCKET)
        blob_name = f"email-ingest/{uuid.uuid4().hex}.wav"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        return f"gs://{TEMP_BUCKET}/{blob_name}"

    def _delete_from_gcs(self, gcs_uri: str):
        try:
            bucket_name = TEMP_BUCKET
            blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
            bucket = self.storage_client.bucket(bucket_name)
            bucket.blob(blob_name).delete()
        except Exception as e:
            logger.warning(f"GCS cleanup failed (non-critical): {e}")

    def _transcribe_google_gcs(self, gcs_uri: str) -> list[TranscriptSegment]:
        """Existing Google Speech-to-Text longRunningRecognize implementation."""
        min_speakers = self.speaker_count
        max_speakers = max(self.speaker_count, 2)

        operation = self.speech_client.long_running_recognize(
            config={
                "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "sample_rate_hertz": 16000,
                "language_code": "en-US",
                "model": "latest_long",
                "enable_automatic_punctuation": True,
                "enable_word_time_offsets": True,
                "diarization_config": {
                    "enable_speaker_diarization": True,
                    "min_speaker_count": min_speakers,
                    "max_speaker_count": max_speakers,
                },
            },
            audio={"uri": gcs_uri},
        )

        response = operation.result(timeout=600)
        if not response.results:
            return []

        all_words = []
        for result in response.results:
            alt = result.alternatives[0] if result.alternatives else None
            if not alt or not alt.words:
                continue

            for word_info in alt.words:
                speaker_tag = word_info.speaker_tag
                speaker_label = f"spk{speaker_tag}" if speaker_tag else "spk0"
                start_time = word_info.start_time.seconds + word_info.start_time.microseconds / 1_000_000
                end_time = word_info.end_time.seconds + word_info.end_time.microseconds / 1_000_000
                all_words.append({
                    "word": word_info.word,
                    "speaker_label": speaker_label,
                    "start_time": start_time,
                    "end_time": end_time,
                })

        all_words.sort(key=lambda w: w["start_time"])

        segments = []
        current_speaker = None
        current_words = []
        segment_start = 0.0
        segment_end = 0.0

        for w in all_words:
            if w["speaker_label"] != current_speaker:
                if current_words:
                    segments.append(TranscriptSegment(
                        start_time=segment_start,
                        end_time=segment_end,
                        speaker=current_speaker,
                        text=" ".join(current_words),
                    ))
                current_speaker = w["speaker_label"]
                current_words = [w["word"]]
                segment_start = w["start_time"]
                segment_end = w["end_time"]
            else:
                current_words.append(w["word"])
                segment_end = w["end_time"]

        if current_words:
            segments.append(TranscriptSegment(
                start_time=segment_start,
                end_time=all_words[-1]["end_time"],
                speaker=current_speaker,
                text=" ".join(current_words),
            ))

        return segments

    def _map_speakers(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        seen_labels = []
        for seg in segments:
            if seg.speaker not in seen_labels:
                seen_labels.append(seg.speaker)

        label_map = {}
        for i, label in enumerate(seen_labels):
            if i < len(self.speaker_names):
                label_map[label] = self.speaker_names[i]
            else:
                label_map[label] = label

        for seg in segments:
            seg.speaker = label_map.get(seg.speaker, seg.speaker)

        return segments

    def _transcribe_canary(self, audio_path: str) -> Optional[TranscriptResult]:
        """Hit local CUDA Canary daemon on port 5005."""
        try:
            logger.info(f"POSTing {audio_path} to Canary daemon at {CANARY_URL}...")
            resp = requests.post(CANARY_URL, json={"audio_path": audio_path}, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"Canary Daemon returned error: {resp.text}")
                return None
            
            data = resp.json()
            raw_text = data.get("text", "")
            
            # Form segments from daemon result
            segments = []
            for seg in data.get("segments", []):
                segments.append(TranscriptSegment(
                    start_time=seg.get("startTime", 0.0),
                    end_time=seg.get("endTime", 0.0),
                    speaker=self.speaker_names[0],
                    text=seg.get("text", "")
                ))
                
            if not segments and raw_text:
                segments = [TranscriptSegment(start_time=0.0, end_time=0.0, speaker=self.speaker_names[0], text=raw_text)]
                
            return TranscriptResult(
                source="nvidia_canary",
                model=data.get("model", "canary-1b"),
                full_text=raw_text,
                segments=segments,
                speakers=[{"name": name, "label": f"spk{i}"} for i, name in enumerate(self.speaker_names)]
            )
        except Exception as e:
            logger.warning(f"Failed to communicate with Canary Daemon: {e}")
            return None

    def _transcribe_groq(self, audio_path: str) -> Optional[TranscriptResult]:
        """Delegate to resilient Groq Whisper wrapper with key rotation + retry."""
        from groq_resilient import groq_transcribe
        result = groq_transcribe(audio_path)
        if result is None:
            return None

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                speaker=self.speaker_names[0],  # Groq doesn't diarize natively
                text=seg["text"],
            ))
        if not segments and result.get("full_text"):
            segments = [TranscriptSegment(start_time=0.0, end_time=0.0, speaker=self.speaker_names[0], text=result["full_text"])]

        return TranscriptResult(
            source=result["source"],
            model=result["model"],
            full_text=result["full_text"],
            segments=segments,
            speakers=[{"name": name, "label": f"spk{i}"} for i, name in enumerate(self.speaker_names)]
        )

    def _transcribe_gemini(self, video_path: str, horse_name: str) -> dict:
        """Gated Gemini transcription — delegates to ModelRouter so policy is centralised."""
        from model_router import get_router
        return get_router().gemini_transcribe(video_path, horse_name)

    def _transcribe_aistudio(self, audio_path: str, horse_name: str) -> dict:
        """AI Studio free-tier transcription — delegates to ModelRouter."""
        from model_router import get_router
        return get_router().aistudio_transcribe(audio_path, horse_name)
