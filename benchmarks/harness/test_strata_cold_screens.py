"""Execute the actual Strata preset planner without allowing a GPU launch."""
from pathlib import Path
import ast,copy,json,sys,types,hashlib,time,os,subprocess
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';sys.path.insert(0,str(W));sys.path.insert(0,str(W/'basalt-latest'))
import range_tuner
source=W/'range_strata.py';tree=ast.parse(source.read_text());tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom) and n.module=='range_tuner')];code=compile(tree,str(source),'exec')
records=[]
def check_native(config, label):
 binary=Path(config['command'][3])
 env={**os.environ,**config.get('env',{}),'LD_LIBRARY_PATH':str(binary.parent)}
 probe=subprocess.run([str(binary),*config['command'][4:],'--invalid-preflight-sentinel'],
                      capture_output=True,text=True,env=env,timeout=10)
 assert probe.returncode and 'unknown argument: --invalid-preflight-sentinel' in probe.stderr+probe.stdout,(label,probe.stderr,probe.stdout)
for model in ['flash','hybrid','gyro','flash_fp16','hybrid_fp16']:
 ns=dict(range_tuner.__dict__);ns['sys']=types.SimpleNamespace(argv=['range_strata.py',model]);captured=[];ns['tune']=lambda *a,**kw:captured.append((a,kw));exec(code,ns)
 assert len(captured)==1;args,kw=captured[0];assert kw['cache'] is False
 for tag,c in [('base',args[1]),*args[3]]:
  check_native(c,model+'/'+tag)
  assert int(c['command'][c['command'].index('--spec')+1])>=2,(model,tag)
 records.append(dict(model=model,binary=args[1]['command'][3],planned_candidates=len(args[3]),cold_screens=True,native_flag_vocabulary='passed',native_iq_minimum_window=2))
# Exercise the actual joint-stage MTP2 planner with a DFlash starting preset.
joint=ast.parse((W/'range_joint_refine.py').read_text())
node=next(n for n in joint.body if isinstance(n,ast.If) and ast.unparse(n.test)=="key.endswith('_strata')")
ns=dict(range_tuner.__dict__);ns.update(key='flash_strata',base=range_tuner.changed(c,{'--draft':'dflash2','--draft-model':'/fixture','--draft-cap':8,'--draft-conf':.55}),configured=[])
exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-joint-plan','exec'),ns)
assert len(ns['configured'])==5
_,mtp2=ns['configured'][0];assert mtp2['command'][mtp2['command'].index('--spec')+1]=='2'
assert not any(x in mtp2['command']for x in ['--draft','--draft-model','--draft-cap','--draft-conf'])
for _,trial in ns['configured'][1:]:
 a=trial['command'];assert a[a.index('--draft')+1]=='dflash2'and a[a.index('--draft-fallback')+1]=='none'
 assert (int(a[a.index('--draft-cap')+1]),a[a.index('--draft-conf')+1])in[(6,'0.1'),(8,'0.1'),(4,'0.9'),(8,'0.75')]
 check_native(trial,'low-confidence-DFlash')
for name in ['range_deepseek.py','range_deepseek_xs.py']:
 tree=ast.parse((W/name).read_text())
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tune':
   assert any(k.arg=='cache' and isinstance(k.value,ast.Constant) and k.value.value is False for k in node.keywords),name
record=dict(status='passed',updated_unix=time.time(),scope='Actual five-model Strata planner executed with tune replaced by capture-only spy; every base/candidate checked against installed native binary flags; all DeepSeek tune calls explicitly cold. No GPU processes launched.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),models=records,joint_trials=['native-mtp2','DFlash cap6 confidence0.1','DFlash cap8 confidence0.1','DFlash cap4 confidence0.9','DFlash cap8 confidence0.75 full-output'])
(R/'outputs/strata-cold-screen-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
