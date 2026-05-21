"""
Google Speech-to-Text Transcriber

Extracts audio from video, uploads to GCS temp bucket, runs Google STT
with speaker diarization, and returns structured transcript segments.

Speaker mapping rule:
  1 speaker → Andrew Scott
  2 speakers → Andrew Scott (spk0), Lance O'Sullivan (spk1)
"""

import logging
import os
import subprocess
import tempfile
import uuid

from google.cloud import speech, storage

from models import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)

# Temp GCS bucket for STT audio (not for permanent storage)
TEMP_BUCKET = os.getenv("SPEECH_TEMP_BUCKET", "evolution-engine-speech-temp")


class Transcriber:
    """Transcribes video/audio using Google Speech-to-Text with diarization."""

    def __init__(self, speaker_count: int = 1):
        """
        Args:
            speaker_count: Expected number of speakers (1 or 2).
        """
        self.speaker_count = max(1, min(speaker_count, 2))
        self.speech_client = speech.SpeechClient()
        self.storage_client = storage.Client()
        self.speaker_names = _get_speaker_names(self.speaker_count)

    def transcribe_video(self, video_path: str) -> TranscriptResult:
        """
        Transcribe a video file. Extracts audio, uploads to GCS, runs STT.

        Args:
            video_path: Local path to the video file (.mp4, .mov, etc.).

        Returns:
            TranscriptResult with full_text, segments, and speaker mappings.
        """
        logger.info(f"Transcribing video: {video_path} (speakers={self.speaker_count})")

        # Step 1: Extract audio to WAV
        audio_path = self._extract_audio(video_path)

        try:
            # Step 2: Upload to GCS
            gcs_uri = self._upload_to_gcs(audio_path)

            try:
                # Step 3: Run STT with diarization
                segments = self._transcribe(gcs_uri)

                # Step 4: Map speaker labels to real names
                segments = self._map_speakers(segments)

                # Step 5: Build result
                full_text = " ".join(s.text for s in segments)
                speakers = [
                    {"name": name, "label": f"spk{i}"}
                    for i, name in enumerate(self.speaker_names)
                ]

                return TranscriptResult(
                    source="google_speech_v1",
                    model="latest_long",
                    full_text=full_text,
                    segments=segments,
                    speakers=speakers,
                )
            finally:
                # Clean up GCS temp file
                self._delete_from_gcs(gcs_uri)
        finally:
            # Clean up local temp audio
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
            "-vn",                # No video
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", "16000",       # 16kHz sample rate
            "-ac", "1",           # Mono
            "-y",                 # Overwrite
            audio_path,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr.decode()}") from e

        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Audio extracted: {size_mb:.1f}MB")
        return audio_path

    def _upload_to_gcs(self, local_path: str) -> str:
        """Upload audio to GCS temp bucket. Returns gs:// URI."""
        bucket = self.storage_client.bucket(TEMP_BUCKET)
        blob_name = f"email-ingest/{uuid.uuid4().hex}.wav"
        blob = bucket.blob(blob_name)

        logger.info(f"Uploading to gs://{TEMP_BUCKET}/{blob_name}")
        blob.upload_from_filename(local_path)

        return f"gs://{TEMP_BUCKET}/{blob_name}"

    def _delete_from_gcs(self, gcs_uri: str):
        """Delete a temp file from GCS."""
        try:
            bucket_name = TEMP_BUCKET
            blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
            bucket = self.storage_client.bucket(bucket_name)
            bucket.blob(blob_name).delete()
            logger.info(f"Cleaned up GCS: {gcs_uri}")
        except Exception as e:
            logger.warning(f"GCS cleanup failed (non-critical): {e}")

    def _transcribe(self, gcs_uri: str) -> list[TranscriptSegment]:
        """
        Run Google Speech-to-Text with speaker diarization.
        Returns raw segments with diarization labels (spk0, spk1).
        """
        logger.info("Starting Google STT longRunningRecognize...")

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

        logger.info("Waiting for STT operation to complete...")
        response = operation.result(timeout=600)

        if not response.results:
            logger.warning("STT returned no results")
            return []

        # Collect all words with speaker tags
        all_words = []
        for result in response.results:
            alt = result.alternatives[0] if result.alternatives else None
            if not alt or not alt.words:
                continue

            for word_info in alt.words:
                speaker_tag = word_info.speaker_tag
                speaker_label = f"spk{speaker_tag}" if speaker_tag else "spk0"

                start_time = (
                    word_info.start_time.seconds
                    + word_info.start_time.microseconds / 1_000_000
                )
                end_time = (
                    word_info.end_time.seconds
                    + word_info.end_time.microseconds / 1_000_000
                )

                all_words.append({
                    "word": word_info.word,
                    "speaker_label": speaker_label,
                    "start_time": start_time,
                    "end_time": end_time,
                })

        # Sort by time
        all_words.sort(key=lambda w: w["start_time"])

        # Group consecutive words by speaker into segments
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

        # Flush final segment
        if current_words:
            last_word = all_words[-1]
            segments.append(TranscriptSegment(
                start_time=segment_start,
                end_time=last_word["end_time"],
                speaker=current_speaker,
                text=" ".join(current_words),
            ))

        logger.info(f"STT complete: {len(segments)} segments, {len(all_words)} words")
        return segments

    def _map_speakers(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        """
        Map diarization labels (spk0, spk1) to real names.
        Rule: spk0 → first speaker name, spk1 → second speaker name.
        """
        # Build label → name map
        seen_labels = []
        for seg in segments:
            if seg.speaker not in seen_labels:
                seen_labels.append(seg.speaker)

        label_map = {}
        for i, label in enumerate(seen_labels):
            if i < len(self.speaker_names):
                label_map[label] = self.speaker_names[i]
            else:
                label_map[label] = label  # Keep original if more speakers than expected

        logger.info(f"Speaker map: {label_map}")

        for seg in segments:
            seg.speaker = label_map.get(seg.speaker, seg.speaker)

        return segments


def _get_speaker_names(speaker_count: int) -> list[str]:
    """Return speaker names based on count."""
    if speaker_count >= 2:
        return ["Andrew Scott", "Lance O'Sullivan"]
    return ["Andrew Scott"]
