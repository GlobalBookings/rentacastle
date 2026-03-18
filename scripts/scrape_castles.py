#!/usr/bin/env python3
"""
UK Castle Rental Scraper - SerpAPI Edition
Uses SerpAPI for reliable Google search results + direct platform scraping.
"""

import csv
import hashlib
import logging
import os
import random
import re
import sys
import time
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

try:
    from serpapi import GoogleSearch
except ImportError:
    sys.exit("Install serpapi: pip install google-search-results")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPTS_DIR)
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
RAW_CSV = os.path.join(OUTPUT_DIR, "raw_results.csv")
EXCLUDED_CSV = os.path.join(OUTPUT_DIR, "excluded_properties.csv")

# Load API key from .env
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
SERPAPI_KEY = None
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            if line.strip().startswith("SERPAPI_KEY="):
                SERPAPI_KEY = line.strip().split("=", 1)[1].strip()

if not SERPAPI_KEY:
    sys.exit("Set SERPAPI_KEY in .env file")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
os.makedirs(OUTPUT_DIR, exist_ok=True)

KNOWN_PLATFORMS = [
    "airbnb.co.uk", "airbnb.com", "booking.com",
    "sykescottages.co.uk", "oliverstravels.com", "snaptrip.com",
    "uniquehomestays.com", "coolstays.com", "hostunusual.com",
    "independentcottages.co.uk", "cottages.com", "holidaycottages.co.uk",
    "vrbo.com", "landmarktrust.org.uk", "canopyandstars.co.uk",
    "thebigsleepover.com", "largeholidayhouses.com", "bigcottage.com",
    "partyhouses.co.uk", "manorhouses.co.uk", "sheepskinlife.com",
    "crabtreeandcrabtree.com", "sawdays.co.uk", "nationaltrust.org.uk",
    "english-heritage.org.uk", "historichouses.org",
]

BRANDING_BLACKLIST = [
    "castle insurance", "castle dental", "castle estate agents",
    "castle garage", "castle cars", "castle clinic", "castle pharmacy",
    "castle school", "castle surgery", "castle pub", "bouncy castle",
    "castle point council", "castle donington", "castle bromwich",
]

QUERIES = [
    "castle to rent UK",
    "castle holiday rental UK",
    "rent a castle Scotland",
    "rent a castle England",
    "rent a castle Wales",
    "exclusive use castle UK",
    "castle wedding venue hire UK",
    "self catering castle UK",
    "tower house to rent Scotland",
    "castle holiday let UK",
    "castle to rent Cornwall",
    "castle to rent Scottish Highlands",
    "castle to rent Yorkshire",
    "castle to rent Northumberland",
    "castle to rent Lake District",
    "luxury castle hire UK",
    "castle accommodation UK sleeps",
    "rent entire castle UK group",
    "castle Airbnb UK",
    "castle to rent Pembrokeshire Wales",
    "castle to rent Cotswolds",
    "castle to rent Norfolk",
    "castle to rent Devon",
    "castle to rent Northern Ireland",
    "pet friendly castle rental UK",
    "castle with hot tub UK rent",
    "castle hen party UK hire",
    "castle stay UK bedrooms",
]

SITE_QUERIES = [
    "site:sykescottages.co.uk castle",
    "site:oliverstravels.com castle UK",
    "site:coolstays.com castle",
    "site:uniquehomestays.com castle",
    "site:holidaycottages.co.uk castle",
    "site:landmarktrust.org.uk castle",
    "site:snaptrip.com castle",
    "site:cottages.com castle UK",
    "site:largeholidayhouses.com castle",
    "site:canopyandstars.co.uk castle",
    "site:sawdays.co.uk castle",
    "site:airbnb.co.uk castle UK",
    "site:booking.com castle UK hotel",
]


def score_result(title, url, snippet):
    score = 0
    title_l = title.lower()
    snippet_l = snippet.lower()
    url_l = url.lower()
    combined = f"{title_l} {snippet_l} {url_l}"

    for bl in BRANDING_BLACKLIST:
        if bl in combined:
            return -5

    if "castle" in title_l:
        score += 3
    if any(kw in snippet_l for kw in ["castle", "tower house", "fortified", "medieval", "turret"]):
        score += 2

    domain = urlparse(url).netloc.lower().replace("www.", "")
    if any(p in domain for p in KNOWN_PLATFORMS):
        score += 2

    rental_kws = ["rent", "hire", "book", "stay", "sleeps", "bedroom",
                   "self-catering", "self catering", "per night", "holiday",
                   "accommodation", "exclusive use", "wedding", "cottage",
                   "let", "availability", "price", "from £"]
    rental_hits = sum(1 for kw in rental_kws if kw in combined)
    score += min(rental_hits, 3)

    uk_kws = ["scotland", "england", "wales", "northern ireland", "uk",
              "highland", "cornwall", "yorkshire", "lake district",
              "northumberland", "pembrokeshire", "cotswolds", "devon",
              "cumbria", "argyll", "fife", "ayrshire", "sussex",
              "gloucestershire", "cheshire", "durham", "norfolk"]
    if any(kw in combined for kw in uk_kws):
        score += 1

    not_rentable = ["ruins only", "museum only", "english heritage admission",
                    "entry ticket", "tourist attraction only", "opening times only",
                    "guided tour only", "wikipedia"]
    if any(kw in combined for kw in not_rentable):
        score -= 4

    return score


def make_id(url, title):
    raw = f"{url}|{title}".encode()
    return hashlib.md5(raw).hexdigest()[:12]


def search_serpapi(query, num_results=20):
    """Search Google via SerpAPI."""
    try:
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "gl": "uk",
            "hl": "en",
            "num": num_results,
        }
        search = GoogleSearch(params)
        data = search.get_dict()

        results = []
        for r in data.get("organic_results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            })
        return results
    except Exception as e:
        log.error(f"SerpAPI error: {e}")
        return []


def run():
    all_results = {}
    excluded = []

    all_queries = QUERIES + SITE_QUERIES
    total = len(all_queries)

    for i, query in enumerate(all_queries, 1):
        log.info(f"[{i}/{total}] Searching: {query}")
        results = search_serpapi(query)
        log.info(f"  -> {len(results)} results")

        for r in results:
            s = score_result(r["title"], r["url"], r["snippet"])
            uid = make_id(r["url"], r["title"])
            entry = {
                "unique_id": uid,
                "title": r["title"],
                "url": r["url"],
                "snippet": r["snippet"],
                "source_query": query,
                "score": s,
                "domain": urlparse(r["url"]).netloc.lower().replace("www.", ""),
            }
            if s >= 4:
                if uid not in all_results or all_results[uid]["score"] < s:
                    all_results[uid] = entry
            else:
                excluded.append(entry)

        # SerpAPI has its own rate limits, small delay between calls
        time.sleep(1.5)

    # Write results
    fieldnames = ["unique_id", "title", "url", "snippet", "source_query", "score", "domain"]

    with open(RAW_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for entry in sorted(all_results.values(), key=lambda x: x["score"], reverse=True):
            w.writerow(entry)

    with open(EXCLUDED_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for entry in excluded:
            w.writerow(entry)

    log.info(f"\n{'='*60}")
    log.info("Scraping complete.")
    log.info(f"  Total unique results : {len(all_results)}")
    log.info(f"  Included (score >= 4): {len(all_results)}")
    log.info(f"  Excluded (score < 4) : {len(excluded)}")
    log.info(f"  Raw CSV              : {RAW_CSV}")
    log.info(f"  Excluded CSV         : {EXCLUDED_CSV}")


if __name__ == "__main__":
    run()
