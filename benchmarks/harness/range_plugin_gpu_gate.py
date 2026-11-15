"""Serial post-performance plugin smoke, inside its own RAM-limited process scope."""
from pathlib import Path
import json,os,subprocess,sys,time
from benchmark_memory_guard import MemoryGuard
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
key=sys.argv[1];engine=key.rsplit('_',1)[1]
assert engine in ['basalt','strata','ninfer']
marker=json.loads((O/'performance-qualified'/(key+'.json')).read_text());assert marker['performance_qualified']
node=R/'tools/node-v24.11.1-linux-x64/bin/node'
subprocess.run([str(node),str(W/f'export_range_{engine}.mjs')],check=True)
data=json.loads((O/f'dsh-{engine}-range-state/profiles.json').read_text());profiles=data['profiles']if isinstance(data,dict)else data
profiles=[p for p in profiles if p['id'].startswith('scratch-range-'+key.replace('_','-')+'-')]
assert profiles,'No performance-qualified profiles exported'
receipts=[]
for p in profiles:
 out=R/'validation/range-plugin-gpu'/p['id'];out.mkdir(parents=True,exist_ok=True)
 result=out/'adapter-result.json'
 if result.exists():
  previous=json.loads(result.read_text())
  if previous.get('status')=='ok'and previous.get('savedVerification')==p.get('verification8192'):
   receipts.append(dict(profile=p['id'],status='ok',reused_qualified_receipt=True));continue
 guard=MemoryGuard({},out);telemetry=[]
 with(out/'worker.log').open('a')as log:
  proc=subprocess.Popen(guard.command(['taskset','-c','0-21',str(node),str(W/'range_plugin_adapter_smoke.mjs'),engine,p['id'],str(out)]),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  deadline=time.monotonic()+660
  try:
   while proc.poll()is None:
    telemetry.append(dict(time=time.time(),host_memory=guard.sample(proc)))
    if guard.reason:break
    if time.monotonic()>deadline:raise TimeoutError('Plugin GPU smoke exceeded 660 seconds')
    time.sleep(1)
   status=proc.wait(timeout=15)
  finally:
   guard.stop(proc)
   (out/'host-memory.json').write_text(json.dumps(dict(policy=guard.policy,reason=guard.reason,samples=telemetry),indent=2))
  assert status==0 and not guard.reason,f'Plugin GPU smoke failed: {p["id"]}; see {out}'
 receipt=json.loads(result.read_text());assert receipt['status']=='ok';receipts.append(dict(profile=p['id'],status='ok',receipt=str(result)))
(O/'performance-qualified'/(key+'-plugin-gpu.json')).write_text(json.dumps(dict(model_key=key,status='ok',receipts=receipts),indent=2))
print('PLUGIN GPU EVIDENCE GATE PASSED',key,flush=True)
