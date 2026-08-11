#!/usr/bin/env python3
"""
transcribe.py
Standalone premium developer CLI for transcribing local or remote video/audio files.
Supports selecting engines, forcing audits/reconciliation, and saving formatted output.
"""

import os
import re
import sys
import glob
import argparse
import logging
import tempfile
import uuid
import time
import requests

from transcriber import Transcriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("transcribe_cli")

AUDIO_GLOB = ("*.mp3", "*.wav", "*.m4a", "*.mp4", "*.mov", "*.mkv")


def download_remote_file(url: str) -> str:
    """Download remote URL to a temporary file."""
    logger.info(f"Downloading remote file: {url}")
    ext = ".mp4"
    for candidate in (".mov", ".wav", ".mp3", ".m4a", ".mkv"):
        if candidate in url.lower():
            ext = candidate
            break

    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"transcribe-cli-{uuid.uuid4().hex[:8]}{ext}",
    )

    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
    logger.info(f"Downloaded successfully: {size_mb:.1f}MB -> {tmp_path}")
    return tmp_path


def parse_speaker_names(raw: str | None, speaker_count: int) -> list[str] | None:
    if not raw:
        return None
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        return None
    return names[: max(1, min(speaker_count, 2))]


def parse_interview_code(filename: str) -> str | None:
    """Extract interviewee code from filenames like 'TW - 25_02.mp3'."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^([A-Za-z]{1,6})\s*-\s*", stem)
    return match.group(1).upper() if match else None


def discover_audio_files(directory: str) -> list[str]:
    files: list[str] = []
    for pattern in AUDIO_GLOB:
        files.extend(glob.glob(os.path.join(directory, pattern)))
    return sorted({os.path.abspath(path) for path in files})


def save_transcript_markdown(
    save_path: str,
    *,
    title: str,
    local_path: str,
    result,
) -> None:
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"# Transcript: {title}\n\n")
        f.write(f"- **File**: `{os.path.basename(local_path)}`\n")
        f.write(f"- **Engine**: `{result.source} ({result.model})`\n")
        if result.confidence:
            f.write(f"- **LLM Confidence**: `{result.confidence}`\n")
            f.write(f"- **Needs Review**: `{result.needs_human_review}`\n")
            if result.review_reason:
                f.write(f"- **Review Reason**: {result.review_reason}\n")
        f.write("\n## Full Transcript\n\n")
        for seg in result.segments:
            f.write(
                f"**[{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.speaker}**: {seg.text}\n\n"
            )


def run_transcription(
    *,
    local_path: str,
    engine: str,
    reconcile: bool,
    speaker_count: int,
    speaker_names: list[str] | None,
    subject: str,
    title: str,
    venue: str,
    content_type: str,
    save_path: str | None,
) -> None:
    transcriber = Transcriber(
        speaker_count=speaker_count,
        speaker_names=speaker_names,
    )

    print("\n" + "=" * 80)
    print("RUNNING TRANSCRIBER PIPELINE")
    print("=" * 80)
    print(f"  File:       {os.path.basename(local_path)}")
    print(f"  Engine:     {engine}")
    print(f"  Reconcile:  {reconcile}")
    print(f"  Speakers:   {speaker_count} ({', '.join(transcriber.speaker_names)})")
    print(f"  Title:      {title}")
    print(f"  Subject:    {subject}")
    print("=" * 80 + "\n")

    start_time = time.time()
    result = transcriber.transcribe_video(
        video_path=local_path,
        engine=engine,
        force_audit=reconcile,
        horse_name=subject,
        venue=venue,
        content_type=content_type,
        subject=subject,
        title=title,
    )
    duration = time.time() - start_time

    print("\nSTATUS REPORT")
    print(f"  Duration:         {duration:.1f}s")
    print(f"  ASR Source:       {result.source}")
    print(f"  ASR Model:        {result.model}")

    if result.confidence:
        print(f"  Confidence:       {result.confidence.upper()}")
        print(f"  Review Required:  {result.needs_human_review}")
        if result.review_reason:
            print(f"  Review Reason:    {result.review_reason}")

    if result.reconciliation_changes:
        print("\nLLM RECONCILIATION EDITS:")
        for idx, change in enumerate(result.reconciliation_changes, 1):
            print(
                f"    {idx}. '{change.get('original')}' -> "
                f"'{change.get('corrected')}' ({change.get('reason')})"
            )

    print("\nTRANSCRIPT OUTPUT:")
    print("-" * 80)
    for seg in result.segments:
        time_str = f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s]"
        print(f"{time_str} {seg.speaker}: {seg.text}")
    print("-" * 80)

    if save_path:
        save_transcript_markdown(
            save_path,
            title=title,
            local_path=local_path,
            result=result,
        )
        logger.info(f"Transcript report saved to: {save_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Premium on-demand video and audio transcriber.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--file", help="Path to local video or audio file.")
    source.add_argument("--url", help="HTTP URL to remote video or audio file.")
    source.add_argument(
        "--dir",
        help="Directory of audio/video files to transcribe in batch.",
    )

    parser.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "google", "aistudio", "canary", "groq"],
        help="Speech-to-text engine to run.",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Force multi-engine parallel transcription and Ollama LLM consensus reconciliation.",
    )
    parser.add_argument(
        "--speakers",
        type=int,
        default=1,
        help="Expected number of speakers (1 or 2).",
    )
    parser.add_argument(
        "--speaker-names",
        help="Comma-separated speaker labels for diarization mapping (e.g. 'Kay,TW').",
    )
    parser.add_argument(
        "--interviewer",
        default="Kay",
        help="Interviewer name used in batch mode when deriving labels from filenames.",
    )
    parser.add_argument(
        "--subject",
        default="Unknown",
        help="Primary subject for prompting and reconciliation context.",
    )
    parser.add_argument(
        "--title",
        help="Human-readable transcript title. Defaults to subject.",
    )
    parser.add_argument(
        "--horse",
        help="Deprecated alias for --subject (Wexford ingest compatibility).",
    )
    parser.add_argument(
        "--venue",
        default="",
        help="Optional venue/context label.",
    )
    parser.add_argument(
        "--type",
        default="update",
        help="Content type metadata (use 'interview' for academic interviews).",
    )
    parser.add_argument(
        "--save",
        help="Optional local path to save the final transcript (markdown format).",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for batch transcript markdown files (defaults to --dir).",
    )
    parser.add_argument(
        "--check-google-auth",
        action="store_true",
        help="Print Google STT credential/quota status for work + personal accounts and exit.",
    )

    args = parser.parse_args()

    if args.check_google_auth:
        import json
        from google_stt_auth import credentials_status

        print(json.dumps(credentials_status(), indent=2))
        sys.exit(0)

    if not (args.file or args.url or args.dir):
        parser.error("one of --file, --url, or --dir is required")

    subject = args.horse or args.subject
    title = args.title or subject
    speaker_names = parse_speaker_names(args.speaker_names, args.speakers)

    if args.dir:
        input_dir = os.path.abspath(args.dir)
        output_dir = os.path.abspath(args.output_dir or input_dir)
        files = discover_audio_files(input_dir)
        if not files:
            logger.error(f"No audio/video files found in: {input_dir}")
            sys.exit(1)

        logger.info(f"Batch mode: {len(files)} files in {input_dir}")
        failures: list[str] = []

        for idx, local_path in enumerate(files, 1):
            code = parse_interview_code(local_path)
            if code:
                file_speaker_names = [args.interviewer, code]
                file_subject = f"{args.interviewer} and {code} interview"
                file_title = f"{args.interviewer} and {code}"
            else:
                file_speaker_names = speaker_names
                stem = os.path.splitext(os.path.basename(local_path))[0]
                file_subject = subject if subject != "Unknown" else stem
                file_title = title if title != subject or subject != "Unknown" else stem

            stem = os.path.splitext(os.path.basename(local_path))[0]
            save_path = os.path.join(output_dir, f"{stem}.md")

            print("\n" + "#" * 80)
            print(f"BATCH {idx}/{len(files)}: {os.path.basename(local_path)}")
            print("#" * 80)

            try:
                run_transcription(
                    local_path=local_path,
                    engine=args.engine,
                    reconcile=args.reconcile,
                    speaker_count=max(args.speakers, 2 if file_speaker_names and len(file_speaker_names) > 1 else args.speakers),
                    speaker_names=file_speaker_names or speaker_names,
                    subject=file_subject,
                    title=file_title,
                    venue=args.venue,
                    content_type=args.type,
                    save_path=save_path,
                )
            except Exception as exc:
                logger.error(f"Failed on {local_path}: {exc}")
                failures.append(local_path)

        if failures:
            logger.error(f"Batch completed with {len(failures)} failure(s).")
            for path in failures:
                logger.error(f"  - {path}")
            sys.exit(1)

        logger.info(f"Batch completed successfully: {len(files)} transcripts in {output_dir}")
        return

    local_path = None
    is_temp = False

    if args.url:
        try:
            local_path = download_remote_file(args.url)
            is_temp = True
        except Exception as exc:
            logger.error(f"Failed to download URL: {exc}")
            sys.exit(1)
    else:
        local_path = os.path.abspath(args.file)
        if not os.path.exists(local_path):
            logger.error(f"Local file does not exist: {local_path}")
            sys.exit(1)

    try:
        run_transcription(
            local_path=local_path,
            engine=args.engine,
            reconcile=args.reconcile,
            speaker_count=args.speakers,
            speaker_names=speaker_names,
            subject=subject,
            title=title,
            venue=args.venue,
            content_type=args.type,
            save_path=os.path.abspath(args.save) if args.save else None,
        )
    finally:
        if is_temp and os.path.exists(local_path):
            os.unlink(local_path)


if __name__ == "__main__":
    main()