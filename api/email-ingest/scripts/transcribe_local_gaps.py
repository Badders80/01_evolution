#!/usr/bin/env python3
"""Transcribe archived videos in _assets that lack a transcript JSON."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, INGEST_DIR)

from transcriber import Transcriber  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

VIDEOS_DIR = Path("/home/evo/evo_01/_assets/horses/prudentia/videos")
TRANSCRIPTS_DIR = Path("/home/evo/evo_01/_assets/horses/prudentia/transcripts")
OUTPUT_DIR = Path(INGEST_DIR) / "output"


def _has_transcript(content_date: str) -> bool:
    pattern = f"_{content_date}"
    for d in (TRANSCRIPTS_DIR, OUTPUT_DIR):
        if not d.exists():
            continue
        for f in d.glob("transcript_*"):
            if pattern in f.name:
                return True
    return False


def _parse_video_date(name: str) -> str | None:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_", name)
    return m.group(1) if m else None


def main() -> int:
    os.environ.setdefault("INGEST_SKIP_RECONCILE", "true")
    engine = os.getenv("INGEST_STT_ENGINE", "auto")
    transcriber = Transcriber(speaker_count=2)

    if not VIDEOS_DIR.exists():
        logger.error("Videos dir missing: %s", VIDEOS_DIR)
        return 1

    media_files = sorted(
        f for f in VIDEOS_DIR.iterdir()
        if f.suffix.lower() in {".mp4", ".mp3", ".m4a", ".mov"}
    )

    done = 0
    skipped = 0
    failed = 0

    for media in media_files:
        content_date = _parse_video_date(media.name)
        if not content_date:
            logger.warning("Skip (no date in name): %s", media.name)
            skipped += 1
            continue
        if _has_transcript(content_date):
            logger.info("Skip existing transcript: %s", content_date)
            skipped += 1
            continue

        logger.info("Transcribing %s ...", media.name)
        try:
            result = transcriber.transcribe_video(
                str(media),
                engine=engine,
                horse_name="Prudentia",
            )
            fname = f"transcript_Prudentia_{content_date}.json"
            payload = {
                "full_text": result.full_text,
                "segments": [
                    {"start_time": s.start_time, "end_time": s.end_time, "speaker": s.speaker, "text": s.text}
                    for s in result.segments
                ],
                "source": result.source,
                "model": getattr(result, "model", "unknown"),
                "speakers": result.speakers,
                "local_media": str(media),
            }
            out = OUTPUT_DIR / fname
            asset = TRANSCRIPTS_DIR / fname
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            with open(asset, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info("Saved: %s", fname)
            done += 1
        except Exception as exc:
            logger.error("Failed %s: %s", media.name, exc)
            failed += 1

    logger.info("Transcribe gaps: %d done, %d skipped, %d failed", done, skipped, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())