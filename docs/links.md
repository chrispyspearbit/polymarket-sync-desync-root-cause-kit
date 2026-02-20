# Primary Links

## Polymarket docs
- System / CLOB intro: https://docs.polymarket.com/developers/CLOB/introduction
- Relayer transaction states (submitted/mined/confirmed): https://docs.polymarket.com/developers/CLOB/relayer/tx-state
- System contract addresses: https://docs.polymarket.com/developers/CTF/overview/addresses

## On-chain
- `CTFExchange` (Polygon): https://polygonscan.com/address/0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e#code
- `Neg Risk CTF Exchange`: https://polygonscan.com/address/0xc5d563a36ae78145c45a50134d48a1215220f80a#code
- `Neg Risk Fee Module 2` (incident tx target): https://polygonscan.com/address/0xb768891e3130f6df18214ac804d4db76c2c37730

## Incident tx anchors
- Confirmed failed tx (`matchOrders`, status=0):
  https://polygonscan.com/tx/0xccba4c3668a87228c3cf8a84ea90b2f6893f7833317260ad6ae2b13f14b49362
- Surrounding sender sequence (`0xcf7f...`):
  https://polygonscan.com/tx/0x3ba13ad8e32206409e97ab97f5a26c0e261e483e923faeba431ea51aadb5b80b
  https://polygonscan.com/tx/0xe3e755e169acfe561a0cf17573853d53a0bcd3fa916179b8baa11c2aa2229cc4
  https://polygonscan.com/tx/0xf07642b3acba1ca9901a188c3043eba796574b4d60e3c6268109a39108aeff2c
  https://polygonscan.com/tx/0xae99f63182570065bf2c72742bafa1be040d3a448842b390948977b4cac63a20
- In-window `incrementNonce()` confirmations (`0xc5d...`, selector `0x627cdcb9`):
  https://polygonscan.com/tx/0x793ca7ccd0394a287259b873137888d88fc0a13b8074101df1c1c42bc70c16ac
  https://polygonscan.com/tx/0xfa4c8ac2a7d8b59d118f5266c93a3a3f10a597e7de164c6c4a7e932bdfcd9876
  https://polygonscan.com/tx/0xc57d75fc86112338bf1c83b91da0eabd2369158e2240c1393ef803a0b8e85b68

## Social/reporting context
- X post (itslirrato): https://x.com/itslirrato/status/2024444009851072961
- Polymarket profile (suspected attacker):
  https://polymarket.com/@0x6E7E227507569cAead21e5Cd32420197a6297282-1771437664429?via=history
- Secondary summaries (use with caution):
  https://dropstab.com/blog/polymarket-bug-negrisk-fee-module
  https://phemex.com/news/article/polymarket-hacked-due-to-offchain-and-onchain-sync-flaw-61575
  https://www.kucoin.com/news/flash/polymarket-hacked-due-to-off-chain-and-on-chain-sync-vulnerability
