# FlapJax Q78 audit: treasury FLAPJAX outflows on 2026-10-28 COT and first-BNB-funder grouping

**17 transfers in 17 transactions; 10 distinct recipients; 2480000.000000000000000000 FLAPJAX sent.** The requested first-funder rule yields **9 provisional groups**: 3 with funding evidence and 6 unresolved singletons. **Actual distinct operators cannot be determined from this evidence.**

## Scope and assumptions

**This audit covers treasury outflow receipts (transaction hashes) from 2026-10-28 COT only.** Earlier transactions below are first-BNB-funding evidence, not additional audited FLAPJAX outflows.

- Chain: BNB Smart Chain mainnet, chain ID 56. Token: `0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df`. Treasury: `0x7c34e9e21ee28a49ff0b84b61774119e6633359f`.
- Window: 2026-10-28 00:00:00–23:59:59 COT (fixed UTC−5), equivalent to 2026-10-28 05:00:00–2026-10-29 04:59:59 UTC.
- Token decimals: **18**, independently checked with `eth_call` to `decimals()` at day end. All sums use raw integers. Amounts have exactly 18 decimal places. These are gross Transfer-event outflows; incoming transfers are not netted.
- Funding cutoff: block **130490857**, 2026-10-29T14:41:14+00:00 / 2026-10-29T09:41:14-05:00. Funding evidence may predate or follow the outflow day; all identified first receipts in this audit predate the day, so the groups are identical at day end and at this cutoff.
- “First funder” means the immediate sender of the earliest successful positive native-BNB receipt found under the ordinary-EOA-history assumption described below. WBNB token transfers do not qualify. Internal funding is attributed to the immediate sending contract, if present, rather than guessed from a transaction signer.
- First-funder groups are heuristic associations, not identities. Custodial services and gas sponsors can fund unrelated users; multiple groups can also belong to one person.

## Exact block boundaries

