from range_tuner import *
model=sys.argv[1]if len(sys.argv)>1 else'flash'
base=latest(read(W/('quiet-gyro-strata-90.json'if model=='gyro'else'quiet-flash-int8-strata-90.json')),'strata')
opt(base,'--pool-workers',21)
old=read(W/('quiet-gyro-old-90.json'if model=='gyro'else'quiet-flash-int8-old-90.json'))
if model.startswith('hybrid'):
 for c in [base,old]:
  opt(c,'--pack','/mnt/media/AI/Models/Scratch models/Maximilian228/Qwen3.8-Flash-Next-NVFP4-Q8-Mix-Strata/pack');opt(c,'--resident-budget-gib',96);opt(c,'--vram-reserve-mib',1200)
if model.endswith('fp16'):
 selected_state=read(O/'range-selections.json');parent=model.removesuffix('_fp16')+'_strata_long'
 if parent in selected_state:base=read(R/'bench'/selected_state[parent]['selected']/'result.json')['config']
 opt(base,'--kv','fp16')
candidates=[]
for tag,changes in [('mtp6',{'--spec':6}),('mtp4',{'--spec':4}),('spec0',{'--spec':0}),('pcie55',{'--pcie-frac':.55}),('pcie75',{'--pcie-frac':.75}),('workers14',{'--pool-workers':14}),('resident131k',{'--kv-resident':131072})]:
 c=copy.deepcopy(base)
 if tag.startswith('mtp'):
  for flag in ['--draft','--draft-model','--draft-fallback','--draft-cap','--draft-conf']:opt(c,flag,None)
 candidates.append((tag,changed(c,changes)))
if model!='gyro':
 for tag,cap,conf in [('dflash-k7',8,.55),('dflash-cap6',6,.55),('dflash-cap8-conf75',8,.75)]:
  candidates.append((tag,changed(base,{'--draft':'dflash2','--draft-model':R/'packs/flash-dflash2.pack','--draft-fallback':'none','--spec':8,'--draft-cap':cap,'--draft-conf':conf})))
else:
 for kv in ['int8','fp16']:candidates.append(('kv-'+kv,changed(base,{'--kv':kv})))
tune(model+'_strata',base,'qwen',candidates,[('32k',{'--prefill':'auto:32768'}),('4k',{'--prefill':'4096'})],[(f'spec{s}',{'--spec':s})for s in [0,4,6,8]],old=old if model=='gyro'else None)
