"""Verify Q78 saved logs, receipts, funding states/traces, graph and exact sums."""
import json
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import datetime

def read(p):return json.loads(Path(p).read_text())
def active(s):return s['balance']>0 or s['nonce']>0

def incoming(c,a,path=(),failed=False):
 failed=failed or bool(c.get('error'))
 if not failed and c.get('to','').lower()==a and int(c.get('value','0x0'),16)>0 and c.get('type')not in ['DELEGATECALL','STATICCALL','CALLCODE']:yield c,list(path)
 for i,x in enumerate(c.get('calls',[])):yield from incoming(x,a,path+(i,),failed)

def main():
 d=read('results.json');ts=d['transfers'];logs=read('logs_nodereal.json');extra=read('crosschecks.json')
 assert logs==read('logs_nownodes.json')and len(logs)==len(ts)==d['transfer_count']
 assert len({(t['tx_hash'],t['log_index'])for t in ts})==len(ts)
 assert len({t['recipient']for t in ts})==d['distinct_recipients']
 with localcontext()as ctx:
  ctx.prec=100
  assert sum(Decimal(t['amount'])for t in ts)==Decimal(d['total'])and Decimal(d['total'])*10**18==int(d['total_raw'])
  assert sum(Decimal(g['total'])for g in d['groups'])==Decimal(d['total'])
 bounds=d['boundaries'];start=int(datetime.fromisoformat('2026-10-28T05:00:00+00:00').timestamp());end=start+86400
 assert [b['block']for b in bounds]==[d['first_block']-1,d['first_block'],d['last_block'],d['last_block']+1]
 assert bounds[0]['timestamp']<start<=bounds[1]['timestamp']and bounds[2]['timestamp']<end<=bounds[3]['timestamp']
 headers=list(extra['boundary_headers'].values())
 for i,b in enumerate(bounds):
  assert headers[0][i]['hash']==headers[1][i]['hash']
  assert all(int(h[i]['timestamp'],16)==b['timestamp']and int(h[i]['number'],16)==b['block']for h in headers)
 assert int(extra['chain_id'],16)==56 and int(extra['token_decimals_hex'],16)==18
 for provider in ['nodereal','nownodes']:
  cached=[]
  for b in range(d['first_block'],d['last_block']+1,5000):cached+=read(f'log_cache/{provider}_{b}_{min(b+4999,d["last_block"])}.json')
  assert sorted(cached,key=lambda l:(int(l['blockNumber'],16),int(l['logIndex'],16)))==logs
 for t,l in zip(ts,logs):
  assert t['raw_log']==l and l['address'].lower()==d['token']and not l.get('removed',False)
  assert '0x'+l['topics'][1][-40:]==d['treasury']and '0x'+l['topics'][2][-40:]==t['recipient']
  assert int(l['data'],16)==int(t['amount_raw'])and l['transactionHash']==t['tx_hash']
  assert int(l['blockNumber'],16)==t['block']and int(l['logIndex'],16)==t['log_index']
  assert d['first_block']<=t['block']<=d['last_block']and start<=datetime.fromisoformat(t['cot']).timestamp()<end
  assert datetime.fromisoformat(t['utc'])==datetime.fromisoformat(t['cot'])
  e=read(f'receipts/{t["tx_hash"]}.json');r=e['receipt'];tx=e['transaction']
  assert r['status']=='0x1'and tx['hash']==r['transactionHash']==t['tx_hash']and tx['from'].lower()==t['tx_sender']==d['treasury']
  assert r['blockHash']==l['blockHash']and [x for x in r['logs']if int(x['logIndex'],16)==t['log_index']]==[l]
 fs={f['address']:f for f in d['first_funders']};rec={t['recipient']for t in ts};assert set(fs)==rec|{d['treasury']}
 states={s['address']:s for s in read('account_states.json')['states']};zero={s['address']:s for s in extra['dataseed_zero_state_snapshot']['states']}
 for a,f in fs.items():
  assert f['genesis_state']=={'balance':0,'nonce':0}and f['snapshot_state']==states[a]['latest']
  if not f.get('funder'):
   assert f['snapshot_state']==states[a]['audit_end']=={'balance':0,'nonce':0}
   assert zero[a]['balance']==zero[a]['nonce']==0 and zero[a]['code']==states[a]['code_at_snapshot']=='0x'
   continue
  assert f['before']=={'balance':0,'nonce':0}and f['after']['balance']>0 and f['after']['nonce']==0
  lo,hi=0,d['funding_snapshot']['latest_block']
  for p in f['search_checks']:
   assert p['block']==(lo+hi)//2
   if active(p):hi=p['block']
   else:lo=p['block']+1
  assert lo==hi==f['block']
  trace=read(f'traces/{f["block"]}.json');inc=[(c,path,x['txHash'])for x in trace for c,path in incoming(x.get('result',x),a)]
  c,path,h=inc[0];assert (c['from'].lower(),h,int(c['value'],16),path)==(f['funder'],f['tx_hash'],int(f['value_wei']),f['trace_path'])
  r=f['funding_receipt'];tx=f['funding_transaction']
  assert r['status']==f['receipt_status']=='0x1'and tx['hash']==r['transactionHash']==f['tx_hash']and int(tx['blockNumber'],16)==f['block']
  if not path:assert tx['from'].lower()==f['funder']and tx['to'].lower()==a and int(tx['value'],16)==int(f['value_wei'])
 adj={a:set()for a in fs}
 for a in fs:
  for b in fs:
   fa,fb=fs[a].get('funder'),fs[b].get('funder');treasury=d['treasury']
   if a!=b and ((fa and fa==fb)or(b==treasury and fa==treasury)or(a==treasury and fb==treasury)):adj[a].add(b)
 remaining=set(fs);components=set()
 while remaining:
  todo=[next(iter(remaining))];seen=set()
  while todo:
   a=todo.pop()
   if a in seen:continue
   seen.add(a);todo.extend(adj[a]-seen)
  remaining-=seen;components.add(frozenset(seen))
 assert components=={frozenset(g['members'])for g in d['groups']}and len(components)==d['group_count']
 for g in d['groups']:assert sum(int(t['amount_raw'])for t in ts if t['recipient']in g['recipients'])==int(g['total_raw'])
 assert {(t['tx_hash'],t['log_index'])for t in ts}=={(t['tx_hash'],t['log_index'])for t in d['unexplained_transfers']}
 page=Path('README.md').read_text()
 for t in ts:assert t['tx_hash']in page and t['amount']in page and t['recipient']in page
 for f in fs.values():
  if f.get('tx_hash'):assert f['tx_hash']in page
 assert page.rstrip().endswith('Auditor handle: 777sun77 (Taskmarket agent). Payout BSC wallet: 0x0cFe6b3D0B3CFcc95cdf793d8f99829E23aEdE2d')
 print(f"PASS: {len(ts)} transfers / {d['distinct_recipients']} recipients / {d['total']} FLAPJAX; blocks {d['first_block']}–{d['last_block']}; {d['group_count']} provisional groups, {d['unresolved_recipient_count']} unresolved first funders.")
if __name__=='__main__':main()
