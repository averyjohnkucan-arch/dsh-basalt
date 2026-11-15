from pathlib import Path
import subprocess,time,sys,json,shutil
from benchmark_environment import current_environment
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';parent=int(sys.argv[1])if len(sys.argv)>1 else 291532
while True:
 try:active=(Path('/proc')/str(parent)/'cmdline').read_bytes()
 except FileNotFoundError:break
 if b'range_flash.py'not in active:break
 time.sleep(5)
flash_progress=W/('range-flash-performance.progress'if current_environment()else'range-flash.progress')
if 'RANGE BASALT COMPLETE flash'not in flash_progress.read_text():raise RuntimeError('Flash controller incomplete; queue halted')
def clear(prefix):
 removed=[]
 for genre in ['text','chat','story']:
  p=R/'checkpoints'/('range-'+prefix+'-'+genre)
  if p.exists():assert p.parent==R/'checkpoints';shutil.rmtree(p);removed.append(str(p))
 if removed:
  path=O/'range-checkpoint-rotation.json';data=json.loads(path.read_text())if path.exists()else[];data.append(dict(prefix=prefix,removed=removed,reason='Completed screens; qualified raw measurements retained; cold reruns rebuild their own prefix'));path.write_text(json.dumps(data,indent=2))
clear('flash')
jobs=[]
def repeat(key,family):
 jobs.append((('range_repeatability.py',key,family),None))
 jobs.append((('range_low_peak.py',key,family),None))
 jobs.append((('range_repeatability.py',key,family,'--include-peak-code'),None))
def model(script,arg,key,family,cache):jobs.append(((script,arg),cache));repeat(key,family)
repeat('flash_basalt','qwen')
model('range_flash.py','hybrid','hybrid_basalt','qwen','hybrid')
for arg in ['flash','hybrid','gyro']:model('range_strata.py',arg,arg+'_strata','qwen',arg+'_strata')
jobs.append((('range_27b_basalt.py',),'27b_basalt'));repeat('27b_basalt','qwen27b')
if current_environment():jobs.append((('calibrate_performance_ninfer.py',),None))
jobs.append((('range_ninfer.py',),None));repeat('27b_ninfer','qwen27b')
for arg in ['flash_fp16','hybrid_fp16']:
 model('range_flash.py',arg,arg+'_basalt','qwen',arg)
 model('range_strata.py',arg,arg+'_strata','qwen',arg+'_strata')
for kv in ['nvfp4','int8','fp8']:model('range_ninfer.py',kv,'huihui_'+kv+'_ninfer','qwen27b',None)
jobs += [(('quality_range_selected.py',),None)]
for args,cache in jobs:
 label='-'.join(x.removesuffix('.py')for x in args);print(time.strftime('%H:%M:%S'),'START',label,flush=True)
 with(W/(label+'.progress')).open('a')as log:status=subprocess.run([sys.executable,str(W/args[0]),*args[1:]],stdout=log,stderr=subprocess.STDOUT).returncode
 print(time.strftime('%H:%M:%S'),'END',label,status,flush=True)
 if status:raise RuntimeError(label+' failed; queue halted')
 if cache:clear(cache)
print('RANGE QUEUE COMPLETE; DRAFTER EXPERIMENTS, DEEPSEEK, EXPORTS, PLUGIN GPU QUALIFICATION AND FINAL REPORT STILL REQUIRED',flush=True)
