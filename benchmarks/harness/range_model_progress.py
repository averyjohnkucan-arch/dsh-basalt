"""Qualified Basalt family overview; unfinished presets never acquire speed claims."""
from pathlib import Path
import csv,json
from benchmark_environment import current_environment
from range_progress_report import models,qualified,s,O
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=O.parent/'bench';environment=current_environment();records=[]
def verified(metrics):
 if not metrics:return None
 if {x.get('workload')for x in metrics.get('high',{}).get('cases',[])}!={'text','chat','story'}:return None
 try:
  for item in [metrics['low'],*metrics['high']['cases']]:
   result=json.loads((B/item['case']/'result.json').read_text());config=result['config']
   if result['status']!='ok'or result['generated']!=8192 or config['generate']!=8192 or not config.get('host_memory_policy')or result.get('reused_tokens',0)or not result.get('cold_prefill_qualified',True):return None
   if environment and config.get('benchmark_environment_id')!=environment['id']:return None
   if result['prefill_tok_s']!=item['prefill']or result['tail_decode_tok_s']!=item['decode']:return None
  high=metrics['high'];cases=high['cases']
  return {**metrics,'high':{**high,'prefill_range':[min(x['prefill']for x in cases),max(x['prefill']for x in cases)],'decode_range':[min(x['decode']for x in cases),max(x['decode']for x in cases)]}}
 except(FileNotFoundError,KeyError,json.JSONDecodeError):return None
labels={
 'deepseek_basalt':'DeepSeek V4.1 Flash\nIQ2_XXS / native mixed KV',
 'flash_basalt':'Flash Next NVFP4 GPTQ\nINT8 KV',
 'flash_fp16_basalt':'Flash Next NVFP4 GPTQ\nFP16 KV',
 'hybrid_basalt':'Flash Next NVFP4/Q8 hybrid\nINT8 KV',
 'hybrid_fp16_basalt':'Flash Next NVFP4/Q8 hybrid\nFP16 KV',
 '27b_basalt':'27B NVFP4-full\nOld NVFP4 KV / Basalt INT8 KV',
}
for label,key,oldkey,unsupported in models:
 if key is None:continue
 q=qualified(key);old=verified(s.get(oldkey));new=verified(q['long_metrics'])if q else None
 records.append(dict(model=label,key=key,label=labels[key],old=old,new=new))
rows=[]
for record in records:
 for group in ['old','new']:
  metrics=record[group]
  if metrics:
   rows.append(dict(model=record['model'],group=group,prefill_min=metrics['high']['prefill_range'][0],prefill_max=metrics['high']['prefill_range'][1],decode_min=metrics['high']['decode_range'][0],decode_max=metrics['high']['decode_range'][1],cases=';'.join(x['case']for x in metrics['high']['cases'])))
with(O/'range-model-progress.csv').open('w')as f:
 writer=csv.DictWriter(f,fieldnames=['model','group','prefill_min','prefill_max','decode_min','decode_max','cases']);writer.writeheader();writer.writerows(rows)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(13,7.5),sharey=True)
colors={'old':'#356a97','new':'#db9c35'};groups={'old':'Saved settings','new':'Qualified Basalt long preset'}
for ax,metric,title in zip(axes,['prefill','decode'],['Cold-prefix prefill','Sustained late decode']):
 ceiling=max((row[metric+'_max']for row in rows),default=1)
 for i,record in enumerate(records):
  for j,group in enumerate(['old','new']):
   y=i+(-.15 if group=='old'else .15);metrics=record[group]
   if metrics:
    lo,hi=metrics['high'][metric+'_range'];ax.plot([lo,hi],[y,y],color=colors[group],lw=6,alpha=.65,solid_capstyle='round')
    ax.plot(lo,y,'o',color=colors[group],ms=6,label=groups[group]if i==next((k for k,r in enumerate(records)if r[group]),-1)else None)
    text=f'{lo:,.1f}'if lo==hi else f'{lo:,.1f}–{hi:,.1f}'
    ax.annotate(text,(hi,y),xytext=(7,0),textcoords='offset points',va='center',fontsize=8,color=colors[group])
   elif group=='new':ax.text(.02,y,'Pending qualification',transform=ax.get_yaxis_transform(),va='center',fontsize=8,color='#727f8a')
 ax.set_title(title,fontweight='bold');ax.set_xlabel('tokens / second');ax.set_xlim(0,ceiling*1.55);ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True)
axes[0].set_yticks(range(len(records)),[r['label']for r in records]);axes[0].set_ylim(len(records)-.5,-.5);axes[0].legend(frameon=False,fontsize=8,loc='lower right')
count=sum(r['new']is not None for r in records)
fig.suptitle(f'Basalt tuning progress: {count} / {len(records)} model families performance-qualified',fontsize=16,fontweight='bold',y=.98)
fig.text(.03,.06,'80% of each native context • 8,192 generated • final half timed • NVMe only • thinking off',fontsize=10)
fig.text(.03,.025,'Ranges include all selected-settings text/chat/story observations and repeats. Repetitive outputs remain included. Plugin and code-quality gates are separate.',fontsize=8,color='#555555')
fig.tight_layout(rect=[0,.09,1,.93]);fig.savefig(O/'range-model-progress.png',dpi=160)
print('Saved range-model-progress.png;',count,'qualified Basalt families;',len(rows),'verified ranges')
