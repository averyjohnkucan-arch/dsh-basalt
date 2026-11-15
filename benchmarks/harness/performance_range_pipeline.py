"""Fresh matched matrix after verified power-policy repair; legacy data stays intact."""
from pathlib import Path
import json,subprocess,sys,time
from benchmark_environment import current_environment,ensure_environment
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
environment=current_environment();assert environment and environment['require_performance_policy'];ensure_environment()
proof=json.loads((O/'power-policy-matched-comparison.json').read_text());assert proof['status']=='ok'
receipt=O/'matrix-completion.json';state=dict(status='running',benchmark_environment_id=environment['id'],started_unix=time.time());receipt.write_text(json.dumps(state,indent=2))
try:
 for script,args,logfile in [('range_flash.py',['flash'],W/'range-flash-performance.progress'),('range_queue.py',['0'],W/'range-queue.progress')]:
  print(time.strftime('%H:%M:%S'),'START',script,*args,flush=True)
  with logfile.open('a')as log:subprocess.run([sys.executable,str(W/script),*args],stdout=log,stderr=subprocess.STDOUT,check=True)
  print(time.strftime('%H:%M:%S'),'END',script,*args,flush=True)
 state.update(status='complete',completed_unix=time.time(),scope='Matched range matrix, native-performance qualification, actual plugin GPU/argv verification, output inspection and generated-function execution; semantic test failures remain reported separately')
except BaseException as error:
 state.update(status='failed',error=str(error),failed_unix=time.time());raise
finally:receipt.write_text(json.dumps(state,indent=2)+'\n')
