from pathlib import Path
import copy,json,subprocess,sys
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
base=json.loads((w/'latest-27b-basalt-dflash-probe.json').read_text())
fixtures=json.loads((r/'outputs/range-percent-workloads.json').read_text())
base['command'][base['command'].index('--kv-resident')+1]='114688'
rows={}
for genre in ('code10','chat90'):
 c=copy.deepcopy(base)
 fixture=next(x for x in fixtures['cases'] if x['family']=='qwen27b' and x['workload']==genre)
 c.update(prompt_file=fixture['prompt_file'],depth=fixture['depth'],generate=512,timed_tail=256,
          output=str(r/'bench'/('basalt27-resident112k-'+genre)),workload=genre,timeout=3600,
          measurement_role='Final depth check using validated DFlash2 and 112K resident KV; not a maximum claim')
 path=w/('basalt27-resident112k-'+genre+'.json');path.write_text(json.dumps(c,indent=2)+'\n')
 print('START',genre,flush=True)
 with (w/('basalt27-resident112k-'+genre+'.progress')).open('w') as log:
  subprocess.run([sys.executable,str(w/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
 d=json.loads((Path(c['output'])/'result.json').read_text())
 rows[genre]={k:d.get(k) for k in ('status','error','prefill_tok_s','decode_tok_s','tail_decode_tok_s','generated','reused_tokens')}
 rows[genre]['case']=c['output']
 (r/'outputs/basalt27-resident112k-depths.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(genre,rows[genre],flush=True)
