"""Bounded saved-profile/Basalt INT8 checks after the existing GPU queue."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
units=['dsh-basalt-stock041-warm.service','dsh-ninfer1616-functional.service','dsh-flash-fp16-retry.service']
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in units):time.sleep(30)
fixtures=json.loads((r/'outputs/range-percent-workloads.json').read_text())['cases'];rows={}
configs={('flash','old'):'range-perf-flash-old-code.json',('flash','basalt'):'range-perf-flash-basalt-long-profile-code.json',('hybrid','old'):'range-perf-hybrid-old-code.json',('hybrid','basalt'):'range-perf-hybrid-basalt-long-profile-code.json'}
for (family,arm),source in configs.items():
 base=json.loads((w/source).read_text());args=base['command']
 args[args.index('--kv')+1]='int8'
 # Keep each saved or selected INT8 preset's measured resident KV footprint.
 base.update(host_memory_policy={'memory_high_gib':114,'memory_max_gib':114,'minimum_host_available_gib':0},measurement_role='Bounded matched INT8 depth comparison; candidate, not proven maximum')
 base['engine_binary_sha256']=hashlib.file_digest(Path(args[3]).open('rb'),'sha256').hexdigest()
 for genre in ['code10','chat90']:
  c=copy.deepcopy(base);label=f'{family}-{arm}-{genre}'
  fixture=next(x for x in fixtures if x['family']=='qwen' and x['workload']==genre)
  c.update(prompt_file=fixture['prompt_file'],depth=fixture['depth'],generate=512,timed_tail=256,workload=genre,output=str(r/'bench'/('int8-matched-'+label)))
  if '--draft-log' in c['command']:c['command'][c['command'].index('--draft-log')+1]=c['output']+'/draft.log'
  path=w/('int8-matched-'+label+'.json');path.write_text(json.dumps(c,indent=2)+'\n')
  print('START',label,flush=True)
  with (w/('int8-matched-'+label+'.progress')).open('w') as log:
   process=subprocess.run([sys.executable,str(w/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
  result_path=Path(c['output'])/'result.json'
  d=json.loads(result_path.read_text()) if result_path.exists() else {'status':'failed','error':'No result receipt; inspect progress log'}
  rows[label]={k:d.get(k) for k in ['status','error','prefill_tok_s','decode_tok_s','tail_decode_tok_s','generated','reused_tokens']}
  rows[label].update(case=c['output'],binary_sha256=c['engine_binary_sha256'],prompt_sha256=fixture['token_sha256'])
  (r/'outputs/flash-int8-matched-depths.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(label,rows[label],flush=True)
  if process.returncode:break
