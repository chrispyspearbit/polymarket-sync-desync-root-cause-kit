#!/usr/bin/env python3
"""Defensive PoC for Polymarket nonce-desync settlement failures.

This script does two things:
1) Uses incident datasets to prove the nonce-mismatch failure pattern.
2) Simulates the off-chain acknowledgement bug where "executed" is set
   before on-chain finality, leaving stale state after a revert.

It is intentionally non-exploit and read-only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


ANCHOR_TX = "0xccba4c3668a87228c3cf8a84ea90b2f6893f7833317260ad6ae2b13f14b49362"


@dataclass
class Offender:
    address: str
    order_nonce: int
    chain_nonce: int
    side: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Defensive PoC: nonce desync root-cause demonstration")
    p.add_argument(
        "--failed-file",
        default="data/failed_nonce_mismatch_analysis.json",
        help="Path to failed nonce mismatch analysis json",
    )
    p.add_argument(
        "--increment-file",
        default="data/increment_nonce_calls_block_83173550_83173620.json",
        help="Path to incrementNonce call scan json",
    )
    p.add_argument("--anchor-tx", default=ANCHOR_TX, help="Anchor failed tx hash")
    p.add_argument("--json", action="store_true", help="Print machine-readable output")
    return p.parse_args()


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_offenders(row: Dict[str, Any]) -> List[Offender]:
    offenders: List[Offender] = []
    if not row.get("taker_valid", True):
        offenders.append(
            Offender(
                address=row["taker_maker"].lower(),
                order_nonce=int(row["taker_order_nonce"]),
                chain_nonce=int(row["taker_chain_nonce"]),
                side="taker",
            )
        )

    for mc in row.get("maker_checks", []):
        if not mc.get("valid", True):
            offenders.append(
                Offender(
                    address=mc["maker"].lower(),
                    order_nonce=int(mc["order_nonce"]),
                    chain_nonce=int(mc["chain_nonce"]),
                    side="maker",
                )
            )
    return offenders


def find_latest_increment_before(
    increments_by_addr: Dict[str, List[Dict[str, Any]]], address: str, block_num: int
) -> Dict[str, Any] | None:
    candidates = [r for r in increments_by_addr.get(address, []) if int(r["block"]) <= block_num]
    if not candidates:
        return None
    candidates.sort(key=lambda r: int(r["block"]))
    return candidates[-1]


def run_state_machine_demo(order_nonce: int, chain_nonce_before: int, chain_nonce_after: int) -> Dict[str, Any]:
    # Vulnerable off-chain flow (bug): execution marked before chain finality.
    offchain_status = "pending"
    offchain_status = "executed"

    chain_nonce = chain_nonce_before
    chain_nonce = chain_nonce_after  # incrementNonce happened prior to settlement inclusion
    onchain_success = order_nonce == chain_nonce

    if not onchain_success:
        onchain_status = "reverted"
        # Bug: no off-chain rollback on revert.
        offchain_status_after_settle = offchain_status
    else:
        onchain_status = "success"
        offchain_status_after_settle = "executed"

    # Correct flow: only mark executed on successful inclusion/finality.
    fixed_offchain_status = "executed" if onchain_success else "failed"

    return {
        "order_nonce": order_nonce,
        "chain_nonce_before": chain_nonce_before,
        "chain_nonce_after": chain_nonce_after,
        "onchain_status": onchain_status,
        "offchain_status_buggy": offchain_status_after_settle,
        "offchain_status_fixed": fixed_offchain_status,
    }


def main() -> int:
    args = parse_args()
    failed_path = Path(args.failed_file)
    inc_path = Path(args.increment_file)

    failed = load_json(str(failed_path))
    increments = load_json(str(inc_path))

    failed_rows = failed.get("rows", [])
    increment_rows = increments.get("rows", [])
    increments_by_addr: Dict[str, List[Dict[str, Any]]] = {}
    for r in increment_rows:
        addr = r["from"].lower()
        increments_by_addr.setdefault(addr, []).append(r)

    mismatch_txs = 0
    offenders_by_tx: Dict[str, List[Offender]] = {}
    offender_counter: Counter[str] = Counter()

    for row in failed_rows:
        offenders = collect_offenders(row)
        if offenders:
            mismatch_txs += 1
            offenders_by_tx[row["hash"].lower()] = offenders
            for off in offenders:
                offender_counter[off.address] += 1

    anchor = next((r for r in failed_rows if r["hash"].lower() == args.anchor_tx.lower()), None)
    if anchor is None:
        raise SystemExit(f"Anchor tx not found in dataset: {args.anchor_tx}")

    anchor_offenders = collect_offenders(anchor)
    if not anchor_offenders:
        raise SystemExit("Anchor tx has no nonce-mismatch offender in dataset")

    primary = anchor_offenders[0]
    prior_increment = find_latest_increment_before(increments_by_addr, primary.address, int(anchor["block"]))

    if prior_increment is None:
        anchor_increment_summary = None
    else:
        anchor_increment_summary = {
            "hash": prior_increment["hash"],
            "block": int(prior_increment["block"]),
            "time_utc": prior_increment["time_utc"],
            "from": prior_increment["from"],
            "selector": prior_increment["selector"],
            "status": int(prior_increment["status"]),
            "block_delta_to_anchor": int(anchor["block"]) - int(prior_increment["block"]),
        }

    demo = run_state_machine_demo(
        order_nonce=primary.order_nonce,
        chain_nonce_before=max(primary.chain_nonce - 1, 0),
        chain_nonce_after=primary.chain_nonce,
    )

    output = {
        "dataset_failed_count": int(failed.get("count", len(failed_rows))),
        "nonce_mismatch_failed_count": mismatch_txs,
        "anchor": {
            "tx": anchor["hash"],
            "block": int(anchor["block"]),
            "offender_address": primary.address,
            "offender_side": primary.side,
            "order_nonce": primary.order_nonce,
            "chain_nonce": primary.chain_nonce,
            "prior_increment": anchor_increment_summary,
        },
        "top_offenders": [{"address": a, "count": c} for a, c in offender_counter.most_common(5)],
        "state_machine_demo": demo,
        "root_cause": (
            "Orders were treated as executed off-chain before on-chain settlement finality. "
            "When a participant incremented nonce, stale matched orders reverted on-chain "
            "(InvalidNonce path), but buggy off-chain status could remain executed."
        ),
    }

    if args.json:
        print(json.dumps(output, indent=2))
        return 0

    print("== Defensive PoC: Off-chain/On-chain Nonce Desync ==")
    print(f"Failed matchOrders txs in dataset: {output['dataset_failed_count']}")
    print(f"Failed txs with decoded nonce mismatch: {output['nonce_mismatch_failed_count']}")
    print()
    print("Anchor proof:")
    print(
        f"- tx {output['anchor']['tx']} block {output['anchor']['block']} "
        f"offender={output['anchor']['offender_address']} ({output['anchor']['offender_side']}) "
        f"order_nonce={output['anchor']['order_nonce']} chain_nonce={output['anchor']['chain_nonce']}"
    )
    if output["anchor"]["prior_increment"]:
        pi = output["anchor"]["prior_increment"]
        print(
            f"- prior incrementNonce tx {pi['hash']} block {pi['block']} "
            f"(delta {pi['block_delta_to_anchor']} blocks, status={pi['status']})"
        )
    else:
        print("- no prior incrementNonce tx found for anchor offender in supplied window")

    print()
    print("Simple state-machine PoC:")
    demo = output["state_machine_demo"]
    print(
        f"- order_nonce={demo['order_nonce']} chain_nonce_before={demo['chain_nonce_before']} "
        f"chain_nonce_after={demo['chain_nonce_after']} -> onchain={demo['onchain_status']}"
    )
    print(f"- buggy offchain status after revert: {demo['offchain_status_buggy']}")
    print(f"- fixed offchain status after revert: {demo['offchain_status_fixed']}")
    print()
    print("Root cause:")
    print(f"- {output['root_cause']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
