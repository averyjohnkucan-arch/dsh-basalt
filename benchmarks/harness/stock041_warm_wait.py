from pathlib import Path
import subprocess,sys,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
units=['dsh-flash-fp16-retry.service','dsh-ninfer1616-functional.service']
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in units):time.sleep(30)
raise SystemExit(subprocess.run([sys.executable,str(w/'native_warm_240.py'),'--config',str(w/'stock041-deepseek-warm240.json')]).returncode)
