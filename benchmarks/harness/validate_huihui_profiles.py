from pathlib import Path
import subprocess
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
for kv in ['int8','fp8','nvfp4']:
 subprocess.run(['systemd-run','--user','--scope','--quiet','--collect','--unit=dsh-huihui-plugin-'+kv,'-p','MemoryMax=114G','node',str(r/'work/ninfer_measured_adapter_smoke.mjs'),'ninfer','scratch-measured-huihui-'+kv,str(r/'validation'/('huihui-measured-plugin-'+kv))],check=True)
