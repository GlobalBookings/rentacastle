#!/usr/bin/env python3
"""
Castle listing deduplication engine.

Reads  : output/normalized_results.csv
Writes : output/castles_master.csv          – deduplicated master list
         output/possible_duplicates.csv     – pairs scoring 50-69 for review
         output/excluded_properties.csv     – low-score results (appended)

Scoring model (per pair):
    +50  official website match
    +30  postcode match
    +25  geo proximity (< 500 m)
    +20  phone / email match
    +20  exact normalised-name match
    +15  fuzzy name match (SequenceMatcher ratio > 0.8)

Thresholds:
    >= 70  → auto-merge (keep highest-trust source)
    50-69  → flag for manual review
    < 50   → keep separate
"""

import csv
import logging
import math
import os
import sys
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
NORMALIZED_CSV = os.path.join(OUTPUT_DIR, "normalized_results.csv")
MASTER_CSV = os.path.join(OUTPUT_DIR, "castles_master.csv")
DUPES_CSV = os.path.join(OUTPUT_DIR, "possible_duplicates.csv")
EXCLUDED_CSV = os.path.join(OUTPUT_DIR, "excluded_properties.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Trust priority (higher = more trusted)
TRUST_ORDER = {
    "official": 5,
    "direct_owner": 4,
    "maps": 3,
    "major_platform": 2,
    "secondary_directory": 1,
    "": 0,
}

MAJOR_PLATFORMS = {
    "airbnb.com", "booking.com", "vrbo.com",
    "sykescottages.co.uk", "oliverstravels.com",
    "holidaycottages.co.uk", "cottages.com",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trust_score(row: dict) -> int:
    """Derive a numeric trust score for a row."""
    trust_label = row.get("source_trust", "").strip().lower()
    if trust_label in TRUST_ORDER:
        return TRUST_ORDER[trust_label]
    domain = row.get("domain", "").lower()
    if domain in MAJOR_PLATFORMS:
        return TRUST_ORDER["major_platform"]
    return TRUST_ORDER["secondary_directory"]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two WGS-84 coordinates."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def pair_score(a: dict, b: dict) -> int:
    """Score how likely two rows describe the same property."""
    score = 0

    # +50 official website match
    ow_a = (a.get("official_website") or "").strip().lower()
    ow_b = (b.get("official_website") or "").strip().lower()
    if ow_a and ow_b and ow_a == ow_b:
        score += 50

    # +30 postcode match
    pc_a = (a.get("postcode") or "").strip().upper().replace(" ", "")
    pc_b = (b.get("postcode") or "").strip().upper().replace(" ", "")
    if pc_a and pc_b and pc_a == pc_b:
        score += 30

    # +25 geo proximity (< 500 m)
    try:
        lat_a, lon_a = float(a["latitude"]), float(a["longitude"])
        lat_b, lon_b = float(b["latitude"]), float(b["longitude"])
        if _haversine(lat_a, lon_a, lat_b, lon_b) < 500:
            score += 25
    except (ValueError, KeyError, TypeError):
        pass

    # +20 phone / email match
    for field in ("phone", "email"):
        va = (a.get(field) or "").strip().lower()
        vb = (b.get(field) or "").strip().lower()
        if va and vb and va == vb:
            score += 20
            break  # only award once

    # +20 exact normalised name match
    na = (a.get("property_name_normalized") or "").strip()
    nb = (b.get("property_name_normalized") or "").strip()
    if na and nb:
        if na == nb:
            score += 20
        else:
            # +15 fuzzy name match
            ratio = SequenceMatcher(None, na, nb).ratio()
            if ratio > 0.8:
                score += 15

    return score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_dedup() -> None:
    if not os.path.isfile(NORMALIZED_CSV):
        log.error("Normalized CSV not found: %s", NORMALIZED_CSV)
        sys.exit(1)

    with open(NORMALIZED_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    log.info("Loaded %d normalized records.", len(rows))

    # Filter to included results (score >= 4)
    included = []
    excluded = []
    for r in rows:
        try:
            sc = int(r.get("score", 0))
        except ValueError:
            sc = 0
        if sc >= 4:
            included.append(r)
        else:
            excluded.append(r)

    log.info("Included: %d   Excluded: %d", len(included), len(excluded))

    # ---- Pairwise comparison ----
    n = len(included)
    merge_graph: dict[int, int] = {}  # child → parent (index in included)
    review_pairs: list[dict] = []

    for i in range(n):
        for j in range(i + 1, n):
            sc = pair_score(included[i], included[j])
            if sc >= 70:
                # Auto-merge: keep the one with higher trust
                ti = _trust_score(included[i])
                tj = _trust_score(included[j])
                if ti >= tj:
                    merge_graph[j] = merge_graph.get(i, i)
                else:
                    merge_graph[i] = merge_graph.get(j, j)
            elif sc >= 50:
                review_pairs.append({
                    "record_a_id": included[i].get("result_id", ""),
                    "record_a_name": included[i].get("property_name_raw", ""),
                    "record_b_id": included[j].get("result_id", ""),
                    "record_b_name": included[j].get("property_name_raw", ""),
                    "pair_score": sc,
                })

    # Build master list (skip merged-away records)
    merged_indices = set(merge_graph.keys())
    master = [r for idx, r in enumerate(included) if idx not in merged_indices]

    log.info("Auto-merged %d duplicates.", len(merged_indices))
    log.info("Master list: %d records.", len(master))
    log.info("Pairs for manual review: %d", len(review_pairs))

    # ---- Write outputs ----
    fieldnames = list(rows[0].keys()) if rows else []

    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master)
    log.info("Master CSV → %s", MASTER_CSV)

    dup_fields = ["record_a_id", "record_a_name", "record_b_id", "record_b_name", "pair_score"]
    with open(DUPES_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=dup_fields)
        writer.writeheader()
        writer.writerows(review_pairs)
    log.info("Possible duplicates → %s", DUPES_CSV)

    # Append / overwrite excluded
    with open(EXCLUDED_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(excluded)
    log.info("Excluded properties → %s", EXCLUDED_CSV)


if __name__ == "__main__":
    run_dedup()
