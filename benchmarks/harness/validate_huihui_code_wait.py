import subprocess,time
while subprocess.run(['systemctl','--user','is-active','--quiet','dsh-remaining-artifact-code-tests.service']).returncode==0:time.sleep(15)
subprocess.run(['/mnt/media/scratch/dsh-inference-tuning-20261115/tools/build-env/bin/python','/mnt/media/scratch/dsh-inference-tuning-20261115/work/code_function_eval.py','/mnt/media/scratch/dsh-inference-tuning-20261115/work/huihui-functional-configs.json'],check=True)
