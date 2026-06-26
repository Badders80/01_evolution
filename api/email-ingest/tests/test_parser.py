"""Tests for email parser horse/audio extraction."""

from datetime import datetime, timezone

from parser import _extract_date, _extract_horse_name, _extract_video_url, parse_email


def test_audio_update_horse_name():
    assert _extract_horse_name("Audio Update: Prudentia") == "Prudentia"


def test_video_update_colon_format():
    assert _extract_horse_name("Video Update: Prudentia") == "Prudentia"


def test_parse_email_strips_html():
    raw = {
        "message_id": "<test@example.com>",
        "subject": "Race Acceptance - Prudentia - 27 Jun - Tauranga",
        "from_address": "info@wexfordstables.co.nz",
        "date_received": datetime(2026, 6, 23, tzinfo=timezone.utc),
        "body_text": "<html><body><p>Date: 24 Jun 2026</p><p>Accepted for Tauranga</p></body></html>",
        "body_html": "",
    }
    parsed = parse_email(raw)
    assert parsed.horse_name == "Prudentia"
    assert "<html" not in parsed.body_text.lower()


def test_extract_date_from_race_subject_when_body_missing():
    received = datetime(2026, 3, 15, tzinfo=timezone.utc)
    parsed_date = _extract_date(
        "Accepted for Tauranga",
        subject="Race Acceptance - Prudentia - 14 Mar - Tauranga",
        date_received=received,
    )
    assert parsed_date.isoformat() == "2026-03-14"


def test_extract_video_url_prefers_prism_over_wrapper():
    body = (
        "Watch: https://urldefense.proofpoint.com/v2/url?u=https%3A%2F%2Fjunk.mp4 "
        "or https://cdn2.prism.horse/media/abc123/video.mp4"
    )
    assert _extract_video_url(body) == "https://cdn2.prism.horse/media/abc123/video.mp4"