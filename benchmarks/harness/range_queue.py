from pathlib import Path
import subprocess,time,sys,json,shutil,os,hashlib
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
start=int(os.environ.get('DSH_QUEUE_START_INDEX','0'));assert 0<=start<=len(jobs)
environment=current_environment();environment_id=environment['id']if environment else'legacy'
checkpoint=O/'matrix-queue-checkpoint.json';plan_sha=hashlib.sha256(json.dumps(jobs).encode()).hexdigest();completed=set()
if checkpoint.exists():
 prior=json.loads(checkpoint.read_text())
 if prior.get('benchmark_environment_id')==environment_id:
  assert prior['plan_sha256']==plan_sha,'Queue order changed; inspect checkpoint before resuming'
  completed=set(prior['completed_indices'])
if start==3 and not set(range(start))<=completed:
 # The first recovered matrix predates per-job checkpoints. Seed only the
 # three completed Flash qualification jobs, backed by current native/GPU proof.
 state=json.loads((O/'range-selections.json').read_text());proof=json.loads((O/'performance-qualified/flash_basalt.json').read_text());gpu=json.loads((O/'performance-qualified/flash_basalt-plugin-gpu.json').read_text())
 assert proof['performance_qualified']and proof['benchmark_environment_id']==environment_id and gpu['status']=='ok'and gpu['benchmark_environment_id']==environment_id
 for kind in ['long','short']:
  assert proof[kind+'_selection']==state['flash_basalt_'+kind]['selected']and proof[kind+'_metrics']==state.get('flash_basalt_'+kind+'_metrics')
  r=json.loads((R/'bench'/proof[kind+'_selection']/'result.json').read_text());binary=Path(r['config']['command'][3]);assert hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()==r['config']['engine_binary_sha256']
 completed.update(range(3))
assert set(range(start))<=completed,'Cannot skip queue jobs without completion evidence'
if '--plan'in sys.argv:
 print(json.dumps(dict(start_index=start,total_jobs=len(jobs),next_job=list(jobs[start][0])if start<len(jobs)else None,validated_skipped_indices=list(range(start)),benchmark_environment_id=environment_id,plan_sha256=plan_sha),indent=2));raise SystemExit(0)
def checkpoint_status(index,status,error=None):
 data=dict(benchmark_environment_id=environment_id,plan_sha256=plan_sha,total_jobs=len(jobs),next_index=index,status=status,completed_indices=sorted(completed),updated_unix=time.time())
 if error:data['error']=error
 temp=checkpoint.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(checkpoint)
if start==0:clear('flash')
for index,(args,cache)in enumerate(jobs):
 if index<start:continue
 checkpoint_status(index,'running')
 label='-'.join(x.removesuffix('.py')for x in args);print(time.strftime('%H:%M:%S'),'START',label,flush=True)
 with(W/(label+'.progress')).open('a')as log:status=subprocess.run([sys.executable,str(W/args[0]),*args[1:]],stdout=log,stderr=subprocess.STDOUT).returncode
 print(time.strftime('%H:%M:%S'),'END',label,status,flush=True)
 if status:
  checkpoint_status(index,'failed',label+' failed');raise RuntimeError(label+' failed; queue halted')
 if cache:clear(cache)
 completed.add(index);checkpoint_status(index+1,'ready')
checkpoint_status(len(jobs),'complete')
print('RANGE QUEUE COMPLETE; DRAFTER EXPERIMENTS, DEEPSEEK, EXPORTS, PLUGIN GPU QUALIFICATION AND FINAL REPORT STILL REQUIRED',flush=True)
