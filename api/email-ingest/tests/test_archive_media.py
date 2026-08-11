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
    build_transcript_output_filename,
    derive_original_label,
    extract_archivable_image_urls,
    infer_extension,
    infer_media_kind,
    normalize_horse_slug,
    parse_transcript_filename,
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
    assert (
        build_archive_basename(date(2026, 5, 28), "turn-me-loose-x-yearn", "vimeo-1196163233")
        == "2026-05-28_turn-me-loose-x-yearn_vimeo-1196163233"
    )


def test_derive_original_label_vimeo():
    url = "https://player.vimeo.com/video/1196163233?h=abc"
    assert derive_original_label(source_url=url) == "vimeo-1196163233"


def test_build_transcript_output_filename():
    assert (
        build_transcript_output_filename(date(2026, 5, 28), "turn-me-loose-x-yearn", "vimeo-1196163233")
        == "transcript_2026-05-28_turn-me-loose-x-yearn_vimeo-1196163233.json"
    )


def test_parse_transcript_filename_new_and_legacy():
    assert parse_transcript_filename(
        "transcript_2026-05-28_turn-me-loose-x-yearn_vimeo-1196163233.json"
    ) == ("turn-me-loose-x-yearn", "2026-05-28", "vimeo-1196163233")
    assert parse_transcript_filename("transcript_turn-me-loose-x-yearn_2026-05-28.json") == (
        "turn-me-loose-x-yearn",
        "2026-05-28",
        "legacy",
    )


def test_extract_archivable_image_urls_skips_banners():
    html = (
        '<img src="https://media.mistable.com/live/email_banners/banner.png">'
        '<img src="https://mistable.com/site/vimeoThumb/id/1196163233?img=thumb.jpg">'
    )
    urls = extract_archivable_image_urls(html)
    assert len(urls) == 1
    assert urls[0][1] == "vimeo-thumb-1196163233"


def test_derive_original_label_subject_fallback():
    assert (
        derive_original_label(subject="Turn Me Loose - Yearn 23F Horse Report")
        == "turn-me-loose-yearn-23f"
    )


def test_resolve_archive_dest_collision(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))

    dest1 = resolve_archive_dest(
        "prudentia",
        date(2026, 6, 22),
        "abc123",
        ".mp4",
    )
    Path(dest1).parent.mkdir(parents=True, exist_ok=True)
    Path(dest1).write_bytes(b"existing")

    dest2 = resolve_archive_dest(
        "prudentia",
        date(2026, 6, 22),
        "abc123",
        ".mp4",
    )
    assert dest2.endswith("2026-06-22_prudentia_abc123_2.mp4")


def test_archive_media_skips_matching_size(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))
    monkeypatch.setattr("archive_media.get_workspace_root", lambda: str(tmp_path))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as src:
        src.write(b"video-bytes")
        src_path = src.name

    try:
        dest = archive_media(src_path, "prudentia", date(2026, 6, 22), "abc123")
        assert os.path.exists(dest)
        assert Path(dest).read_bytes() == b"video-bytes"

        mtime_before = os.path.getmtime(dest)
        archive_media(src_path, "prudentia", date(2026, 6, 22), "abc123")
        assert os.path.getmtime(dest) == mtime_before
    finally:
        os.unlink(src_path)


def test_to_relative_asset_path(monkeypatch, tmp_path):
    assets_root = tmp_path / "_assets"
    monkeypatch.setattr("archive_media.get_assets_root", lambda: str(assets_root))
    monkeypatch.setattr("archive_media.get_workspace_root", lambda: str(tmp_path))

    abs_path = str(
        assets_root / "horses" / "prudentia" / "videos" / "2026-06-22_prudentia_abc123.mp4"
    )
    assert (
        to_relative_asset_path(abs_path)
        == "_assets/horses/prudentia/videos/2026-06-22_prudentia_abc123.mp4"
    )