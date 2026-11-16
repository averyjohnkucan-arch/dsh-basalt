"""Three-column comparison with explicit pending/unsupported cells; native engines stay separate."""
from pathlib import Path
import json,html,csv,datetime
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';s=json.loads((O/'range-selections.json').read_text())
def fmt(x):return f'{x:,.1f}'
def speed(metrics):
 if not metrics:return 'Pending matched measurements'
 low=metrics['low'];high=metrics['high'];return f"8K code P{fmt(low['prefill'])}/D{fmt(low['decode'])}; 80% P{fmt(high['prefill_range'][0])}–{fmt(high['prefill_range'][1])}, D{fmt(high['decode_range'][0])}–{fmt(high['decode_range'][1])}"
def qualified(key):
 p=O/'performance-qualified'/(key+'.json')
 if not p.exists():return None
 data=json.loads(p.read_text());current=s.get(key+'_long',{});short=s.get(key+'_short',{})
 if data['long_selection']!=current.get('selected')or data['short_selection']!=short.get('selected'):return None
 return data
models=[
 ('DeepSeek V4.1 Flash IQ2_XXS / native mixed KV','deepseek_basalt','deepseek_basalt_old_metrics',None),
 ('Flash Next NVFP4 GPTQ / INT8 KV','flash_basalt','flash_old_metrics',None),
 ('Flash Next NVFP4 GPTQ / FP16 KV','flash_fp16_basalt','flash_fp16_old_metrics',None),
 ('Flash Next NVFP4 Q8 hybrid / INT8 KV','hybrid_basalt','hybrid_old_metrics',None),
 ('Flash Next NVFP4 Q8 hybrid / FP16 KV','hybrid_fp16_basalt','hybrid_fp16_old_metrics',None),
 ('27B NVFP4-full / old NVFP4 KV; Basalt INT8 KV','27b_basalt','27b_ninfer_old_metrics',None),
 ('27B IQ3_S Huihui / INT8 KV',None,'huihui_int8_ninfer_old_metrics','No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support'),
 ('27B IQ3_S Huihui / FP8 KV',None,'huihui_fp8_ninfer_old_metrics','No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support'),
 ('27B IQ3_S Huihui / NVFP4 KV',None,'huihui_nvfp4_ninfer_old_metrics','No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support'),
 ('Gyro S / saved FP16 KV',None,'gyro_strata_old_metrics','Kept on Strata; Basalt Hadamard expert support is unavailable')]
rows=[]
for label,key,oldkey,unsupported in models:
 q=qualified(key)if key else None
 current=unsupported or'In progress: long-context and peak-code qualification'
 if q:
  current='Long preset: '+speed(q['long_metrics'])
  if q.get('short_metrics')and q['short_identity']!=q['long_identity']:current+=' | Peak-code preset: '+speed(q['short_metrics'])
 rows.append([label,speed(s.get(oldkey)),current])
headers=['Model name','Old settings speed','Current max settings speed on Basalt']
with(O/'range-comparison-progress.csv').open('w')as f:w=csv.writer(f);w.writerow(headers);w.writerows(rows)
def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>'for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>'for x in row)+'</tr>'for row in rows)+'</tbody></table>'
other=[]
for key,label,oldkey in [('flash_strata','Flash Next INT8 / Strata0.1.59','flash_old_metrics'),('hybrid_strata','Hybrid INT8 / Strata0.1.59','hybrid_old_metrics'),('flash_fp16_strata','Flash Next FP16 / Strata0.1.59','flash_fp16_old_metrics'),('hybrid_fp16_strata','Hybrid FP16 / Strata0.1.59','hybrid_fp16_old_metrics'),('gyro_strata','Gyro S / Strata0.1.59','gyro_strata_old_metrics'),('27b_ninfer','27B NVFP4-full / latest custom NInfer','27b_ninfer_old_metrics'),('huihui_int8_ninfer','27B IQ3_S INT8 / latest custom NInfer','huihui_int8_ninfer_old_metrics'),('huihui_fp8_ninfer','27B IQ3_S FP8 / latest custom NInfer','huihui_fp8_ninfer_old_metrics'),('huihui_nvfp4_ninfer','27B IQ3_S NVFP4 / latest custom NInfer','huihui_nvfp4_ninfer_old_metrics'),('deepseek_strata','DeepSeek / latest specialized Strata','deepseek_basalt_old_metrics')]:
 q=qualified(key);other.append([label,speed(s.get(oldkey)),speed(q['long_metrics'])if q else'Pending qualification'])
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds');count=sum(qualified(key) is not None for key in {k.removesuffix('_long') for k in s if k.endswith('_long')})
text='''<!doctype html><meta charset="utf-8"><title>Inference tuning progress</title><style>body{font:16px system-ui;max-width:1500px;margin:36px auto;padding:0 24px;color:#172a3a;background:#f7fafc}h1{font-size:30px}table{border-collapse:collapse;width:100%;background:white;margin:20px 0}td,th{border:1px solid #d8e2eb;padding:12px;text-align:left;vertical-align:top}th{background:#e9f1f7}p{max-width:1100px;line-height:1.5}.status{padding:16px;background:#fff4d5;border-left:5px solid #d89c2d}</style>'''
text+='<h1>Inference tuning progress</h1><p class="status">Work remains in progress. '+str(count)+' preset families have passed the native performance evidence gate. Plugin-owned GPU, generated-code, packaging and publication gates are tracked separately.</p><p>Updated '+html.escape(now)+'. P = prefill tokens/s; D = sustained late decode tokens/s. Low input: 8,192 code tokens. High input: floor(80% native capacity), with text, chat and original-story tasks. All continuations: 8,192 tokens; final 4,096 timed (HTTP draft-batch boundaries can differ by up to seven tokens).</p>'
text+=table(headers,rows)+'<h2>Strata and NInfer, reported separately</h2>'+table(['Model / engine','Old settings','Current long preset'],other)
text+='<p>95 W requested/default GPU power; enforced limit varies under load; thinking off; NVMe model reads; isolated worker RAM high/max96/108GiB. The first pre-recovery sweep is diagnostic; final profiles require fresh isolated measurements. The long preset maximizes the minimum genre-median decode, then minimum cold prefill while each genre median retains at least95% of its value in that peak-decode preset. Both absolute and relative limiting genres are repeated. Profile-name high pairs come from the slowest actual selected-settings genre/repeat. Cold process/prefix does not imply globally dropped OS file cache.</p><p>Finite measured workloads establish an observed range, not a guarantee for every possible prompt. Small generated-function checks and numerical kernel tests are separate from BF16-reference model quality. Some greedy continuations repeat paragraphs; their rates remain in the measured range. Offline output-audit receipts record repetition, so higher throughput must not be treated as evidence of better conversational quality.</p>'
(O/'range-progress.html').write_text(text);print('Updated progress report;',count,'performance-qualified preset families')
