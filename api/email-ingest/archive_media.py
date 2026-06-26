"""Archive ingested media to the local asset vault before temp cleanup."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

HORSE_ALIASES = {
    "audio update: prudentia": "prudentia",
    "prudentia": "prudentia",
    "prudentia (nz)": "prudentia",
}

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
    key = name.lower().strip()
    if ".." in key or "/" in key or "\\" in key:
        raise ValueError(f"Invalid horse slug from name: {name!r}")

    if key in HORSE_ALIASES:
        return HORSE_ALIASES[key]

    slug = key.replace(" ", "-")
    if not re.match(r"^[a-z0-9_-]+$", slug):
        slug = re.sub(r"[^a-z0-9_-]", "", slug)
    if not slug or ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError(f"Invalid horse slug from name: {name!r}")
    return slug


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


def build_archive_basename(content_date: date, media_kind: str) -> str:
    return f"{content_date.isoformat()}_{media_kind}"


def archive_target_dir(horse_slug: str) -> str:
    horse_slug = normalize_horse_slug(horse_slug)
    target_dir = os.path.join(get_assets_root(), "horses", horse_slug, "videos")
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def base_archive_dest(
    horse_slug: str,
    content_date: date,
    media_kind: str,
    ext: str,
) -> str:
    """Return canonical archive path without collision suffix."""
    target_dir = archive_target_dir(horse_slug)
    base_name = build_archive_basename(content_date, media_kind)
    return os.path.join(target_dir, f"{base_name}{ext}")


def resolve_archive_dest(
    horse_slug: str,
    content_date: date,
    media_kind: str,
    ext: str,
) -> str:
    """Return absolute destination path for archived media."""
    target_dir = archive_target_dir(horse_slug)
    base_name = build_archive_basename(content_date, media_kind)
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
    content_date: date,
    media_kind: str,
    *,
    source_cdn_url: Optional[str] = None,
    force: bool = False,
) -> str:
    """Copy media to _assets/horses/{slug}/videos/. Returns destination path."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source media not found: {source_path}")

    ext = infer_extension(source_cdn_url or "", source_path)
    dest = resolve_archive_dest(horse_slug, content_date, media_kind, ext)

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


def archive_and_cleanup_temp(
    source_path: str,
    *,
    horse_slug: str,
    content_date: date,
    source_cdn_url: Optional[str] = None,
    force_archive: bool = False,
) -> Optional[str]:
    """Archive downloaded media (if enabled) then delete temp file. Returns archive path."""
    archived_path: Optional[str] = None
    media_kind = infer_media_kind(source_cdn_url or "", source_path)

    if archive_enabled():
        archived_path = archive_media(
            source_path,
            horse_slug,
            content_date,
            media_kind,
            source_cdn_url=source_cdn_url,
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