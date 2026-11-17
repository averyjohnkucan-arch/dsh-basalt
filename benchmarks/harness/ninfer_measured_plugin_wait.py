from pathlib import Path
import subprocess,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
units=['dsh-flash-int8-matched.service','dsh-remaining-release-checks.service','dsh-fp16-plugin-validation.service']
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in units):time.sleep(30)
subprocess.run(['systemd-run','--user','--scope','--quiet','--collect','--unit=dsh-ninfer-measured-plugin','-p','MemoryMax=114G','node',str(w/'ninfer_measured_adapter_smoke.mjs'),'ninfer','scratch-measured-27b-ninfer1616',str(r/'validation/ninfer1616-measured-plugin')],check=True)
