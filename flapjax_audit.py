#!/usr/bin/env python3
"""Reproducible FlapJax treasury audit, generalized from the Q74 workflow.

Run: python3 flapjax_audit.py --date YYYY-MM-DD --out DIR
Offline: python3 flapjax_audit.py --out DIR --validate-only
Only public, read-only JSON-RPC methods are used. Never reads wallet files.
"""
import argparse
import csv
import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

TOKEN = '0x90c8889f428f9ebb77bb8f15cad3a50a9ac680df'
TREASURY = '0x7c34e9e21ee28a49ff0b84b61774119e6633359f'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
COT = timezone(timedelta(hours=-5))
DIRECTORY = 'https://chainlist.org/rpcs.json'
WALLET = '0x0cFe6b3D0B3CFcc95cdf793d8f99829E23aEdE2d'
TRANSFER_TYPES = {'CALL', 'CREATE', 'CREATE2', 'SELFDESTRUCT', 'SUICIDE'}
LOG_FIELDS = ('address', 'topics', 'data', 'blockHash', 'blockNumber',
              'transactionHash', 'transactionIndex', 'logIndex')


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Several recipients may share a first block or a transaction with multiple logs.
    # Each writer needs its own temporary file before the atomic replacement.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.' + path.name,
                                     delete=False) as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
        temporary = Path(stream.name)
    temporary.replace(path)


def load(path):
    return json.loads(Path(path).read_text())


def dec(value):
    return f'{value // 10**18}.{value % 10**18:018d}'


def times(timestamp):
    return {'timestamp': timestamp,
            'utc': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
            'cot': datetime.fromtimestamp(timestamp, COT).isoformat()}


def txlink(tx):
    return f'[{tx}](https://bscscan.com/tx/{tx})'


def address(value):
    return f'`{value}`'


def canonical(log):
    return {key: log[key] for key in LOG_FIELDS}


def ordered(logs):
    return sorted((canonical(log) for log in logs),
                  key=lambda log: (int(log['blockNumber'], 16),
                                   int(log['transactionIndex'], 16),
                                   int(log['logIndex'], 16)))


def parallel(function, items, workers=5):
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(function, items))


