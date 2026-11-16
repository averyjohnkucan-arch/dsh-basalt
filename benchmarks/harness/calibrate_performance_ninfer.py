"""Serial, build-matched route calibration under the repaired performance policy."""
from pathlib import Path
import hashlib,json,os,subprocess,time
from benchmark_environment import ensure_environment,current_environment,power_snapshot
from benchmark_memory_guard import MemoryGuard
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';environment=current_environment();assert environment;ensure_environment();receipts=[]
for kind,build,old_name in [('compatible','ninfer-latest','ninfer-device-profile-latest-custom.json'),('native','ninfer-latest-native','ninfer-device-profile-latest-native.json')]:
 binary=R/'build'/build/'apps/ninfer-calibrate';output=W/old_name.replace('.json','-performance.json');folder=R/'validation'/('ninfer-performance-calibration-'+kind);folder.mkdir(parents=True,exist_ok=True)
 prior=json.loads((W/old_name).read_text())['devices'][0];guard=MemoryGuard({},folder);telemetry=[]
 command=['taskset','-c','0-21',str(binary),'--device','0','--repeat','7','--out',str(output)]
 print(time.strftime('%H:%M:%S'),'CALIBRATE',kind,flush=True)
 with(folder/'calibrator.log').open('w')as log:
  proc=subprocess.Popen(guard.command(command),stdout=log,stderr=subprocess.STDOUT,start_new_session=True);deadline=time.monotonic()+3600
  try:
   while proc.poll()is None:
    row=dict(time=time.time(),host_memory=guard.sample(proc),power_policy=power_snapshot());telemetry.append(row)
    try:row['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=power.draw,enforced.power.limit,clocks.current.graphics,temperature.gpu','--format=csv,noheader,nounits'],text=True,timeout=5).strip()
    except Exception as error:row['gpu_error']=str(error)
    if guard.reason:break
    if time.monotonic()>deadline:raise TimeoutError('Device calibration exceeded3600seconds')
    time.sleep(1)
   status=proc.wait(timeout=15)
  finally:
   guard.stop(proc);(folder/'telemetry.json').write_text(json.dumps(dict(policy=guard.policy,reason=guard.reason,samples=telemetry),indent=2))
  assert status==0 and not guard.reason,'Device calibration failed; inspect '+str(folder)
 ensure_environment();entry=json.loads(output.read_text())['devices'][0]
 assert entry['multiprocessors']==prior['multiprocessors']==82
 assert entry['calibration']['route_catalog']==prior['calibration']['route_catalog']
 assert set(entry['routes'])==set(prior['routes'])
 receipts.append(dict(backend=kind,benchmark_environment_id=environment['id'],profile=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),calibrator=str(binary),calibrator_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),route_catalog=entry['calibration']['route_catalog'],route_keys=len(entry['routes']),changed_keys=[key for key in entry['routes']if entry['routes'][key]!=prior['routes'][key]],previous_profile_unchanged=str(W/old_name)))
 (O/'ninfer-performance-calibrations.json').write_text(json.dumps(dict(status='complete'if len(receipts)==2 else'partial',receipts=receipts),indent=2)+'\n')
print('BOTH PERFORMANCE DEVICE CALIBRATIONS COMPLETE',flush=True)
