"""Evidence gate for a completed long/peak-code tuning pair, independent of plugin/quality gates."""
from pathlib import Path
import json,statistics,sys,time,subprocess
from range_identity import config_id
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';B=R/'bench';key=sys.argv[1];s=json.loads((O/'range-selections.json').read_text());long=s[key+'_long'];short=s[key+'_short']
def read(case):return json.loads((B/case/'result.json').read_text())
def check_metrics(metrics,selection):
 ident=config_id(read(selection['selected'])['config']);assert {x['workload']for x in metrics['high']['cases']}=={'text','chat','story'}
 for item in [metrics['low'],*metrics['high']['cases']]:
  r=read(item['case']);c=r['config'];assert r['status']=='ok'and c['generate']==8192 and r['generated']==8192 and c.get('host_memory_policy')and not r.get('reused_tokens',0)
  assert config_id(c)==ident and item['prefill']==r['prefill_tok_s']and item['decode']==r['tail_decode_tok_s']
  assert c['gpu_power_limit_w']==95
 return ident
long_metrics=s[key+'_long_metrics'];long_id=check_metrics(long_metrics,long)
qualified=[x for x in long['candidates']if x['complete']];peak=max(x['decode']for x in qualified);chosen=next(x for x in qualified if x['identity']==long_id)
assert chosen['decode']>=.95*peak and abs(long['decode_floor_tok_s']-.95*peak)<1e-9
assert chosen['prefill']==max(x['prefill']for x in qualified if x['decode']>=.95*peak)
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
(folder/(key+'.json')).write_text(json.dumps(record,indent=2));print('PERFORMANCE EVIDENCE GATE PASSED',key,flush=True)

subprocess.run([sys.executable,str(R/'work/range_progress_report.py')],check=True)
if key=='flash_basalt':subprocess.run(['taskset','-c','22',str(R/'tools/build-env/bin/python'),str(R/'work/range_progress_chart.py')],check=True)
subprocess.run([sys.executable,str(R/'work/range_plugin_gpu_gate.py'),key],check=True)
