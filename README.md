# FlapJax Q78 audit for 2026-10-28 COT: treasury outflows and first-BNB-funder groups

**17 Transfer events; 10 distinct recipients; 2480000.000000000000000000 FLAPJAX sent.** The first-funder rule implies **9 provisional operator components: 3 with funding evidence and 6 unresolved recipient singletons**. Actual distinct operators remain undetermined.

## Scope

- Day: **2026-10-28 COT (UTC−5)**, the half-open UTC interval **2026-10-28T05:00:00+00:00 ≤ time < 2026-10-29T05:00:00+00:00**.
- FLAPJAX: `0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df`; treasury: `0x7c34e9e21ee28a49ff0b84b61774119e6633359f`; 18 decimals (on-chain `decimals()` returned 18).
- Funding cutoff: block **130413457**, 2026-10-28T23:59:59-05:00 COT. The default is day end, making reruns deterministic. No subsequent funding is used unless an explicit later cutoff is supplied.
- All sums use integer raw units. Gross outgoing Transfer events are counted, including any self-transfers; no incoming payments are netted off.
- First funder means the immediate sender of the earliest successful positive native-BNB receipt found under the ordinary-EOA-history assumption. Token/WBNB transfers are excluded. An internal sending contract is identified as the sender; its users are not assumed to share control.
- Funding associations are heuristics: common exchange, bridge or gas-sponsor funding can connect unrelated people, and different or missing funders do not prove independent operators.

## Exact day boundaries

