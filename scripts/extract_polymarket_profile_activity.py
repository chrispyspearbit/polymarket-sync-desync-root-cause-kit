#!/usr/bin/env python3
"""Extract profile activity tx hashes from Polymarket profile HTML (__NEXT_DATA__).

Example:
  python3 scripts/extract_polymarket_profile_activity.py \
    --profile-url 'https://polymarket.com/@0x...?...' \
    --out data/profile_activity.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from typing import Any, Dict, List

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract Polymarket profile activity transactions")
    p.add_argument("--profile-url", required=True)
    p.add_argument("--out", default=None, help="Optional output path (json)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    html = requests.get(args.profile_url, timeout=30).text
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        # Fallback: requests can intermittently return a different HTML variant.
        html = subprocess.check_output(
            ["curl", "-L", "-s", "--max-time", "30", args.profile_url]
        ).decode("utf-8", "ignore")
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            raise SystemExit("Could not find __NEXT_DATA__ script block")

    data = json.loads(m.group(1))
    queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])

    rows: List[Dict[str, Any]] = []
    for q in queries:
        qk = q.get("queryKey", [])
        if len(qk) >= 3 and qk[0] == "profile" and qk[1] == "activity":
            pages = q.get("state", {}).get("data", {}).get("pages", [])
            for page in pages:
                rows.extend(page)

    condensed: List[Dict[str, Any]] = []
    seen = set()
    for r in rows:
        tx_hash = r.get("transactionHash")
        if not tx_hash:
            continue
        if tx_hash.lower() in seen:
            continue
        seen.add(tx_hash.lower())

        condensed.append(
            {
                "timestamp": r.get("timestamp"),
                "type": r.get("type"),
                "transactionHash": tx_hash,
                "proxyWallet": r.get("proxyWallet"),
                "title": r.get("title"),
                "side": r.get("side"),
                "usdcSize": r.get("usdcSize"),
                "price": r.get("price"),
            }
        )

    output = {
        "profile_url": args.profile_url,
        "count": len(condensed),
        "rows": sorted(condensed, key=lambda x: x.get("timestamp") or 0, reverse=True),
    }

    rendered = json.dumps(output, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
