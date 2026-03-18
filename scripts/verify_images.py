#!/usr/bin/env python3
"""Verify all Unsplash image URLs used across the RentACastle site."""

import os
import re
import time
import requests

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
URL_PATTERN = re.compile(r'https://images\.unsplash\.com/photo-[^\s"\'`,)\]]+')
EXTENSIONS = ('.astro', '.ts')
RATE_LIMIT = 0.2  # 5 requests per second


def find_urls():
    """Scan .astro and .ts files for Unsplash image URLs."""
    url_to_files = {}  # url -> set of files
    total_count = 0

    for root, _, files in os.walk(SRC_DIR):
        for fname in files:
            if not fname.endswith(EXTENSIONS):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, SRC_DIR)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for match in URL_PATTERN.findall(content):
                total_count += 1
                url_to_files.setdefault(match, set()).add(rel_path)

    return url_to_files, total_count


def check_url(url):
    """HEAD request to verify URL returns 200."""
    try:
        resp = requests.head(url, timeout=15, allow_redirects=True)
        return resp.status_code
    except requests.RequestException as e:
        return str(e)


def main():
    print("Scanning src/ for Unsplash image URLs...")
    url_to_files, total_count = find_urls()
    unique_urls = list(url_to_files.keys())

    print(f"\nTotal URL references found: {total_count}")
    print(f"Unique URLs to verify: {len(unique_urls)}\n")
    print("Verifying each URL (rate-limited to 5 req/s)...\n")

    working = []
    broken = []

    for i, url in enumerate(unique_urls, 1):
        status = check_url(url)
        short = url[:80] + "..." if len(url) > 80 else url
        if status == 200:
            working.append(url)
            print(f"  [{i}/{len(unique_urls)}] ✓ 200  {short}")
        else:
            broken.append((url, status, url_to_files[url]))
            print(f"  [{i}/{len(unique_urls)}] ✗ {status}  {short}")
        time.sleep(RATE_LIMIT)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Total URL references : {total_count}")
    print(f"  Unique URLs checked  : {len(unique_urls)}")
    print(f"  Working (200)        : {len(working)}")
    print(f"  Broken (non-200)     : {len(broken)}")

    if broken:
        print(f"\n{'=' * 60}")
        print("BROKEN URLs")
        print("=" * 60)
        for url, status, files in broken:
            print(f"\n  Status: {status}")
            print(f"  URL: {url}")
            print(f"  Found in:")
            for f in sorted(files):
                print(f"    - {f}")
    else:
        print("\n  ✓ All image URLs are working!")

    print()


if __name__ == "__main__":
    main()
