from range_tuner import *
model=sys.argv[1]if len(sys.argv)>1 else'flash'
base=latest(read(W/('quiet-gyro-strata-90.json'if model=='gyro'else'quiet-flash-int8-strata-90.json')),'strata')
opt(base,'--pool-workers',21)
old=read(W/('quiet-gyro-old-90.json'if model=='gyro'else'quiet-flash-int8-old-90.json'))
if model.startswith('hybrid'):
 for c in [base,old]:
  opt(c,'--pack',hybrid_strata_pack());opt(c,'--resident-budget-gib',96);opt(c,'--vram-reserve-mib',1200)
if model.startswith('hybrid')and(O/'hybrid-memory-fit-basalt-high104.json').exists():
 memory_policy=read(O/'hybrid-memory-fit-basalt-high104.json');assert memory_policy['status']=='complete'
 for target in [base,old]:
  target['benchmark_memory_policy_id']=memory_policy['benchmark_memory_policy_id'];target['host_memory_policy']=memory_policy['host_memory_policy']
if model.startswith('hybrid')and(O/'hybrid-memory-fit-strata-high104.json').exists():
 fit=read(O/'hybrid-memory-fit-strata-high104.json');assert fit['status']=='complete'
 opt(base,'--resident-budget-gib',fit['selected_budget_gib'])
if model.endswith('fp16'):
 selected_state=read(O/'range-selections.json');parent=model.removesuffix('_fp16')+'_strata_long'
 if parent in selected_state:base=read(R/'bench'/selected_state[parent]['selected']/'result.json')['config']
 opt(base,'--kv','fp16')
# The in-flight INT8 hybrid cohort remains pinned. New families use the
# released engine after the exact executable has passed the CLI preflight.
if model in ('gyro','flash_fp16','hybrid_fp16'):
 proof=read(O/'strata060-cli-preflight.json')
 binary=R/'runtimes/strata-engine-0.1.60/strata'
 assert proof['status']=='passed-cli-no-inference' and digest(binary)==proof['engine_sha256']
 base['command'][3]=str(binary)
 base['env']={**base.get('env',{}),'LD_LIBRARY_PATH':str(binary.parent)}
 base['engine_channel']='official-0.1.60'
candidates=[]
for tag,changes in [('mtp6',{'--spec':6}),('mtp4',{'--spec':4}),('mtp2',{'--spec':2}),('pcie55',{'--pcie-frac':.55}),('pcie75',{'--pcie-frac':.75}),('workers14',{'--pool-workers':14}),('resident131k',{'--kv-resident':131072})]:
 c=copy.deepcopy(base)
 if tag.startswith('mtp')or tag=='mtp2':
  for flag in ['--draft','--draft-model','--draft-fallback','--draft-cap','--draft-conf']:opt(c,flag,None)
 candidates.append((tag,changed(c,changes)))
candidates.append(('workers8',changed(base,{'--pool-workers':8})))
if base['command'][base['command'].index('--pool-workers')+1]!='21':candidates.append(('workers21',changed(base,{'--pool-workers':21})))
if model!='gyro':
 for tag,cap,conf in [('dflash-k7',8,.55),('dflash-cap6',6,.55),('dflash-cap8-conf75',8,.75)]:
  candidates.append((tag,changed(base,{'--draft':'dflash2','--draft-model':R/'packs/flash-dflash2.pack','--draft-fallback':'none','--spec':8,'--draft-cap':cap,'--draft-conf':conf})))
else:
 for kv in ['int8','fp16']:candidates.append(('kv-'+kv,changed(base,{'--kv':kv})))
tune(model+'_strata',base,'qwen',candidates,[('32k',{'--prefill':'auto:32768'}),('4k',{'--prefill':'4096'})],[(f'spec{s}',{'--spec':s})for s in [2,4,6,8]],old=old if model=='gyro'else None,cache=False)
