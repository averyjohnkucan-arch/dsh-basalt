from pathlib import Path
import subprocess,time,json,sys
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
while subprocess.run(['systemctl','--user','is-active','--quiet','dsh-bounded-remaining80.service']).returncode==0:time.sleep(15)
c=json.loads((w/'bounded80-ninfer27-saved.json').read_text());c['output']=str(r/'bench/bounded80-ninfer27-saved-repeat');c['measurement_role']='Third NInfer run: A/B/A saved-setting repeat; distinguish throughput variation from prefill2048 improvement';p=w/'bounded80-ninfer27-saved-repeat.json';p.write_text(json.dumps(c,indent=2)+'\n')
subprocess.run([sys.executable,str(w/'http_bench.py'),'--config',str(p)],check=True)
