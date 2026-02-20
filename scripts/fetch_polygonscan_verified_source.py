#!/usr/bin/env python3
"""Fetch verified source files from a PolygonScan contract page.

This parser targets the rendered HTML blocks:
- "File X of N : <filename>"
- corresponding <pre class='js-sourcecopyarea editor' ...>...</pre>

Example:
  python3 scripts/fetch_polygonscan_verified_source.py \
    --address 0xb768891e3130f6df18214ac804d4db76c2c37730 \
    --out-dir contracts/negriskfeemodule2__0xb768891e3130f6df18214ac804d4db76c2c37730/verified_source
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import subprocess
from typing import List, Tuple

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch PolygonScan verified source files")
    p.add_argument("--address", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--url", default=None, help="Optional direct URL override")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    address = args.address.lower()
    url = args.url or f"https://polygonscan.com/address/{address}#code"

    html_text = requests.get(url, timeout=45).text

    # Pair each file label with its source block.
    # File label is in: <span class='text-muted'>File X of N : Name.sol</span>
    name_matches = list(re.finditer(r"File\s+\d+\s+of\s+\d+\s*:\s*([^<]+)</span>", html_text))
    pre_matches = list(
        re.finditer(
            r"<pre class='js-sourcecopyarea editor' id='editor\d+'[^>]*>(.*?)</pre>",
            html_text,
            re.S,
        )
    )

    if not name_matches or not pre_matches:
        # Fallback: curl often bypasses intermittent anti-bot HTML variants.
        html_text = subprocess.check_output(
            ["curl", "-L", "-s", "--max-time", "45", url]
        ).decode("utf-8", "ignore")
        name_matches = list(re.finditer(r"File\s+\d+\s+of\s+\d+\s*:\s*([^<]+)</span>", html_text))
        pre_matches = list(
            re.finditer(
                r"<pre class='js-sourcecopyarea editor' id='editor\d+'[^>]*>(.*?)</pre>",
                html_text,
                re.S,
            )
        )
        if not name_matches or not pre_matches:
            raise SystemExit("Could not parse source files from page")

    if len(name_matches) != len(pre_matches):
        # Keep best-effort pairing by index.
        min_len = min(len(name_matches), len(pre_matches))
        name_matches = name_matches[:min_len]
        pre_matches = pre_matches[:min_len]

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files: List[Tuple[str, pathlib.Path]] = []
    for nm, pm in zip(name_matches, pre_matches):
        filename = nm.group(1).strip()
        source = html.unescape(pm.group(1))

        # Normalize leading slashes and keep directories if provided.
        rel_path = pathlib.Path(filename.lstrip("/"))
        dst = out_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(source + "\n", encoding="utf-8")
        files.append((filename, dst))

    abi_match = re.search(
        r"<pre class='wordwrap js-copytextarea2[^>]*id='js-copytextarea2'[^>]*>(.*?)</pre>",
        html_text,
        re.S,
    )
    if abi_match:
        abi_text = html.unescape(abi_match.group(1)).strip()
        (out_dir / "ABI.json").write_text(abi_text + "\n", encoding="utf-8")

    meta = {
        "address": address,
        "url": url,
        "file_count": len(files),
        "files": [str(p.relative_to(out_dir)) for _, p in files],
        "has_abi": bool(abi_match),
    }
    (out_dir / "_source_fetch_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
