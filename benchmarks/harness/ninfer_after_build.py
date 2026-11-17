"""Validate the recovered NInfer revision once its owned build succeeds."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
w=r/'work';b=r/'build/ninfer-20261116-custom'
unit='dsh-ninfer1616-build-parallel.service'
out=r/'outputs/ninfer1616-recovery-validation.json'
def record(value):
 out.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(value),flush=True)
while subprocess.run(['systemctl','--user','is-active','--quiet',unit]).returncode==0:
 time.sleep(30)
status=subprocess.check_output(['systemctl','--user','show',unit,'-p','Result','--value'],text=True).strip()
if status!='success':
 record({'status':'build-failed','systemd_result':status});sys.exit(1)
binary=b/'apps/ninfer-serve'
receipt={'status':'testing','source_revision':subprocess.check_output(['git','-C',str(w/'upstream-20261116/ninfer'),'rev-parse','HEAD'],text=True).strip(),
         'binary_sha256':hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()}
test=subprocess.run([str(b/'tests/ninfer_dflash2_nvfp4_routes_test')],capture_output=True,text=True,timeout=300)
(w/'ninfer1616-routes-test.log').write_text(test.stdout+test.stderr)
receipt['route_test_exit']=test.returncode
if test.returncode!=0:
 receipt['status']='route-test-failed-or-skipped';record(receipt);sys.exit(1)
config=json.loads((w/'latest-ninfer-native-k7-probe.json').read_text())
config['command'][3]=str(binary)
config['output']=str(r/'bench/ninfer1616-native-k7-probe')
config['engine_binary_sha256']=receipt['binary_sha256']
path=w/'ninfer1616-native-k7-probe.json'
path.write_text(json.dumps(config,indent=2)+'\n')
with (w/'ninfer1616-native-k7-probe.progress').open('w') as log:
 process=subprocess.run([sys.executable,str(w/'http_bench.py'),'--config',str(path)],
                        stdout=log,stderr=subprocess.STDOUT)
result=json.loads((Path(config['output'])/'result.json').read_text())
receipt.update(status=result['status'],case=config['output'],
               prefill_tok_s=result.get('prefill_tok_s'),decode_tok_s=result.get('decode_tok_s'),
               error=result.get('error'))
record(receipt)
