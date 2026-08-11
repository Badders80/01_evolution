"""Archive ingested media to the local asset vault before temp cleanup."""

from __future__ import annotations

import hashlib
import html as htmlmod
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

logger = logging.getLogger(__name__)

from horse_registry import normalize_horse_slug as _registry_slug

_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


def _email_ingest_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def get_assets_root() -> str:
    """Resolve _assets root (../../../_assets from api/email-ingest/)."""
    return os.path.normpath(os.path.join(_email_ingest_dir(), "..", "..", "..", "_assets"))


def get_workspace_root() -> str:
    """Resolve evo_01 workspace root (parent of _assets)."""
    return os.path.normpath(os.path.join(get_assets_root(), ".."))


def normalize_horse_slug(name: str) -> str:
    """Normalize horse name to a filesystem-safe slug with alias lookup."""
    return _registry_slug(name)


def infer_extension(url: str, fallback_path: Optional[str] = None) -> str:
    """Infer media extension from URL or local path."""
    for candidate in (url, fallback_path or ""):
        lower = candidate.lower()
        for ext in sorted(_AUDIO_EXTENSIONS | _VIDEO_EXTENSIONS, key=len, reverse=True):
            if ext in lower:
                return ext
    return ".mp4"


def infer_media_kind(url: str, fallback_path: Optional[str] = None) -> str:
    """Return 'audio' or 'video' based on URL/path extension."""
    ext = infer_extension(url, fallback_path)
    return "audio" if ext in _AUDIO_EXTENSIONS else "video"


def _collision_safe_path(target_dir: str, base_name: str, ext: str) -> str:
    """Return a non-colliding destination path, appending _2, _3, etc."""
    candidate = os.path.join(target_dir, f"{base_name}{ext}")
    if not os.path.exists(candidate):
        return candidate

    suffix = 2
    while True:
        candidate = os.path.join(target_dir, f"{base_name}_{suffix}{ext}")
        if not os.path.exists(candidate):
            return candidate
        suffix += 1


def _sanitize_label(label: str) -> str:
    cleaned = label.lower().strip()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:80] or "media"


def derive_original_label(
    *,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
    media_kind: str = "video",
    subject: Optional[str] = None,
) -> str:
    """Derive a stable 'original' slug for archive filenames from source metadata."""
    if source_url:
        lower = source_url.lower()
        vimeo_match = re.search(r"vimeo\.com/video/(\d+)", lower)
        if vimeo_match:
            return f"vimeo-{vimeo_match.group(1)}"

        prism_match = re.search(r"prism\.horse/media/([a-f0-9]+)", lower, re.I)
        if prism_match:
            return prism_match.group(1)

        if "mistable.com" in lower and "/site/report/" in lower:
            return "mistable-horse-report"

        path = urlparse(unquote(source_url)).path
        base = os.path.basename(path)
        if base:
            stem = os.path.splitext(base)[0]
            if stem and stem not in {"video", "media", "audio"}:
                return _sanitize_label(stem)

    if source_path:
        base = os.path.basename(source_path)
        if base and not base.startswith("email-video-"):
            stem = os.path.splitext(base)[0]
            if stem:
                return _sanitize_label(stem)

    if subject:
        trimmed = re.sub(r"\s+Horse\s+Report\s*$", "", subject, flags=re.IGNORECASE).strip()
        label = _sanitize_label(trimmed)
        if label:
            return label

    return _sanitize_label(media_kind)


def build_archive_basename(
    received_date: date,
    horse_slug: str,
    original_label: str,
) -> str:
    """Build shared asset stem: {received_date}_{horse}_{original}."""
    horse = normalize_horse_slug(horse_slug)
    original = _sanitize_label(original_label)
    return f"{received_date.isoformat()}_{horse}_{original}"


def asset_labels_for_parsed(parsed, *, source_path: Optional[str] = None) -> tuple[date, str, str]:
    """Return received_date, horse_slug, original_label for a parsed email."""
    horse_slug = normalize_horse_slug(parsed.horse_name)
    media_kind = infer_media_kind(parsed.video_url or "", source_path)
    original_label = derive_original_label(
        source_url=parsed.video_url,
        source_path=source_path,
        media_kind=media_kind,
        subject=parsed.subject,
    )
    return parsed.date_received.date(), horse_slug, original_label


def build_transcript_output_filename(
    received_date: date,
    horse_slug: str,
    original_label: str,
) -> str:
    """Staging filename in output/: transcript_{received}_{horse}_{original}.json"""
    return f"transcript_{build_archive_basename(received_date, horse_slug, original_label)}.json"


