"""Require every selected family, then bind code-generation completion to its controls."""
from pathlib import Path
import json,sys,subprocess,time
from range_identity import config_id
from benchmark_environment import current_environment
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
s=json.loads((O/'range-selections.json').read_text());configs={};bindings={};missing=[]
environment=current_environment();environment_id=environment['id']if environment else'legacy'
models=[('flash_basalt','qwen'),('hybrid_basalt','qwen'),('27b_basalt','qwen27b'),('27b_ninfer','qwen27b'),('flash_strata','qwen'),('hybrid_strata','qwen'),('gyro_strata','qwen'),('flash_fp16_basalt','qwen'),('hybrid_fp16_basalt','qwen'),('flash_fp16_strata','qwen'),('hybrid_fp16_strata','qwen'),('huihui_nvfp4_ninfer','qwen27b'),('huihui_int8_ninfer','qwen27b'),('huihui_fp8_ninfer','qwen27b')]
for key,family in models:
 paths=[O/'performance-qualified'/(key+suffix+'.json')for suffix in ['','-plugin-gpu']]
 if not s.get(key+'_long')or not s.get(key+'_short')or not all(p.exists()for p in paths):missing.append(key);continue
 native,plugin=[json.loads(p.read_text())for p in paths]
 if not native.get('performance_qualified')or plugin.get('status')!='ok'or native.get('benchmark_environment_id','legacy')!=environment_id or plugin.get('benchmark_environment_id','legacy')!=environment_id:missing.append(key);continue
 selected={kind:s[key+'_'+kind]['selected']for kind in ['long','short']}
 if any(native[kind+'_selection']!=selected[kind]for kind in selected):missing.append(key);continue
 paths={kind:W/(selected[kind]+'.json')for kind in selected};ids={kind:config_id(json.loads(path.read_text()))for kind,path in paths.items()}
 if any(ids[kind]!=native[kind+'_identity']for kind in ids):missing.append(key);continue
 bindings[key]=ids;configs[key.replace('_','-')]=dict(config=str(paths['long']),family=family)
 if ids['short']!=ids['long']:configs[key.replace('_','-')+'-peak-code']=dict(config=str(paths['short']),family=family)
if missing:
 print(json.dumps(dict(status='not-ready',missing_qualified_families=missing,scope='No functional generations launched; partial matrices cannot satisfy the complete selected-family code gate'),indent=2));raise SystemExit(1)
plan=dict(status='ready',benchmark_environment_id=environment_id,selections=bindings,configs=configs,functions=['merge_intervals','lru_trace','verify_draft'])
if '--plan'in sys.argv:print(json.dumps(plan,indent=2));raise SystemExit(0)
p=W/'range-selected-functional-configs.json';p.write_text(json.dumps(configs,indent=2))
receipt=O/'selected-code-quality-completion.json';state={**plan,'status':'running','started_unix':time.time()};receipt.write_text(json.dumps(state,indent=2)+'\n')
try:
 state['phase']='current-plugin-and-mode-validation';receipt.write_text(json.dumps(state,indent=2)+'\n')
 for model_key,_ in models:subprocess.run([sys.executable,str(W/'range_plugin_gpu_gate.py'),model_key],check=True)
 state['phase']='generated-functions';state['current_plugin_sources_revalidated']=True;receipt.write_text(json.dumps(state,indent=2)+'\n')
 subprocess.run([sys.executable,str(W/'code_function_eval.py'),str(p)],check=True)
 rows=json.loads((O/('code-functional-'+p.stem+'.json')).read_text())
 assert {(row['model'],row['function'])for row in rows}=={(label,task)for label in configs for task in plan['functions']}
 assert len(rows)==len(configs)*3 and all(row['status']=='ok'and row.get('grade_schema')==2 and row.get('functional_attempt_id')for row in rows)
 state.update(status='complete',completed_unix=time.time(),all_generations_completed=True,all_independent_functions_passed=all(row['passed']for row in rows),passed=sum(row['passed']for row in rows),total=len(rows),quality_receipt='code-functional-'+p.stem+'.json',scope='All selected long/distinct-peak-code controls generated and independently tested; genuine semantic failures retained separately from completed generation')
except BaseException as error:
 state.update(status='failed',error=str(error),failed_unix=time.time());raise
finally:receipt.write_text(json.dumps(state,indent=2)+'\n')
