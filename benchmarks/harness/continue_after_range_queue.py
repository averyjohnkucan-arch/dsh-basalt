"""Wait for the durable serial matrix; never overlap GPU owners or skip failure."""
from pathlib import Path
import json,subprocess,sys,time,os
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
unit=os.environ.get('DSH_MATRIX_UNIT','dsh-inference-range-20261115-recovery.service')
while subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','--value'],capture_output=True,text=True).stdout.strip()in ['active','activating','deactivating']:
 time.sleep(10)
environment=O/'active-benchmark-environment.json'
if environment.exists():
 receipt=json.loads((O/'matrix-completion.json').read_text());expected=json.loads(environment.read_text())['id']
 assert receipt['status']=='complete'and receipt['benchmark_environment_id']==expected,'Earlier performance matrix did not complete; no DeepSeek rotation'
else:
 status=subprocess.run(['systemctl','--user','show',unit,'-p','Result','--value'],capture_output=True,text=True).stdout.strip()
 assert status=='success','Earlier benchmark service failed; no automatic DeepSeek restart or rotation'
assert 'RANGE QUEUE COMPLETE;'in(W/'range-queue.progress').read_text(),'Earlier serial matrix did not finish'
jobs=[('range_deepseek.py',)]
for key in ['deepseek_basalt','deepseek_strata']:
 jobs.extend([('range_repeatability.py',key,'deepseek'),('range_low_peak.py',key,'deepseek'),('range_repeatability.py',key,'deepseek','--include-peak-code')])
for args in jobs:
 print(time.strftime('%H:%M:%S'),'START',' '.join(args),flush=True)
 with(W/('-'.join(args).replace('.py','')+'.progress')).open('a')as log:
  subprocess.run([sys.executable,str(W/args[0]),*args[1:]],stdout=log,stderr=subprocess.STDOUT,check=True)
 print(time.strftime('%H:%M:%S'),'END',' '.join(args),flush=True)
configs={};s=json.loads((O/'range-selections.json').read_text())
for key in ['deepseek_basalt','deepseek_strata']:
 for kind in ['long','short']:
  configs[key+'-'+kind]=dict(config=str(W/(s[key+'_'+kind]['selected']+'.json')),family='deepseek')
path=W/'range-deepseek-selected-functional-configs.json';path.write_text(json.dumps(configs,indent=2))
subprocess.run([sys.executable,str(W/'code_function_eval.py'),str(path)],check=True)
print('DEEPSEEK RANGE AND PLUGIN STAGE COMPLETE; FINAL PACKAGING, PUBLICATION AND REPORT REMAIN REQUIRED',flush=True)