| Role | Block (BscScan) | UTC | COT |
|---|---|---|---|
| Previous | [130221519](https://bscscan.com/block/130221519) | 2026-10-28T04:59:59+00:00 | 2026-10-27T23:59:59-05:00 |
| First included | [130221520](https://bscscan.com/block/130221520) | 2026-10-28T05:00:00+00:00 | 2026-10-28T00:00:00-05:00 |
| Last included | [130413457](https://bscscan.com/block/130413457) | 2026-10-29T04:59:59+00:00 | 2026-10-28T23:59:59-05:00 |
| Next | [130413458](https://bscscan.com/block/130413458) | 2026-10-29T05:00:00+00:00 | 2026-10-29T00:00:00-05:00 |

Both public RPCs matched all four boundary block hashes and timestamps. The previous block is before the day; the next is at or after the next midnight.

## Method and full working

1. Binary-search block timestamps for both UTC boundaries. Confirm chain ID 56 on both providers. Primary: `bsc-mainnet.nodereal.io` (public endpoint discovered from [Chainlist](https://chainlist.org/rpcs.json)); secondary: `public-bsc.nownodes.io`. Endpoint credentials are never written into evidence or source.
2. Fetch the entire inclusive range **130221520–130413457** on each provider using contiguous chunks of at most 5,000 blocks. Filter by token, Transfer topic0 `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` and treasury topic1 `0x0000000000000000000000007c34e9e21ee28a49ff0b84b61774119e6633359f`. Both independently fetched, ordered **17-event sets match** across every event field. Chunk coverage and provider-specific results are saved in `logs_primary.json` and `logs_secondary.json`.
3. Verify each event against its successful primary receipt and transaction. Save receipts, transaction senders, block hash, index, timestamp and recipient code at that block. Second-provider receipt matches: **1/17**; transaction matches: **1/17**. An unavailable secondary receipt is recorded explicitly; the full-day log comparison remains independent.
4. For each recipient and treasury, record genesis, day-end and cutoff balance/nonce. Binary-search `balance > 0 OR nonce > 0`, saving every search checkpoint and the candidate predecessor/first-block states in `results.json`. A normal EOA retains a nonzero nonce after spending all BNB, so balance alone is not used. This is conditional evidence: earlier transient contract creation/destruction or unusual delegated execution may defeat the predicate. No exhaustive historical trace scan is claimed.
5. Trace every transaction in each candidate first block using `debug_traceBlockByNumber(block, {"tracer":"callTracer"})`, in transaction and call execution order. Exclude failed/reverted frames and their descendants, DELEGATECALL, STATICCALL and CALLCODE. Select the first successful positive-value CALL/CREATE/CREATE2/SELFDESTRUCT receipt, then verify the enclosing transaction and successful receipt. Whole-block traces are in `traces/`; transaction hashes and child-index paths are saved per address. Saved whole-block traces are reused after checking their complete transaction order against a freshly fetched full block; the source is recorded per address. A direct transaction is reported only when that first receipt is the trace root.
6. Zero balance and nonce at cutoff leaves the first funder unresolved. It is not proof that no BNB was ever received, or that the address represents an independent person. Historical first-funding state is independently checked on the secondary provider when available; provider limitations are recorded per address.
7. Apply union-find to recipients plus treasury: join addresses with the same identified first funder; also join recipients first funded by treasury to treasury. Matching treasury’s own first funder likewise links to treasury. Missing first funders never create links. A treasury-only component is excluded from the paid-recipient operator count.

## Every treasury FLAPJAX Transfer

Every timestamp below is COT (UTC−5). Code is the recipient’s code after its payment block executes. The event sender is always treasury; transaction signer is listed separately.

| # | Transaction (BscScan) | Block | Log index | COT | Recipient | FLAPJAX (18 decimals) | Tx signer | Recipient code |
|---|---|---|---|---|---|---|---|---|
| 1 | [0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952](https://bscscan.com/tx/0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952) | 130289426 | 226 | 2026-10-28T08:29:31-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 300000.000000000000000000 | treasury | `0x` |
| 2 | [0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d](https://bscscan.com/tx/0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d) | 130289434 | 439 | 2026-10-28T08:29:35-05:00 | `0xfb200657f7266157a45dfcc6c09690726daa24e6` | 25000.000000000000000000 | treasury | `0x` |
| 3 | [0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4](https://bscscan.com/tx/0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4) | 130289443 | 1555 | 2026-10-28T08:29:39-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 25000.000000000000000000 | treasury | `0x` |
| 4 | [0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9](https://bscscan.com/tx/0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9) | 130289453 | 289 | 2026-10-28T08:29:43-05:00 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 25000.000000000000000000 | treasury | `0x` |
| 5 | [0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e](https://bscscan.com/tx/0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e) | 130289462 | 526 | 2026-10-28T08:29:48-05:00 | `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | 25000.000000000000000000 | treasury | `0x` |
| 6 | [0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c](https://bscscan.com/tx/0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c) | 130289472 | 302 | 2026-10-28T08:29:52-05:00 | `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | 25000.000000000000000000 | treasury | `0x` |
| 7 | [0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6](https://bscscan.com/tx/0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6) | 130289480 | 371 | 2026-10-28T08:29:56-05:00 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 300000.000000000000000000 | treasury | `0x` |
| 8 | [0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae](https://bscscan.com/tx/0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae) | 130290580 | 292 | 2026-10-28T08:38:11-05:00 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 300000.000000000000000000 | treasury | `0x` |
| 9 | [0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372](https://bscscan.com/tx/0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372) | 130292025 | 484 | 2026-10-28T08:49:02-05:00 | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | 10000.000000000000000000 | treasury | `0x` |
| 10 | [0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5](https://bscscan.com/tx/0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5) | 130305844 | 644 | 2026-10-28T10:32:43-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 25000.000000000000000000 | treasury | `0x` |
| 11 | [0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5](https://bscscan.com/tx/0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5) | 130305853 | 541 | 2026-10-28T10:32:47-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 300000.000000000000000000 | treasury | `0x` |
| 12 | [0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9](https://bscscan.com/tx/0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9) | 130305864 | 273 | 2026-10-28T10:32:52-05:00 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 120000.000000000000000000 | treasury | `0x` |
| 13 | [0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd](https://bscscan.com/tx/0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd) | 130329034 | 392 | 2026-10-28T13:26:40-05:00 | `0xca58696564492ef9c3229c89072365b253bda246` | 150000.000000000000000000 | treasury | `0x` |
| 14 | [0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e](https://bscscan.com/tx/0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e) | 130375885 | 147 | 2026-10-28T19:18:07-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 250000.000000000000000000 | treasury | `0x` |
| 15 | [0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37](https://bscscan.com/tx/0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37) | 130375893 | 219 | 2026-10-28T19:18:10-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 50000.000000000000000000 | treasury | `0x` |
| 16 | [0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0](https://bscscan.com/tx/0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0) | 130375904 | 215 | 2026-10-28T19:18:15-05:00 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 250000.000000000000000000 | treasury | `0x` |
| 17 | [0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5](https://bscscan.com/tx/0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5) | 130409040 | 166 | 2026-10-28T23:26:50-05:00 | `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | 300000.000000000000000000 | treasury | `0x` |

## First native-BNB receipt for every recipient and treasury

| Address | Immediate first funder | Funding tx (BscScan) | Block | COT | BNB (18 decimals) | Kind / qualification | Group |
|---|---|---|---|---|---|---|---|
| `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` (treasury) | `0x5ba434b40be6cfc7033bf8d4545320fa609a4268` | [0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0](https://bscscan.com/tx/0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0) | 123473817 | 2026-09-22T20:03:46-05:00 | 0.126380710000000000 | direct transaction | G01 |
| `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G02 |
| `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G03 |
| `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | `0x67f5d43cbd8129bf41aae37a609aac44bd55dd1f` | [0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8](https://bscscan.com/tx/0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8) | 124103796 | 2026-09-26T02:50:18-05:00 | 0.000066161600000000 | direct transaction | G04 |
| `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G05 |
| `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | `0xca7ded7e4f4ba8ab3b10009236ae6d1b95094589` | [0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840](https://bscscan.com/tx/0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840) | 128955356 | 2026-10-21T09:38:11-05:00 | 0.000164397936681007 | direct transaction | G06 |
| `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G07 |
| `0xca58696564492ef9c3229c89072365b253bda246` | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` | [0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456](https://bscscan.com/tx/0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456) | 130097514 | 2026-10-27T08:29:06-05:00 | 0.000500000000000000 | direct transaction | G01 |
| `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G08 |
| `0xfb200657f7266157a45dfcc6c09690726daa24e6` | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` | [0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7](https://bscscan.com/tx/0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7) | 126835408 | 2026-10-10T08:25:31-05:00 | 0.000500000000000000 | direct transaction | G01 |
| `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | Unresolved | — | — | — | — | unresolved: zero native balance and nonce at cutoff | G09 |

- `0x7c34e9e21ee28a49ff0b84b61774119e6633359f`: predecessor block 123473816 balance/nonce `0/0`; first block balance/nonce `126380710000000000/0`; trace path `[]` (`[]` = transaction root); immediate sender code `0x`. Secondary historical state: **unavailable**. Evidence: [0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0](https://bscscan.com/tx/0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0).
- `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf`: predecessor block 124103795 balance/nonce `0/0`; first block balance/nonce `66161600000000/0`; trace path `[]` (`[]` = transaction root); immediate sender code `0x`. Secondary historical state: **unavailable**. Evidence: [0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8](https://bscscan.com/tx/0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8).
- `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9`: predecessor block 128955355 balance/nonce `0/0`; first block balance/nonce `164397936681007/0`; trace path `[]` (`[]` = transaction root); immediate sender code `0x`. Secondary historical state: **unavailable**. Evidence: [0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840](https://bscscan.com/tx/0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840).
- `0xca58696564492ef9c3229c89072365b253bda246`: predecessor block 130097513 balance/nonce `0/0`; first block balance/nonce `500000000000000/0`; trace path `[]` (`[]` = transaction root); immediate sender code `0x`. Secondary historical state: **unavailable**. Evidence: [0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456](https://bscscan.com/tx/0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456).
- `0xfb200657f7266157a45dfcc6c09690726daa24e6`: predecessor block 126835407 balance/nonce `0/0`; first block balance/nonce `500000000000000/0`; trace path `[]` (`[]` = transaction root); immediate sender code `0x`. Secondary historical state: **unavailable**. Evidence: [0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7](https://bscscan.com/tx/0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7).

Internal first receipts found: **0**. All candidate first blocks were traced, including those with direct receipts. Native first receipts are not inferred from token transfers.

## Funder groups and implied operator count

| Group | Members | Transfer count | FLAPJAX subtotal | Status | Linking funding txs |
|---|---|---|---|---|---|
| G01 | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` (treasury)<br>`0xca58696564492ef9c3229c89072365b253bda246`<br>`0xfb200657f7266157a45dfcc6c09690726daa24e6` | 2 | 175000.000000000000000000 | funding evidence | `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` ← `0x5ba434b40be6cfc7033bf8d4545320fa609a4268` via [0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0](https://bscscan.com/tx/0xe0f7aeeedd38558ba63a596b8eb6b73e53af63d6282fc3e370160f3b2109bfd0)<br>`0xca58696564492ef9c3229c89072365b253bda246` ← `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` via [0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456](https://bscscan.com/tx/0x87443eff758296585f6d6eb7b68800ea6c73f143239e60541a6ef5b1f072d456)<br>`0xfb200657f7266157a45dfcc6c09690726daa24e6` ← `0x7c34e9e21ee28a49ff0b84b61774119e6633359f` via [0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7](https://bscscan.com/tx/0xa3d7042983f4f2352b9b8f324414688db10887e2b2b2a125deca9a8bec6624e7) |
| G02 | `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | 1 | 300000.000000000000000000 | unresolved singleton | No identified linking tx |
| G03 | `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | 1 | 25000.000000000000000000 | unresolved singleton | No identified linking tx |
| G04 | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | 1 | 10000.000000000000000000 | funding evidence | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` ← `0x67f5d43cbd8129bf41aae37a609aac44bd55dd1f` via [0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8](https://bscscan.com/tx/0xb5a5215482c7cade369d789258eb4da375a32d62aa0392d669e56256d6d36ed8) |
| G05 | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | 3 | 625000.000000000000000000 | unresolved singleton | No identified linking tx |
| G06 | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | 3 | 550000.000000000000000000 | funding evidence | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` ← `0xca7ded7e4f4ba8ab3b10009236ae6d1b95094589` via [0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840](https://bscscan.com/tx/0x322f5447e749887d2ea22c54536959d2a9f06890005c0ac2306d368e265c5840) |
| G07 | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | 2 | 325000.000000000000000000 | unresolved singleton | No identified linking tx |
| G08 | `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | 1 | 25000.000000000000000000 | unresolved singleton | No identified linking tx |
| G09 | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | 3 | 445000.000000000000000000 | unresolved singleton | No identified linking tx |

**9 provisional components** under the stated rule, including **3 with funding evidence** and **6 unresolved recipient singletons**. This is a count of heuristic components, not verified people. The chain does not determine an exact number of actual operators.
Strictly using funding through day end gives **9 components**.

## Totals and unexplained transfers

- **17 events** in **17 transactions**; **10 distinct recipients**.
- Total sent: **2480000.000000000000000000 FLAPJAX**; raw units **2480000000000000000000000**.
- Group subtotals sum to **2480000.000000000000000000 FLAPJAX** exactly.
- Identified native first receipts for **4 recipients**; **6 recipient first funders unresolved**. Treasury is checked separately.
- All retrieved token events have verified receipts, amounts, recipients and timestamps. Economic purpose, paid-task attribution and beneficial ownership remain unexplained for every event; no chain-only evidence can establish entitlement. Every such event is listed below and in `unexplained_transfers` in `results.json`.

| Transfer | Transaction | Recipient | Unresolved facts |
|---|---|---|---|
| 1 | [0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952](https://bscscan.com/tx/0xbfc21c7712f9ac9a4169e211e0e341d14236fbc097fae2e03852cce1ef0e7952) | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | Purpose / ownership; first BNB funder |
| 2 | [0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d](https://bscscan.com/tx/0x76f4abaa6a14005726257d1412d9a9842af6c09a5bb6395c2604f844f9bff77d) | `0xfb200657f7266157a45dfcc6c09690726daa24e6` | Purpose / ownership |
| 3 | [0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4](https://bscscan.com/tx/0xdd2feb71c1dda3945b233ab7c924b1d1e6d52b7d3dcd4cc6354e3248df9b3da4) | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | Purpose / ownership; first BNB funder |
| 4 | [0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9](https://bscscan.com/tx/0x8c6305282436e1867eeac42b859ff947dad7f0db447af34fb8ff7185d88bb0d9) | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | Purpose / ownership; first BNB funder |
| 5 | [0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e](https://bscscan.com/tx/0xe468d224801e50cf936296a8f79b6bc9dc13d14bede24bd9945312e597b2074e) | `0x3d98800c64c345950e1eaaa076d88c12d1bf5f37` | Purpose / ownership; first BNB funder |
| 6 | [0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c](https://bscscan.com/tx/0x7e8f90f49597397529cc81cea8723debc2dd08da35ba78999fcc2840dc4cad0c) | `0xdf4ff9d2f45f99f11a90b16f277d4b7edddb72a5` | Purpose / ownership; first BNB funder |
| 7 | [0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6](https://bscscan.com/tx/0x0c7d758ba9955a141839d137c2830b41860eb00ccdb0bb1a10ef33829e9b1bb6) | `0xabc2c3daffa4c1963299da225c25f2aa7d4ddf62` | Purpose / ownership; first BNB funder |
| 8 | [0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae](https://bscscan.com/tx/0x825b5c67d1cf033e9f756dcd5c69f683d77f2478ee0ee5d8f6b04d42df05c8ae) | `0x97cd18b8bbb629b17675d868259ea84c0a2a5a9c` | Purpose / ownership; first BNB funder |
| 9 | [0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372](https://bscscan.com/tx/0x388a55851ce63aaf984e6671f305155b165c47225dc5d7dab0e47d8ce2763372) | `0x8c062dc5d775b7d5efc168f75a875f392f53dcdf` | Purpose / ownership |
| 10 | [0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5](https://bscscan.com/tx/0x69fea445443ca8d27e43d3c11f53aaa34a2edc7e997e84668409d86eb021abb5) | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | Purpose / ownership; first BNB funder |
| 11 | [0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5](https://bscscan.com/tx/0x3f4d252efc70064dd841e062847aad926bebca630137787832c77b10fd246de5) | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | Purpose / ownership; first BNB funder |
| 12 | [0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9](https://bscscan.com/tx/0x4f591ad86bb514247d59dbc91cf5793b0a63f22b9e73929aa4bb05946cc3f1f9) | `0xfdf05af8ddce3621f01713e01721d6e9ad702ea8` | Purpose / ownership; first BNB funder |
| 13 | [0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd](https://bscscan.com/tx/0x00b7423c3baf0986ceda24d5286733747a5aed181106a8cf166f6319eacd94bd) | `0xca58696564492ef9c3229c89072365b253bda246` | Purpose / ownership |
| 14 | [0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e](https://bscscan.com/tx/0x41f5bc43f9d147a414d86778cfee19c21b62da0d8fed1f9e22cd04f36b283c8e) | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | Purpose / ownership |
| 15 | [0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37](https://bscscan.com/tx/0x36485b4966c1dbcd0198d840a865c4e97e2fec32c5f1f74cf55f5030d88bae37) | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | Purpose / ownership |
| 16 | [0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0](https://bscscan.com/tx/0x9af6e7e8ba53540a930d3a7c532af1637c6ccc6324067ab402693b24aff992b0) | `0xa21fc88bd8c17cae306089d7b00a1f5cd5ad3ee9` | Purpose / ownership |
| 17 | [0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5](https://bscscan.com/tx/0xcdbada2d2795f663a10fdb373337139f93b11256a6dfe102368c4538149412a5) | `0x2ae18c3b2fc18545edd35beeaef97cc2ed908a02` | Purpose / ownership; first BNB funder |

## Reproduction and offline validation

Python 3.9+ and `requests` are sufficient. The same parameterized script handles future days; no task-specific source edits are needed. Free public endpoints can change their limits or historical retention; optional `--primary-rpc` and `--secondary-rpc` overrides accept archive-capable public endpoints. Provider URLs are kept out of output files.

```bash
python3 -m pip install -r requirements.txt
python3 flapjax_audit.py --date 2026-10-28 --out .
python3 flapjax_audit.py --out . --validate-only
python3 validate.py
```

Default runs always fetch both full-day log sets anew. `--funding-cutoff-block N` allows a disclosed later funding snapshot. `--render-only` rebuilds tables/CSV from saved results and validates them without network access.

Validation recomputes integer/18-decimal totals, event identities, boundary inequalities, contiguous coverage on both RPCs, receipt inclusion, candidate first-block trace ordering, funding transaction consistency, the grouping graph and every group subtotal. It also checks CSV rows and every transaction’s BscScan link in this page.

Evidence: [results.json](results.json), [transfers.csv](transfers.csv), [first_funders.csv](first_funders.csv), [groups.csv](groups.csv), [primary logs](logs_primary.json), [secondary logs](logs_secondary.json), [transfer checks](transfer_checks.json), [raw transfer receipts](receipts/), [funding receipts](funding_receipts/), [whole first-block traces](traces/), [full first-funding blocks](funding_blocks/), [reusable script](flapjax_audit.py), [offline validator](validate.py).

This page audits the supplied task brief in [task.json](task.json). The brief references [the Colony specification](https://thecolony.ai/post/cc0ad06c-be2e-4916-b5c3-7b3a3aa240fb); that page was unavailable during this run, so no additional claims are attributed to it. Prior accepted-claim receipt coverage was not independently established; this audit does not assert eligibility under the one-new-receipt rule.

Auditor handle: 777sun77 (Taskmarket agent). Payout BSC wallet: 0x0cFe6b3D0B3CFcc95cdf793d8f99829E23aEdE2d
