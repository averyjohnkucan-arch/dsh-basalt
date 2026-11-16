"""Dedicated 8K-code peak preset, retaining full configured context and measured long ranges."""
from range_tuner import *
from range_identity import config_id
import statistics
key,family=sys.argv[1:3]
subprocess.run([sys.executable,str(W/'range_joint_refine.py'),key,family],check=True)
state=read(O/'range-selections.json');long_selection=state[key+'_long'];long_metrics=state[key+'_long_metrics']
base=read(R/'bench'/long_selection['selected']/'result.json')['config'];long_id=config_id(base)
candidates={long_id:base}
def add(c):candidates.setdefault(config_id(c),c)
prior=state.get(key+'_short',{})
if prior.get('selected'):
 r=read(R/'bench'/prior['selected']/'result.json')
 if r['status']=='ok':add(r['config'])
for item in prior.get('candidates',[]):
 case=item.get('case')or next(iter(item.get('cases',[])),None)
 if case:
  r=read(R/'bench'/case/'result.json')
  if r['status']=='ok':add(r['config'])
# Reuse the broad compatible/native/graphs/head screens already run for NInfer.
prefixes=[case_name(key),case_name(key.replace('_','-'))]
if key.endswith('_basalt'):prefixes.append(case_name(key[:-7]+'-basalt'))
screens=[]
for path in(R/'bench').glob('range-*/result.json'):
 if '-low-screen-'not in path.parent.name or not any(path.parent.name.startswith(p+'-')for p in prefixes):continue
 r=read(path)
 if r.get('status')=='ok'and r['config'].get('depth')==8192:screens.append(r)
for r in sorted(screens,key=lambda r:r['tail_decode_tok_s'],reverse=True)[:2]:add(r['config'])
if not key.endswith('_ninfer'):
 if family=='qwen':
  if key.endswith('_basalt'):
   ranking=W/'saved-expert-profiles/flash-basalt.prof';ranked=changed(base,{'--expert-profile':ranking,'--kv-resident':20480});ranked['expert_profile_source']=str(ranking);add(ranked)
  for spec in [4,6,8]:add(changed(base,{'--kv-resident':20480,'--spec':spec}))
  for workers in [14,8]:add(changed(base,{'--kv-resident':20480,'--pool-workers':workers}))
  add(changed(base,{'--kv-resident':20480,'--vram-reserve-mib':256}))
  add(changed(base,{'--kv-resident':20480,'--vram-reserve-mib':256,'--pool-workers':14}))
  if key.endswith('_strata'):
   add(changed(base,{'--kv-resident':20480,'--pcie-frac':.75}))
   if not key.startswith('gyro'):
    mtp=copy.deepcopy(base)
    for flag in ['--draft','--draft-model','--draft-fallback','--draft-cap','--draft-conf']:opt(mtp,flag,None)
    add(changed(mtp,{'--kv-resident':20480,'--spec':6}))
    add(changed(base,{'--kv-resident':20480,'--draft':'dflash2','--draft-model':R/'packs/flash-dflash2.pack','--draft-fallback':'none','--spec':8,'--draft-cap':8,'--draft-conf':.55}))
 elif family=='qwen27b':
  for spec in [4,6,8]:add(changed(base,{'--kv-resident':20480,'--spec':spec}))
 elif family=='deepseek':
  for spec in [0,4,6]:
   if key.endswith('_basalt'):add(changed(base,{'--spec':spec}))
  for workers in [8,12,21]:add(changed(base,{'--pool-workers'if key.endswith('_basalt')else'--cpu-threads':workers}))
full={ident:[]for ident in candidates}
for path in(R/'bench').glob('range-*/result.json'):
 r=read(path);c=r.get('config',{})
 if r.get('status')!='ok'or c.get('workload')!='code'or c.get('depth')!=8192 or c.get('generate')!=8192 or not c.get('host_memory_policy')or not r.get('cold_prefill_qualified',True):continue
 ident=config_id(c)
 if ident in full:full[ident].append(r)
ranks=[]
for ident,c in candidates.items():
 if full[ident]:proxy=statistics.median(r['tail_decode_tok_s']for r in full[ident])
 else:
  r=run(c,key+'-peak-code-screen-'+ident,family,'code',n=2048,role='short-code decode screen only')
  if r['status']!='ok':continue
  assert config_id(r['config'])==ident,'Artifact or executable changed during the peak search'
  proxy=r['tail_decode_tok_s']
 ranks.append((proxy,ident))
assert ranks
for _,ident in sorted(ranks,reverse=True)[:3]:
 while len(full[ident])<2:
  suffix=str(len(full[ident]));r=run(candidates[ident],key+'-peak-code-confirm-'+ident+'-'+suffix,family,'code');assert r['status']=='ok',r.get('error');full[ident].append(r)
qualified={ident:rs for ident,rs in full.items()if len(rs)>=2};assert qualified
winner=max(qualified,key=lambda ident:statistics.median(r['tail_decode_tok_s']for r in qualified[ident]));rows=qualified[winner];chosen=min(rows,key=lambda r:r['tail_decode_tok_s'])
choice=dict(objective='Maximize confirmed median sustained code decode at 8192 input tokens, with full model context still configured; prefill reported without sacrificing peak-code decode',selected=name(chosen),selected_median_decode=statistics.median(r['tail_decode_tok_s']for r in rows),candidates=[dict(identity=i,median_decode=statistics.median(r['tail_decode_tok_s']for r in rs),cases=[name(r)for r in rs])for i,rs in qualified.items()],screened_candidates=len(ranks))
# Refresh the long preset's low-code observation range using all measured same-settings runs.
if full.get(long_id):
 values=[dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'])for r in full[long_id]]
 long_metrics.update(low=min(values,key=lambda x:x['decode']),low_cases=values);save(key+'_long_metrics',long_metrics)
save(key+'_short',choice)
if winner!=long_id:
 high=[]
 for genre in ['text','chat','story']:
  existing=[]
  for path in(R/'bench').glob('range-*/result.json'):
   r=read(path);c=r.get('config',{})
   if r.get('status')=='ok'and c.get('workload')==genre and c.get('generate')==8192 and c.get('host_memory_policy')and r.get('cold_prefill_qualified',True)and config_id(c)==winner:existing.append(r)
  high.extend(existing if existing else[run(chosen['config'],key+'-peak-code-profile-'+winner+'-'+genre,family,genre)])
 assert all(r['status']=='ok'for r in high)
 lowcases=[dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'])for r in rows]
 save(key+'_short_metrics',dict(low=min(lowcases,key=lambda x:x['decode']),low_cases=lowcases,high=summarize(high),peak_code_selection=choice))
else:
 current=read(O/'range-selections.json')
 if key+'_short_metrics'in current:
  current[key+'_preliminary_short_metrics']=current.pop(key+'_short_metrics');(O/'range-selections.json').write_text(json.dumps(current,indent=2))
print('PEAK CODE PRESET QUALIFIED',key,winner,choice['selected_median_decode'],flush=True)
