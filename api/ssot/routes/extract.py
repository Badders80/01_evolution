"""
Loveracing.nz URL Extractor

Proxies loveracing.nz extraction to the racing-data Cloud Function.
Every NZ thoroughbred has one of these pages.

URL pattern: https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx
Example:     https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx
"""

import os
import re
import requests
from flask import Request, jsonify

RACING_DATA_URL = os.getenv("RACING_DATA_URL", "")


def handle(request: Request):
    """
    POST /extract
    Body: { "url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx" }
    
    Returns: Extracted horse data or error
    """
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405
    
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        
        if not url:
            return jsonify({"error": "Missing 'url' in request body"}), 400
        
        # Validate URL format
        loveracing_id, name_slug = parse_loveracing_url(url)
        if not loveracing_id:
            return jsonify({"error": "Invalid loveracing.nz URL. Expected format: https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx"}), 400
        
        # Proxy to racing-data
        try:
            extracted = scrape_loveracing_page(url, loveracing_id, name_slug)
            return jsonify(extracted), 200
        except requests.RequestException as e:
            return jsonify({"error": f"Failed to fetch loveracing.nz page: {str(e)}"}), 502
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
            
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 500


def parse_loveracing_url(url: str) -> tuple[int | None, str | None]:
    """
    Extract HorseID and NameSlug from loveracing.nz URL.
    
    Returns: (loveracing_id, name_slug) or (None, None) if invalid
    """
    pattern = r"https?://loveracing\.nz/Breeding/(\d+)/([^.]+)\.aspx"
    match = re.match(pattern, url, re.IGNORECASE)
    
    if not match:
        return None, None
    
    return int(match.group(1)), match.group(2)


def scrape_loveracing_page(url: str, loveracing_id: int, name_slug: str) -> dict:
    """Proxy to racing-data Cloud Function."""
    if not RACING_DATA_URL:
        raise ValueError("RACING_DATA_URL not configured")
    resp = requests.post(
        f"{RACING_DATA_URL}/loveracing/{loveracing_id}",
        json={"url": url, "name_slug": name_slug},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()
