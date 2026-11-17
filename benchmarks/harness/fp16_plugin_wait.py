from pathlib import Path
import subprocess,time
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work'
while any(subprocess.run(['systemctl','--user','is-active','--quiet',u]).returncode==0 for u in ['dsh-flash-int8-matched.service','dsh-remaining-release-checks.service']):time.sleep(30)
for family in ['flash','hybrid']:
 command=['systemd-run','--user','--scope','--quiet','--collect','--unit=dsh-fp16-plugin-'+family,'-p','MemoryMax=114G','node',str(w/'fp16_plugin_adapter_smoke.mjs'),'basalt','scratch-measured-'+family+'-fp16',str(r/'validation'/('fp16-plugin-'+family))]
 subprocess.run(command,check=True)
