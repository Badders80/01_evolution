"""
Tests for loveracing.nz adapter parsing logic.

Run: PYTHONPATH=/home/evo/evo_01/01_evolution/api python3 -m pytest api/racing-data/tests/test_loveracing_adapter.py -v
"""

import pytest
import sys
import os
from datetime import date

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.loveracing import (
    parse_breeding_page,
    parse_race_history,
    compute_horse_racing_summary,
    breeding_url,
    race_history_url,
    _parse_placing,
    _parse_race_date,
    _parse_distance,
    _parse_track_condition,
    _parse_money,
    _extract_detail,
    _parse_colour_sex,
    _parse_nz_date,
    _name_to_slug,
)


# ── Test Fixtures ───────────────────────────────────────────────────

SAMPLE_BREEDING_HTML = """
<html>
<body>
    <h2 class="horse-name">Prudentia (NZ) 2021</h2>
    <ul class="no-bullets horse-attr">
        <li>Born: 15/09/2021</li>
        <li>Age: 3</li>
        <li>Sire: <a href="/Breeding/12345/PROISIR-AUS-2009.aspx">PROISIR (AUS) 2009</a></li>
        <li>Dam: <a href="/Breeding/67890/LITTLE-BIT-IRISH-NZ-2012.aspx">LITTLE BIT IRISH (NZ) 2012</a></li>
        <li>Bay Mare</li>
    </ul>
    <div class="content-block">
        <strong>Microchip:</strong> 985125000126462<br>
        <strong>Life no:</strong> NZ00427416<br>
        <strong>Left shoulder:</strong> KB INSIDE CIRCLE<br>
        <strong>Right shoulder:</strong> 85 OVER 1<br>
        <strong>Breeder:</strong> Golden Eye Trust<br>
        <strong>Trainer:</strong> Stephen Grey<br>
        <strong>PV:</strong> Y<br>
        <strong>BT:</strong> N<br>
    </div>
</body>
</html>
"""

SAMPLE_RACE_HISTORY_HTML = """
<html>
<body>
    <table class="table-indepth">
        <tr>
            <td>1-12</td>
            <td>30 May 26</td>
            <td>1200m</td>
            <td>ROY AND PAM BROWNE SPRINT</td>
            <td><a href="#">Video</a></td>
            <td>$35,000</td>
        </tr>
        <tr class="odd">
            <td>WAIK  Soft5</td>
            <td>Maiden</td>
            <td>Raced handy, strong finish</td>
            <td>Sam Spratt</td>
            <td>$12,500</td>
        </tr>
        <tr>
            <td>Bar: 5 SP: $3.20 Rtg: 65 Wgt: 56.5 Raceday Gear: Approved Plates</td>
        </tr>
    </table>
    <table class="table-indepth">
        <tr>
            <td>3-14</td>
            <td>15 Apr 26</td>
            <td>1400m</td>
            <td>RATING 65 BENCHMARK</td>
            <td><a href="#">Video</a></td>
            <td>$40,000</td>
        </tr>
        <tr class="odd">
            <td>ELLE  Good4</td>
            <td>Rating 65 Benchmark*</td>
            <td>Midfield, angled wide, solid</td>
            <td>Masa Hashizume</td>
            <td>$3,150</td>
        </tr>
        <tr>
            <td>Bar: 3 SP: $8.50 Rtg: 65 Wgt: 57.0 Raceday Gear: Lugging Bit</td>
        </tr>
    </table>
    <table class="table-indepth">
        <tr>
            <td>U-10</td>
            <td>2 Mar 26</td>
            <td>1600m</td>
            <td>OPEN HCP</td>
            <td><a href="#">Video</a></td>
            <td>$50,000</td>
        </tr>
        <tr class="odd">
            <td>PUKE  Heavy8</td>
            <td>Open</td>
            <td>Never in contention</td>
            <td>Joe Doyle</td>
            <td>$0</td>
        </tr>
        <tr>
            <td>Bar: 8 SP: $15.00 Rtg: 72 Wgt: 54.0 Raceday Gear: Approved Plates</td>
        </tr>
    </table>
</body>
</html>
"""


# ── Unit Tests for Helper Functions ────────────────────────────────

def test_parse_placing_win():
    pos, field = _parse_placing("1-14")
    assert pos == 1
    assert field == 14


def test_parse_placing_unplaced():
    pos, field = _parse_placing("U-8")
    assert pos == 0  # Unplaced = 0
    assert field == 8


def test_parse_placing_regular():
    pos, field = _parse_placing("5-13")
    assert pos == 5
    assert field == 13


def test_parse_race_date():
    d = _parse_race_date("30 May 26")
    assert d == date(2026, 5, 30)


def test_parse_distance():
    assert _parse_distance("1200m") == 1200
    assert _parse_distance("  1400m  ") == 1400


def test_parse_track_condition():
    venue, condition = _parse_track_condition("WAIK  Soft5")
    assert venue == "WAIK"
    assert condition == "Soft5"

    venue, condition = _parse_track_condition("ELLE  Good4")
    assert venue == "ELLE"
    assert condition == "Good4"


def test_parse_money():
    assert _parse_money("$12,500") == 1250000  # cents
    assert _parse_money("$3,150") == 315000
    assert _parse_money("$0") == 0
    assert _parse_money("") == 0


