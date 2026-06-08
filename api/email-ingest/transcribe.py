#!/usr/bin/env python3
"""
transcribe.py
Standalone premium developer CLI for transcribing local or remote video/audio files.
Supports selecting engines, forcing audits/reconciliation, and saving formatted output.
"""

import os
import sys
import argparse
import logging
import tempfile
import uuid
import time
import requests

from transcriber import Transcriber

# Set up logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("transcribe_cli")


def download_remote_file(url: str) -> str:
    """Download remote URL to a temporary file."""
    logger.info(f"Downloading remote file: {url}")
    ext = ".mp4"
    if ".mov" in url.lower():
        ext = ".mov"
    elif ".wav" in url.lower():
        ext = ".wav"
    elif ".mp3" in url.lower():
        ext = ".mp3"
        
    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"transcribe-cli-{uuid.uuid4().hex[:8]}{ext}"
    )
    
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            
    size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
    logger.info(f"Downloaded successfully: {size_mb:.1f}MB -> {tmp_path}")
    return tmp_path


def main():
    parser = argparse.ArgumentParser(
        description="Premium on-demand video and audio transcriber.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to local video or audio file.")
    group.add_argument("--url", help="HTTP URL to remote video or audio file.")
    
    parser.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "google", "aistudio", "canary", "groq"],
        help="Speech-to-text engine to run."
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Force multi-engine parallel transcription and Ollama LLM consensus reconciliation."
    )
    parser.add_argument(
        "--speakers",
        type=int,
        default=1,
        help="Expected number of speakers (1 or 2)."
    )
    parser.add_argument(
        "--horse",
        default="Unknown",
        help="Horse name metadata for context and dictionary mapping."
    )
    parser.add_argument(
        "--venue",
        default="Te Rapa",
        help="Venue name metadata for context."
    )
    parser.add_argument(
        "--type",
        default="update",
        help="Content type metadata for context."
    )
    parser.add_argument(
        "--save",
        help="Optional local path to save the final transcript (markdown format)."
    )

    args = parser.parse_args()

    # Determine input path
    local_path = None
    is_temp = False
    
    if args.url:
        try:
            local_path = download_remote_file(args.url)
            is_temp = True
        except Exception as e:
            logger.error(f"Failed to download URL: {e}")
            sys.exit(1)
    else:
        local_path = os.path.abspath(args.file)
        if not os.path.exists(local_path):
            logger.error(f"Local file does not exist: {local_path}")
            sys.exit(1)

    try:
        # Initialize and run pipeline
        transcriber = Transcriber(speaker_count=args.speakers)
        
        print("\n" + "="*80)
        print(f"🎙️  RUNNING TRANSCRIBER PIPELINE")
        print("="*80)
        print(f"  File:       {os.path.basename(local_path)}")
        print(f"  Engine:     {args.engine}")
        print(f"  Reconcile:  {args.reconcile}")
        print(f"  Speakers:   {args.speakers}")
        print(f"  Horse:      {args.horse}")
        print(f"  Venue:      {args.venue}")
        print("="*80 + "\n")

        start_time = time.time()
        result = transcriber.transcribe_video(
            video_path=local_path,
            engine=args.engine,
            force_audit=args.reconcile,
            horse_name=args.horse,
            venue=args.venue,
            content_type=args.type
        )
        duration = time.time() - start_time

        # Print beautiful terminal report
        print("\n" + "✨" + " STATUS REPORT " + "✨")
        print(f"  Duration:         {duration:.1f}s")
        print(f"  ASR Source:       {result.source}")
        print(f"  ASR Model:        {result.model}")
        
        if result.confidence:
            print(f"  Confidence:       {result.confidence.upper()}")
            print(f"  Review Required:  {result.needs_human_review}")
            if result.review_reason:
                print(f"  Review Reason:    {result.review_reason}")

        # Print reconciliation changes if available
        if result.reconciliation_changes:
            print("\n" + "📝" + " LLM RECONCILIATION EDITS:")
            for idx, change in enumerate(result.reconciliation_changes, 1):
                print(f"    {idx}. '{change.get('original')}' ➔ '{change.get('corrected')}' ({change.get('reason')})")

        print("\n" + "💬" + " TRANSCRIPT OUTPUT:")
        print("-"*80)
        for seg in result.segments:
            time_str = f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s]"
            print(f"{time_str} \033[1m{seg.speaker}\033[0m: {seg.text}")
        print("-"*80)
        
        print("\n" + "📄" + " FULL CONCATENATED TEXT:")
        print(result.full_text)
        print("="*80 + "\n")

        # Save to markdown if requested
        if args.save:
            save_path = os.path.abspath(args.save)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, "w") as f:
                f.write(f"# Transcript Report: {args.horse} - {args.venue}\n\n")
                f.write(f"- **File**: `{os.path.basename(local_path)}`\n")
                f.write(f"- **Engine**: `{result.source} ({result.model})`\n")
                if result.confidence:
                    f.write(f"- **LLM Confidence**: `{result.confidence}`\n")
                    f.write(f"- **Needs Review**: `{result.needs_human_review}`\n")
                    if result.review_reason:
                        f.write(f"- **Review Reason**: {result.review_reason}\n")
                f.write("\n## Full Transcript\n\n")
                for seg in result.segments:
                    f.write(f"**[{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.speaker}**: {seg.text}\n\n")
                    
            logger.info(f"Transcript report saved to: {save_path}")

    finally:
        if is_temp and os.path.exists(local_path):
            os.unlink(local_path)


if __name__ == "__main__":
    main()
