#!/usr/bin/env python3
"""Inspect Polygon transaction hashes via JSON-RPC.

Examples:
  python3 scripts/inspect_txs.py --tx 0xccba... --tx 0xe3e7...
  python3 scripts/inspect_txs.py --tx-file data/txs.txt --out data/tx_details.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from typing import Any, Dict, List

import requests


DEFAULT_RPC = "https://polygon.publicnode.com"
SELECTOR_MAP = {
    "0x2287e350": "matchOrders",
    "0x627cdcb9": "incrementNonce",
    "0x6a761202": "redeemPositions?",
}


def rpc_call(session: requests.Session, rpc_url: str, method: str, params: List[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = session.post(rpc_url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error for {method}: {data['error']}")
    return data["result"]


def hex_to_int(x: str | None) -> int:
    if x is None:
        return 0
    return int(x, 16)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect tx hashes")
    p.add_argument("--rpc-url", default=DEFAULT_RPC)
    p.add_argument("--tx", action="append", default=[], help="Transaction hash (repeatable)")
    p.add_argument("--tx-file", default=None, help="Optional file with one tx hash per line")
    p.add_argument("--out", default=None, help="Optional output path (json)")
    return p.parse_args()


def load_hashes(args: argparse.Namespace) -> List[str]:
    hashes = list(args.tx)
    if args.tx_file:
        with open(args.tx_file, "r", encoding="utf-8") as f:
            for line in f:
                h = line.strip()
                if h and not h.startswith("#"):
                    hashes.append(h)

    deduped: List[str] = []
    seen = set()
    for h in hashes:
        h_l = h.lower()
        if h_l not in seen:
            seen.add(h_l)
            deduped.append(h_l)
    return deduped


def main() -> int:
    args = parse_args()
    hashes = load_hashes(args)
    if not hashes:
        raise SystemExit("No tx hashes provided")

    session = requests.Session()
    rows: List[Dict[str, Any]] = []

    for tx_hash in hashes:
        tx = rpc_call(session, args.rpc_url, "eth_getTransactionByHash", [tx_hash])
        receipt = rpc_call(session, args.rpc_url, "eth_getTransactionReceipt", [tx_hash])

        if tx is None:
            rows.append({"hash": tx_hash, "found": False})
            continue

        block_num = hex_to_int(tx.get("blockNumber"))
        block = rpc_call(session, args.rpc_url, "eth_getBlockByNumber", [tx.get("blockNumber"), False])
        ts = hex_to_int(block.get("timestamp")) if block else 0
        selector = (tx.get("input") or "")[:10].lower()

        rows.append(
            {
                "hash": tx_hash,
                "found": True,
                "time_utc": dt.datetime.utcfromtimestamp(ts).isoformat() + "Z",
                "block": block_num,
                "from": tx.get("from"),
                "to": tx.get("to"),
                "nonce": hex_to_int(tx.get("nonce")),
                "status": hex_to_int(receipt.get("status")) if receipt else None,
                "gas_used": hex_to_int(receipt.get("gasUsed")) if receipt else None,
                "selector": selector,
                "selector_name": SELECTOR_MAP.get(selector, "unknown"),
                "value_wei": hex_to_int(tx.get("value")),
            }
        )

    output = {
        "rpc_url": args.rpc_url,
        "count": len(rows),
        "rows": rows,
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
