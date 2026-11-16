"""Serial measured tuning. Screens rank candidates; only full cold runs label profiles."""
from range_common import *

def changed(config, changes):
 c=copy.deepcopy(config)
 for flag,value in changes.items():opt(c,flag,value)
 return c

def metrics(low,high):
 assert low['status']=='ok' and all(x['status']=='ok' for x in high)
 return dict(low=dict(case=name(low),prefill=low['prefill_tok_s'],decode=low['tail_decode_tok_s']),high=summarize(high))

def tune(key,base,family,candidates,prefill_candidates,low_candidates,old=None,cache=True,low_configs=()):
 initial=[run(base,key+'-base-'+g,family,g,cache=key+'-'+g if cache else None)for g in ['text','chat','story']]
 assert all(x['status']=='ok'for x in initial), 'Initial workload failed; inspect before tuning'
 worst=min(initial,key=lambda x:x['tail_decode_tok_s']);genre=worst['config']['workload']
 save(key+'_screen_workload',genre)
 screens=[]
 for tag,config in candidates:
  result=decode_screen(config,key+'-screen-'+tag,family,genre,n=2048,cache=key+'-'+genre if cache else None)
  if result['status']=='ok':screens.append((result,tag,config))
 screens.sort(key=lambda x:x[0]['tail_decode_tok_s'],reverse=True)
 save(key+'_screens',[dict(case=name(r),decode=r['tail_decode_tok_s'])for r,_,_ in screens])
 fresh=[worst]+[run(c,key+'-confirm-'+tag,family,genre)for _,tag,c in screens[:2]]
 fast=max([r for r in fresh if r['status']=='ok'],key=lambda r:r['tail_decode_tok_s'])['config']
 for tag,changes in prefill_candidates:
  fresh.append(run(changed(fast,changes),key+'-prefill-'+tag,family,genre))
 choice,selected=select(fresh);save(key+'_long',choice);chosen=selected['config']
 high=[selected if g==genre else run(chosen,key+'-final-'+g,family,g)for g in ['text','chat','story']]
 low=run(chosen,key+'-long-profile-code',family,'code');save(key+'_long_metrics',metrics(low,high))
 low_screens=[]
 for tag,changes in low_candidates:
  c=changed(chosen,changes);result=run(c,key+'-low-screen-'+tag,family,'code',n=2048,role='short-context code screen only')
  if result['status']=='ok':low_screens.append((result,tag,c))
 for tag,c in low_configs:
  result=run(c,key+'-low-screen-'+tag,family,'code',n=2048,role='short-context code screen only')
  if result['status']=='ok':low_screens.append((result,tag,c))
 low_screens.sort(key=lambda x:x[0]['tail_decode_tok_s'],reverse=True)
 short=[low]+[run(c,key+'-low-confirm-'+tag,family,'code')for _,tag,c in low_screens[:2]]
 short_choice,short_selected=select(short);save(key+'_short',short_choice)
 if short_selected['tail_decode_tok_s']>1.05*low['tail_decode_tok_s']:
  high=[run(short_selected['config'],key+'-short-profile-'+g,family,g)for g in ['text','chat','story']]
  save(key+'_short_metrics',metrics(short_selected,high))
 if old:
  control=[run(old,key+'-old-'+g,family,g)for g in ['code','text','chat','story']]
  save(key+'_old_metrics',metrics(control[0],control[1:]))
 print('RANGE COMPLETE',key,flush=True)

