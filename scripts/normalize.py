#!/usr/bin/env python3
"""
Normalize raw castle search results.

Reads  : output/raw_results.csv
Writes : output/normalized_results.csv

Normalization steps:
  1. Clean and standardise property names.
  2. Extract structured fields from snippets (sleeps, bedrooms, price, region).
  3. Assign uk_country based on region/county.
  4. Score castle_type_confidence (0-100).
"""

import csv
import logging
import os
import re
import string

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
RAW_CSV = os.path.join(OUTPUT_DIR, "raw_results.csv")
NORMALIZED_CSV = os.path.join(OUTPUT_DIR, "normalized_results.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

REMOVE_SUFFIXES = re.compile(
    r"\b(hotel|estate|venue|accommodation|lodge|spa|resort)\b", re.IGNORECASE
)

ABBREVIATIONS = {
    r"\bst\b": "saint",
    r"\bmt\b": "mount",
    r"\bft\b": "fort",
    r"\bdr\b": "drive",
    r"\brd\b": "road",
    r"\bnr\b": "near",
}

# Map known counties/regions to UK country
SCOTLAND_REGIONS = {
    "highland", "highlands", "argyll", "argyll and bute", "perthshire",
    "perth and kinross", "fife", "angus", "aberdeenshire", "moray",
    "stirling", "stirlingshire", "ayrshire", "dumfries and galloway",
    "scottish borders", "west lothian", "east lothian", "midlothian",
    "edinburgh", "glasgow", "dundee", "inverness", "clackmannanshire",
    "falkirk", "renfrewshire", "lanarkshire", "orkney", "shetland",
    "western isles", "isle of skye", "ross-shire", "caithness",
    "sutherland", "nairn", "banffshire", "kincardineshire",
}

WALES_REGIONS = {
    "powys", "ceredigion", "pembrokeshire", "carmarthenshire",
    "vale of glamorgan", "glamorgan", "gwynedd", "conwy",
    "denbighshire", "flintshire", "wrexham", "anglesey",
    "monmouthshire", "newport", "swansea", "cardiff", "brecon",
    "brecon beacons", "snowdonia", "neath port talbot",
    "rhondda cynon taf", "caerphilly", "torfaen", "blaenau gwent",
    "merthyr tydfil", "bridgend",
}

NI_REGIONS = {
    "northern ireland", "antrim", "armagh", "down", "fermanagh",
    "londonderry", "derry", "tyrone", "belfast",
}

ENGLAND_REGIONS = {
    "cornwall", "devon", "dorset", "somerset", "wiltshire", "hampshire",
    "west sussex", "east sussex", "kent", "surrey", "berkshire",
    "oxfordshire", "buckinghamshire", "hertfordshire", "essex",
    "suffolk", "norfolk", "cambridgeshire", "bedfordshire",
    "northamptonshire", "warwickshire", "worcestershire",
    "herefordshire", "gloucestershire", "shropshire", "staffordshire",
    "cheshire", "merseyside", "greater manchester", "lancashire",
    "cumbria", "lake district", "northumberland", "county durham",
    "tyne and wear", "yorkshire", "north yorkshire", "west yorkshire",
    "south yorkshire", "east yorkshire", "lincolnshire", "nottinghamshire",
    "derbyshire", "leicestershire", "rutland", "isle of wight",
    "london", "middlesex", "bristol", "cotswolds",
}

# Keywords for castle-type confidence scoring
CASTLE_KEYWORDS = {
    "castle": 25,
    "tower house": 20,
    "fortified": 15,
    "medieval": 10,
    "turret": 10,
    "battlements": 10,
    "portcullis": 10,
    "keep": 8,
    "drawbridge": 8,
    "moat": 8,
    "baronial": 8,
    "curtain wall": 8,
    "self-catering": 5,
    "exclusive use": 5,
    "holiday let": 5,
    "sleeps": 3,
    "bedrooms": 3,
    "per night": 3,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_name(raw: str) -> str:
    """Lowercase, strip punctuation, remove noise suffixes, standardise abbreviations."""
    name = raw.lower().strip()
    # Remove punctuation
    name = name.translate(str.maketrans("", "", string.punctuation))
    # Remove suffixes
    name = REMOVE_SUFFIXES.sub("", name)
    # Standardise abbreviations
    for pat, repl in ABBREVIATIONS.items():
        name = re.sub(pat, repl, name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def extract_sleeps(text: str) -> int | None:
    m = re.search(r"sleeps?\s+(\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def extract_bedrooms(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(?:bed)?rooms?", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def extract_price(text: str) -> str | None:
    m = re.search(r"(?:from\s+)?[£](\d[\d,]*)", text, re.IGNORECASE)
    if m:
        return f"£{m.group(1)}"
    return None


def detect_region(text: str) -> tuple[str | None, str | None]:
    """Return (uk_country, region_county) from free text."""
    low = text.lower()
    for region in sorted(SCOTLAND_REGIONS, key=len, reverse=True):
        if region in low:
            return ("Scotland", region.title())
    for region in sorted(WALES_REGIONS, key=len, reverse=True):
        if region in low:
            return ("Wales", region.title())
    for region in sorted(NI_REGIONS, key=len, reverse=True):
        if region in low:
            return ("Northern Ireland", region.title())
    for region in sorted(ENGLAND_REGIONS, key=len, reverse=True):
        if region in low:
            return ("England", region.title())
    return (None, None)


def castle_type_confidence(title: str, snippet: str) -> int:
    """0-100 confidence that this is a genuine castle rental."""
    combined = f"{title} {snippet}".lower()
    score = 0
    for keyword, points in CASTLE_KEYWORDS.items():
        if keyword in combined:
            score += points
    return min(score, 100)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

OUTPUT_FIELDS = [
    "result_id",
    "property_name_raw",
    "property_name_normalized",
    "source_url",
    "domain",
    "snippet",
    "score",
    "query",
    "sleeps",
    "bedrooms",
    "bathrooms",
    "price_from",
    "uk_country",
    "region_county",
    "castle_type_confidence",
    "castle_type",
    "rental_type",
    "description_clean",
    "image_urls",
    "latitude",
    "longitude",
    "postcode",
    "address",
    "phone",
    "email",
    "official_website",
    "booking_platforms",
    "pets_allowed",
    "wedding_friendly",
    "self_catering",
    "source_trust",
]


def run_normalize() -> None:
    if not os.path.isfile(RAW_CSV):
        log.error("Raw CSV not found: %s", RAW_CSV)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    rows: list[dict] = []
    with open(RAW_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)

    log.info("Loaded %d raw results.", len(rows))

    normalized: list[dict] = []
    for row in rows:
        title = row.get("title", "")
        snippet = row.get("snippet", "")
        url = row.get("url", "")
        combined_text = f"{title} {snippet}"

        country, county = detect_region(combined_text)
        sleeps = extract_sleeps(combined_text)
        bedrooms = extract_bedrooms(combined_text)
        price = extract_price(combined_text)
        confidence = castle_type_confidence(title, snippet)

        # Infer rental type from snippet keywords
        rental_type = ""
        snippet_low = snippet.lower()
        if "self-catering" in snippet_low or "self catering" in snippet_low:
            rental_type = "self-catering"
        elif "exclusive use" in snippet_low or "exclusive-use" in snippet_low:
            rental_type = "exclusive-use"
        elif "wedding" in snippet_low:
            rental_type = "wedding-venue"
        elif "hotel" in snippet_low:
            rental_type = "hotel-style"

        # Infer castle_type
        castle_type = "Castle"
        if "tower house" in title.lower() or "tower house" in snippet_low:
            castle_type = "Tower House"
        elif "fortified manor" in combined_text.lower():
            castle_type = "Fortified Manor"

        # Boolean flags
        pets = "yes" if re.search(r"\bpet[s\-]?\s*friendly\b|\bdogs?\s+welcome\b", snippet_low) else ""
        wedding = "yes" if "wedding" in snippet_low else ""
        self_catering = "yes" if "self-catering" in snippet_low or "self catering" in snippet_low else ""

        out = {
            "result_id": row.get("result_id", ""),
            "property_name_raw": title,
            "property_name_normalized": normalize_name(title),
            "source_url": url,
            "domain": row.get("domain", ""),
            "snippet": snippet,
            "score": row.get("score", ""),
            "query": row.get("query", ""),
            "sleeps": sleeps if sleeps else "",
            "bedrooms": bedrooms if bedrooms else "",
            "bathrooms": "",
            "price_from": price if price else "",
            "uk_country": country if country else "",
            "region_county": county if county else "",
            "castle_type_confidence": confidence,
            "castle_type": castle_type,
            "rental_type": rental_type,
            "description_clean": snippet,
            "image_urls": "",
            "latitude": "",
            "longitude": "",
            "postcode": "",
            "address": "",
            "phone": "",
            "email": "",
            "official_website": "",
            "booking_platforms": row.get("domain", ""),
            "pets_allowed": pets,
            "wedding_friendly": wedding,
            "self_catering": self_catering,
            "source_trust": "",
        }
        normalized.append(out)

    with open(NORMALIZED_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)

    log.info("Normalization complete. %d records → %s", len(normalized), NORMALIZED_CSV)


if __name__ == "__main__":
    import sys
    run_normalize()
