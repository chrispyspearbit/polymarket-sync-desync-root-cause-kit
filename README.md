# Polymarket Sync/Settlement Root-Cause Kit

This repo is a fast incident-analysis pack for the Feb 19, 2026 Polymarket sync/desync exploit pattern.

It includes:
- Curated Polymarket contract source artifacts (from verified Polygon deployments)
- A high-signal `CONTEXT.md` for AI agents
- Reproducible on-chain query scripts
- Precomputed datasets from a known exploit window
- Source notes and references

## Quick Start

1. Install deps:
```bash
python3 -m pip install -r requirements.txt
```

2. Read context first:
```bash
cat CONTEXT.md
```

3. Reproduce failed `matchOrders` scan around incident:
```bash
python3 scripts/scan_match_orders.py \
  --start-block 83173550 \
  --end-block 83173620 \
  --contract 0xb768891e3130f6df18214ac804d4db76c2c37730 \
  --only-failed
```

4. Verify key tx hashes:
```bash
python3 scripts/inspect_txs.py --tx-file data/key_txs.txt
```

5. Scan `incrementNonce()` calls in the same window (selector `0x627cdcb9`):
```bash
python3 scripts/scan_match_orders.py \
  --start-block 83173550 \
  --end-block 83173620 \
  --contract 0xc5d563a36ae78145c45a50134d48a1215220f80a \
  --selector 0x627cdcb9
```

6. (Optional) Re-fetch verified source for the live incident module:
```bash
python3 scripts/fetch_polygonscan_verified_source.py \
  --address 0xb768891e3130f6df18214ac804d4db76c2c37730 \
  --out-dir contracts/negriskfeemodule2__0xb768891e3130f6df18214ac804d4db76c2c37730/verified_source
```

## Repo Layout

- `CONTEXT.md`: gist-ready incident context for agents
- `contracts/`: relevant smart contract source + ABIs (curated from verified deployments)
- `scripts/`: on-chain and profile extraction tooling
- `data/`: extracted and validated incident datasets
- `sources/`: source notes with confidence and links
- `docs/`: primary links and investigation map

## Notes

- This is detection/forensics-focused. It does not include exploit execution instructions.
- Some social-reported tx hashes were not found on-chain and are marked unverified in `CONTEXT.md`.
- Nonce-mismatch decode data is precomputed in `data/failed_nonce_mismatch_analysis.json`.
