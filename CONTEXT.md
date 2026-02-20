# CONTEXT.md

## Purpose
This file is a gist-ready context pack for an AI investigator to root-cause the Feb 19, 2026 Polymarket off-chain/on-chain settlement desync exploit pattern.

## Incident Snapshot (UTC)
- Incident date: **February 19, 2026**
- Primary contract involved in failed settlement calls: `0xb768891e3130f6df18214ac804d4db76c2c37730` (Polygonscan label: `Polymarket: Neg Risk Fee Module 2`)
- Confirmed failed anchor tx:
  - `0xccba4c3668a87228c3cf8a84ea90b2f6893f7833317260ad6ae2b13f14b49362`
  - `time_utc`: `2026-02-19T02:12:40Z`
  - `from`: `0xcf7f5083a0fcd7a3eba791514e6f8fae1b73f26a`
  - `to`: `0xb768891e3130f6df18214ac804d4db76c2c37730`
  - `selector`: `0x2287e350` (`matchOrders`)
  - `status`: `0` (reverted)

## Root-Cause Hypothesis
The exploitable condition appears to be a synchronization gap between:
- Off-chain order execution/acknowledgement (CLOB/API state)
- On-chain settlement finality (Polygon transaction success/failure)

Relevant on-chain code behavior:
- Exchange validation includes strict nonce checks (`isValidNonce` equality).
- Settlement paths revert at chain level if nonce/order checks fail.
- Fee-module-style wrappers call `exchange.matchOrders(...)` first; if that call fails, transaction reverts.

If an off-chain component marks orders as executed before final chain confirmation, bots can become directionally exposed.

## Confirmed On-Chain Evidence in This Repo

### 1) Failed `matchOrders` cluster in exploit window
- Data file: `data/failed_match_orders_block_83173550_83173620.json`
- Result: **16 reverted `matchOrders` txs** to `0xb768...` in ~71 blocks around the incident anchor.

### 2) Sender sequence around anchor failure (`0xcf7f...`)
- Data file: `data/cf7f_sender_sequence_block_83173550_83173620.json`
- Sequence includes successful calls before/after the failed tx:
  - Success: `0x3ba13ad8e32206409e97ab97f5a26c0e261e483e923faeba431ea51aadb5b80b`
  - Success: `0xe3e755e169acfe561a0cf17573853d53a0bcd3fa916179b8baa11c2aa2229cc4`
  - **Fail**: `0xccba4c3668a87228c3cf8a84ea90b2f6893f7833317260ad6ae2b13f14b49362`
  - Success: `0xf07642b3acba1ca9901a188c3043eba796574b4d60e3c6268109a39108aeff2c`
  - Success: `0xae99f63182570065bf2c72742bafa1be040d3a448842b390948977b4cac63a20`

### 3) Suspected attacker profile activity feed (off-chain context)
- Data file: `data/profile_activity_0x6e7e.json`
- Source URL: `https://polymarket.com/@0x6E7E227507569cAead21e5Cd32420197a6297282-1771437664429?via=history`
- Contains 30 activity tx hashes extracted from profile page `__NEXT_DATA__`.

### 4) Nonce-mismatch decode across failed tx corpus
- Data file: `data/failed_nonce_mismatch_analysis.json`
- Result: **15 / 16** reverted `matchOrders` txs include at least one stale order nonce (`order.nonce != nonces[maker]` at that block).
- Anchor tx decode (`0xccba...`) shows:
  - maker: `0x437eda540441a17af77852a9bb5f283682d02d3b`
  - maker order nonce in calldata: `0`
  - on-chain nonce at block `83173568`: `1`
  - nonce check fails (`InvalidNonce` path in exchange validation).

### 5) Direct `incrementNonce()` activity in same block window
- Data file: `data/increment_nonce_calls_block_83173550_83173620.json`
- Function selector: `0x627cdcb9` (`incrementNonce()`)
- Confirmed successful nonce bumps on `NegRiskCTFExchange (0xc5d...)`:
  - `0x793ca7ccd0394a287259b873137888d88fc0a13b8074101df1c1c42bc70c16ac` (block `83173551`, from `0x8cb943...`)
  - `0xfa4c8ac2a7d8b59d118f5266c93a3a3f10a597e7de164c6c4a7e932bdfcd9876` (block `83173566`, from `0x437eda...`)
  - `0xc57d75fc86112338bf1c83b91da0eabd2369158e2240c1393ef803a0b8e85b68` (block `83173580`, from `0x13078c...`)

