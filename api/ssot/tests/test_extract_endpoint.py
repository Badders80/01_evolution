#!/usr/bin/env python3
"""
Test the /extract endpoint

Usage:
    python test_extract_endpoint.py

Verify:
    - Endpoint accepts POST with URL
    - Returns extracted horse data
    - Microchip, life number, and foaling date are correct
"""

import requests
import json

ENDPOINT = "http://localhost:8080/extract"

TEST_URLS = [
    "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
]

def test_extract():
    """Test the extract endpoint with a real loveracing.nz URL."""
    print("=" * 60)
    print("Testing /extract endpoint")
    print("=" * 60)
    
    for url in TEST_URLS:
        print(f"\n📋 Testing URL: {url}")
        print("-" * 60)
        
        response = requests.post(
            ENDPOINT,
            json={"url": url},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Extraction successful!")
            print(f"   Microchip: {data['microchip']}")
            print(f"   Life Number: {data['life_number']}")
            print(f"   Name: {data['name']}")
            print(f"   Foaling Date: {data['foaling_date']}")
            print(f"   Sex: {data['sex']}")
            print(f"   Colour: {data['colour']}")
            print(f"   Sire: {data['sire_name']}")
            print(f"   Dam: {data['dam_name']}")
            print(f"   Breeder: {data['breeder']}")
            
            # Verify critical fields
            assert data['microchip'] == "985125000126462", "Microchip mismatch"
            assert data['life_number'] == "NZ00427416", "Life number mismatch"
            assert "2021" in data['foaling_date'], "Foaling date year mismatch"
            assert data['sex'] in ["mare", "filly", "colt", "gelding", "stallion"], "Invalid sex"
            
            print("\n✅ All validations passed!")
            
        elif response.status_code == 400:
            print(f"❌ Validation error: {response.json().get('error')}")
        else:
            print(f"❌ Server error ({response.status_code}): {response.text}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_extract()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running on http://localhost:8080?")
        print("\nStart the API with:")
        print("  cd api/ssot && source ../venv/bin/activate")
        print("  functions-framework --target=ssot --port=8080")
    except AssertionError as e:
        print(f"\n❌ Validation failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
