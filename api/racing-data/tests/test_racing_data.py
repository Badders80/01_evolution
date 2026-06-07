"""
Tests for racing-data module.

Run: cd api && pytest racing-data/tests/ -v
"""

import pytest
from datetime import date

# Import from sibling directories (mimic how Cloud Functions resolves)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import RaceResult, HorseRacingSummary


def test_race_result_model():
    """RaceResult validates required fields."""
    race = RaceResult(
        horse_microchip="985125000126462",
        loveracing_id=427416,
        race_date=date(2024, 11, 9),
        venue="Te Rapa",
        race_name="Maiden 1200",
        finish_position=1,
        prize_money_nzd=12500,
        stake_type="win",
    )
    assert race.venue == "Te Rapa"
    assert race.prize_money_nzd == 12500


def test_race_result_invalid_microchip():
    """Microchip must be 15 digits."""
    with pytest.raises(Exception):
        RaceResult(
            horse_microchip="bad",
            loveracing_id=1,
            race_date=date(2024, 1, 1),
            venue="Test",
            race_name="Test",
            finish_position=1,
            prize_money_nzd=0,
            stake_type="win",
        )


def test_horse_racing_summary():
    """Summary computes from races."""
    summary = HorseRacingSummary(
        horse_microchip="985125000126462",
        loveracing_id=427416,
        total_starts=18,
        total_wins=3,
        total_earnings_nzd=84750,
    )
    assert summary.total_starts == 18
    assert summary.total_wins == 3


# ── Engine tests (require API keys / env) ───────────────────────
# Marked as integration tests — skipped in CI without keys.

@pytest.mark.skipif(
    not os.getenv("WEBCLAW_API_KEY"),
    reason="WEBCLAW_API_KEY not configured",
)
def test_webclaw_engine_fetch():
    from racing_data.engines.webclaw import WebclawEngine
    engine = WebclawEngine()
    # Use a simple public page for smoke test
    html = engine.fetch("https://example.com/")
    assert len(html) > 100


@pytest.mark.skip(reason="Scrapling requires venv activation")
def test_scrapling_engine_fetch():
    from racing_data.engines.scrapling import ScraplingEngine
    engine = ScraplingEngine()
    html = engine.fetch("https://example.com/")
    assert len(html) > 100