class RPC:
    def __init__(self, url, name):
        self.url, self.name = url, name
        self.host = urlsplit(url).hostname

    def call(self, method, params):
        # Exceptions deliberately omit URLs, which may contain provider credentials.
        failure = 'request failed'
        for attempt in range(4):
            try:
                response = requests.post(self.url, json={
                    'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, timeout=45)
                response.raise_for_status()
                data = response.json()
                if 'result' in data:
                    return data['result']
                failure = f'JSON-RPC error code {data.get("error", {}).get("code", "unknown")}'
            except (requests.RequestException, ValueError) as error:
                failure = type(error).__name__
                if isinstance(error, requests.HTTPError) and error.response is not None:
                    failure += f' status {error.response.status_code}'
            if attempt < 3:
                time.sleep(attempt + 1)
        raise RuntimeError(f'{self.name}: {method}: {failure}')

    def block(self, number, full=False):
        value = self.call('eth_getBlockByNumber', [hex(number), full])
        if value is None:
            raise RuntimeError(f'{self.name}: missing block {number}')
        return value

    def state(self, addr, number):
        return {'balance': int(self.call('eth_getBalance', [addr, hex(number)]), 16),
                'nonce': int(self.call('eth_getTransactionCount', [addr, hex(number)]), 16)}

    def code(self, addr, number):
        return self.call('eth_getCode', [addr, hex(number)])


def public_primary():
    """Resolve the public directory entry at runtime; publish no API-key strings."""
    response = requests.get(DIRECTORY, timeout=30)
    response.raise_for_status()
    chain = next(chain for chain in response.json() if chain['chainId'] == 56)
    for entry in chain['rpc']:
        url = entry if isinstance(entry, str) else entry['url']
        if urlsplit(url).hostname == 'bsc-mainnet.nodereal.io' and url.startswith('https://'):
            return url
    raise RuntimeError('Public archive endpoint absent from Chainlist; supply --primary-rpc')


def lower_bound(rpc, timestamp, head):
    lo, hi = 0, head
    while lo < hi:
        middle = (lo + hi) // 2
        if int(rpc.block(middle)['timestamp'], 16) < timestamp:
            lo = middle + 1
        else:
            hi = middle
    return lo


def active(state):
    return state['balance'] > 0 or state['nonce'] > 0


def walk(frame, path=(), reverted=False):
    reverted = reverted or bool(frame.get('error')) or bool(frame.get('revertReason'))
    yield frame, path, reverted
    for index, child in enumerate(frame.get('calls', [])):
        yield from walk(child, path + (index,), reverted)


def incoming_traces(traces, addr):
    incoming = []
    for index, trace in enumerate(traces):
        root = trace.get('result', trace)
        for frame, path, reverted in walk(root):
            kind = frame.get('type', '').upper()
            if (not reverted and kind in TRANSFER_TYPES and
                    frame.get('to', '').lower() == addr and
                    int(frame.get('value', '0x0'), 16) > 0):
                amount = int(frame['value'], 16)
                incoming.append({'tx_hash': trace['txHash'], 'tx_order_in_block': index,
                                 'trace_path': list(path), 'from': frame['from'].lower(),
                                 'to': addr, 'type': kind, 'value_wei': str(amount),
                                 'value_bnb': dec(amount)})
    return incoming


def funding(rpc, secondary, addr, cutoff, last, out):
    print('First-funder search:', addr, flush=True)
    genesis, snapshot, day_end = rpc.state(addr, 0), rpc.state(addr, cutoff), rpc.state(addr, last)
    result = {'address': addr, 'genesis_state': genesis, 'snapshot_state': snapshot,
              'day_end_state': day_end, 'code_at_snapshot': rpc.code(addr, cutoff)}
    if active(genesis):
        result['status'] = 'unresolved: activity at genesis; no transaction funder established'
        return result
    if not active(snapshot):
        result['status'] = 'unresolved: zero native balance and nonce at cutoff'
        return result
    lo, hi, checks = 0, cutoff, []
    while lo < hi:
        middle = (lo + hi) // 2
        state = rpc.state(addr, middle)
        checks.append({'block': middle, **state})
        if active(state):
            hi = middle
        else:
            lo = middle + 1
    number = lo
    before, after = rpc.state(addr, number - 1), rpc.state(addr, number)
    assert not active(before) and active(after)
    result.update(candidate_first_block=number, before=before, after=after, search_checks=checks)
    block = rpc.block(number, True)
    save(out / 'funding_blocks' / f'{number}.json', block)
    result.update(times(int(block['timestamp'], 16)))
    trace_file = out / 'traces' / f'{number}.json'
    if trace_file.exists():
        trace = load(trace_file)
        result['trace_source'] = 'saved whole-block trace; transaction order checked against freshly fetched block'
    else:
        trace = rpc.call('debug_traceBlockByNumber', [hex(number), {'tracer': 'callTracer'}])
        result['trace_source'] = 'fresh debug_traceBlockByNumber response'
    assert isinstance(trace, list) and len(trace) == len(block['transactions'])
    # Normalize providers that omit txHash using the independently fetched full block.
    for raw, tx in zip(trace, block['transactions']):
        if raw.get('txHash'):
            assert raw['txHash'] == tx['hash']
        raw['txHash'] = tx['hash']
    save(trace_file, trace)
    incoming = incoming_traces(trace, addr)
    result['first_block_incoming_traces'] = incoming
    result['address_code_before_funding'] = rpc.code(addr, number - 1)
    result['address_code_after_funding'] = rpc.code(addr, number)
    if not incoming:
        result['status'] = 'unresolved: no successful native receipt in candidate block trace'
        return result
    first = incoming[0]
    tx = rpc.call('eth_getTransactionByHash', [first['tx_hash']])
    receipt = rpc.call('eth_getTransactionReceipt', [first['tx_hash']])
    assert receipt['status'] == '0x1'
    assert tx['hash'] == receipt['transactionHash'] == first['tx_hash']
    assert int(tx['blockNumber'], 16) == int(receipt['blockNumber'], 16) == number
    assert int(tx['transactionIndex'], 16) == first['tx_order_in_block']
    save(out / 'funding_receipts' / f'{first["tx_hash"]}.json', receipt)
    result.update(funder=first['from'], tx_hash=first['tx_hash'], block=number,
                  value_wei=first['value_wei'], value_bnb=first['value_bnb'],
                  trace_path=first['trace_path'], tx_sender=tx['from'].lower(),
                  funding_kind='internal transfer' if first['trace_path'] else 'direct transaction',
                  receipt_status=receipt['status'], funding_transaction=tx,
                  funder_code_at_funding=rpc.code(first['from'], number),
                  post_day=number > last,
                  status='identified under ordinary-EOA-history assumption')
    try:
        states = {'before': secondary.state(addr, number - 1), 'after': secondary.state(addr, number)}
        assert states == {'before': before, 'after': after}
        result['second_rpc_state'] = 'matched'
    except RuntimeError:
        result['second_rpc_state'] = 'unavailable'
    print('Identified:', addr, number, first['from'], result['funding_kind'], flush=True)
    return result


def group_results(data):
    recipients = sorted({t['recipient'] for t in data['transfers']})
    funders = {f['address']: f for f in data['first_funders']}

    def build(cutoff):
        parent = {a: a for a in set(recipients) | {TREASURY}}

        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            parent[root(a)] = root(b)

        seen = {}
        eligible = {a: f for a, f in funders.items() if f.get('funder') and f['block'] <= cutoff}
        for a, f in eligible.items():
            sender = f['funder']
            if sender in seen:
                union(a, seen[sender])
            seen[sender] = a
            if sender == TREASURY:
                union(a, TREASURY)
        components = {}
        for a in parent:
            components.setdefault(root(a), []).append(a)
        groups = []
        for members in sorted(components.values(), key=lambda m: (TREASURY not in m, sorted(m))):
            payees = sorted(set(members) & set(recipients))
            if not payees:
                continue  # Treasury alone is a reference, not an additional paid operator.
            transfers = [t for t in data['transfers'] if t['recipient'] in payees]
            total = sum(int(t['amount_raw']) for t in transfers)
            evidence = [eligible[a] for a in sorted(members) if a in eligible]
            groups.append({'id': f'G{len(groups)+1:02}', 'members': sorted(members),
                           'recipients': payees, 'total_raw': str(total), 'total': dec(total),
                           'transfer_count': len(transfers),
                           'status': 'funding evidence' if evidence else 'unresolved singleton',
                           'evidence': [{'recipient': f['address'], 'funder': f['funder'],
                                         'tx_hash': f['tx_hash'], 'block': f['block']} for f in evidence]})
        return groups

    data['groups'] = build(data['funding_cutoff_block'])
    data['day_end_groups'] = build(data['last_block'])
    data['group_count'] = len(data['groups'])
    data['unresolved_recipient_count'] = sum(not funders[a].get('funder') for a in recipients)
    data['evidenced_group_count'] = sum(bool(g['evidence']) for g in data['groups'])
    data['unexplained_transfers'] = [
        {'tx_hash': t['tx_hash'], 'log_index': t['log_index'], 'recipient': t['recipient'],
         'reason': 'Economic purpose and beneficial ownership cannot be established from the chain',
         'first_funder_unresolved': not bool(funders[t['recipient']].get('funder'))}
        for t in data['transfers']]


def write_csv(path, rows, fields):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join('---' for _ in headers) + '|'] +
                     ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows])


