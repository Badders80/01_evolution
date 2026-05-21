"""
Loveracing.nz URL Extractor

Scrapes horse data from loveracing.nz Stud Book pages.
Every NZ thoroughbred has one of these pages.

URL pattern: https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx
Example:     https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx

Extracts:
- Microchip (15 digits)
- Life Number (NZ + 8 digits)
- Name, Foaling Date, Sex, Colour
- Sire, Dam (names + links)
- Breeder, Brands
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Request, jsonify
from models import LoveracingRef


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
        
        # Fetch and scrape the page
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
    """
    Fetch and extract data from loveracing.nz Stud Book page.
    
    Returns dict matching LoveracingRef model
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract name from page title or heading
    name = extract_name(soup, name_slug)
    
    # Extract basic info
    microchip = extract_microchip(soup)
    life_number = extract_life_number(soup)
    foaling_date = extract_foaling_date(soup)
    sex, colour = extract_sex_colour(soup)
    
    # Extract pedigree
    sire_name, sire_id = extract_sire(soup)
    dam_name, dam_id = extract_dam(soup)
    
    # Extract breeder and brands
    breeder = extract_breeder(soup)
    brands = extract_brands(soup)
    
    # Build reference object
    ref = LoveracingRef(
        loveracing_id=loveracing_id,
        name=name,
        name_slug=name_slug,
        microchip=microchip,
        life_number=life_number,
        foaling_date=foaling_date,
        sex=sex,
        colour=colour,
        sire_name=sire_name,
        sire_loveracing_id=sire_id,
        dam_name=dam_name,
        dam_loveracing_id=dam_id,
        breeder=breeder,
        left_shoulder_brand=brands.get("left"),
        right_shoulder_brand=brands.get("right"),
    )
    
    return ref.model_dump()


def extract_name(soup: BeautifulSoup, name_slug: str) -> str:
    """Extract horse name from page title or h1."""
    # Try h1 first
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    
    # Try page title
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).replace(" - loveracing.nz", "")
    
    # Fallback: reconstruct from slug
    return name_slug.replace("-", " ").title()


def extract_microchip(soup: BeautifulSoup) -> str:
    """Extract 15-digit microchip number."""
    # Find <strong>Microchip:</strong> and get next text sibling
    label = soup.find("strong", string=re.compile(r"Microchip:", re.IGNORECASE))
    if label and label.next_sibling:
        text = str(label.next_sibling).strip()
        match = re.search(r"\d{15}", text)
        if match:
            return match.group()
    
    return "000000000000000"  # Placeholder if not found


def extract_life_number(soup: BeautifulSoup) -> str:
    """Extract NZTR life number (NZ + 8 digits)."""
    # Look for pattern like "NZ00427416" in page text
    text = soup.get_text()
    match = re.search(r"(NZ\d{6,8})", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return "NZ00000000"  # Placeholder


def extract_foaling_date(soup: BeautifulSoup) -> datetime:
    """Extract foaling date."""
    # Find <strong>Born:</strong> or <strong>Foaling date:</strong>
    for pattern in [r"Born:", r"Foaling date:"]:
        label = soup.find("strong", string=re.compile(pattern, re.IGNORECASE))
        if label and label.next_sibling:
            text = str(label.next_sibling).strip()
            match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
            if match:
                day, month, year = match.groups()
                return datetime(int(year), int(month), int(day))
    
    return datetime(2020, 1, 1)  # Placeholder


def extract_sex_colour(soup: BeautifulSoup) -> tuple[str, str | None]:
    """Extract sex and colour from page content."""
    text = soup.get_text().lower()
    
    # Common colour patterns
    colours = ["bay", "brown", "chestnut", "black", "grey", "gray", "roan", "white"]
    sexes = ["colt", "filly", "gelding", "mare", "stallion", "horse"]
    
    sex = "unknown"
    colour = None
    
    # Search for colour
    for colour_word in colours:
        if colour_word in text:
            colour = colour_word.title()
            break
    
    # Search for sex
    for sex_word in sexes:
        if sex_word in text:
            sex = sex_word
            break
    
    return sex, colour


def extract_sire(soup: BeautifulSoup) -> tuple[str | None, int | None]:
    """Extract sire name and loveracing ID from pedigree link."""
    # Find <strong>Sire:</strong> label
    label = soup.find("strong", string=re.compile(r"^Sire:$", re.IGNORECASE))
    if not label:
        return None, None
    
    # Look for link in the same parent div
    parent = label.find_parent()
    if parent:
        link = parent.find("a")
        if link:
            name = link.get_text(strip=True)
            href = link.get("href", "")
            match = re.search(r"/Breeding/(\d+)/", href)
            sire_id = int(match.group(1)) if match else None
            return name, sire_id
    
    return None, None


def extract_dam(soup: BeautifulSoup) -> tuple[str | None, int | None]:
    """Extract dam name and loveracing ID from pedigree link."""
    # Find <strong>Dam:</strong> label
    label = soup.find("strong", string=re.compile(r"^Dam:$", re.IGNORECASE))
    if not label:
        return None, None
    
    # Look for link in the same parent div
    parent = label.find_parent()
    if parent:
        link = parent.find("a")
        if link:
            name = link.get_text(strip=True)
            href = link.get("href", "")
            match = re.search(r"/Breeding/(\d+)/", href)
            dam_id = int(match.group(1)) if match else None
            return name, dam_id
    
    return None, None


def extract_breeder(soup: BeautifulSoup) -> str | None:
    """Extract breeder name."""
    # Find <strong>Breeder:</strong> label
    label = soup.find("strong", string=re.compile(r"Breeder:", re.IGNORECASE))
    if label and label.next_sibling:
        return str(label.next_sibling).strip()
    
    return None


def extract_brands(soup: BeautifulSoup) -> dict[str, str | None]:
    """Extract left and right shoulder brands."""
    brands = {"left": None, "right": None}
    
    # Find <strong>Brands:</strong> or similar
    label = soup.find("strong", string=re.compile(r"Brand", re.IGNORECASE))
    if label and label.next_sibling:
        text = str(label.next_sibling).strip()
        brands["left"] = text
        brands["right"] = text
    
    return brands
