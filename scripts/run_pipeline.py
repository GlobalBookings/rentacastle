#!/usr/bin/env python3
"""
UK Castle Rental Data Pipeline
Runs: scrape -> normalize -> deduplicate -> enrich -> export
"""

import os
import subprocess
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

steps = [
    ("Scraping castle listings", "scrape_castles.py"),
    ("Normalizing data", "normalize.py"),
    ("Deduplicating records", "deduplicate.py"),
    ("Enriching data", "enrich.py"),
    ("Exporting to site format", "export_to_site.py"),
]

for label, script in steps:
    print(f'\n{"="*60}')
    print(f"STEP: {label}")
    print(f'{"="*60}')
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script)],
        cwd=SCRIPTS_DIR,
    )
    if result.returncode != 0:
        print(f"ERROR: {script} failed with code {result.returncode}")
        sys.exit(1)
    print(f"DONE: {label}")

print("\nPipeline complete! Check scripts/output/ for results.")
