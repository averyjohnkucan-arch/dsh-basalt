"""Serial post-performance plugin smoke, inside its own RAM-limited process scope."""
from pathlib import Path
import json,os,subprocess,sys,time,copy,hashlib,re
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
def same_launch_profile(a,b):
 if not a:return False
 a=copy.deepcopy(a);b=copy.deepcopy(b)
 for profile in [a,b]:profile.get('verification8192',{}).pop('codeFunctionalEvidence',None)
 return a==b
def expects_projection(profile):
 m=profile.get('model',{});metadata=next((f.get('metadata',{})for f in m.get('files',[])if f.get('index')==1),{})
 name=str(m.get('name',''))+' '+str(metadata.get('general.name',''))
 if m.get('architecture')!='qwen4exp'or'swift'in name.lower():return False
 layers=m.get('layerCount',metadata.get('qwen4exp.block_count'));width=m.get('embeddingLength',metadata.get('qwen4exp.embedding_length'))
 if layers is not None and layers!=48 or width is not None and width!=2560:return False
 return layers==48 and width==2560 or re.search(r'Qwen3[.]8[- ]Flash[- ]Next',name,re.I)is not None

def gpu_receipt_reusable(previous,profile,signature):
 return previous.get('status')=='ok'and previous.get('schemaVersion')==2 and previous.get('pluginSourceSha256')==signature and previous.get('nativeCommandEvidence',{}).get('status')=='ok'and same_launch_profile(previous.get('savedProfile'),profile)and(not expects_projection(profile)or previous.get('projectionModes',{}).get('status')=='passed')

source_files=[W/'range_plugin_adapter_smoke.mjs',W/f'dsh-{engine}/package.json',W/f'dsh-{engine}/engine.json',W/f'dsh-{engine}/index.js',W/f'dsh-{engine}/client.js',*sorted((W/f'dsh-{engine}/lib').glob('*.js'))]
hash_state=hashlib.sha256()
for path in source_files:
 if path.is_file():hash_state.update(str(path.relative_to(W)).encode()+b'\0'+path.read_bytes()+b'\0')
plugin_signature=hash_state.hexdigest()
for p in profiles:
 out=R/'validation/range-plugin-gpu'/p['id'];out.mkdir(parents=True,exist_ok=True)
 result=out/'adapter-result.json'
 if result.exists():
  previous=json.loads(result.read_text())
  if gpu_receipt_reusable(previous,p,plugin_signature):
   receipts.append(dict(profile=p['id'],status='ok',reused_qualified_receipt=True));continue
 evidence=p.get('verification8192',{}).get('hostMemoryEvidence',[])
 policy=evidence[0]['policy']if evidence else{}
 guard=MemoryGuard({'host_memory_policy':policy},out);telemetry=[]
 with(out/'worker.log').open('a')as log:
  proc=subprocess.Popen(guard.command(['taskset','-c','0-21',str(node),str(W/'range_plugin_adapter_smoke.mjs'),engine,p['id'],str(out)]),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'DSH_PLUGIN_SOURCE_SHA256':plugin_signature})
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
 receipt=json.loads(result.read_text());assert gpu_receipt_reusable(receipt,p,plugin_signature),'New GPU receipt lacks current source or projection-mode evidence';receipts.append(dict(profile=p['id'],status='ok',receipt=str(result)))
(O/'performance-qualified'/(key+'-plugin-gpu.json')).write_text(json.dumps(dict(model_key=key,status='ok',plugin_source_sha256=plugin_signature,benchmark_environment_id=marker.get('benchmark_environment_id','legacy'),receipts=receipts),indent=2))
print('PLUGIN GPU EVIDENCE GATE PASSED',key,flush=True)
