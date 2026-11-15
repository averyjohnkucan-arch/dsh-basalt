"""Matched Flash range chart; provisional guarded evidence until final gate passes."""
from pathlib import Path
import json,statistics,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';B=R/'bench';rows=[]
marker=O/'performance-qualified/flash_basalt.json';q=json.loads(marker.read_text())if marker.exists()else None
selections=json.loads((O/'range-selections.json').read_text())
if q and (q['long_selection']!=selections.get('flash_basalt_long',{}).get('selected')or q['short_selection']!=selections.get('flash_basalt_short',{}).get('selected')):q=None
new_label='Qualified Basalt long preset'if q else'Basalt recovery reference (provisional)'
for genre in ['text','chat','story']:
 groups=[('Saved Strata settings',['range-flash-old-'+genre])]
 new=[x['case']for x in q['long_metrics']['high']['cases']if x['workload']==genre]if q else['range-flash_basalt-memory-check-0011b16c9e49-'+genre]
 groups.append((new_label,new))
 for group,cases in groups:
  samples=[]
  for case in cases:
   p=B/case/'result.json'
   if not p.exists():continue
   r=json.loads(p.read_text())
   if r.get('status')=='ok'and r['config'].get('host_memory_policy')and r['generated']==8192:samples.append(r)
  if samples:rows.append(dict(group=group,genre=genre,prefill=statistics.median(x['prefill_tok_s']for x in samples),decode=statistics.median(x['tail_decode_tok_s']for x in samples),minimum_decode=min(x['tail_decode_tok_s']for x in samples),maximum_decode=max(x['tail_decode_tok_s']for x in samples),samples=len(samples),cases=';'.join(Path(x['config']['output']).name for x in samples)))
with(O/'range-progress.csv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=['group','genre','prefill','decode','minimum_decode','maximum_decode','samples','cases']);w.writeheader();w.writerows(rows)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(12,5));colors=['#356a97','#db9c35'];genres=['text','chat','story']
for ax,metric,title in zip(axes,['prefill','decode'],['Cold-prefix prefill','Sustained decode: final 4,096 tokens']):
 ceiling=max((r[metric]for r in rows),default=1)
 for j,group in enumerate(['Saved Strata settings',new_label]):
  for i,genre in enumerate(genres):
   r=next((x for x in rows if x['group']==group and x['genre']==genre),None)
   if r:
    x=i+(j-.5)*.32;v=r[metric];ax.bar(x,v,.29,color=colors[j],label=group if i==0 else None);ax.text(x,v+.015*ceiling,f'{v:,.1f}',ha='center',va='bottom',fontsize=9)
 ax.set_xticks(range(3),['Text','Chat','Story']);ax.set_title(title);ax.set_ylabel('tokens / second');ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.set_ylim(0,ceiling*1.18)
axes[0].legend(frameon=False,fontsize=8)
fig.suptitle('Flash Next INT8 KV: matched long-context progress',fontsize=16,fontweight='bold',y=.98)
fig.text(.06,.06,'209,715 input tokens • 8,192 generated • 95 W GPU • thinking off • isolated worker RAM',fontsize=10)
fig.text(.06,.015,'Medians shown; free continuations vary. '+('Performance gate passed; plugin and quality qualification are separate.'if q else'PROVISIONAL: current candidate is not the final tuned maximum.'),fontsize=9,color='#555555')
fig.tight_layout(rect=[0,.1,1,.91]);fig.savefig(O/'range-progress.png',dpi=160);print('Saved range-progress.png with',len(rows),'guarded genre measurements')
