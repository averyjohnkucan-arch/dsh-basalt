"""Matched short-code release comparison using the saved Strata controls."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
base=json.loads((w/'range-perf-flash_strata-long-profile-code.json').read_text())
rows={}
for version in ('0.1.59','0.1.60'):
 c=copy.deepcopy(base);runtime=r/'runtimes'/('strata-engine-'+version)
 c['command'][3]=str(runtime/'strata')
 c['env']['LD_LIBRARY_PATH']=str(runtime)
 c.update(generate=1024,timed_tail=512,timeout=900,engine_channel='official-'+version,
          output=str(r/'bench'/('strata-release-code-'+version)),
          measurement_role='Matched 8K code release check; 1024 output; last512 timed')
 c['engine_binary_sha256']=hashlib.file_digest((runtime/'strata').open('rb'),'sha256').hexdigest()
 c.pop('benchmark_environment_id',None)
 path=w/('strata-release-code-'+version+'.json')
 path.write_text(json.dumps(c,indent=2)+'\n')
 print('START',version,flush=True)
 with (w/('strata-release-code-'+version+'.progress')).open('w') as log:
  subprocess.run([sys.executable,str(w/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
 result=json.loads((Path(c['output'])/'result.json').read_text())
 rows[version]={k:result.get(k) for k in ('status','error','prefill_tok_s','tail_decode_tok_s','generated','reused_tokens')}
 rows[version]['case']=c['output']
 (r/'outputs/strata-release-code-comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(version,rows[version],flush=True)
