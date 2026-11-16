from range_common import *
model=sys.argv[1]if len(sys.argv)>1 else'flash'
base=latest(read(W/'quiet-flash-int8-basalt-90.json'),'basalt');opt(base,'--pool-workers',21)
old=read(W/'quiet-flash-int8-old-90.json')
if model.startswith('hybrid'):
 opt(base,'--model',R/'packs/qwen-nvfp4-q8-hybrid.basalt');opt(base,'--resident-budget-gib',96)
 opt(old,'--pack','/mnt/media/AI/Models/Scratch models/Maximilian228/Qwen3.8-Flash-Next-NVFP4-Q8-Mix-Strata/pack');opt(old,'--resident-budget-gib',96);opt(old,'--vram-reserve-mib',1200)
if model.endswith('fp16'):
 parent=model.removesuffix('_fp16')+'_basalt_long'
 selected_state=read(O/'range-selections.json')
 if parent in selected_state:base=read(R/'bench'/selected_state[parent]['selected']/'result.json')['config']
 opt(base,'--kv','fp16');opt(old,'--kv','fp16')
# Start with all three actual long-answer genres. Decode screens are never profile-name measurements.
initial=[]
for workload in['text','chat','story']:
 x=run(base,model+'-basalt-base-'+workload,'qwen',workload,cache=model+'-'+workload);assert x['status']=='ok';initial.append(x)
worst=min(initial,key=lambda x:x['tail_decode_tok_s']);workload=worst['config']['workload'];save(model+'_screen_workload',workload)
screens=[]
variants=[('base-controls',{}),('spec6',{'--spec':6}),('spec4',{'--spec':4}),('workers14',{'--pool-workers':14}),('workers8',{'--pool-workers':8}),('resident131k',{'--kv-resident':131072})]
if base['command'][base['command'].index('--spec')+1]!='8':variants.append(('spec8',{'--spec':8}))
if base['command'][base['command'].index('--pool-workers')+1]!='21':variants.append(('workers21',{'--pool-workers':21}))
for tag,changes in variants:
 c=copy.deepcopy(base)
 for flag,value in changes.items():opt(c,flag,value)
 x=run(c,model+'-basalt-screen-'+tag,'qwen',workload,n=2048,cache=model+'-'+workload,reuse=True,role='decode screen only')
 if x['status']=='ok':screens.append((x,tag,c))
screens.sort(key=lambda x:x[0]['tail_decode_tok_s'],reverse=True);save(model+'_screens',[dict(case=name(x),decode=x['tail_decode_tok_s'])for x,_,_ in screens])
fresh=[worst]
for x,tag,c in screens[:2]:fresh.append(run(c,model+'-basalt-confirm-'+tag,'qwen',workload))
plain=copy.deepcopy(base);opt(plain,'--spec',0);fresh.append(run(plain,model+'-basalt-confirm-spec0','qwen',workload))
fast=max([r for r in fresh if r['status']=='ok'],key=lambda r:r['tail_decode_tok_s'])['config']
for tag,prefill in [('32k','auto:32768'),('4k','4096')]:
 c=copy.deepcopy(fast);opt(c,'--prefill',prefill);fresh.append(run(c,model+'-basalt-prefill-'+tag,'qwen',workload))
choice,selected=select(fresh);save(model+'_basalt_long',choice);chosen=selected['config']
final=[]
for genre in['text','chat','story']:
 final.append(selected if genre==workload else run(chosen,model+'-basalt-final-'+genre,'qwen',genre))
low=run(chosen,model+'-basalt-long-profile-code','qwen','code');save(model+'_basalt_long_metrics',dict(low=dict(case=name(low),prefill=low.get('prefill_tok_s'),decode=low.get('tail_decode_tok_s')),high=summarize(final)))
# Discover short-context alternatives with short screens, then confirm two full continuations.
short_screens=[]
for spec in[0,4,6,8]:
 c=copy.deepcopy(chosen);opt(c,'--spec',spec);x=run(c,model+'-basalt-low-screen-spec'+str(spec),'qwen','code',n=2048,role='short-context code screen only')
 if x['status']=='ok':short_screens.append((x,spec,c))
short_screens.sort(key=lambda x:x[0]['tail_decode_tok_s'],reverse=True);short=[low]
for x,spec,c in short_screens[:2]:short.append(run(c,model+'-basalt-low-confirm-spec'+str(spec),'qwen','code'))
short_choice,short_selected=select(short);save(model+'_basalt_short',short_choice)
if short_selected['tail_decode_tok_s']>1.05*low['tail_decode_tok_s']:
 high=[run(short_selected['config'],model+'-basalt-short-profile-'+g,'qwen',g)for g in['text','chat','story']]
 save(model+'_basalt_short_metrics',dict(low=dict(case=name(short_selected),prefill=short_selected['prefill_tok_s'],decode=short_selected['tail_decode_tok_s']),high=summarize(high)))
oldresults=[run(old,model+'-old-'+g,'qwen',g)for g in['code','text','chat','story']]
save(model+'_old_metrics',dict(low=dict(case=name(oldresults[0]),prefill=oldresults[0].get('prefill_tok_s'),decode=oldresults[0].get('tail_decode_tok_s')),high=summarize(oldresults[1:])))
print('RANGE BASALT COMPLETE',model,flush=True)
