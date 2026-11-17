import subprocess,time
while subprocess.run(['systemctl','--user','is-active','--quiet','dsh-huihui-profile-validation-retry.service']).returncode==0:time.sleep(10)
subprocess.run(['systemd-run','--user','--scope','--quiet','--collect','--unit=dsh-gyro-measured-plugin','-p','MemoryMax=114G','node','/mnt/media/scratch/dsh-inference-tuning-20261115/work/gyro_measured_adapter_smoke.mjs','strata','scratch-measured-gyro-strata','/mnt/media/scratch/dsh-inference-tuning-20261115/validation/gyro-measured-plugin'],check=True)
