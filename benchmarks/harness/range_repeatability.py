"""Qualify all-genre minima and repeat the actual limiting workload before export."""
from range_common import *
import statistics,hashlib
key,family=sys.argv[1:3];GENRES=['text','chat','story']
state=read(O/'range-selections.json');plan=repeatability_plan(key)
if plan.exists():original=read(plan)
else:
 original=dict(selection=state[key+'_long'],metrics=state[key+'_long_metrics']);plan.write_text(json.dumps(original,indent=2))
from range_identity import config_id
if '--include-peak-code'in sys.argv and state.get(key+'_short',{}).get('selected'):
 case=state[key+'_short']['selected'];candidate=read(R/'bench'/case/'result.json')
 identities={config_id(read(R/'bench'/item['case']/'result.json')['config'])for item in original['selection']['candidates']}
 if config_id(candidate['config'])not in identities:
  original['selection']['candidates'].append(dict(case=case,prefill=candidate['prefill_tok_s'],decode=candidate['tail_decode_tok_s'],source='qualified peak-code preset with its own high-context genre matrix'))
  plan.write_text(json.dumps(original,indent=2))
groups={};original_coverage={}
for item in original['selection']['candidates']:
 r=read(R/'bench'/item['case']/'result.json');ident=config_id(r['config']);groups.setdefault(ident,dict(config=r['config'],results={g:[]for g in GENRES}))
for path in(R/'bench').glob('range-*/result.json'):
 r=read(path);c=r.get('config',{});genre=c.get('workload')
 if r.get('status')!='ok'or c.get('generate')!=8192 or genre not in GENRES or not r.get('cold_prefill_qualified',True):continue
 ident=config_id(c)
 if ident in groups:
  original_coverage.setdefault(ident,set()).add(genre)
  if c.get('host_memory_policy'):groups[ident]['results'][genre].append(r)
# Normalize the first pre-OOM sweep to the same isolated RAM policy as all later runs.
reference=read(R/'bench'/original['selection']['selected']/'result.json')['config']['workload']
for ident,group in groups.items():
 required=GENRES if len(original_coverage.get(ident,set()))==3 else ([reference]if not any(group['results'].values())else [])
 for genre in required:
  if not group['results'][genre]:
   r=run(group['config'],key+'-memory-check-'+ident+'-'+genre,family,genre)
   assert r['status']=='ok',r.get('error');group['results'][genre].append(r)
def summary():
 rows=[]
 for ident,group in groups.items():
  genres={g:dict(prefill=statistics.median(r['prefill_tok_s']for r in rs),decode=statistics.median(r['tail_decode_tok_s']for r in rs),samples=len(rs),cases=[name(r)for r in rs])for g,rs in group['results'].items()if rs}
  worst=min(genres,key=lambda g:genres[g]['decode'])
  rows.append(dict(identity=ident,complete=len(genres)==3,prefill=min(x['prefill']for x in genres.values()),decode=genres[worst]['decode'],worst_genre=worst,genres=genres))
 return rows
def measure(ident,genre,repeat=False):
 tag=key+('-range-repeat-'if repeat else'-range-check-')+ident+'-'+genre
 r=run(groups[ident]['config'],tag,family,genre);assert r['status']=='ok',r.get('error')
 rs=groups[ident]['results'][genre]
 if name(r)not in{name(x)for x in rs}:rs.append(r)
 else:raise RuntimeError('Repeated case already counted; selection made no progress')
# Every partial configuration has an upper bound on its all-genre minimum.
# Complete it only if it can improve decode or prefill within the current decode floor.
for iteration in range(8*len(groups)+12):
 stats=summary();complete=[x for x in stats if x['complete']];assert complete,'No complete initial all-genre configuration'
 peak=max(complete,key=lambda x:x['decode']);floor=.95*peak['decode'];winner=max([x for x in complete if x['decode']>=floor],key=lambda x:x['prefill'])
 promising=[x for x in stats if not x['complete']and(x['decode']>peak['decode']or(x['decode']>=floor and x['prefill']>winner['prefill']))]
 if promising:
  candidate=max(promising,key=lambda x:(x['decode'],x['prefill']))
  for genre in GENRES:
   if not groups[candidate['identity']]['results'][genre]:measure(candidate['identity'],genre)
  continue
 pending=next((x for x in [peak,winner]if x['genres'][x['worst_genre']]['samples']<2),None)
 if pending:
  measure(pending['identity'],pending['worst_genre'],repeat=True);continue
 break
else:raise RuntimeError('Global range qualification did not converge')
ident=winner['identity'];all_high=[r for rs in groups[ident]['results'].values()for r in rs];chosen=min(all_high,key=lambda r:r['tail_decode_tok_s']);c=chosen['config']
low=run(c,key+'-repeat-final-code-'+ident,family,'code');assert low['status']=='ok';lowcases=[dict(case=name(low),prefill=low['prefill_tok_s'],decode=low['tail_decode_tok_s'])]
oldlow=original['metrics']['low'];r=read(R/'bench'/oldlow['case']/'result.json')
if r['config'].get('host_memory_policy')and config_id(r['config'])==ident:lowcases.append(oldlow)
choice=dict(objective='Maximize the minimum cold prefill across three genres, subject to minimum sustained late decode across genre medians >=95% of the fastest measured complete configuration. Repeat the actual limiting genre of both winner and peak.',selected=name(chosen),peak_decode_tok_s=peak['decode'],decode_floor_tok_s=floor,candidates=stats,original_selection=original['selection'],free_generation_variation='Continuations can change draft acceptance. Final name uses the slowest actual paired measurement across all selected-setting genres and repeats; the selection floor uses per-genre medians. Cold process/prefix does not imply globally dropped OS file cache.')
save(key+'_long',choice);save(key+'_long_metrics',dict(low=min(lowcases,key=lambda x:x['decode']),low_cases=lowcases,high=summarize(all_high),repeatability=choice))
print('REPEATED ALL-GENRE RANGE COMPLETE',key,flush=True)

if '--include-peak-code'in sys.argv:subprocess.run([sys.executable,str(W/'mark_performance_qualified.py'),key],check=True)
