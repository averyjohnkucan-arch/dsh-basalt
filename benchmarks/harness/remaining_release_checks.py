"""Latest Gyro/Huihui checks preserving historical benchmark prompts and lengths."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
while subprocess.run(['systemctl','--user','is-active','--quiet','dsh-flash-int8-matched.service']).returncode==0:time.sleep(30)
rows={}
for family in ['gyro','huihui-int8','huihui-fp8','huihui-nvfp4']:
 for depth in ['10','90']:
  source=w/(f'quiet-gyro-strata-{depth}.json' if family=='gyro' else f'quiet-ninfer-{family}-tuned-{depth}.json')
  c=json.loads(source.read_text());label=family+'-'+depth
  binary=r/'runtimes/strata-engine-0.1.60/strata' if family=='gyro' else r/'build/ninfer-20261116-custom/apps/ninfer-serve'
  c['command'][3]=str(binary)
  if family=='gyro':c['env']={'LD_LIBRARY_PATH':str(binary.parent)}
  else:
   i=c['command'].index('--device-profile-path')+1
   c['command'][i]=str(w/('ninfer1616-device-profile-'+family+'.json'))
  c.update(output=str(r/'bench'/('latest-remaining-'+label)),engine_binary_sha256=hashlib.file_digest(binary.open('rb'),'sha256').hexdigest(),measurement_role='Latest supported engine check; original saved prompt fixture and generation length; not Basalt support',host_memory_policy={'memory_high_gib':114,'memory_max_gib':114,'minimum_host_available_gib':0,'pressure_avg10_limit':100})
  path=w/('latest-remaining-'+label+'.json');path.write_text(json.dumps(c,indent=2)+'\n');print('START',label,flush=True)
  harness='native_bench.py' if family=='gyro' else 'http_bench.py'
  with (w/('latest-remaining-'+label+'.progress')).open('w') as log:
   process=subprocess.run([sys.executable,str(w/harness),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
  p=Path(c['output'])/'result.json';d=json.loads(p.read_text()) if p.exists() else {'status':'failed','error':'Missing result receipt'}
  rows[label]={k:d.get(k)for k in ['status','error','prefill_tok_s','decode_tok_s','tail_decode_tok_s','generated','reused_tokens']};rows[label].update(case=c['output'],binary_sha256=c['engine_binary_sha256'])
  (r/'outputs/latest-remaining-models.json').write_text(json.dumps(rows,indent=2)+'\n');print(label,rows[label],flush=True)
  if process.returncode:break
