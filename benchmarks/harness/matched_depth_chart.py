from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');o=r/'outputs'
f=json.loads((o/'flash-fp16-matched-depths.json').read_text());retry=json.loads((o/'flash-fp16-retry-depths.json').read_text());n=json.loads((o/'ninfer-matched-depths.json').read_text());b=json.loads((o/'basalt27-resident112k-depths.json').read_text())
labels=['Flash Next FP16','Hybrid FP16','27B NVFP4-all']
fig,axes=plt.subplots(2,2,figsize=(12,8))
for col,genre in enumerate(['code10','chat90']):
 old=[retry['flash-old-'+genre],f['hybrid-old-'+genre],n['prior-'+genre]]
 new=[f['flash-basalt-'+genre],f['hybrid-basalt-'+genre],b[genre]]
 assert all(v['status']=='ok'for v in old+new)
 for row,metric in enumerate(['prefill_tok_s','tail_decode_tok_s']):
  ax=axes[row,col]
  for offset,values,color,label in [(-.19,old,'#377e91','Prior engine'),(.19,new,'#ce8238','Basalt')]:
   bars=ax.bar([i+offset for i in range(3)],[v[metric] for v in values],.36,label=label,color=color)
   ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=9)
  ax.set_xticks(range(3),labels);ax.set_ylabel('tokens / second');ax.set_title(('10% code'if col==0 else '90% prose')+' — '+('prefill'if row==0 else 'decode'))
  ax.set_ylim(0,ax.get_ylim()[1]*1.15);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
axes[0,0].legend(frameon=False)
fig.suptitle('Completed matched-prompt comparisons',fontsize=17)
fig.text(.06,.025,'512 generated tokens; decode times the final 256. Prior = saved Strata for Flash/Hybrid, prior NInfer for 27B.\n27B uses NVFP4 KV in NInfer vs INT8 KV / 112K resident in Basalt; stop handling differs. Single comparisons, not proven maxima.',fontsize=10)
fig.tight_layout(rect=[0,.09,1,.95]);fig.savefig(o/'matched-depth-comparison.png',dpi=160)
