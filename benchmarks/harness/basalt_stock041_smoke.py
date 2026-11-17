"""Official release smoke coverage, serialized after existing benchmark queue."""
import copy,hashlib,json,subprocess,sys,time
from pathlib import Path
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
units=['dsh-ninfer1616-build-parallel.service','dsh-ninfer1616-after-build.service','dsh-ninfer-matched-depths.service','dsh-flash-fp16-matched.service']
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in units):time.sleep(30)
stock=r/'runtimes/basalt-stock-0.4.1/basalt-v0.4.1-linux-x64';binary=stock/'bin/basalt'
rows={};digest=hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()
for name,source in [('hybrid','range-perf-hybrid-basalt-long-profile-code.json'),('27b','latest-27b-basalt-dflash-probe.json'),('deepseek-xxs','deepseek-warm-240-fixed-xxs.json')]:
 c=copy.deepcopy(json.loads((w/source).read_text()));args=c['command'];args[3]=str(binary)
 c.update(output=str(r/'bench'/('stock041-smoke-'+name)),depth=4096,generate=256,timed_tail=128,cwd=str(stock),timeout=900,engine_binary_sha256=digest,measurement_role='Official 0.4.1 compatibility smoke; not maximum or matched speed comparison')
 c['env']={**c.get('env',{}),'LD_LIBRARY_PATH':str(r/'runtimes/strata-engine-0.1.60')}
 c['host_memory_policy']={'memory_high_gib':114,'memory_max_gib':114,'minimum_host_available_gib':0}
 if name=='deepseek-xxs':
  i=args.index('--deepseek-engram-gguf');del args[i:i+2]
  c['prompt_file']=str(w/'quick-basalt-deepseek.json')
  c['deepseek_storage_evidence']={'layout':'Official runtime uses embedded Engram in system-NVMe pack, unlike the split-runtime comparison; no storage-matched speed claim'}
 else:
  c['prompt_file']=str(w/'range-fixtures'/('qwen27b-code.json' if name=='27b' else 'qwen-code.json'))
 ids=json.loads(Path(c['prompt_file']).read_text());c['depth']=len(ids['ids'] if isinstance(ids,dict) else ids)
 if '--draft-log' in args:args[args.index('--draft-log')+1]=c['output']+'/draft.log'
 path=w/('stock041-smoke-'+name+'.json');path.write_text(json.dumps(c,indent=2)+'\n')
 print('START',name,flush=True)
 with (w/('stock041-smoke-'+name+'.progress')).open('w') as log:
  p=subprocess.run([sys.executable,str(w/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
 rp=Path(c['output'])/'result.json';d=json.loads(rp.read_text()) if rp.exists() else {'status':'failed','error':'No receipt; inspect progress log'}
 rows[name]={k:d.get(k) for k in ['status','error','prefill_tok_s','decode_tok_s','tail_decode_tok_s','generated']}
 rows[name].update(case=c['output'],binary_sha256=digest)
 (r/'outputs/basalt-stock041-smoke.json').write_text(json.dumps(rows,indent=2)+'\n');print(name,rows[name],flush=True)
