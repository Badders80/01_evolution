"""Tests for archive_media path safety and naming."""

from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

from archive_media import (
    archive_media,
    build_archive_basename,
    infer_extension,
    infer_media_kind,
    normalize_horse_slug,
    resolve_archive_dest,
    to_relative_asset_path,
)


def test_normalize_horse_slug_aliases():
    assert normalize_horse_slug("Audio Update: Prudentia") == "prudentia"
    assert normalize_horse_slug("Prudentia") == "prudentia"


def test_normalize_horse_slug_rejects_traversal():
    with pytest.raises(ValueError):
        normalize_horse_slug("../etc/passwd")
    with pytest.raises(ValueError):
        normalize_horse_slug("foo/bar")


def test_infer_media_kind_and_extension():
    assert infer_media_kind("https://cdn.example/media/foo.mp3") == "audio"
    assert infer_extension("https://cdn.example/media/foo.mp3") == ".mp3"
    assert infer_media_kind("https://cdn.example/media/foo.mp4") == "video"
    assert infer_extension("https://cdn.example/media/foo.m4a") == ".m4a"


def test_build_archive_basename():
    assert build_archive_basename(date(2026, 6, 22), "video") == "2026-06-22_video"


def test_resolve_archive_dest_collision(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))

    dest1 = resolve_archive_dest("prudentia", date(2026, 6, 22), "video", ".mp4")
    Path(dest1).parent.mkdir(parents=True, exist_ok=True)
    Path(dest1).write_bytes(b"existing")

    dest2 = resolve_archive_dest("prudentia", date(2026, 6, 22), "video", ".mp4")
    assert dest2.endswith("2026-06-22_video_2.mp4")


def test_archive_media_skips_matching_size(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))
    monkeypatch.setattr("archive_media.get_workspace_root", lambda: str(tmp_path))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as src:
        src.write(b"video-bytes")
        src_path = src.name

    try:
        dest = archive_media(src_path, "prudentia", date(2026, 6, 22), "video")
        assert os.path.exists(dest)
        assert Path(dest).read_bytes() == b"video-bytes"

        # Second call with same content should skip copy
        mtime_before = os.path.getmtime(dest)
        archive_media(src_path, "prudentia", date(2026, 6, 22), "video")
        assert os.path.getmtime(dest) == mtime_before
    finally:
        os.unlink(src_path)


def test_to_relative_asset_path(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))
    monkeypatch.setattr("archive_media.get_workspace_root", lambda: str(tmp_path))

    abs_path = str(assets_root / "horses" / "prudentia" / "videos" / "2026-06-22_video.mp4")
    assert to_relative_asset_path(abs_path) == "_assets/horses/prudentia/videos/2026-06-22_video.mp4"