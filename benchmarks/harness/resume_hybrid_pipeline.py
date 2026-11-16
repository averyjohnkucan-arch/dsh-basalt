"""Serial recovery after the hybrid-pack layout fix; never overlap GPU owners."""
from pathlib import Path
import json,os,subprocess,sys,time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
unit='dsh-hybrid-fit-overlay-old-20261115.service'
while subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','--value'],capture_output=True,text=True).stdout.strip()in ['active','activating','deactivating']:
 time.sleep(10)
fit=json.loads((O/'hybrid-memory-fit-old-strata-high104.json').read_text())
assert fit['status']=='complete','Corrected original-Strata compatibility fit failed; inspect before restarting matrix'
assert fit['selected_budget_gib']==96,'Saved original96GiB budget did not fit; do not silently change the baseline'
for script,args,log in [('fit_hybrid_memory.py',['strata','--high104'],'hybrid-overlay-strata-fit.progress'),('performance_range_pipeline.py',[],'performance-pipeline.progress')]:
 print(time.strftime('%H:%M:%S'),'START',script,*args,flush=True)
 env={**os.environ,'DSH_QUEUE_START_INDEX':'3'}
 with(W/log).open('a')as output:subprocess.run([sys.executable,str(W/script),*args],env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
 print(time.strftime('%H:%M:%S'),'END',script,*args,flush=True)
print('RECOVERED MATRIX COMPLETE; DEEPSEEK, PACKAGING, PUBLICATION AND FINAL REPORT REMAIN REQUIRED',flush=True)
