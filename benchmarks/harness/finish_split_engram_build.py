"""Install a new private runtime only after its managed CPU build succeeds."""
from pathlib import Path
import subprocess,time,shutil,json,hashlib,os
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs'
unit='dsh-basalt-split-engram-build-20261116.service'
while subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','--value'],capture_output=True,text=True,check=True).stdout.strip() in ('active','activating','deactivating'):
    time.sleep(5)
assert subprocess.run(['systemctl','--user','show',unit,'-p','Result','--value'],capture_output=True,text=True,check=True).stdout.strip()=='success', 'Split Engram build failed'
assert json.loads((O/'external-engram-cpu-tests.json').read_text())['status']=='passed'
dest=R/'runtimes/basalt-deepseek-split';shutil.copytree(R/'runtimes/basalt-custom-latest',dest,dirs_exist_ok=True,symlinks=True)
source=R/'work/basalt-latest/bin/basalt';temp=dest/'bin/basalt.new';shutil.copy2(source,temp);os.replace(temp,dest/'bin/basalt')
with (dest/'bin/basalt').open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
assert sha!='a2bb78bc53910cb738395d5582ab048c1ffc3aa7a0bd95838fcd31e4bf5ebeb0'
manifest=dest/'dsh-engine.json';metadata=json.loads(manifest.read_text());metadata['features']=sorted(set(metadata.get('features',[])+['deepseek_external_engram']));metadata['binarySha256']=sha;manifest.write_text(json.dumps(metadata,indent=2)+'\n')
record=dict(status='built-cpu-validated-gpu-parity-pending',binary=str(dest/'bin/basalt'),binary_sha256=sha,
            completed_unix=time.time(),purpose='Optional split-drive Engram; old frozen runtime and active Qwen benchmarks untouched',
            required_gpu_gate='range_deepseek frozen64 identity probe with external Engram before throughput tuning')
(O/'basalt-split-engram-build.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