| Role | Block | UTC timestamp | COT timestamp |
|---|---|---|---|
| Previous (excluded) | [130221519](https://bscscan.com/block/130221519) | 2026-10-28T04:59:59+00:00 | 2026-10-27T23:59:59-05:00 |
| First included | [130221520](https://bscscan.com/block/130221520) | 2026-10-28T05:00:00+00:00 | 2026-10-28T00:00:00-05:00 |
| Last included | [130413457](https://bscscan.com/block/130413457) | 2026-10-29T04:59:59+00:00 | 2026-10-28T23:59:59-05:00 |
| Next (excluded) | [130413458](https://bscscan.com/block/130413458) | 2026-10-29T05:00:00+00:00 | 2026-10-29T00:00:00-05:00 |

The boundary timestamps match on both RPCs. The previous and next blocks fall outside the requested interval. The next block is the first block at or after 2026-10-29 05:00:00 UTC.

## Method and verification

1. Binary-searched `eth_getBlockByNumber` timestamps on `https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3`. Verified both endpoints and their neighbours against `https://public-bsc.nownodes.io`; retained all four headers from each endpoint in [crosschecks.json](crosschecks.json).
2. Requested `eth_getLogs` over **every block 130221520–130413457**, using contiguous chunks of at most 5,000 blocks. Filtered token address, Transfer topic0 and treasury topic1. Both complete ordered **17-log sets match exactly**, including block hashes, transaction hashes, log indexes, topics and values. Raw data: [NodeReal](logs_nodereal.json), [NOWNodes](logs_nownodes.json), and [per-chunk cache](log_cache/).
3. Re-read all 17 `eth_getTransactionByHash` transactions and successful `eth_getTransactionReceipt` receipts on NodeReal. Every receipt contains the exact event. Every transaction signer is treasury. `eth_getCode(recipient, transferBlock)` returned `0x` for all recipients. NOWNodes supplied **1** individual matching receipt/transaction; the other 16 were unavailable there. Raw receipts and transactions are in [receipts/](receipts/).
4. Used archive `eth_getBalance` and `eth_getTransactionCount` on NodeReal to binary-search **balance > 0 OR nonce > 0**, starting at genesis. Balance alone can fall back to zero after spending; an ordinary EOA spend increments the persistent nonce. Recorded each search probe, zero genesis state, zero predecessor balance/nonce, and first active state in `results.json`. For all five identified addresses (four recipients plus treasury), the first block ends with nonce 0 and positive balance.
5. Fetched each candidate block with full transactions and traced the **entire block** using `debug_traceBlockByNumber(block, {"tracer":"callTracer"})`. Traversed transactions/calls in execution order, excluded reverted frames and non-value-transferring call types, and selected the first successful positive BNB receipt. All five are direct transactions; no internal-transfer exception was found. Checked each cited transaction and successful receipt on NodeReal. Raw traces: [traces/](traces/).
6. Six recipients have zero balance and nonce at day end and the fixed funding cutoff, plus empty code at the cutoff. Independently rechecked their zero balance, zero nonce and empty code on `https://bsc-dataseed.bnbchain.org` at block **130490986** (2026-10-29T14:42:12+00:00 / 2026-10-29T09:42:12-05:00). In an ordinary EOA history, they have no BNB funding yet. No first-funder transaction is invented for them.
7. Used union-find over every recipient plus treasury. Joined addresses sharing an identified first funder; joined recipients first funded by treasury to treasury. Treasury’s own first-funder entry participates in shared-funder matching. Unresolved addresses remain provisional singletons.

**Earliest-history limitation:** the activity predicate is monotone for ordinary EOAs, including when a funded wallet later spends its entire balance. A historically created/destroyed contract or transient contract execution can evade such a search. This audit does not trace every block since genesis to exclude all such histories. Zero predecessor state alone is therefore not an unconditional proof of no earlier native receipts. No code was present before or after any identified first-funding block, and all identified funders also had empty code at their funding block.

**Provider limits:** NOWNodes did not serve the historical funding states or any of the five cited funding transactions/receipts. bloXroute also returned no transactions/receipts for those five hashes. PublicNode required a personal token for archive state; BNB dataseed lacked the old trie state. First-funding evidence is re-checkable on the public NodeReal endpoint, with raw evidence retained, but is not claimed to have independent second-provider confirmation. Only public BSC RPC data was used; no explorer history, private keys or private account data was used.

## Every treasury FLAPJAX transfer

All times below are COT (UTC−5). **“Treasury” in the tx-sender column means `0x7c34e9e21ee28a49ff0b84b61774119e6633359f`**. The event sender is also treasury in every row. Recipient code is measured at the end of the transfer block.

| # | Transaction (BscScan) | Block | Log index | COT time | Recipient | FLAPJAX (18 decimals) | Tx sender | Recipient code |
|---|---|---|---|---|---|---|---|---|
| 1 | [0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952](https://bscscan.com/tx/0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952) | 130289426 | 226 | 2026-10-28T08:29:31-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 300000.000000000000000000 | Treasury | 0x (empty) |
| 2 | [0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d](https://bscscan.com/tx/0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d) | 130289434 | 439 | 2026-10-28T08:29:35-05:00 | `0xfb200657f7266157a45dfcc6c09690726daa24e6` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 3 | [0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4](https://bscscan.com/tx/0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4) | 130289443 | 1555 | 2026-10-28T08:29:39-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 4 | [0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9](https://bscscan.com/tx/0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9) | 130289453 | 289 | 2026-10-28T08:29:43-05:00 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 5 | [0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e](https://bscscan.com/tx/0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e) | 130289462 | 526 | 2026-10-28T08:29:48-05:00 | `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 6 | [0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c](https://bscscan.com/tx/0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c) | 130289472 | 302 | 2026-10-28T08:29:52-05:00 | `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 7 | [0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6](https://bscscan.com/tx/0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6) | 130289480 | 371 | 2026-10-28T08:29:56-05:00 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 300000.000000000000000000 | Treasury | 0x (empty) |
| 8 | [0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae](https://bscscan.com/tx/0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae) | 130290580 | 292 | 2026-10-28T08:38:11-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 300000.000000000000000000 | Treasury | 0x (empty) |
| 9 | [0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372](https://bscscan.com/tx/0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372) | 130292025 | 484 | 2026-10-28T08:49:02-05:00 | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | 10000.000000000000000000 | Treasury | 0x (empty) |
| 10 | [0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5](https://bscscan.com/tx/0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5) | 130305844 | 644 | 2026-10-28T10:32:43-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 25000.000000000000000000 | Treasury | 0x (empty) |
| 11 | [0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5](https://bscscan.com/tx/0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5) | 130305853 | 541 | 2026-10-28T10:32:47-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 300000.000000000000000000 | Treasury | 0x (empty) |
| 12 | [0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9](https://bscscan.com/tx/0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9) | 130305864 | 273 | 2026-10-28T10:32:52-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 120000.000000000000000000 | Treasury | 0x (empty) |
| 13 | [0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd](https://bscscan.com/tx/0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd) | 130329034 | 392 | 2026-10-28T13:26:40-05:00 | `0xca58696564492ef9c3229c89072365b253bda246` | 150000.000000000000000000 | Treasury | 0x (empty) |
| 14 | [0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e](https://bscscan.com/tx/0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e) | 130375885 | 147 | 2026-10-28T19:18:07-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 250000.000000000000000000 | Treasury | 0x (empty) |
| 15 | [0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37](https://bscscan.com/tx/0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37) | 130375893 | 219 | 2026-10-28T19:18:10-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 50000.000000000000000000 | Treasury | 0x (empty) |
| 16 | [0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0](https://bscscan.com/tx/0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0) | 130375904 | 215 | 2026-10-28T19:18:15-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 250000.000000000000000000 | Treasury | 0x (empty) |
| 17 | [0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5](https://bscscan.com/tx/0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5) | 130409040 | 166 | 2026-10-28T23:26:50-05:00 | `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | 300000.000000000000000000 | Treasury | 0x (empty) |

## First native-BNB receipt for every recipient and treasury

UTC and COT times refer to the funding block. “No receipt identified” means no funding tx was found for a zero-state address, under the stated ordinary-EOA assumption; it does not assert an independent operator. Every resolved row was freshly searched and verified on chain for Q78, including addresses seen in an earlier audit.

| Address | Immediate first funder | Funding tx (BscScan) | Block | UTC | COT | BNB received (18 decimals) | Kind / qualification | Group |
|---|---|---|---|---|---|---|---|---|
| `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` (treasury) | `0x5ba434b40be6cfc7033bf8d4545320fa609a4268` | [0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0](https://bscscan.com/tx/0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0) | 123473817 | 2026-09-23T01:03:46+00:00 | 2026-09-22T20:03:46-05:00 | 0.126380710000000000 | direct transaction | G01 |
| `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G04 |
| `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G05 |
| `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | `0x67f5d43cbd8129bf41aae37a609aac44bd55dd1f` | [0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8](https://bscscan.com/tx/0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8) | 124103796 | 2026-09-26T07:50:18+00:00 | 2026-09-26T02:50:18-05:00 | 0.000066161600000000 | direct transaction | G02 |
| `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G06 |
| `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | `0xca7ded7e4f4ba8ab3b10009236ae6d1b95094589` | [0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840](https://bscscan.com/tx/0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840) | 128955356 | 2026-10-21T14:38:11+00:00 | 2026-10-21T09:38:11-05:00 | 0.000164397936681007 | direct transaction | G03 |
| `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G07 |
| `0xca58696564492ef9c3229c89072365b253bda246` | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` | [0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456](https://bscscan.com/tx/0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456) | 130097514 | 2026-10-27T13:29:06+00:00 | 2026-10-27T08:29:06-05:00 | 0.000500000000000000 | direct transaction | G01 |
| `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G08 |
| `0xfb200657f7266157a45dfcc6c09690726daa24e6` | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` | [0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7](https://bscscan.com/tx/0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7) | 126835408 | 2026-10-10T13:25:31+00:00 | 2026-10-10T08:25:31-05:00 | 0.000500000000000000 | direct transaction | G01 |
| `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | No receipt identified | — | — | — | — | — | Balance 0; nonce 0; empty code at cutoff | G09 |

## Groups and implied operators

G01 links two recipients with treasury through their separate first-BNB-funding transactions. Treasury’s own first-funder tx anchors the comparison; no other audited recipient shares that upstream funder. G02 and G03 each have a distinct identified first funder and no shared-funder edge to another audited address. G04–G09 have no first-funder evidence.

| Group | Members | FLAPJAX received in day | Evidence status | Linking funder transaction(s) |
|---|---|---|---|---|
| G01 | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` (treasury)<br>`0xca58696564492ef9c3229c89072365b253bda246`<br>`0xfb200657f7266157a45dfcc6c09690726daa24e6` | 175000.000000000000000000 | funding evidence | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` ← `0x5ba434b40be6cfc7033bf8d4545320fa609a4268` via [0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0](https://bscscan.com/tx/0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0) (block 123473817)<br>`0xca58696564492ef9c3229c89072365b253bda246` ← `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` via [0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456](https://bscscan.com/tx/0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456) (block 130097514)<br>`0xfb200657f7266157a45dfcc6c09690726daa24e6` ← `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` via [0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7](https://bscscan.com/tx/0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7) (block 126835408) |
| G02 | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | 10000.000000000000000000 | funding evidence | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` ← `0x67f5d43cbd8129bf41aae37a609aac44bd55dd1f` via [0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8](https://bscscan.com/tx/0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8) (block 124103796) |
| G03 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 550000.000000000000000000 | funding evidence | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` ← `0xca7ded7e4f4ba8ab3b10009236ae6d1b95094589` via [0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840](https://bscscan.com/tx/0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840) (block 128955356) |
| G04 | `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | 300000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |
| G05 | `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | 25000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |
| G06 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 625000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |
| G07 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 325000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |
| G08 | `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | 25000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |
| G09 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 445000.000000000000000000 | unresolved singleton | No first-funder tx identified; no linking evidence |

**Implied count under the rule: 9 provisional operator groups** (3 funding-evidenced components and 6 unresolved singletons). This is a graph count, not a verified count of people or controllers. The six unfunded addresses cannot be linked or separated by a first-funder test. Actual distinct operators remain **undetermined**.

## Totals and unexplained transfers

- **17 Transfer events**, each in a distinct successful transaction.
- **10 distinct recipients**; **2480000.000000000000000000 FLAPJAX** sent.
- Exact raw sum: **2480000000000000000000000**. Group subtotals sum to that same integer.
- **4 recipients** have verified first native receipts; treasury’s first receipt is recorded separately. **6 recipients** have no first funding identified.
- No recipient had contract code at its FLAPJAX receipt block. No pool/contract recipient or internal first-BNB transfer was identified.
- Every token movement is accounted for. **The economic purpose and beneficial ownership of all 17 transfers (rows #1–#17) remain unexplained from chain data alone.** Each hash is linked in the full table and listed individually in `results.json.unexplained_transfers`; funding associations do not explain why payments were made.

The following transfers also lack first-BNB-funder attribution:

| Recipient | Transfers (BscScan) | FLAPJAX subtotal | Unresolved fact |
|---|---|---|---|
| `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | #17: [0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5](https://bscscan.com/tx/0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5) | 300000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |
| `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | #5: [0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e](https://bscscan.com/tx/0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e) | 25000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |
| `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | #1: [0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952](https://bscscan.com/tx/0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952)<br>#3: [0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4](https://bscscan.com/tx/0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4)<br>#8: [0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae](https://bscscan.com/tx/0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae) | 625000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |
| `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | #4: [0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9](https://bscscan.com/tx/0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9)<br>#7: [0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6](https://bscscan.com/tx/0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6) | 325000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |
| `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | #6: [0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c](https://bscscan.com/tx/0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c) | 25000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |
| `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | #10: [0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5](https://bscscan.com/tx/0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5)<br>#11: [0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5](https://bscscan.com/tx/0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5)<br>#12: [0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9](https://bscscan.com/tx/0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9) | 445000.000000000000000000 | Zero balance and nonce at day end and funding cutoff; no first-funder tx identified |

## Reproduction

Python 3 and `requests` are sufficient. Run in this folder; the scripts do not read wallet keys. Public services may change limits or history retention. The NodeReal URL is a public endpoint inherited from the supplied earlier audit, not a wallet credential.

```bash
cd /workspace/flapjax/q78
python3 -m pip install --user --break-system-packages requests
python3 probe_rpc.py
python3 scan.py
python3 funders.py
python3 verify_funding.py
python3 verify_transfers.py
python3 crosscheck.py
python3 report.py
python3 validate.py
```

`scan.py` binary-searches this day, caches per-provider log chunks and requires both full log sets to agree. To force fresh log reads, remove `log_cache/` first. `funders.py` uses the published cutoff in `account_states.json` (block 130490857) when that file exists; on a fresh run without it, the script takes a new head snapshot. Keeping this file reproduces the published funding cutoff. `verify_funding.py` uses saved full-block traces when present; remove `traces/` to fetch them again. `verify_transfers.py` freshly reads all transfer receipts. `crosscheck.py` saves boundary headers, checks chain ID and decimals, and repeats additional public-node checks (its dataseed snapshot is a new head). `report.py` rebuilds the groups and this page. `validate.py` independently checks raw logs, receipts, funding traces, first-state evidence, the grouping graph and all exact sums offline.

To recheck a token movement, call `eth_getTransactionReceipt(txHash)` and find the decimal log index in the table. For direct funding, call `eth_getBlockByNumber(hex(block), true)` and inspect the cited tx’s `from`, `to` and `value`, then verify successful receipt status. To check that no earlier receipt occurred within the candidate block, run `debug_traceBlockByNumber(hex(block), {"tracer":"callTracer"})`. An internal receipt, if encountered on a future rerun, can also be checked with `debug_traceTransaction(txHash, {"tracer":"callTracer"})`; the immediate sending contract and call path must be recorded. Reproduce the ordinary-EOA earliest-activity search with `eth_getBalance` and `eth_getTransactionCount` at genesis and each recorded probe, predecessor and candidate block.

Exact log filter:

```json
{
  "address": "0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df",
  "fromBlock": "0x7c305d0",
  "toBlock": "0x7c5f391",
  "topics": [
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    "0x0000000000000000000000007c34e9e21ee28a49ff0b84b61774119e6633359f"
  ]
}
```

Primary RPC: `https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3`. Second RPC: `https://public-bsc.nownodes.io`.

Evidence: [results.json](results.json), [account states](account_states.json), [receipt checks](transfer_checks.json), [cross-checks and headers](crosschecks.json), [endpoint probes](rpc_probes.json), [NodeReal logs](logs_nodereal.json), [NOWNodes logs](logs_nownodes.json), [receipts](receipts/), [funding traces](traces/).

Auditor handle: 777sun77 (Taskmarket agent). Payout BSC wallet: 0x0cFe6b3D0B3CFcc95cdf793d8f99829E23aEdE2d
