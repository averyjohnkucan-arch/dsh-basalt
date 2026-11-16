from range_common import *
from range_tuner import confirmation_configs
model=sys.argv[1]if len(sys.argv)>1 else'flash'
memory_fit=None
base=latest(read(W/'quiet-flash-int8-basalt-90.json'),'basalt');opt(base,'--pool-workers',21)
old=read(W/'quiet-flash-int8-old-90.json')
if model.startswith('hybrid'):
 opt(base,'--model',R/'packs/qwen-nvfp4-q8-hybrid.basalt');opt(base,'--resident-budget-gib',96)
 fit_path=O/'hybrid-memory-fit-basalt-high104.json'
 if not fit_path.exists():fit_path=O/'hybrid-memory-fit-basalt.json'
 if fit_path.exists():
  memory_fit=read(fit_path);assert memory_fit['status']=='complete','Hybrid fit must finish before tuning resumes'
  opt(base,'--resident-budget-gib',memory_fit['selected_budget_gib'])
  if memory_fit.get('benchmark_memory_policy_id'):
   for target in [base,old]:
    target['benchmark_memory_policy_id']=memory_fit['benchmark_memory_policy_id'];target['host_memory_policy']=memory_fit['host_memory_policy']
 opt(old,'--pack',hybrid_strata_pack());opt(old,'--resident-budget-gib',96);opt(old,'--vram-reserve-mib',1200)
if model.endswith('fp16'):
 parent=model.removesuffix('_fp16')+'_basalt_long'
 selected_state=read(O/'range-selections.json')
 if parent in selected_state:base=read(R/'bench'/selected_state[parent]['selected']/'result.json')['config']
 opt(base,'--kv','fp16');opt(old,'--kv','fp16')
# Start with all three actual long-answer genres. Decode screens are never profile-name measurements.
initial=[]
budgets=[None]
if memory_fit:
 current=int(float(base['command'][base['command'].index('--resident-budget-gib')+1]))
 budgets=[current]+[b for b in [88,84,80]if b<current]
 sustained_attempts=[]
for budget in budgets:
 if budget is not None:opt(base,'--resident-budget-gib',budget)
 initial=[]
 for workload in ['text','chat','story']:
  x=run(base,model+'-basalt-base-'+workload,'qwen',workload,cache=model+'-'+workload)
  if x['status']!='ok':
   assert memory_fit and 'RAM safety stop'in str(x.get('error','')), 'Initial workload failed; inspect non-memory error before tuning'
   sustained_attempts.append(dict(budget_gib=budget,failed_case=name(x),error=x.get('error')))
   save(model+'_sustained_memory_fit',dict(status='screening',attempts=sustained_attempts));break
  initial.append(x)
 if len(initial)==3:
  if memory_fit:
   sustained_attempts.append(dict(budget_gib=budget,status='all-three-full-output-genres-passed',cases=[name(x)for x in initial]))
   save(model+'_sustained_memory_fit',dict(status='complete',selected_initial_budget_gib=budget,attempts=sustained_attempts))
   failed={a['budget_gib']for a in sustained_attempts if 'failed_case'in a}
   memory_fit={**memory_fit,'safe_budgets_gib':sorted((set(memory_fit['safe_budgets_gib'])-failed)|{budget})}
  break
assert len(initial)==3,'No hybrid budget passed all three guarded full-output genres'
worst=min(initial,key=lambda x:x['tail_decode_tok_s']);workload=worst['config']['workload'];save(model+'_screen_workload',workload)
screens=[]
variants=[('base-controls',{}),('spec6',{'--spec':6}),('spec4',{'--spec':4}),('workers14',{'--pool-workers':14}),('workers8',{'--pool-workers':8}),('resident131k',{'--kv-resident':131072})]
if memory_fit:
 current_budget=float(base['command'][base['command'].index('--resident-budget-gib')+1])
 variants.extend((f'ram-budget-{budget}',{'--resident-budget-gib':budget})for budget in memory_fit['safe_budgets_gib']if budget!=current_budget)
if base['command'][base['command'].index('--spec')+1]!='8':variants.append(('spec8',{'--spec':8}))
if base['command'][base['command'].index('--pool-workers')+1]!='21':variants.append(('workers21',{'--pool-workers':21}))
for tag,changes in variants:
 c=copy.deepcopy(base)
 for flag,value in changes.items():opt(c,flag,value)
 x=decode_screen(c,model+'-basalt-screen-'+tag,'qwen',workload,n=2048,cache=model+'-'+workload)
 if x['status']=='ok':screens.append((x,tag,c))
screens.sort(key=lambda x:x[0]['tail_decode_tok_s'],reverse=True);save(model+'_screens',[dict(case=name(x),decode=x['tail_decode_tok_s'])for x,_,_ in screens])
fresh=[worst]
for tag,c in confirmation_configs(screens,worst):fresh.append(run(c,model+'-basalt-confirm-'+tag,'qwen',workload))
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
