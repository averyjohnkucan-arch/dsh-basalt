"""Evidence gate for a completed long/peak-code tuning pair, independent of plugin/quality gates."""
from pathlib import Path
import json,statistics,sys,time,subprocess
from range_identity import config_id
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';B=R/'bench';key=sys.argv[1]
subprocess.run([sys.executable,str(R/'work/refresh_range_metrics.py'),key],check=True)
s=json.loads((O/'range-selections.json').read_text());long=s[key+'_long'];short=s[key+'_short']
def read(case):return json.loads((B/case/'result.json').read_text())
def check_metrics(metrics,selection):
 ident=config_id(read(selection['selected'])['config']);assert {x['workload']for x in metrics['high']['cases']}=={'text','chat','story'}
 for item in [metrics['low'],*metrics['high']['cases']]:
  r=read(item['case']);c=r['config'];assert r['status']=='ok'and c['generate']==8192 and r['generated']==8192 and c.get('host_memory_policy')and not r.get('reused_tokens',0)
  assert config_id(c)==ident and item['prefill']==r['prefill_tok_s']and item['decode']==r['tail_decode_tok_s']
  assert c['gpu_power_limit_w']==95
 return ident
long_metrics=s[key+'_long_metrics'];long_id=check_metrics(long_metrics,long)
for candidate in long['candidates']:
 assert candidate['complete']==(set(candidate['genres'])=={'text','chat','story'})
 for genre,values in candidate['genres'].items():
  assert len(values['cases'])==len(set(values['cases']))==values['samples']
  rows=[read(case)for case in values['cases']]
  assert all(r['status']=='ok'and r['generated']==8192 and r['config']['generate']==8192 and r['config']['workload']==genre and r['config'].get('host_memory_policy')and r.get('cold_prefill_qualified',True)and not r.get('reused_tokens',0)and config_id(r['config'])==candidate['identity']for r in rows)
  assert statistics.median(r['tail_decode_tok_s']for r in rows)==values['decode']and statistics.median(r['prefill_tok_s']for r in rows)==values['prefill']
 assert candidate['decode']==min(x['decode']for x in candidate['genres'].values())and candidate['prefill']==min(x['prefill']for x in candidate['genres'].values())
qualified=[x for x in long['candidates']if x['complete']];peak_row=max(qualified,key=lambda x:x['decode']);peak=peak_row['decode'];chosen=next(x for x in qualified if x['identity']==long_id)
assert chosen['decode']>=.95*peak and abs(long['decode_floor_tok_s']-.95*peak)<1e-9
floors={genre:.95*peak_row['genres'][genre]['decode']for genre in ['text','chat','story']}
assert long['peak_decode_identity']==peak_row['identity']and long['genre_decode_floor_tok_s']==floors
eligible=[x for x in qualified if x['decode']>=.95*peak and all(x['genres'][genre]['decode']>=value for genre,value in floors.items())]
assert chosen in eligible and chosen['prefill']==max(x['prefill']for x in eligible)
assert all(x['genres'][x['worst_genre']]['samples']>=2 for x in [peak_row,chosen])
if chosen['identity']!=peak_row['identity']:
 relative=min(floors,key=lambda genre:chosen['genres'][genre]['decode']/peak_row['genres'][genre]['decode'])
 assert chosen['genres'][relative]['samples']>=2 and peak_row['genres'][relative]['samples']>=2
for candidate in long['candidates']:
 if candidate['complete']:continue
 feasible=candidate['decode']>=.95*peak and all(values['decode']>=floors[genre]for genre,values in candidate['genres'].items())
 assert not(candidate['decode']>peak or(feasible and candidate['prefill']>chosen['prefill'])),'A partial candidate can still improve the objective'
short_id=config_id(read(short['selected'])['config']);choices=[]
for item in short['candidates']:
 rows=[read(case)for case in item['cases']];assert len(rows)>=2 and all(x['status']=='ok'and x['config'].get('host_memory_policy')and x['generated']==8192 and x['config']['depth']==8192 for x in rows)
 assert all(config_id(x['config'])==item['identity']for x in rows);score=statistics.median(x['tail_decode_tok_s']for x in rows);assert score==item['median_decode'];choices.append(score)
assert short['selected_median_decode']==max(choices)
assert any(item['identity']==short_id and item['median_decode']==short['selected_median_decode'] for item in short['candidates'])
short_metrics=s.get(key+'_short_metrics')
if short_metrics:assert check_metrics(short_metrics,short)==short_id
else:assert long_id==short_id
folder=O/'performance-qualified';folder.mkdir(exist_ok=True)
record=dict(model_key=key,performance_qualified=True,qualified_at_unix=time.time(),scope='Native throughput and paired metric labels only; separate generated-code, plugin GPU and final-publication gates remain',long_selection=long['selected'],short_selection=short['selected'],long_identity=long_id,short_identity=short_id,long_metrics=long_metrics,short_metrics=short_metrics,peak_long_minimum_median_decode=peak,selected_long_minimum_median_decode=chosen['decode'],decode_floor=.95*peak,peak_code_median_decode=short['selected_median_decode'])
record['benchmark_environment_id']=read(long['selected'])['config'].get('benchmark_environment_id','legacy')
record['genre_decode_floor_tok_s']=floors
(folder/(key+'.json')).write_text(json.dumps(record,indent=2));print('PERFORMANCE EVIDENCE GATE PASSED',key,flush=True)

subprocess.run([sys.executable,str(R/'work/range_progress_report.py')],check=True)
if key=='flash_basalt':subprocess.run(['taskset','-c','22',str(R/'tools/build-env/bin/python'),str(R/'work/range_progress_chart.py')],check=True)
subprocess.run(['taskset','-c','22',str(R/'tools/build-env/bin/python'),str(R/'work/range_model_progress.py')],check=True)
subprocess.run([sys.executable,str(R/'work/range_plugin_gpu_gate.py'),key],check=True)
family='deepseek'if key.startswith('deepseek')else'qwen27b'if key.startswith(('27b','huihui'))else'qwen'
subprocess.run(['taskset','-c','22',str(R/'tools/build-env/bin/python'),str(R/'work/audit_range_outputs.py'),key,family],check=True)