def report(data, out):
    ts, fs, groups = data['transfers'], data['first_funders'], data['groups']
    group_for = {a: g['id'] for g in groups for a in g['members']}
    rows = []
    for f in sorted(fs, key=lambda f: (f['address'] != TREASURY, f['address'])):
        label = address(f['address']) + (' (treasury)' if f['address'] == TREASURY else '')
        if f.get('funder'):
            rows.append([label, address(f['funder']), txlink(f['tx_hash']), f['block'], f['cot'],
                         f['value_bnb'], f['funding_kind'] + ('; post-day' if f['post_day'] else ''),
                         group_for.get(f['address'], 'treasury reference')])
        else:
            rows.append([label, 'Unresolved', '—', '—', '—', '—', f['status'],
                         group_for.get(f['address'], 'treasury reference')])
    group_rows = []
    for g in groups:
        evidence = '<br>'.join(address(e['recipient']) + ' ← ' + address(e['funder']) +
                               ' via ' + txlink(e['tx_hash']) for e in g['evidence'])
        group_rows.append([g['id'], '<br>'.join(address(a) + (' (treasury)' if a == TREASURY else '')
                                              for a in g['members']),
                           g['transfer_count'], g['total'], g['status'], evidence or 'No identified linking tx'])
    unresolved = [f for f in fs if f['address'] != TREASURY and not f.get('funder')]
    funded = [f for f in fs if f['address'] != TREASURY and f.get('funder')]
    internal = [f for f in fs if f.get('funding_kind') == 'internal transfer']
    checks = data['transfer_checks']
    title = data.get('task_title', f'FlapJax audit for {data["cot_day"]}')
    lines = [f'# {title}: treasury outflows and first-BNB-funder groups', '',
             f'**{len(ts)} Transfer events; {data["distinct_recipients"]} distinct recipients; '
             f'{data["total"]} FLAPJAX sent.** The first-funder rule implies '
             f'**{len(groups)} provisional operator components: {data["evidenced_group_count"]} '
             f'with funding evidence and {len(unresolved)} unresolved recipient singletons**. '
             'Actual distinct operators remain undetermined.', '',
             '## Scope', '',
             f'- Day: **{data["cot_day"]} COT (UTC−5)**, the half-open UTC interval '
             f'**{data["utc_start"]} ≤ time < {data["utc_end_exclusive"]}**.',
             f'- FLAPJAX: {address(TOKEN)}; treasury: {address(TREASURY)}; 18 decimals '
             f'(on-chain `decimals()` returned {data["token_decimals"]}).',
             f'- Funding cutoff: block **{data["funding_cutoff_block"]}**, '
             f'{data["funding_cutoff"]["cot"]} COT. The default is day end, making reruns deterministic. '
             'No subsequent funding is used unless an explicit later cutoff is supplied.',
             '- All sums use integer raw units. Gross outgoing Transfer events are counted, including '
             'any self-transfers; no incoming payments are netted off.',
             '- First funder means the immediate sender of the earliest successful positive native-BNB '
             'receipt found under the ordinary-EOA-history assumption. Token/WBNB transfers are excluded. '
             'An internal sending contract is identified as the sender; its users are not assumed to share control.',
             '- Funding associations are heuristics: common exchange, bridge or gas-sponsor funding can '
             'connect unrelated people, and different or missing funders do not prove independent operators.', '',
             '## Exact day boundaries', '',
             table(['Role', 'Block (BscScan)', 'UTC', 'COT'],
                   [[role, f'[{b["block"]}](https://bscscan.com/block/{b["block"]})', b['utc'], b['cot']]
                    for role, b in zip(['Previous', 'First included', 'Last included', 'Next'], data['boundaries'])]), '',
             'Both public RPCs matched all four boundary block hashes and timestamps. The previous '
             'block is before the day; the next is at or after the next midnight.', '',
             '## Method and full working', '',
             f'1. Binary-search block timestamps for both UTC boundaries. Confirm chain ID 56 on both providers. '
             f'Primary: `{data["providers"][0]["host"]}` (public endpoint discovered from '
             f'[Chainlist]({DIRECTORY})); secondary: `{data["providers"][1]["host"]}`. '
             'Endpoint credentials are never written into evidence or source.',
             f'2. Fetch the entire inclusive range **{data["first_block"]}–{data["last_block"]}** '
             'on each provider using contiguous chunks of at most 5,000 blocks. Filter by token, '
             f'Transfer topic0 `{TOPIC}` and treasury topic1 `0x{"0"*24}{TREASURY[2:]}`. '
             f'Both independently fetched, ordered **{len(ts)}-event sets match** across every event field. '
             'Chunk coverage and provider-specific results are saved in `logs_primary.json` and `logs_secondary.json`.',
             '3. Verify each event against its successful primary receipt and transaction. Save receipts, '
             'transaction senders, block hash, index, timestamp and recipient code at that block. '
             f'Second-provider receipt matches: **{sum(c["second_receipt"] == "matched" for c in checks)}/{len(checks)}**; '
             f'transaction matches: **{sum(c["second_transaction"] == "matched" for c in checks)}/{len(checks)}**. '
             'An unavailable secondary receipt is recorded explicitly; the full-day log comparison remains independent.',
             '4. For each recipient and treasury, record genesis, day-end and cutoff balance/nonce. '
             'Binary-search `balance > 0 OR nonce > 0`, saving every search checkpoint and the '
             'candidate predecessor/first-block states in `results.json`. A normal EOA retains a nonzero '
             'nonce after spending all BNB, so balance alone is not used. This is conditional evidence: '
             'earlier transient contract creation/destruction or unusual delegated execution may defeat '
             'the predicate. No exhaustive historical trace scan is claimed.',
             '5. Trace every transaction in each candidate first block using '
             '`debug_traceBlockByNumber(block, {"tracer":"callTracer"})`, in transaction and call execution '
             'order. Exclude failed/reverted frames and their descendants, DELEGATECALL, STATICCALL and '
             'CALLCODE. Select the first successful positive-value CALL/CREATE/CREATE2/SELFDESTRUCT receipt, '
             'then verify the enclosing transaction and successful receipt. Whole-block traces are in '
             '`traces/`; transaction hashes and child-index paths are saved per address. '
             'Saved whole-block traces are reused after checking their complete transaction order '
             'against a freshly fetched full block; the source is recorded per address. '
             'A direct transaction is reported only when that first receipt is the trace root.',
             '6. Zero balance and nonce at cutoff leaves the first funder unresolved. It is not proof '
             'that no BNB was ever received, or that the address represents an independent person. '
             'Historical first-funding state is independently checked on the secondary provider when '
             'available; provider limitations are recorded per address.',
             '7. Apply union-find to recipients plus treasury: join addresses with the same identified '
             'first funder; also join recipients first funded by treasury to treasury. Matching treasury’s '
             'own first funder likewise links to treasury. Missing first funders never create links. '
             'A treasury-only component is excluded from the paid-recipient operator count.', '',
             '## Every treasury FLAPJAX Transfer', '',
             'Every timestamp below is COT (UTC−5). Code is the recipient’s code after its payment '
             'block executes. The event sender is always treasury; transaction signer is listed separately.', '',
             table(['#', 'Transaction (BscScan)', 'Block', 'Log index', 'COT', 'Recipient',
                    'FLAPJAX (18 decimals)', 'Tx signer', 'Recipient code'],
                   [[i, txlink(t['tx_hash']), t['block'], t['log_index'], t['cot'], address(t['recipient']),
                     t['amount'], 'treasury' if t['tx_sender'] == TREASURY else address(t['tx_sender']),
                     address(t['recipient_code'])] for i, t in enumerate(ts, 1)]), '',
             '## First native-BNB receipt for every recipient and treasury', '',
             table(['Address', 'Immediate first funder', 'Funding tx (BscScan)', 'Block', 'COT',
                    'BNB (18 decimals)', 'Kind / qualification', 'Group'], rows), '']
    for f in [f for f in fs if f.get('funder')]:
        lines.append(f'- {address(f["address"])}: predecessor block {f["block"]-1} balance/nonce '
                     f'`{f["before"]["balance"]}/{f["before"]["nonce"]}`; first block balance/nonce '
                     f'`{f["after"]["balance"]}/{f["after"]["nonce"]}`; trace path '
                     f'`{f["trace_path"]}` (`[]` = transaction root); immediate sender code '
                     f'{address(f["funder_code_at_funding"])}. Secondary historical state: '
                     f'**{f["second_rpc_state"]}**. Evidence: {txlink(f["tx_hash"])}.')
    lines += ['', f'Internal first receipts found: **{len(internal)}**. '
              'All candidate first blocks were traced, including those with direct receipts. '
              'Native first receipts are not inferred from token transfers.', '',
              '## Funder groups and implied operator count', '',
              table(['Group', 'Members', 'Transfer count', 'FLAPJAX subtotal', 'Status', 'Linking funding txs'],
                    group_rows), '',
              f'**{len(groups)} provisional components** under the stated rule, including '
              f'**{data["evidenced_group_count"]} with funding evidence** and **{len(unresolved)} '
              'unresolved recipient singletons**. This is a count of heuristic components, not verified '
              'people. The chain does not determine an exact number of actual operators.',
              f'Strictly using funding through day end gives **{len(data["day_end_groups"])} components**.', '',
              '## Totals and unexplained transfers', '',
              f'- **{len(ts)} events** in **{len({t["tx_hash"] for t in ts})} transactions**; '
              f'**{data["distinct_recipients"]} distinct recipients**.',
              f'- Total sent: **{data["total"]} FLAPJAX**; raw units **{data["total_raw"]}**.',
              f'- Group subtotals sum to **{dec(sum(int(g["total_raw"]) for g in groups))} FLAPJAX** exactly.',
              f'- Identified native first receipts for **{len(funded)} recipients**; '
              f'**{len(unresolved)} recipient first funders unresolved**. Treasury is checked separately.',
              '- All retrieved token events have verified receipts, amounts, recipients and timestamps. '
              'Economic purpose, paid-task attribution and beneficial ownership remain unexplained '
              'for every event; no chain-only evidence can establish entitlement. Every such event is '
              'listed below and in `unexplained_transfers` in `results.json`.', '',
              table(['Transfer', 'Transaction', 'Recipient', 'Unresolved facts'],
                    [[i, txlink(t['tx_hash']), address(t['recipient']),
                      'Purpose / ownership' + ('; first BNB funder' if t['recipient'] in
                                               {f['address'] for f in unresolved} else '')]
                     for i, t in enumerate(ts, 1)]), '',
              '## Reproduction and offline validation', '',
              'Python 3.9+ and `requests` are sufficient. The same parameterized script handles future '
              'days; no task-specific source edits are needed. Free public endpoints can change their '
              'limits or historical retention; optional `--primary-rpc` and `--secondary-rpc` overrides '
              'accept archive-capable public endpoints. Provider URLs are kept out of output files.', '',
              '```bash', 'python3 -m pip install -r requirements.txt',
              f'python3 flapjax_audit.py --date {data["cot_day"]} --out .',
              'python3 flapjax_audit.py --out . --validate-only', 'python3 validate.py', '```', '',
              'Default runs always fetch both full-day log sets anew. `--funding-cutoff-block N` '
              'allows a disclosed later funding snapshot. `--render-only` rebuilds tables/CSV from '
              'saved results and validates them without network access.', '',
              'Validation recomputes integer/18-decimal totals, event identities, boundary inequalities, '
              'contiguous coverage on both RPCs, receipt inclusion, candidate first-block trace ordering, '
              'funding transaction consistency, the grouping graph and every group subtotal. It also '
              'checks CSV rows and every transaction’s BscScan link in this page.', '',
              'Evidence: [results.json](results.json), [transfers.csv](transfers.csv), '
              '[first_funders.csv](first_funders.csv), [groups.csv](groups.csv), '
              '[primary logs](logs_primary.json), [secondary logs](logs_secondary.json), '
              '[transfer checks](transfer_checks.json), [raw transfer receipts](receipts/), '
              '[funding receipts](funding_receipts/), [whole first-block traces](traces/), '
              '[full first-funding blocks](funding_blocks/), '
              '[reusable script](flapjax_audit.py), [offline validator](validate.py).', '',
              'This page audits the supplied task brief in [task.json](task.json). The brief references '
              '[the Colony specification](https://thecolony.ai/post/cc0ad06c-be2e-4916-b5c3-7b3a3aa240fb); '
              'that page was unavailable during this run, so no additional claims are attributed to it. '
              'Prior accepted-claim receipt coverage was not independently established; this audit '
              'does not assert eligibility under the one-new-receipt rule.', '',
              f'Auditor handle: 777sun77 (Taskmarket agent). Payout BSC wallet: {WALLET}']
    (out / 'README.md').write_text('\n'.join(lines) + '\n')
    write_csv(out / 'transfers.csv', [{**t, 'bscscan_url': f'https://bscscan.com/tx/{t["tx_hash"]}'} for t in ts],
              ['tx_hash', 'block', 'log_index', 'utc', 'cot', 'recipient', 'amount_raw', 'amount',
               'tx_sender', 'recipient_code', 'bscscan_url'])
    write_csv(out / 'first_funders.csv', [{**f, 'trace_path': json.dumps(f.get('trace_path')),
               'bscscan_url': f'https://bscscan.com/tx/{f["tx_hash"]}' if f.get('tx_hash') else ''} for f in fs],
              ['address', 'funder', 'tx_hash', 'block', 'utc', 'cot', 'value_wei', 'value_bnb',
               'funding_kind', 'trace_path', 'status', 'bscscan_url'])
    write_csv(out / 'groups.csv', [{**g, 'members': ';'.join(g['members']),
               'recipients': ';'.join(g['recipients']), 'funding_tx_hashes': ';'.join(e['tx_hash'] for e in g['evidence'])}
               for g in groups], ['id', 'members', 'recipients', 'transfer_count', 'total_raw', 'total',
                                 'status', 'funding_tx_hashes'])


