from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
o=r/'outputs'
warm=json.loads((o/'deepseek-warm-240.json').read_text())
follow=json.loads((o/'deepseek-followup.json').read_text())
raid=json.loads((o/'deepseek-raid-comparison.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(14,4.8))
colors=['#277c8e','#ca7b32']
for i,q in enumerate(('XXS','XS')):
 values=[follow[f'deepseek-count-tweak-{q.lower()}-fixed-control']['tail_decode_tok_s'],
         warm[f'final-chat90-{q}']['decode_tok_s'],follow[f'count90-{q.lower()}']['decode_tok_s']]
 x=[n+(i-.5)*.34 for n in range(3)]
 bars=axes[0].bar(x,values,.32,label=q,color=colors[i])
 axes[0].bar_label(bars,fmt='%.1f',padding=3,fontsize=9)
 bars=axes[1].bar(i,warm[f'final-chat90-{q}']['prefill_tok_s'],.6,color=colors[i])
 axes[1].bar_label(bars,fmt='%.1f',padding=3)
axes[0].set_xticks(range(3),['Warm count','90% prose','90% count'])
axes[0].set_title('DeepSeek decode');axes[0].legend(frameon=False)
axes[1].set_xticks(range(2),['XXS','XS']);axes[1].set_title('90% prose prefill')
labels=['A1 system','B1 RAID','B2 RAID','A2 system']
keys=['A1-system-nvme','B1-raid0','B2-raid0','A2-system-nvme']
bars=axes[2].bar(range(4),[raid[k]['decode_windows_tok_s']['180-240'] for k in keys],color=[colors[0],colors[1],colors[1],colors[0]])
axes[2].bar_label(bars,fmt='%.2f',padding=3)
axes[2].set_xticks(range(4),labels,rotation=20);axes[2].set_title('XXS storage smoke test')
for ax in axes:
 ax.set_ylabel('tokens / second');ax.set_ylim(0,ax.get_ylim()[1]*1.12)
 ax.spines[['top','right']].set_visible(False)
 ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
fig.suptitle('Completed DeepSeek benchmarks',fontsize=17)
fig.text(.04,.025,'Fixed 102.3 GiB, 21 workers • Warm count: final 500 of 1,000 tokens • 90%: 943,718 input, 512 output\nStorage: 43-token story prompt, four-minute generation, final minute shown • Independent workloads',fontsize=9)
fig.tight_layout(rect=[0,.12,1,.92])
fig.savefig(o/'deepseek-completed-progress.png',dpi=150)
print(o/'deepseek-completed-progress.png')
