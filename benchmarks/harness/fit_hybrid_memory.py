"""Serial long-prefix memory fits under the existing guard; these are not final speed tests."""
from range_common import *
engine=sys.argv[1]if len(sys.argv)>1 else'basalt';assert engine in ['basalt','strata','old-strata']
base=read(W/('quiet-flash-int8-basalt-90.json'if engine=='basalt'else'quiet-flash-int8-strata-90.json'if engine=='strata'else'quiet-flash-int8-old-90.json'))
if engine!='old-strata':base=latest(base,engine);opt(base,'--pool-workers',21)
opt(base,'--model'if engine=='basalt'else'--pack',R/'packs/qwen-nvfp4-q8-hybrid.basalt'if engine=='basalt'else'/mnt/media/AI/Models/Scratch models/Maximilian228/Qwen3.8-Flash-Next-NVFP4-Q8-Mix-Strata/pack')
if engine!='basalt':opt(base,'--vram-reserve-mib',1200)
path=O/('hybrid-memory-fit-'+engine+'.json');record=dict(engine=engine,status='running',scope='64 generated tokens after a fresh 80%-full text prefix; memory compatibility only, not a final throughput claim. Existing guard and original source weights are unchanged.',probes=[])
refine='--refine-existing'in sys.argv
if refine:
 record=read(path);assert record['status']=='complete'and record['engine']==engine
 assert all(x['engine_binary_sha256']==digest(base['command'][3])for x in record['probes'])
 record['status']='running'
path.write_text(json.dumps(record,indent=2)+'\n')
def probe(budget):
 c=copy.deepcopy(base);opt(c,'--resident-budget-gib',budget)
 r=run(c,'hybrid-'+engine+'-budget-fit-'+str(budget),'qwen','text',n=64,role='long-prefix memory-fit only; not qualified throughput')
 record['probes'].append(dict(budget_gib=budget,status=r['status'],case=name(r),error=r.get('error'),engine_binary_sha256=r['config']['engine_binary_sha256']))
 path.write_text(json.dumps(record,indent=2)+'\n');return r['status']=='ok'
if refine:
 low=max(x['budget_gib']for x in record['probes']if x['status']=='ok');high=min(x['budget_gib']for x in record['probes']if x['status']!='ok'and x['budget_gib']>low);record['refined_from_budget_bounds']=[low,high]
 while high-low>1:
  budget=(low+high)//2
  if probe(budget):low=budget
  else:high=budget
elif engine!='basalt'and probe(96):pass
elif probe(80):
 for budget in [84,86]:
  if not probe(budget):break
else:
 for budget in [72,64,48]:
  if probe(budget):break
safe=[x['budget_gib']for x in record['probes']if x['status']=='ok'];record.update(status='complete'if safe else'failed',safe_budgets_gib=safe,selected_budget_gib=max(safe)if safe else None);path.write_text(json.dumps(record,indent=2)+'\n');assert safe,'No hybrid budget passed the guarded long-prefix fit';print('HYBRID MEMORY FIT COMPLETE',engine,record['selected_budget_gib'],flush=True)
