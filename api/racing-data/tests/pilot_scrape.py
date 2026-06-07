#!/usr/bin/env python3
"""
Pilot scrape script for Prudentia (427416) and First Gear (428364).

Run: PYTHONPATH=/home/evo/evo_01/01_evolution/api python3 api/racing-data/tests/pilot_scrape.py
"""

import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters import loveracing as adapter
from engines.scrapling import ScraplingEngine


def test_horse(loveracing_id: int, name: str):
    """Test full scrape pipeline for a horse."""
    print(f"\n{'='*60}")
    print(f"Testing {name} (loveracing_id={loveracing_id})")
    print(f"{'='*60}")

    # 1. Test breeding page URL
    breeding_url = adapter.breeding_url(loveracing_id, "")
    print(f"\n1. Breeding URL: {breeding_url}")

    # 2. Test race history URL
    race_history_url = adapter.race_history_url(loveracing_id)
    print(f"2. Race History URL: {race_history_url}")

    # 3. Try fetching with Scrapling (fallback engine)
    print("\n3. Fetching with Scrapling StealthyFetcher...")
    engine = ScraplingEngine()

    try:
        print("   Fetching breeding page...")
        breeding_html = engine.fetch(breeding_url)
        print(f"   ✅ Breeding page: {len(breeding_html)} chars")

        # Parse breeding page
        print("   Parsing breeding page...")
        breeding_data = adapter.parse_breeding_page(breeding_html, loveracing_id)
        print(f"   ✅ Parsed: {breeding_data.get('name')}, microchip={breeding_data.get('microchip')}")

        microchip = breeding_data.get("microchip")
        if not microchip:
            print("   ❌ No microchip found - cannot continue")
            return False

        print(f"   Fetching race history...")
        race_html = engine.fetch(race_history_url)
        print(f"   ✅ Race history page: {len(race_html)} chars")

        # Parse race history
        print("   Parsing race history...")
        races = adapter.parse_race_history(race_html, microchip, loveracing_id)
        print(f"   ✅ Found {len(races)} races")

        # Print race summary
        total_earnings = sum(r.get("prize_money_nzd", 0) for r in races)
        wins = sum(1 for r in races if r.get("finish_position") == 1)
        places = sum(1 for r in races if r.get("finish_position") in (2, 3))
        print(f"   Total starts: {len(races)}")
        print(f"   Wins: {wins}")
        print(f"   Places (2nd/3rd): {places}")
        print(f"   Total earnings: ${total_earnings/100:,.2f} NZD")

        # Check for non-zero prize money
        non_zero_races = [r for r in races if r.get("prize_money_nzd", 0) > 0]
        print(f"   Races with prize money: {len(non_zero_races)}")

        # Compute summary
        foaling_date = breeding_data.get("foaling_date")
        if isinstance(foaling_date, str):
            from datetime import date
            foaling_date = date.fromisoformat(foaling_date)

        summary = adapter.compute_horse_racing_summary(races, microchip, loveracing_id, foaling_date=foaling_date)
        print(f"\n   Summary computed:")
        print(f"     Total starts: {summary['total_starts']}")
        print(f"     Total wins: {summary['total_wins']}")
        print(f"     Total places: {summary['total_places']}")
        print(f"     Total earnings: ${summary['total_earnings_nzd']/100:,.2f}")
        print(f"     Earnings by age: {summary['earnings_by_age']}")
        print(f"     Earnings by class: {summary['earnings_by_class']}")

        # Validation: sum of races = total earnings
        race_sum = sum(r.get("prize_money_nzd", 0) for r in races)
        if race_sum == summary["total_earnings_nzd"]:
            print(f"   ✅ Earnings consistency check PASSED")
        else:
            print(f"   ❌ Earnings consistency check FAILED: sum={race_sum}, summary={summary['total_earnings_nzd']}")
            return False

        # Validation: at least one race with non-zero prize money
        if len(non_zero_races) > 0:
            print(f"   ✅ Non-zero prize money check PASSED")
        else:
            print(f"   ❌ Non-zero prize money check FAILED")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Running pilot scrapes for Racing Data module...")

    # Test Prudentia
    prudentia_ok = test_horse(427416, "Prudentia")

    # Test First Gear
    first_gear_ok = test_horse(428364, "First Gear")

    print(f"\n{'='*60}")
    print("PILOT SCRAPE RESULTS")
    print(f"{'='*60}")
    print(f"Prudentia: {'✅ PASS' if prudentia_ok else '❌ FAIL'}")
    print(f"First Gear: {'✅ PASS' if first_gear_ok else '❌ FAIL'}")

    if prudentia_ok and first_gear_ok:
        print("\n🎉 All pilot success criteria met!")
        sys.exit(0)
    else:
        print("\n⚠️  Some pilot checks failed")
        sys.exit(1)