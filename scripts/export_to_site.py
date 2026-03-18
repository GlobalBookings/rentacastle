#!/usr/bin/env python3
"""
Export enriched castle data to a TypeScript file matching the Castle interface.

Reads  : output/enriched_castles_master.csv  (falls back to castles_master.csv)
Writes : output/castles_scraped.ts
"""

import csv
import json
import logging
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
ENRICHED_CSV = os.path.join(OUTPUT_DIR, "enriched_castles_master.csv")
MASTER_CSV = os.path.join(OUTPUT_DIR, "castles_master.csv")
TS_OUTPUT = os.path.join(OUTPUT_DIR, "castles_scraped.ts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_REGIONS = {"Scotland", "England", "Wales", "Northern Ireland"}
VALID_TYPES = {"Castle", "Castle House", "Tower House", "Fortified Manor", "Chateau"}


def slugify(name: str) -> str:
    """Create a URL-friendly slug from a property name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def to_price_range(price_str: str) -> str:
    """Map a price string to a $ bucket."""
    try:
        val = int(re.sub(r"[^\d]", "", price_str))
    except (ValueError, TypeError):
        return "$$"
    if val <= 150:
        return "$"
    if val <= 300:
        return "$$"
    if val <= 500:
        return "$$$"
    return "$$$$"


def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val: str) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _ts_string(s: str) -> str:
    """Escape a value for embedding in a TypeScript single-quoted string."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def _bool_field(val: str) -> str:
    """Return 'true' or 'false' TS literal."""
    return "true" if val.strip().lower() in ("yes", "true", "1") else "false"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def row_to_ts(row: dict) -> str | None:
    """Convert a CSV row into a TypeScript Castle object literal."""
    name = row.get("property_name_raw", "").strip()
    if not name:
        return None

    slug = slugify(name)
    region = row.get("uk_country", "England").strip()
    if region not in VALID_REGIONS:
        region = "England"

    county = row.get("region_county", "").strip()
    castle_type = row.get("castle_type", "Castle").strip()
    if castle_type not in VALID_TYPES:
        castle_type = "Castle"

    price_from = row.get("price_from", "").strip()
    avg_price = f"{price_from}/night" if price_from else "£200/night"
    if not price_from:
        price_from = "£200"
    price_range = to_price_range(price_from)

    sleeps = safe_int(row.get("sleeps", ""), 2)
    bedrooms = safe_int(row.get("bedrooms", ""), 1)
    bathrooms = safe_int(row.get("bathrooms", ""), 1)

    booking_url = row.get("source_url", "#").strip() or "#"
    description = row.get("description_clean", "").strip() or name

    image_urls_raw = row.get("image_urls", "").strip()
    images = [u.strip() for u in image_urls_raw.split("|") if u.strip()] if image_urls_raw else []
    primary_image = images[0] if images else "https://images.unsplash.com/photo-1533154683836-84ea7a0bc310?w=800&q=80"

    lat = safe_float(row.get("latitude", ""))
    lng = safe_float(row.get("longitude", ""))

    pets = _bool_field(row.get("pets_allowed", ""))
    wedding = _bool_field(row.get("wedding_friendly", ""))
    self_catering = _bool_field(row.get("self_catering", ""))

    platform = row.get("booking_platforms", "").strip()

    # Build TypeScript object
    lines = [
        "  {",
        f"    slug: '{_ts_string(slug)}',",
        f"    name: '{_ts_string(name)}',",
        f"    region: '{_ts_string(region)}',",
        f"    county: '{_ts_string(county)}',",
        f"    type: '{_ts_string(castle_type)}',",
        f"    priceRange: '{price_range}',",
        f"    avgPrice: '{_ts_string(avg_price)}',",
        f"    sleeps: {sleeps},",
        f"    bedrooms: {bedrooms},",
        f"    bathrooms: {bathrooms},",
        f"    bookingUrl: '{_ts_string(booking_url)}',",
        f"    image: '{_ts_string(primary_image)}',",
        f"    description: '{_ts_string(description)}',",
        "    highlights: [],",
        "    nearbyAttractions: [],",
    ]

    if description:
        lines.append(f"    overview: '{_ts_string(description)}',")

    lines.append(f"    weddingSuitable: {wedding},")
    lines.append(f"    petFriendly: {pets},")
    lines.append(f"    selfCatering: {self_catering},")
    lines.append("    hasWifi: true,")

    if lat is not None:
        lines.append(f"    lat: {lat},")
    if lng is not None:
        lines.append(f"    lng: {lng},")

    if images:
        imgs_ts = ", ".join(f"'{_ts_string(u)}'" for u in images)
        lines.append(f"    images: [{imgs_ts}],")

    if platform:
        lines.append(f"    bookingPlatform: '{_ts_string(platform)}',")

    lines.append("  }")
    return "\n".join(lines)


def run_export() -> None:
    # Pick the best available input
    if os.path.isfile(ENRICHED_CSV):
        source = ENRICHED_CSV
    elif os.path.isfile(MASTER_CSV):
        source = MASTER_CSV
        log.warning("Enriched CSV not found; falling back to %s", MASTER_CSV)
    else:
        log.error("No input CSV found. Run earlier pipeline stages first.")
        sys.exit(1)

    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    log.info("Loaded %d records from %s", len(rows), source)

    ts_objects: list[str] = []
    for row in rows:
        obj = row_to_ts(row)
        if obj:
            ts_objects.append(obj)

    ts_content = (
        "// Auto-generated by export_to_site.py — do not edit by hand.\n"
        "// To update, re-run the scraping pipeline.\n\n"
        "import type { Castle } from './castles';\n\n"
        "export const scrapedCastles: Castle[] = [\n"
        + ",\n".join(ts_objects)
        + "\n];\n"
    )

    with open(TS_OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(ts_content)

    log.info("Exported %d castles → %s", len(ts_objects), TS_OUTPUT)


if __name__ == "__main__":
    run_export()
