"""Run matched old/latest NInfer depth checks after successful build validation."""
import copy, hashlib, json, subprocess, sys, time
from pathlib import Path
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115'); w=r/'work'
unit='dsh-ninfer1616-after-build.service'
while subprocess.run(['systemctl','--user','is-active','--quiet',unit]).returncode==0:
 time.sleep(30)
receipt=json.loads((r/'outputs/ninfer1616-recovery-validation.json').read_text())
if receipt.get('status')!='ok':
 raise RuntimeError('Latest runtime validation did not pass; no benchmark launched')
base=json.loads((w/'latest-ninfer-native-k7-probe.json').read_text())
fixtures=json.loads((r/'outputs/range-percent-workloads.json').read_text())['cases']
rows={}
for version,binary in [('prior',Path(base['command'][3])),('latest',r/'build/ninfer-20261116-custom/apps/ninfer-serve')]:
 digest=hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()
 for genre in ('code10','chat90'):
  label=version+'-'+genre
  c=copy.deepcopy(base); c['command'][3]=str(binary)
  fixture=next(x for x in fixtures if x['family']=='qwen27b' and x['workload']==genre)
  c.update(prompt_file=fixture['prompt_file'],depth=fixture['depth'],generate=512,timed_tail=256,
   output=str(r/'bench'/('ninfer-matched-'+label)),engine_binary_sha256=digest,
   measurement_role='Matched prior/latest NInfer; same prompt IDs as Basalt, distinct stop-control implementation')
  path=w/('ninfer-matched-'+label+'.json');path.write_text(json.dumps(c,indent=2)+'\n')
  print('START',label,flush=True)
  with (w/('ninfer-matched-'+label+'.progress')).open('w') as log:
   p=subprocess.run([sys.executable,str(w/'http_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
  result=json.loads((Path(c['output'])/'result.json').read_text())
  rows[label]={k:result.get(k) for k in ('status','error','prefill_tok_s','decode_tok_s','tail_decode_tok_s','generated','reused_tokens')}
  rows[label].update(case=c['output'],binary_sha256=digest,prompt_sha256=fixture['token_sha256'])
  (r/'outputs/ninfer-matched-depths.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(label,rows[label],flush=True)
  if p.returncode: raise RuntimeError('Benchmark failed: '+label)
