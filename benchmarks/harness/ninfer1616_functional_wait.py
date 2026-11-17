from pathlib import Path
import subprocess,sys,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
units=['dsh-flash-fp16-matched.service','dsh-basalt-stock041-smoke.service','dsh-flash-fp16-retry.service']
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in units):time.sleep(30)
raise SystemExit(subprocess.run([sys.executable,str(w/'code_function_eval.py'),str(w/'ninfer1616-functional-configs.json')]).returncode)