### 6) Causality chain for anchor failure (fully on-chain)
1. `0xfa4c8ac2...` calls `incrementNonce()` for `0x437eda...` at block `83173566` (status `1`).
2. By block `83173568`, on-chain `nonces(0x437eda...) == 1`.
3. Anchor tx `0xccba...` (block `83173568`) includes maker order from `0x437eda...` with nonce `0`.
4. Exchange validation enforces equality (`isValidNonce`), so `matchOrders` reverts.
5. This proves stale order replay/match against advanced nonce state at settlement time.

## Addresses to Track
- Suspected attacker profile proxy wallet: `0x6e7e227507569caead21e5cd32420197a6297282`
- Failed tx sender (anchor): `0xcf7f5083a0fcd7a3eba791514e6f8fae1b73f26a`
- Neg Risk Fee Module 2 (incident settlement target): `0xb768891e3130f6df18214ac804d4db76c2c37730`
- Main CTFExchange (core exchange logic): `0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e`
- Neg Risk CTFExchange wrapper: `0xc5d563a36ae78145c45a50134d48a1215220f80a`
- Neg Risk FeeModule v1 source reference in repo: `0x78769d50be1763ed1ca0d5e878d93f05aabff29e`

## Relevant Code Material Included

### Core exchange nonce + order validation
- `contracts/ctfexchange__0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e/verified_source/src/exchange/mixins/NonceManager.sol`
  - `incrementNonce`
  - `isValidNonce` (strict equality)
- `contracts/ctfexchange__0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e/verified_source/src/exchange/mixins/Trading.sol`
  - `_validateOrder` (nonce/order validation)
  - `_performOrderChecks`
  - `_matchOrders`
- `contracts/ctfexchange__0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e/verified_source/src/exchange/CTFExchange.sol`
  - `matchOrders` / `fillOrder` entry points (`onlyOperator`)

### Fee module path
- `contracts/negriskfeemodule__0x78769d50be1763ed1ca0d5e878d93f05aabff29e/verified_source/lib/exchange-fee-module/src/FeeModule.sol`
  - `matchOrders` -> `exchange.matchOrders(...)` then `_refundFees(...)`
- `contracts/negriskfeemodule2__0xb768891e3130f6df18214ac804d4db76c2c37730/verified_source/FeeModule.sol`
  - exact incident-module code fetched from PolygonScan for `0xb768...`
- `contracts/negriskfeemodule2__0xb768891e3130f6df18214ac804d4db76c2c37730/verified_source/ABI.json`

### Wrappers
- `contracts/negriskctfexchange__0xc5d563a36ae78145c45a50134d48a1215220f80a/verified_source/src/NegRiskCtfExchange.sol`
- `contracts/negriskoperator__0x71523d0f655b41e805cec45b17163f528b59b820/verified_source/src/NegRiskOperator.sol`

## Exact On-Chain Query Instructions

## Option A: Use included scripts

1. Scan failed `matchOrders` calls in the incident window:
```bash
python3 scripts/scan_match_orders.py \
  --start-block 83173550 \
  --end-block 83173620 \
  --contract 0xb768891e3130f6df18214ac804d4db76c2c37730 \
  --only-failed
```

2. Follow one sender sequence around the failure:
```bash
python3 scripts/scan_match_orders.py \
  --start-block 83173550 \
  --end-block 83173620 \
  --contract 0xb768891e3130f6df18214ac804d4db76c2c37730 \
  --from-address 0xcf7f5083a0fcd7a3eba791514e6f8fae1b73f26a
```

3. Inspect specific tx hashes:
```bash
python3 scripts/inspect_txs.py --tx-file data/key_txs.txt
```