def validate(out):
    data = load(out / 'results.json')
    start = int(datetime.combine(date.fromisoformat(data['cot_day']), datetime.min.time(), COT).timestamp())
    end = start + 86400
    bounds = data['boundaries']
    first, last = data['first_block'], data['last_block']
    assert [b['block'] for b in bounds] == [first-1, first, last, last+1]
    assert bounds[0]['timestamp'] < start <= bounds[1]['timestamp']
    assert bounds[2]['timestamp'] < end <= bounds[3]['timestamp']
    for b in bounds:
        assert b['primary_header']['hash'] == b['secondary_header']['hash']
        assert int(b['primary_header']['timestamp'], 16) == int(b['secondary_header']['timestamp'], 16) == b['timestamp']
        assert times(b['timestamp']) == {k: b[k] for k in ('timestamp', 'utc', 'cot')}
    assert data['funding_cutoff_block'] >= last
    assert data['token_decimals'] == 18
    assert data['providers'][0]['host'] != data['providers'][1]['host']
    logs = []
    for name in ('primary', 'secondary'):
        proof = load(out / f'logs_{name}.json')
        chunks = proof['chunks']
        assert chunks[0]['from_block'] == first and chunks[-1]['to_block'] == last
        previous, aggregate = first - 1, []
        for chunk in chunks:
            assert chunk['from_block'] == previous + 1
            assert chunk['from_block'] <= chunk['to_block'] <= chunk['from_block'] + 4999
            assert all(chunk['from_block'] <= int(l['blockNumber'], 16) <= chunk['to_block'] for l in chunk['logs'])
            aggregate.extend(chunk['logs'])
            previous = chunk['to_block']
        logs.append(ordered(aggregate))
        assert ordered(aggregate) == proof['logs']
    assert logs[0] == logs[1]
    ts = data['transfers']
    assert len(ts) == len(logs[0]) == data['transfer_count']
    assert ordered(t['raw_log'] for t in ts) == logs[0]
    assert len({(t['tx_hash'], t['log_index']) for t in ts}) == len(ts)
    assert len({t['recipient'] for t in ts}) == data['distinct_recipients']
    total = sum(int(t['amount_raw']) for t in ts)
    assert str(total) == data['total_raw'] and dec(total) == data['total']
    page = (out / 'README.md').read_text()
    for t in ts:
        log = t['raw_log']
        assert first <= t['block'] <= last and start <= t['timestamp'] < end
        assert log['address'].lower() == TOKEN and log['topics'][0] == TOPIC
        assert log['topics'][1].lower() == '0x' + '0'*24 + TREASURY[2:]
        assert t['recipient'] == '0x' + log['topics'][2][-40:].lower()
        assert int(log['data'], 16) == int(t['amount_raw'])
        assert t['amount'] == dec(int(t['amount_raw']))
        assert int(log['blockNumber'], 16) == t['block']
        assert int(log['logIndex'], 16) == t['log_index'] and log['transactionHash'] == t['tx_hash']
        assert times(t['timestamp']) == {k: t[k] for k in ('timestamp', 'utc', 'cot')}
        receipt = load(out / 'receipts' / f'{t["tx_hash"]}.json')
        assert receipt['status'] == '0x1' and receipt['blockHash'] == log['blockHash']
        assert receipt['transactionHash'] == t['tx_hash']
        assert canonical(log) in [canonical(l) for l in receipt['logs']]
        assert t['transaction']['from'].lower() == t['tx_sender']
        assert t['transaction']['hash'] == t['tx_hash']
        assert txlink(t['tx_hash']) in page and t['amount'] in page and t['recipient'] in page
    fs = data['first_funders']
    assert len(fs) == len({f['address'] for f in fs})
    assert {f['address'] for f in fs} == {t['recipient'] for t in ts} | {TREASURY}
    for f in fs:
        if not f.get('funder'):
            assert 'unresolved' in f['status']
            continue
        assert f['before'] == {'balance': 0, 'nonce': 0}
        assert f['genesis_state'] == {'balance': 0, 'nonce': 0}
        assert f['block'] == f['candidate_first_block'] <= data['funding_cutoff_block']
        incoming = incoming_traces(load(out / 'traces' / f'{f["block"]}.json'), f['address'])
        raw_trace = load(out / 'traces' / f'{f["block"]}.json')
        full_block = load(out / 'funding_blocks' / f'{f["block"]}.json')
        assert [t['txHash'] for t in raw_trace] == [t['hash'] for t in full_block['transactions']]
        assert int(full_block['timestamp'], 16) == f['timestamp']
        assert incoming == f['first_block_incoming_traces']
        event = incoming[0]
        assert (event['from'], event['tx_hash'], event['value_wei'], event['trace_path']) == (
            f['funder'], f['tx_hash'], f['value_wei'], f['trace_path'])
        assert dec(int(f['value_wei'])) == f['value_bnb']
        assert f['funding_kind'] == ('internal transfer' if f['trace_path'] else 'direct transaction')
        receipt = load(out / 'funding_receipts' / f'{f["tx_hash"]}.json')
        assert receipt['status'] == f['receipt_status'] == '0x1'
        assert receipt['transactionHash'] == f['tx_hash']
        assert receipt['blockHash'] == full_block['hash']
        assert int(receipt['blockNumber'], 16) == f['block']
        tx = f['funding_transaction']
        assert tx['hash'] == f['tx_hash'] and int(tx['blockNumber'], 16) == f['block']
        if not f['trace_path']:
            assert tx['from'].lower() == f['funder'] and tx['to'].lower() == f['address']
            assert int(tx['value'], 16) == int(f['value_wei'])
        lo, hi = 0, data['funding_cutoff_block']
        for check in f['search_checks']:
            assert check['block'] == (lo+hi)//2
            if active(check):
                hi = check['block']
            else:
                lo = check['block'] + 1
        assert lo == hi == f['block']
        assert txlink(f['tx_hash']) in page
    rebuilt = json.loads(json.dumps(data))
    group_results(rebuilt)
    for key in ('groups', 'day_end_groups', 'group_count', 'unresolved_recipient_count',
                'evidenced_group_count', 'unexplained_transfers'):
        assert rebuilt[key] == data[key]
    assert sum(int(g['total_raw']) for g in data['groups']) == total
    assert sum(len(g['recipients']) for g in data['groups']) == data['distinct_recipients']
    for g in data['groups']:
        assert g['total'] == dec(int(g['total_raw']))
    for filename, expected in [('transfers.csv', ts), ('first_funders.csv', fs), ('groups.csv', data['groups'])]:
        with (out / filename).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(expected)
        for row, item in zip(rows, expected):
            for key in ('tx_hash', 'recipient', 'address', 'id', 'amount_raw', 'amount', 'total_raw', 'total'):
                if key in row:
                    assert row[key] == str(item.get(key, ''))
    assert load(out / 'transfer_checks.json') == data['transfer_checks']
    print(f'PASS: {len(ts)} transfers / {data["distinct_recipients"]} recipients / {data["total"]} '
          f'FLAPJAX / {data["group_count"]} provisional groups; both complete RPC log sets match.', flush=True)


