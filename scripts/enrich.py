#!/usr/bin/env python3
"""
Enrich deduplicated castle records.

Reads  : output/castles_master.csv
Writes : output/enriched_castles_master.csv

For each castle:
  - Search Google for the official website.
  - Geocode the location via Nominatim (free, no API key).
  - Extract postcode from address or geocode result.
  - Classify rental type.
  - Identify alternate names.

Rate limits:
  - 1 second between Nominatim calls (per their usage policy).
  - 2-3 seconds between Google lookups.
"""

import csv
import logging
import os
import random
import re
import sys
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
MASTER_CSV = os.path.join(OUTPUT_DIR, "castles_master.csv")
ENRICHED_CSV = os.path.join(OUTPUT_DIR, "enriched_castles_master.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    return s


def _request_with_retry(session: requests.Session, url: str, **kwargs) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=15, **kwargs)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt + random.uniform(1, 3)
                log.warning("Rate-limited (429). Waiting %.1fs …", wait)
                time.sleep(wait)
                continue
            log.warning("HTTP %s for %s (attempt %d)", resp.status_code, url, attempt)
        except requests.RequestException as exc:
            log.warning("Request error: %s (attempt %d)", exc, attempt)
        if attempt < MAX_RETRIES:
            time.sleep(BACKOFF_BASE ** attempt)
    return None


# ---------------------------------------------------------------------------
# Enrichment functions
# ---------------------------------------------------------------------------


def find_official_website(name: str, session: requests.Session) -> str | None:
    """Google for '{name} official website' and return the first non-platform link."""
    query = f"{name} official website UK"
    encoded = quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}&num=5&hl=en&gl=uk"
    session.headers["User-Agent"] = random.choice(USER_AGENTS)

    resp = _request_with_retry(session, url)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    skip_domains = {
        "google.com", "google.co.uk", "wikipedia.org", "tripadvisor.com",
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
    }
    for g in soup.select("div.g"):
        link = g.select_one("a[href]")
        if not link:
            continue
        href = link.get("href", "")
        if not href.startswith("http"):
            continue
        from urllib.parse import urlparse
        domain = urlparse(href).netloc.lower().replace("www.", "")
        if domain not in skip_domains:
            return href
    return None


def geocode_nominatim(query: str, session: requests.Session) -> dict | None:
    """Geocode *query* using Nominatim (OpenStreetMap).

    Returns dict with keys: lat, lon, display_name, or None.
    Respects 1-second rate limit per Nominatim policy.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": "gb",
    }
    headers = {
        "User-Agent": "RentACastle-Pipeline/1.0 (castle-rental-directory)",
    }
    resp = _request_with_retry(session, url, params=params, headers=headers)
    if resp is None:
        return None
    try:
        data = resp.json()
        if data:
            return data[0]
    except Exception:
        pass
    return None


def extract_postcode(text: str) -> str:
    """Extract a UK postcode from text."""
    m = UK_POSTCODE_RE.search(text)
    return m.group(1).upper() if m else ""


def classify_rental_type(row: dict) -> str:
    """Classify rental type from existing data."""
    if row.get("rental_type"):
        return row["rental_type"]
    combined = f"{row.get('snippet', '')} {row.get('property_name_raw', '')}".lower()
    if "self-catering" in combined or "self catering" in combined:
        return "self-catering"
    if "exclusive use" in combined or "exclusive-use" in combined:
        return "exclusive-use"
    if "wedding" in combined:
        return "wedding-venue"
    if "hotel" in combined:
        return "hotel-style"
    return "self-catering"  # default assumption for rentals


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_enrich() -> None:
    if not os.path.isfile(MASTER_CSV):
        log.error("Master CSV not found: %s", MASTER_CSV)
        sys.exit(1)

    with open(MASTER_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    log.info("Loaded %d master records for enrichment.", len(rows))

    session = _get_session()
    enriched: list[dict] = []

    for idx, row in enumerate(rows, 1):
        name = row.get("property_name_raw", "").strip()
        log.info("[%d/%d] Enriching: %s", idx, len(rows), name or "(unnamed)")

        # 1. Official website
        if not row.get("official_website"):
            website = find_official_website(name, session)
            if website:
                row["official_website"] = website
                log.info("  Official website: %s", website)
            time.sleep(random.uniform(2.0, 3.0))

        # 2. Geocode
        if not row.get("latitude") or not row.get("longitude"):
            geo_query = name
            if row.get("region_county"):
                geo_query += f", {row['region_county']}"
            if row.get("uk_country"):
                geo_query += f", {row['uk_country']}"
            geo_query += ", UK"

            geo = geocode_nominatim(geo_query, session)
            if geo:
                row["latitude"] = geo.get("lat", "")
                row["longitude"] = geo.get("lon", "")
                display = geo.get("display_name", "")
                if not row.get("address"):
                    row["address"] = display
                # Extract postcode from geocode result
                if not row.get("postcode"):
                    row["postcode"] = extract_postcode(display)
                log.info("  Geocoded: %s, %s", row["latitude"], row["longitude"])
            time.sleep(1.0)  # Nominatim 1-second policy

        # 3. Extract postcode from existing address if still missing
        if not row.get("postcode") and row.get("address"):
            row["postcode"] = extract_postcode(row["address"])

        # 4. Classify rental type
        row["rental_type"] = classify_rental_type(row)

        enriched.append(row)

    # Write enriched output
    fieldnames = list(rows[0].keys()) if rows else []
    with open(ENRICHED_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    log.info("Enrichment complete. %d records → %s", len(enriched), ENRICHED_CSV)


if __name__ == "__main__":
    run_enrich()
