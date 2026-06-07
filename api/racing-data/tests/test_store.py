"""
Tests for racing-data store module.

Run: pytest racing-data/tests/test_store.py -v
"""

import pytest
import os
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import (
    write_race_results,
    read_race_results,
    write_horse_racing_summary,
    read_horse_racing_summary,
    get_horse_racing_data,
    get_horse_ref,
    get_horse_doc_id,
)

# Test microchip (use a test-specific one to avoid conflicts)
TEST_MICROCHIP = "999999999999999"


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test data before and after each test."""
    # Cleanup before
    _cleanup_test_data()
    yield
    # Cleanup after
    _cleanup_test_data()


def _cleanup_test_data():
    """Delete test documents from Firestore."""
    from google.cloud import firestore
    db = firestore.Client()
    # Delete races subcollection
    horse_ref = db.collection("horses").document(TEST_MICROCHIP)
    races_ref = horse_ref.collection("races")
    for doc in races_ref.list_documents():
        doc.delete()
    # Delete summary
    summary_ref = horse_ref.collection("summary").document("summary")
    summary_ref.delete()


def test_write_and_read_race_results():
    """Test writing and reading race results."""
    # Sample race data
    races = [
        {
            "horse_microchip": TEST_MICROCHIP,
            "loveracing_id": 999999,
            "race_date": "2024-11-09",
            "venue": "TE RAPA",
            "race_name": "Maiden 1200",
            "race_class": "Maiden",
            "distance_metres": 1200,
            "field_size": 12,
            "barrier": 5,
            "jockey": "Sam Spratt",
            "finish_position": 1,
            "prize_money_nzd": 12500,
            "stake_type": "win",
            "source_url": "https://loveracing.nz/test",
        },
        {
            "horse_microchip": TEST_MICROCHIP,
            "loveracing_id": 999999,
            "race_date": "2024-12-15",
            "venue": "ELLE",
            "race_name": "Rating 65 1400",
            "race_class": "Rating 65 Benchmark*",
            "distance_metres": 1400,
            "field_size": 14,
            "barrier": 3,
            "jockey": "Masa Hashizume",
            "finish_position": 3,
            "prize_money_nzd": 3150,
            "stake_type": "place",
            "source_url": "https://loveracing.nz/test2",
        },
    ]

    # Write
    written_ids = write_race_results(TEST_MICROCHIP, races, "test/v1")
    assert len(written_ids) == 2
    assert all(isinstance(id, str) for id in written_ids)

    # Read
    read_races = read_race_results(TEST_MICROCHIP)
    assert len(read_races) == 2
    # Should be ordered by race_date DESC
    assert read_races[0]["race_date"] == "2024-12-15"
    assert read_races[1]["race_date"] == "2024-11-09"

    # Verify fields
    assert read_races[0]["finish_position"] == 3
    assert read_races[0]["prize_money_nzd"] == 3150
    assert read_races[1]["finish_position"] == 1
    assert read_races[1]["prize_money_nzd"] == 12500


def test_write_race_results_idempotent():
    """Test that re-writing same races doesn't create duplicates."""
    races = [
        {
            "horse_microchip": TEST_MICROCHIP,
            "loveracing_id": 999999,
            "race_date": "2024-11-09",
            "venue": "TE RAPA",
            "race_name": "Maiden 1200",
            "finish_position": 1,
            "prize_money_nzd": 12500,
            "stake_type": "win",
            "source_url": "https://loveracing.nz/test",
        },
    ]

    # Write twice
    write_race_results(TEST_MICROCHIP, races, "test/v1")
    write_race_results(TEST_MICROCHIP, races, "test/v2")

    # Should still only have 1 race
    read_races = read_race_results(TEST_MICROCHIP)
    assert len(read_races) == 1


def test_write_and_read_summary():
    """Test writing and reading horse racing summary."""
    summary = {
        "horse_microchip": TEST_MICROCHIP,
        "loveracing_id": 999999,
        "total_starts": 2,
        "total_wins": 1,
        "total_places": 1,
        "total_earnings_nzd": 15650,
        "earnings_by_age": {"2": 15650},
        "earnings_by_class": {"Maiden": 12500, "Rating 65 Benchmark*": 3150},
        "first_start_date": "2024-11-09",
        "last_start_date": "2024-12-15",
    }

    # Write
    doc_id = write_horse_racing_summary(TEST_MICROCHIP, summary)
    assert doc_id == "summary"

    # Read
    read_summary = read_horse_racing_summary(TEST_MICROCHIP)
    assert read_summary is not None
    assert read_summary["total_starts"] == 2
    assert read_summary["total_wins"] == 1
    assert read_summary["total_earnings_nzd"] == 15650
    assert read_summary["earnings_by_class"]["Maiden"] == 12500


def test_get_horse_racing_data():
    """Test combined read of horse + races + summary."""
    from google.cloud import firestore

    db = firestore.Client()

    # Create a horse document first
    horse_ref = db.collection("horses").document(TEST_MICROCHIP)
    horse_ref.set({
        "microchip": TEST_MICROCHIP,
        "name": "Test Horse",
        "foaling_date": "2022-01-01",
        "sex": "gelding",
        "colour": "Bay",
        "loveracing_id": 999999,
    })

    # Write some races
    write_race_results(TEST_MICROCHIP, [
        {
            "horse_microchip": TEST_MICROCHIP,
            "loveracing_id": 999999,
            "race_date": "2024-11-09",
            "venue": "TE RAPA",
            "race_name": "Maiden 1200",
            "finish_position": 1,
            "prize_money_nzd": 12500,
            "stake_type": "win",
            "source_url": "https://loveracing.nz/test",
        },
    ])

    # Write summary
    write_horse_racing_summary(TEST_MICROCHIP, {
        "horse_microchip": TEST_MICROCHIP,
        "loveracing_id": 999999,
        "total_starts": 1,
        "total_wins": 1,
        "total_places": 0,
        "total_earnings_nzd": 12500,
        "earnings_by_age": {"2": 12500},
        "earnings_by_class": {"Maiden": 12500},
        "first_start_date": "2024-11-09",
        "last_start_date": "2024-11-09",
    })

    # Get combined data
    data = get_horse_racing_data(TEST_MICROCHIP)

    assert data["horse"] is not None
    assert data["horse"]["microchip"] == TEST_MICROCHIP
    assert len(data["races"]) == 1
    assert data["summary"] is not None
    assert data["summary"]["total_starts"] == 1


def test_get_horse_ref_and_doc_id():
    """Test helper functions for horse reference."""
    from google.cloud import firestore

    db = firestore.Client()

    # Create a horse document
    horse_ref = db.collection("horses").document(TEST_MICROCHIP)
    horse_ref.set({
        "microchip": TEST_MICROCHIP,
        "name": "Test Horse",
        "foaling_date": "2022-01-01",
        "sex": "gelding",
    })

    # Test get_horse_ref
    ref = get_horse_ref(TEST_MICROCHIP)
    assert ref is not None
    assert ref.id == horse_ref.id

    # Test get_horse_doc_id
    doc_id = get_horse_doc_id(TEST_MICROCHIP)
    assert doc_id == horse_ref.id

    # Test with non-existent microchip
    assert get_horse_ref("000000000000000") is None
    assert get_horse_doc_id("000000000000000") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])