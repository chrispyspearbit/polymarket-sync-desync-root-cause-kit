#!/usr/bin/env python3
"""Scan Polygon blocks for matchOrders calls to a target contract.

Examples:
  python3 scripts/scan_match_orders.py \
    --start-block 83173550 \
    --end-block 83173620 \
    --contract 0xb768891e3130f6df18214ac804d4db76c2c37730 \
    --only-failed

  python3 scripts/scan_match_orders.py \
    --start-block 83173550 \
    --end-block 83173620 \
    --contract 0xb768891e3130f6df18214ac804d4db76c2c37730 \
    --from-address 0xcf7f5083a0fcd7a3eba791514e6f8fae1b73f26a
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import Any, Dict, List

import requests


DEFAULT_RPC = "https://polygon.publicnode.com"
DEFAULT_SELECTOR = "0x2287e350"  # matchOrders


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
    p = argparse.ArgumentParser(description="Scan matchOrders calls in a block range")
    p.add_argument("--rpc-url", default=DEFAULT_RPC)
    p.add_argument("--start-block", type=int, required=True)
    p.add_argument("--end-block", type=int, required=True)
    p.add_argument("--contract", required=True, help="Target contract address")
    p.add_argument("--selector", default=DEFAULT_SELECTOR, help="Function selector hex")
    p.add_argument("--from-address", default=None, help="Optional sender filter")
    p.add_argument("--only-failed", action="store_true", help="Only include reverted txs")
    p.add_argument("--out", default=None, help="Optional output path (json)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    contract = args.contract.lower()
    selector = args.selector.lower()
    from_addr = args.from_address.lower() if args.from_address else None

    if args.start_block > args.end_block:
        raise SystemExit("--start-block must be <= --end-block")

    session = requests.Session()
    rows: List[Dict[str, Any]] = []

    for block_num in range(args.start_block, args.end_block + 1):
        block = rpc_call(session, args.rpc_url, "eth_getBlockByNumber", [hex(block_num), True])
        block_ts = hex_to_int(block.get("timestamp"))
        block_time = dt.datetime.utcfromtimestamp(block_ts).isoformat() + "Z"

        for tx in block.get("transactions", []):
            to = (tx.get("to") or "").lower()
            if to != contract:
                continue

            tx_from = (tx.get("from") or "").lower()
            if from_addr and tx_from != from_addr:
                continue

            tx_input = (tx.get("input") or "").lower()
            if not tx_input.startswith(selector):
                continue

            receipt = rpc_call(session, args.rpc_url, "eth_getTransactionReceipt", [tx["hash"]])
            status = hex_to_int(receipt.get("status"))
            if args.only_failed and status != 0:
                continue

            rows.append(
                {
                    "block": block_num,
                    "time_utc": block_time,
                    "hash": tx["hash"],
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "nonce": hex_to_int(tx.get("nonce")),
                    "selector": tx_input[:10],
                    "status": status,
                    "gas_used": hex_to_int(receipt.get("gasUsed")),
                    "tx_index": hex_to_int(tx.get("transactionIndex")),
                }
            )

    output = {
        "rpc_url": args.rpc_url,
        "contract": args.contract,
        "selector": args.selector,
        "from_address": args.from_address,
        "start_block": args.start_block,
        "end_block": args.end_block,
        "only_failed": args.only_failed,
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