def build_transcript_asset_filename(
    received_date: date,
    horse_slug: str,
    original_label: str,
) -> str:
    """Canonical filename in _assets/.../transcripts/: {received}_{horse}_{original}.json"""
    return f"{build_archive_basename(received_date, horse_slug, original_label)}.json"


def parse_transcript_filename(filename: str) -> tuple[str, str, str] | None:
    """Parse transcript filename → (horse_slug, received_date, original_label)."""
    if not filename.endswith(".json"):
        return None

    core = filename[:-5]
    if core.startswith("transcript_"):
        core = core[len("transcript_") :]

    # New: {YYYY-MM-DD}_{horse-slug}_{original}
    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})_([a-z0-9_-]+)_(.+)$",
        core,
    )
    if match:
        return match.group(2), match.group(1), match.group(3)

    # Legacy: {horse-slug}_{YYYY-MM-DD}
    match = re.match(r"^(.+?)_(\d{4}-\d{2}-\d{2})$", core)
    if match:
        try:
            horse_slug = normalize_horse_slug(match.group(1).replace("_", " "))
        except ValueError:
            horse_slug = normalize_horse_slug(match.group(1))
        return horse_slug, match.group(2), "legacy"

    return None


_SKIP_IMAGE_KEYWORDS = (
    "email_banners",
    "logo.svg",
    "play_audio",
    "tracking.mistable",
    "unsubscribe",
    "/brand/",
    "app_store",
    "play_store",
    "owners-app-banner",
)


def extract_archivable_image_urls(body: str) -> list[tuple[str, str]]:
    """Extract content image URLs from email HTML with per-image original labels."""
    if not body:
        return []

    decoded = htmlmod.unescape(body)
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    for raw_url in re.findall(r"https?://[^\s\"'<>]+", decoded, re.IGNORECASE):
        url = raw_url.rstrip(".,;:!?)")
        lower = url.lower()
        if any(keyword in lower for keyword in _SKIP_IMAGE_KEYWORDS):
            continue
        image_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif")
        has_image_ext = any(lower.endswith(ext) for ext in image_exts) or any(
            ext in lower for ext in image_exts
        )
        if "vimeothumb" in lower or "/vimeothumb/" in lower:
            has_image_ext = True
        if not has_image_ext:
            continue
        if "vimeothumb" in lower or "/vimeothumb/" in lower:
            match = re.search(r"/id/(\d+)", lower)
            label = f"vimeo-thumb-{match.group(1)}" if match else "vimeo-thumb"
        else:
            path = urlparse(unquote(url)).path
            stem = os.path.splitext(os.path.basename(path))[0]
            label = _sanitize_label(stem) if stem else "image"

        if url in seen:
            continue
        seen.add(url)
        urls.append((url, label))

    return urls


def _asset_type_dir(horse_slug: str, asset_type: str) -> str:
    horse_slug = normalize_horse_slug(horse_slug)
    target_dir = os.path.join(get_assets_root(), "horses", horse_slug, asset_type)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def archive_target_dir(horse_slug: str) -> str:
    return _asset_type_dir(horse_slug, "videos")


def images_target_dir(horse_slug: str) -> str:
    return _asset_type_dir(horse_slug, "images")


def transcripts_target_dir(horse_slug: str) -> str:
    return _asset_type_dir(horse_slug, "transcripts")


def base_archive_dest(
    horse_slug: str,
    received_date: date,
    original_label: str,
    ext: str,
    *,
    asset_type: str = "videos",
) -> str:
    """Return canonical archive path without collision suffix."""
    target_dir = _asset_type_dir(horse_slug, asset_type)
    base_name = build_archive_basename(received_date, horse_slug, original_label)
    return os.path.join(target_dir, f"{base_name}{ext}")


def resolve_archive_dest(
    horse_slug: str,
    received_date: date,
    original_label: str,
    ext: str,
    *,
    asset_type: str = "videos",
) -> str:
    """Return absolute destination path for archived assets."""
    target_dir = _asset_type_dir(horse_slug, asset_type)
    base_name = build_archive_basename(received_date, horse_slug, original_label)
    return _collision_safe_path(target_dir, base_name, ext)


def to_relative_asset_path(abs_path: str) -> str:
    """Convert absolute path to _assets/... relative form for ledger metadata."""
    workspace_root = get_workspace_root()
    rel = os.path.relpath(abs_path, workspace_root)
    if rel.startswith(".."):
        assets_root = get_assets_root()
        rel = os.path.relpath(abs_path, assets_root)
        return os.path.join("_assets", rel)
    return rel.replace(os.sep, "/")


def _files_match(source_path: str, dest_path: str) -> bool:
    if not os.path.exists(dest_path):
        return False
    if os.path.getsize(dest_path) <= 0:
        return False
    return os.path.getsize(source_path) == os.path.getsize(dest_path)