4. Extract profile activity tx hashes from Polymarket page payload:
```bash
python3 scripts/extract_polymarket_profile_activity.py \
  --profile-url 'https://polymarket.com/@0x6E7E227507569cAead21e5Cd32420197a6297282-1771437664429?via=history'
```

5. Scan nonce-bump calls in same incident window (`incrementNonce` on `0xc5d...`):
```bash
python3 scripts/scan_match_orders.py \
  --start-block 83173550 \
  --end-block 83173620 \
  --contract 0xc5d563a36ae78145c45a50134d48a1215220f80a \
  --selector 0x627cdcb9
```

6. Prove nonce state changed before a failed settle (anchor maker `0x437eda...`):
```bash
cast call 0xc5d563a36ae78145c45a50134d48a1215220f80a "nonces(address)(uint256)" \
  0x437eda540441a17af77852a9bb5f283682d02d3b \
  --rpc-url https://polygon.drpc.org --block 83173565

cast call 0xc5d563a36ae78145c45a50134d48a1215220f80a "nonces(address)(uint256)" \
  0x437eda540441a17af77852a9bb5f283682d02d3b \
  --rpc-url https://polygon.drpc.org --block 83173566

cast call 0xc5d563a36ae78145c45a50134d48a1215220f80a "nonces(address)(uint256)" \
  0x437eda540441a17af77852a9bb5f283682d02d3b \
  --rpc-url https://polygon.drpc.org --block 83173568
```

## Option B: Raw JSON-RPC methods
Use Polygon RPC:
- `eth_getTransactionByHash`
- `eth_getTransactionReceipt`
- `eth_getBlockByNumber`
- `eth_call` (for `nonces(address)` at historical block tags)

Minimal detection condition per tx:
- `to == 0xb768891e3130f6df18214ac804d4db76c2c37730`
- `input[:10] == 0x2287e350`
- `receipt.status == 0`

Nonce-desync corroboration:
- `to == 0xc5d563a36ae78145c45a50134d48a1215220f80a` and `input[:10] == 0x627cdcb9` in nearby blocks
- at failed match block, at least one decoded order maker has `order.nonce != nonces(maker)`

## What To Feed Your Scanner (minimum viable input pack)

1. **Smart contract code + ABI**
- Core exchange + mixins listed above
- FeeModule code and interfaces

2. **Address map**
- Exchange, fee module, wrappers, observed sender(s), suspected attacker wallet

3. **Tx corpus**
- Known failed tx set (`data/failed_match_orders_block_83173550_83173620.json`)
- Sender sequence (`data/cf7f_sender_sequence_block_83173550_83173620.json`)
- Nonce-bump call set (`data/increment_nonce_calls_block_83173550_83173620.json`)
- Nonce mismatch decode set (`data/failed_nonce_mismatch_analysis.json`)
- Key tx list (`data/key_txs.txt`, `data/key_tx_details.json`)

4. **Off-chain context**
- Profile activity extraction (`data/profile_activity_0x6e7e.json`)
- Polymarket relayer transaction-state docs (submitted/mined/confirmed)

5. **Heuristic checks**
- Off-chain “executed” records present while chain settlement tx status is `0`
- Burst of `matchOrders` reverts in narrow block windows
- Nonce-adjacent tx sequences with isolated reverts
- Successful `incrementNonce()` txs by participants immediately preceding failed `matchOrders`
- Reverted `matchOrders` where decoded maker/taker order nonces are stale vs historical `nonces(address)`

## Caveats / Confidence Flags
- Confirmed: the anchor failed tx and failed-window scan data in this repo.
- Confirmed: nonce and order-validation logic in included contract source.
- Confirmed: 3 successful `incrementNonce()` txs in-window align with repeated nonce-mismatch failures.
- Confirmed: `15/16` failed `matchOrders` txs in this window include at least one nonce mismatch.
- Unverified: several socially-circulated tx hashes from secondary posts were not found on-chain.
- Confirmed outlier: `1/16` failed `matchOrders` txs in-window is not nonce-related and reverts with `TRANSFER_FROM_FAILED` (`ERC20: transfer amount exceeds balance`) on collateral transfer path.

## Source Index
See:
- `docs/links.md`
- `sources/source_notes.md`