def run(args, out):
    day = date.fromisoformat(args.date)
    start = int(datetime.combine(day, datetime.min.time(), COT).timestamp())
    end = start + 86400
    primary = RPC(args.primary_rpc or public_primary(), 'primary')
    secondary = RPC(args.secondary_rpc, 'secondary')
    assert primary.host != secondary.host, 'Use two independent public providers'
    for rpc in (primary, secondary):
        assert int(rpc.call('eth_chainId', []), 16) == 56
    head = int(primary.call('eth_blockNumber', []), 16)
    assert int(primary.block(head)['timestamp'], 16) >= end, 'Requested day is not yet complete'
    first, last = lower_bound(primary, start, head), lower_bound(primary, end, head) - 1
    cutoff = args.funding_cutoff_block if args.funding_cutoff_block is not None else last
    assert last <= cutoff <= head
    bounds = []
    for number in (first-1, first, last, last+1):
        a, b = primary.block(number), secondary.block(number)
        assert a['hash'] == b['hash'] and a['timestamp'] == b['timestamp']
        bounds.append({'block': number, **times(int(a['timestamp'], 16)),
                       'primary_header': a, 'secondary_header': b})
    print(f'{day} COT: first block {first}; last block {last}; neighbours matched.', flush=True)
    providers = [{'name': rpc.name, 'host': rpc.host, 'chain_id': 56} for rpc in (primary, secondary)]
    log_sets = []
    for rpc in (primary, secondary):
        def chunk(number):
            stop = min(last, number+4999)
            logs = rpc.call('eth_getLogs', [{'address': TOKEN, 'fromBlock': hex(number),
                         'toBlock': hex(stop), 'topics': [TOPIC, '0x'+'0'*24+TREASURY[2:]]}])
            assert all(not log.get('removed', False) for log in logs)
            return {'from_block': number, 'to_block': stop, 'logs': logs}
        chunks = parallel(chunk, range(first, last+1, 5000))
        logs = ordered(log for chunk in chunks for log in chunk['logs'])
        save(out / f'logs_{rpc.name}.json', {'provider': rpc.host, 'chunks': chunks, 'logs': logs})
        log_sets.append(logs)
        print(rpc.name, 'complete log count:', len(logs), flush=True)
    assert log_sets[0] == log_sets[1], 'Independent full-day logs disagree'

    def detail(log):
        txhash, number = log['transactionHash'], int(log['blockNumber'], 16)
        tx = primary.call('eth_getTransactionByHash', [txhash])
        receipt = primary.call('eth_getTransactionReceipt', [txhash])
        assert receipt['status'] == '0x1'
        assert canonical(log) in [canonical(l) for l in receipt['logs']]
        assert receipt['blockHash'] == log['blockHash']
        save(out / 'receipts' / f'{txhash}.json', receipt)
        recipient = '0x' + log['topics'][2][-40:].lower()
        block = primary.block(number)
        assert block['hash'] == log['blockHash']
        amount = int(log['data'], 16)
        checks = {'tx_hash': txhash, 'log_index': int(log['logIndex'], 16), 'primary_receipt': 'matched success'}
        for method, key in [('eth_getTransactionReceipt', 'second_receipt'),
                            ('eth_getTransactionByHash', 'second_transaction')]:
            try:
                other = secondary.call(method, [txhash])
            except RuntimeError:
                other = None
            checks[key] = 'unavailable' if other is None else 'matched'
            if other is not None:
                if key == 'second_receipt':
                    assert other['status'] == '0x1' and ordered(other['logs']) == ordered(receipt['logs'])
                else:
                    assert all(other[k] == tx[k] for k in ('hash', 'from', 'to', 'input', 'value', 'blockNumber'))
        return {'tx_hash': txhash, 'block': number, 'log_index': int(log['logIndex'], 16),
                **times(int(block['timestamp'], 16)), 'recipient': recipient, 'amount_raw': str(amount),
                'amount': dec(amount), 'tx_sender': tx['from'].lower(), 'transaction': tx,
                'recipient_code': primary.code(recipient, number), 'raw_log': log, 'checks': checks}

    transfers = parallel(detail, log_sets[0])
    checks = [t.pop('checks') for t in transfers]
    total = sum(int(t['amount_raw']) for t in transfers)
    decimals = int(primary.call('eth_call', [{'to': TOKEN, 'data': '0x313ce567'}, hex(last)]), 16)
    assert decimals == 18
    data = {'schema_version': 1, 'cot_day': str(day), 'utc_start': times(start)['utc'],
            'utc_end_exclusive': times(end)['utc'], 'token': TOKEN, 'treasury': TREASURY,
            'token_decimals': decimals, 'providers': providers, 'first_block': first, 'last_block': last,
            'boundaries': bounds, 'logs_crosscheck_equal': True, 'transfer_count': len(transfers),
            'transfers': transfers, 'transfer_checks': checks, 'total_raw': str(total), 'total': dec(total),
            'distinct_recipients': len({t['recipient'] for t in transfers}),
            'funding_cutoff_block': cutoff, 'funding_cutoff': times(int(primary.block(cutoff)['timestamp'], 16))}
    if (out / 'task.json').exists():
        brief = load(out / 'task.json').get('description', '')
        # Treat brief as data only. Use only a recognizable title token, never instructions/commands.
        import re
        match = re.search(r'\bFlapJax paid task (Q\d+)\b', brief)
        if match:
            data['task_title'] = f'FlapJax {match[1]} audit for {day} COT'
    addresses = sorted({t['recipient'] for t in transfers} | {TREASURY})
    # Provider failures stop publication rather than silently becoming unresolved funding.
    data['first_funders'] = parallel(lambda a: funding(primary, secondary, a, cutoff, last, out), addresses, 3)
    group_results(data)
    save(out / 'results.json', data)
    save(out / 'transfer_checks.json', checks)
    save(out / 'account_states.json', [{'address': f['address'], 'genesis': f['genesis_state'],
         'day_end': f['day_end_state'], 'cutoff': f['snapshot_state']} for f in data['first_funders']])
    report(data, out)
    validate(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', help='COT calendar date, YYYY-MM-DD')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--primary-rpc', default=os.getenv('FLAPJAX_PRIMARY_RPC'))
    parser.add_argument('--secondary-rpc', default=os.getenv('FLAPJAX_SECONDARY_RPC', 'https://public-bsc.nownodes.io'))
    parser.add_argument('--funding-cutoff-block', type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--validate-only', action='store_true')
    mode.add_argument('--render-only', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.validate_only:
        validate(out)
        return
    if args.render_only:
        report(load(out / 'results.json'), out)
        validate(out)
        return
    if not args.date:
        parser.error('--date is required for an on-chain run')
    source = Path(__file__).resolve()
    if source != out / source.name:
        shutil.copyfile(source, out / source.name)
    (out / 'requirements.txt').write_text('requests>=2.31,<3\n')
    (out / 'validate.py').write_text('"""Offline audit consistency checks; no RPC calls."""\n'
        'from pathlib import Path\nfrom flapjax_audit import validate\n'
        'if __name__ == "__main__":\n    validate(Path(__file__).resolve().parent)\n')
    run(args, out)


if __name__ == '__main__':
    main()