def test_extract_detail():
    text = "Bar: 5 SP: $3.20 Rtg: 65 Wgt: 56.5 Raceday Gear: Approved Plates"
    assert _extract_detail(text, "Bar:") == "5"
    assert _extract_detail(text, "SP:") == "$3.20"
    assert _extract_detail(text, "Rtg:") == "65"
    assert _extract_detail(text, "Wgt:") == "56.5"
    assert _extract_detail(text, "Raceday Gear:") == "Approved"


def test_parse_colour_sex():
    colour, sex = _parse_colour_sex("Bay Mare")
    assert colour == "Bay"
    assert sex == "mare"

    colour, sex = _parse_colour_sex("Chestnut Gelding")
    assert colour == "Chestnut"
    assert sex == "gelding"


def test_parse_nz_date():
    d = _parse_nz_date("15/09/2021")
    assert d == date(2021, 9, 15)


def test_name_to_slug():
    assert _name_to_slug("Prudentia (NZ) 2021") == "Prudentia-NZ-2021"
    assert _name_to_slug("First Gear (AUS) 2020") == "First-Gear-AUS-2020"


# ── Integration Tests for Full Parsing ──────────────────────────────

def test_parse_breeding_page():
    """Test parsing breeding page HTML into LoveracingRef dict."""
    result = parse_breeding_page(SAMPLE_BREEDING_HTML, 427416)

    assert result["loveracing_id"] == 427416
    assert result["name"] == "Prudentia (NZ) 2021"
    assert result["name_slug"] == "Prudentia-NZ-2021"
    assert result["microchip"] == "985125000126462"
    assert result["life_number"] == "NZ00427416"
    assert result["foaling_date"] == date(2021, 9, 15)
    assert result["sex"] == "mare"
    assert result["colour"] == "Bay"
    assert result["sire_name"] == "PROISIR (AUS) 2009"
    assert result["dam_name"] == "LITTLE BIT IRISH (NZ) 2012"
    assert result["pv"] is True
    assert result["bt"] is False
    assert result["breeder"] == "Golden Eye Trust"
    assert result["left_shoulder_brand"] == "KB INSIDE CIRCLE"
    assert result["right_shoulder_brand"] == "85 OVER 1"
    assert result["trainer"] == "Stephen Grey"


def test_parse_race_history():
    """Test parsing race history HTML into RaceResult list."""
    races = parse_race_history(SAMPLE_RACE_HISTORY_HTML, "985125000126462", 427416)

    assert len(races) == 3

    # Race 1: Win
    r1 = races[0]
    assert r1["horse_microchip"] == "985125000126462"
    assert r1["loveracing_id"] == 427416
    assert r1["race_date"] == date(2026, 5, 30)
    assert r1["venue"] == "WAIK"
    assert r1["race_name"] == "ROY AND PAM BROWNE SPRINT"
    assert r1["race_class"] == "Maiden"
    assert r1["distance_metres"] == 1200
    assert r1["field_size"] == 12
    assert r1["barrier"] == 5
    assert r1["jockey"] == "Sam Spratt"
    assert r1["finish_position"] == 1
    assert r1["prize_money_nzd"] == 1250000  # $12,500 in cents
    assert r1["starting_price"] == "$3.20"
    assert r1["rating"] == 65
    assert r1["weight"] == 56.5
    assert r1["gear"] == "Approved"
    assert r1["stake_type"] == "win"

    # Race 2: Place (3rd)
    r2 = races[1]
    assert r2["race_date"] == date(2026, 4, 15)
    assert r2["venue"] == "ELLE"
    assert r2["race_name"] == "RATING 65 BENCHMARK"
    assert r2["finish_position"] == 3
    assert r2["prize_money_nzd"] == 315000  # $3,150 in cents
    assert r2["stake_type"] == "place"

    # Race 3: Unplaced
    r3 = races[2]
    assert r3["race_date"] == date(2026, 3, 2)
    assert r3["venue"] == "PUKE"
    assert r3["finish_position"] == 0  # Unplaced
    assert r3["prize_money_nzd"] == 0
    assert r3["stake_type"] == "unplaced"


def test_compute_horse_racing_summary():
    """Test computing summary from parsed races."""
    races = parse_race_history(SAMPLE_RACE_HISTORY_HTML, "985125000126462", 427416)
    summary = compute_horse_racing_summary(
        races, "985125000126462", 427416, foaling_date=date(2021, 9, 15)
    )

    assert summary["horse_microchip"] == "985125000126462"
    assert summary["loveracing_id"] == 427416
    assert summary["total_starts"] == 3
    assert summary["total_wins"] == 1
    assert summary["total_places"] == 1  # 1 third place
    assert summary["total_earnings_nzd"] == 1565000  # 1,250,000 + 315,000
    assert summary["earnings_by_age"]["4"] == 1565000  # Age 4 in 2026
    assert "Maiden" in summary["earnings_by_class"]
    assert "Rating 65 Benchmark*" in summary["earnings_by_class"]
    assert "Open" in summary["earnings_by_class"]
    assert summary["first_start_date"] == date(2026, 3, 2)
    assert summary["last_start_date"] == date(2026, 5, 30)


# ── URL Builder Tests ──────────────────────────────────────────────

def test_breeding_url():
    url = breeding_url(427416, "Prudentia-NZ-2021")
    assert url == "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"


def test_race_history_url():
    url = race_history_url(427416)
    assert url == "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&DisplayContext=Modal01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])