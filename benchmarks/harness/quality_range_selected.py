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
def is_dflash_k7(config,key):
 args=config['command']
 def option(name):
  return args[args.index(name)+1] if name in args and args.index(name)+1<len(args) else None
 if key.endswith('_strata'):
  return option('--draft')=='dflash2' and option('--draft-fallback')=='none' and option('--spec')=='8' and option('--draft-cap')=='8'
 if key.endswith('_ninfer'):
  return option('--spec')=='dflash2' and option('--draft-tokens')=='7'
 # This packed model's only speculative backend is its embedded DFlash2 drafter.
 return key=='27b_basalt' and option('--spec')=='8' and Path(option('--model') or '').name=='qwen27b-nvfp4full-experimental.basalt'

def add_dflash_code_trials():
 evidence={}
 for key,family in models:
  if not (key.endswith('_ninfer') or key in ['27b_basalt','flash_strata','hybrid_strata','flash_fp16_strata','hybrid_fp16_strata']):continue
  label=key.replace('_','-')
  for selected_label in [label,label+'-peak-code']:
   if selected_label not in configs:continue
   path=Path(configs[selected_label]['config'])
   config=json.loads(path.read_text())
   if is_dflash_k7(config,key):
    evidence[key]=dict(status='selected',label=selected_label,source_case=path.stem,identity=config_id(config))
    break
  if key in evidence:continue
  prefix='range-perf-' if environment else 'range-'
  eligible=[]
  for path in (R/'bench').glob(prefix+key+'-*/result.json'):
   result=json.loads(path.read_text());c=result.get('config',{})
   if result.get('status')!='ok' or c.get('workload')!='code' or c.get('benchmark_environment_id','legacy')!=environment_id:continue
   if not is_dflash_k7(c,key):continue
   source=W/(path.parent.name+'.json')
   if not source.is_file():continue
   planned=json.loads(source.read_text())
   if config_id(planned)!=config_id(c):continue
   eligible.append((result['tail_decode_tok_s'],path.parent.name,source,c))
  if not eligible:
   evidence[key]=dict(status='no-successful-matched-k7-code-run')
   continue
  _,case,source,c=max(eligible,key=lambda row:(row[0],row[1]))
  label+='-dflash-k7'
  configs[label]=dict(config=str(source),family=family)
  evidence[key]=dict(status='added',label=label,source_case=case,identity=config_id(c))
 return evidence

dflash_code_trials=add_dflash_code_trials()
plan=dict(status='ready',benchmark_environment_id=environment_id,selections=bindings,configs=configs,dflash_code_trials=dflash_code_trials,functions=['merge_intervals','lru_trace','verify_draft'])
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
 state.update(status='complete',completed_unix=time.time(),all_generations_completed=True,all_independent_functions_passed=all(row['passed']for row in rows),passed=sum(row['passed']for row in rows),total=len(rows),quality_receipt='code-functional-'+p.stem+'.json',scope='All selected long/distinct-peak-code controls and available matched DFlash2 K7 code candidates generated and independently tested; genuine semantic failures retained separately from completed generation')
except BaseException as error:
 state.update(status='failed',error=str(error),failed_unix=time.time());raise
finally:receipt.write_text(json.dumps(state,indent=2)+'\n')

# Confirm the saved and tuned presets at the original exact context percentages.
subprocess.run([sys.executable,str(W/'range_percent_check.py'),'qwen'],check=True)
subprocess.run([sys.executable,str(W/'range_progress_report.py')],check=True)