def archive_media(
    source_path: str,
    horse_slug: str,
    received_date: date,
    original_label: str,
    *,
    source_cdn_url: Optional[str] = None,
    force: bool = False,
) -> str:
    """Copy media to _assets/horses/{slug}/videos/. Returns destination path."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source media not found: {source_path}")

    ext = infer_extension(source_cdn_url or "", source_path)
    dest = resolve_archive_dest(horse_slug, received_date, original_label, ext)

    if not force and _files_match(source_path, dest):
        logger.info("Archive exists with matching size, skipping copy: %s", dest)
        return dest

    if os.path.exists(dest) and os.path.getsize(dest) > 0 and not force:
        # Different size — collision path already chosen by resolve_archive_dest
        pass

    shutil.copy2(source_path, dest)
    logger.info("Archived media → %s", dest)
    return dest


def archive_enabled() -> bool:
    return os.getenv("INGEST_ARCHIVE_MEDIA", "true").lower() == "true"


def delete_temp_enabled() -> bool:
    return os.getenv("INGEST_DELETE_TEMP", "true").lower() == "true"


def archive_from_parsed(
    source_path: str,
    horse_slug: str,
    parsed,
    *,
    force: bool = False,
) -> str:
    """Archive using email received date and source-derived original label."""
    received_date, _, original_label = asset_labels_for_parsed(parsed, source_path=source_path)
    return archive_media(
        source_path,
        horse_slug,
        received_date,
        original_label,
        source_cdn_url=parsed.video_url,
        force=force,
    )


def archive_image_url(
    image_url: str,
    horse_slug: str,
    received_date: date,
    original_label: str,
    *,
    force: bool = False,
) -> str:
    """Download and archive an email image to _assets/horses/{slug}/images/."""
    ext = infer_extension(image_url)
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    dest = resolve_archive_dest(
        horse_slug,
        received_date,
        original_label,
        ext,
        asset_type="images",
    )

    if not force and os.path.exists(dest) and os.path.getsize(dest) > 0:
        logger.info("Image archive exists, skipping download: %s", dest)
        return dest

    logger.info("Downloading image: %s", image_url[:100])
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        if not force and _files_match(tmp_path, dest):
            logger.info("Image archive matches existing file: %s", dest)
            return dest
        shutil.copy2(tmp_path, dest)
        logger.info("Archived image → %s", dest)
        return dest
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def archive_images_from_parsed(parsed, *, body_html: str = "") -> list[str]:
    """Archive content images from email HTML using the shared naming convention."""
    if not archive_enabled():
        return []

    received_date, horse_slug, _ = asset_labels_for_parsed(parsed)
    archived: list[str] = []
    for image_url, image_label in extract_archivable_image_urls(body_html):
        try:
            path = archive_image_url(
                image_url,
                horse_slug,
                received_date,
                image_label,
            )
            archived.append(path)
        except Exception as exc:
            logger.warning("Failed to archive image %s: %s", image_url[:80], exc)
    return archived


def save_transcript_json(
    transcript,
    parsed,
    *,
    output_dir: str,
    source_path: Optional[str] = None,
) -> str:
    """Save transcript JSON to output/ using shared asset naming."""
    received_date, horse_slug, original_label = asset_labels_for_parsed(
        parsed,
        source_path=source_path,
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(
        output_dir,
        build_transcript_output_filename(received_date, horse_slug, original_label),
    )
    segments_list = [
        {
            "start_time": s.start_time,
            "end_time": s.end_time,
            "speaker": s.speaker,
            "text": s.text,
        }
        for s in transcript.segments
    ]
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "full_text": transcript.full_text,
                "segments": segments_list,
                "source": transcript.source,
                "model": getattr(transcript, "model", "unknown"),
                "speakers": transcript.speakers,
                "horse_slug": horse_slug,
                "received_date": received_date.isoformat(),
                "original_label": original_label,
                "email_subject": parsed.subject,
            },
            handle,
            indent=2,
        )
    return output_path


def archive_and_cleanup_temp(
    source_path: str,
    *,
    horse_slug: str,
    parsed,
    force_archive: bool = False,
) -> Optional[str]:
    """Archive downloaded media (if enabled) then delete temp file. Returns archive path."""
    archived_path: Optional[str] = None

    if archive_enabled():
        archived_path = archive_from_parsed(
            source_path,
            horse_slug,
            parsed,
            force=force_archive,
        )

    if delete_temp_enabled() and os.path.exists(source_path):
        os.unlink(source_path)
        logger.info("Cleaned up temp media file: %s", source_path)

    return archived_path


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_content_date(value: str) -> Optional[date]:
    """Parse ISO date or datetime string to date."""
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return None