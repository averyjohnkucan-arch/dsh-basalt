"""Separate preliminary candidate chart; never promoted to qualified model metrics."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';B=R/'bench'
selection=json.loads((O/'range-selections.json').read_text())
metrics=selection['hybrid_basalt_long_metrics']
selected={g:min((x for x in metrics['high']['cases']if x['workload']==g),key=lambda x:x['decode'])['case']for g in ['text','chat','story']}
pairs=[('8K code','range-perf-hybrid-old-code',metrics['low']['case']),('209K text','range-perf-hybrid-old-text',selected['text']),('209K chat','range-perf-hybrid-old-chat',selected['chat']),('209K story','range-perf-hybrid-old-story',selected['story'])]
from range_identity import config_id
candidate_identities=set()
rows=[]
for label,old,new in pairs:
 row=dict(workload=label,measurements={})
 for role,case in [('Saved Strata',old),('Basalt candidate',new)]:
  path=B/case/'result.json'
  if not path.exists():continue
  d=json.loads(path.read_text());c=d['config']
  if d['status']!='ok':continue
  assert d['generated']==c['generate']==8192 and d.get('reused_tokens',0)==0 and d['cold_prefill_qualified']
  assert c['depth']==(8192 if label=='8K code' else 209715)
  assert c['benchmark_environment_id']=='performance-powerd-20261115'
  if role=='Basalt candidate':candidate_identities.add(config_id(c))
  prompt=json.loads((B/case/'prompt.json').read_text())
  row['measurements'][role]=dict(case=case,prefill=d['prefill_tok_s'],decode=d['tail_decode_tok_s'],prompt_sha256=prompt['sha256'],result_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 values=list(row['measurements'].values())
 if len(values)==2:assert values[0]['prompt_sha256']==values[1]['prompt_sha256']
 rows.append(row)
assert len(candidate_identities)==1,'Candidate chart must use one consistent long-context preset'
fig,axes=plt.subplots(1,2,figsize=(12,5.4),layout='constrained');colors=['#8796ac','#208d76'];roles=['Saved Strata','Basalt candidate']
for ax,metric,title in zip(axes,['prefill','decode'],['Cold prefill (tokens/sec)','Sustained decode (tokens/sec)']):
 for i,row in enumerate(rows):
  for j,role in enumerate(roles):
   value=row['measurements'].get(role,{}).get(metric);y=i+(j-.5)*.32
   if value is None:ax.text(0,y,'Pending',va='center',color='#667085',fontsize=9);continue
   ax.barh(y,value,height=.29,color=colors[j],label=role if i==0 else None)
   ax.text(value,y,f' {value:,.1f}',va='center',fontsize=9)
 ax.set_yticks(range(4),[x['workload']for x in rows]);ax.set_ylim(4.1,-.6);ax.set_title(title);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False);ax.set_xlim(0,max([x['measurements'][role][metric]for x in rows for role in roles if role in x['measurements']]+[1])*1.24)
axes[0].legend(loc='lower left',frameon=False,ncol=2,fontsize=9)
fig.suptitle('Flash Next NVFP4 / Q8 hybrid — preliminary long-context preset',fontsize=15)
fig.supxlabel('8192 generated; final 4096 timed. Matched native input. Same candidate controls; slowest actual high-context sample per genre.\nFull repeats, peak-code search and final all-genre 5% decode-floor qualification remain pending.',fontsize=9)
path=O/'hybrid-candidate-progress.png';fig.savefig(path,dpi=150);plt.close(fig)
(O/'hybrid-candidate-progress.json').write_text(json.dumps(dict(status='preliminary',scope='Separate candidate progress only; not qualified-profile or final maximum claims.',rows=rows,png_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2)+'\n')
print('Plotted',sum(len(x['measurements'])for x in rows),'verified measurements; incomplete baselines explicitly pending')
