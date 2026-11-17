from pathlib import Path
import json,statistics,math
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');d=json.loads((r/'outputs/range-selections.json').read_text());audit={}
for name,sel in d.items():
 if not name.endswith('_long'):continue
 candidates=[]
 for c in sel['candidates']:
  if not c['complete']:continue
  genres={}
  for genre,g in c['genres'].items():
   receipts=[json.loads((r/'bench'/case/'result.json').read_text()) for case in g['cases']]
   assert all(x['status']=='ok' and x['generated']==8192 and x['prompt_tokens']==209715 and not x.get('reused_tokens',0) for x in receipts),(name,c['identity'],genre)
   dec=statistics.median(x['tail_decode_tok_s'] for x in receipts)
   pre=statistics.median(x['prefill_tok_s'] for x in receipts)
   assert math.isclose(dec,g['decode'],rel_tol=1e-8)
   genres[genre]={'decode':dec,'prefill':pre,'cases':g['cases']}
  assert set(genres)=={'text','chat','story'}
  candidates.append({'identity':c['identity'],'genres':genres,'decode':min(x['decode'] for x in genres.values()),'prefill':min(x['prefill'] for x in genres.values())})
 peak=max(candidates,key=lambda c:c['decode']);eligible=[c for c in candidates if all(c['genres'][g]['decode']>=.95*peak['genres'][g]['decode'] for g in peak['genres'])];winner=max(eligible,key=lambda c:c['prefill'])
 selected=next(c for c in candidates if any(sel['selected'] in g['cases'] for g in c['genres'].values()))
 audit[name]={'status':'verified' if winner['identity']==selected['identity'] else 'selection_mismatch','scope':'Recorded complete 80% genre candidates;8192 output, no prefix reuse; not a global maximum or latest-release proof','peak':peak,'selected':selected,'prefill_winner':winner['identity'],'complete_candidates':len(candidates),'eligible_candidates':len(eligible)}
(r/'outputs/decode-first-receipt-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print({k:{x:v[x] for x in ['status','complete_candidates','eligible_candidates','prefill_winner']}for k,v in audit.items()})
