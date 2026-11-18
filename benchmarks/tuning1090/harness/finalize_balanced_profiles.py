from pathlib import Path
import json,hashlib,shutil
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';W=R/'work';dest=Path('/mnt/media/AI/Model Configs/new profiles')
keys={'scratch-tuned1090-measured-27b-ninfer1616':('27b-ninfer','27B NVFP4 — NInfer'),'scratch-tuned1090-measured-huihui-int8':('huihui-int8','Huihui IQ3_S — NInfer, INT8 KV'),'scratch-tuned1090-range-flash-basalt-long':('range-flash-basalt-long','Flash NVFP4 — Basalt, INT8 KV'),'scratch-tuned1090-range-hybrid-basalt-long':('range-hybrid-basalt-long','Flash NVFP4/Q8 hybrid — Basalt, INT8 KV'),'scratch-tuned1090-measured-gyro-strata':('measured-gyro-strata','Gyro S — Strata, FP16 KV'),'scratch-tuned1090-deepseek-iq2-xxs':('deepseek-xxs','DeepSeek XXS — Basalt')}
allrows=json.loads((O/'tune1090-table.json').read_text());bykey={x['model']:x for x in allrows};ps=[]
for e in ['basalt','ninfer','strata']:
 x=json.loads((dest/(e+'-profiles.json')).read_text());ps.extend(x if isinstance(x,list)else x['profiles'])
assert len(ps)==6 and {p['id']for p in ps}==set(keys)
rows=[]
for pid,(key,label)in keys.items():
 p=next(x for x in ps if x['id']==pid);row=bykey[key];receipt=json.loads((R/'validation'/('tune1090-'+pid)/'adapter-result.json').read_text());assert receipt['status']=='ok'
 for side,field in [('low','after10'),('high','after90')]:
  for metric in ['prefill_tok_s','tail_decode_tok_s']:assert p['measuredPerformance'][side][metric]==row[field][metric]
 rows.append({**row,'label':label,'profileId':pid})
fmt=lambda d:f"p{d['prefill_tok_s']:.0f}/d{d['tail_decode_tok_s']:.1f}"
lines=['# One balanced profile per model','', 'Six recommended profiles. Each uses ONE set of engine and sampling settings at both context depths. The two p/d pairs in its name are measurements, not selectable settings.','','Protocol: 10% counting, then 90% prose/chat. 1,024 generated tokens; final 512 timed. Thinking off; no reused prefix. Rates in tokens/second. Before means original saved engine controls remeasured under the same protocol and sampler.','','| Model | Before 10% | After 10% | Before 90% | After 90% |','|---|---:|---:|---:|---:|']
for r in rows:lines.append('|'+ '|'.join([r['label']]+[fmt(r[k]) for k in ['before10','after10','before90','after90']])+'|')
lines+=['','Selection prioritizes 90% decode, then accepts a 1% decode loss only for at least 3% prefill gain among usable candidates. No cache/buffer/KV retuning was performed merely to change the non-model RAM allowance.','', 'All six recommended profiles passed real plugin adapter launches. All 13 tested variants passed after the Strata startup fix; the seven nonselected variants are reference material in tested alternatives. The historical full test matrix includes a fourteenth diagnostic Basalt 27B case with poor host-KV-offload performance; it is not recommended.','','Huihui benchmark framing was corrected and selected prose passed repetition screening and excerpt review. Speculative generated-code checks passed 17/18; the failed LRU case was a rejected NInfer K3 trial. These small tests do not establish general model accuracy.','','Strata Flash, now an archived alternative, required STRATA_NO_ARENA_THP=1 to avoid reproduced startup compaction pressure. Its corrected measurements were p2096/d109.9 and p2306/d51.5. Gyro S does not use that workaround.','','## Status and use','','Completed: throughput comparisons, selected-output review, six-profile selection, adapter validation, profile names, original backups, table and chart.','', 'Plugin packages are staged in plugin packages and are not installed into live DSH. These JSON files are native provider profile snapshots, not portable model manifests; do not use the portable model-import dialog for them. Keep their referenced model/runtime/ranking files in place. Original snapshots and tested alternatives are preserved.','','GitHub publication status is recorded separately in github-publication.json when completed.']
text='\n'.join(lines)+'\n';(dest/'RESULTS.md').write_text(text);(O/'balanced-model-results.md').write_text(text);(O/'balanced-model-results.json').write_text(json.dumps(rows,indent=2)+'\n')
(dest/'README.txt').write_text('Six recommended models; one balanced profile per model. Both p/d pairs describe that same configuration at10% and90% context.\n\nRead RESULTS.md for measurements and limitations. Read SELECTED-PROFILES.txt for the selected profile names.\nMain JSON files contain only six selected profiles; tested alternatives contains historical variants, not additional recommended context-specific settings.\nPlugin packages are staged, not live-installed. Profile JSONs are native provider snapshots, not portable-import manifests. Originals remain untouched.\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
y=np.arange(len(rows));fig,axes=plt.subplots(1,4,figsize=(18,5.4),sharey=True)
for ax,depth,metric,title in zip(axes,[10,10,90,90],['prefill_tok_s','tail_decode_tok_s']*2,['10% counting: prefill','10% counting: decode','90% prose: prefill','90% prose: decode']):
 ax.barh(y-.18,[r['before'+str(depth)][metric]for r in rows],.34,label='Before',color='#9ca3af');ax.barh(y+.18,[r['after'+str(depth)][metric]for r in rows],.34,label='Balanced profile',color='#2563eb');ax.set_title(title);ax.set_xlabel('tokens/second');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
axes[0].set_yticks(y,[r['label']for r in rows]);axes[0].invert_yaxis();axes[-1].legend();fig.suptitle('One balanced configuration per model — measured at both context depths\n1,024 generated tokens; final 512 timed');fig.tight_layout()
for p in [dest/'tune1090-comparison.png',O/'balanced-model-comparison.png']:fig.savefig(p,dpi=150)
plt.close(fig)
shutil.copy2(O/'tune1090-comparison.md',dest/'tested alternatives/ALL-TESTED-RESULTS.md');shutil.copy2(O/'tune1090-comparison.png',dest/'tested alternatives/all-tested-comparison.png')
receipt={'status':'verified','selectedProfiles':6,'oneConfigurationAtBothDepths':True,'profileIds':list(keys),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.glob('*-profiles.json')}}
(O/'balanced-profile-final-audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Six-profile report, chart and final export audit complete')
