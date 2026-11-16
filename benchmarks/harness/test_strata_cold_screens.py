"""Execute the actual Strata preset planner without allowing a GPU launch."""
from pathlib import Path
import ast,copy,json,sys,types,hashlib,time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';sys.path.insert(0,str(W));sys.path.insert(0,str(W/'basalt-latest'))
import range_tuner
from serve.config import engine_flags_of,check_engine_flags
source=W/'range_strata.py';tree=ast.parse(source.read_text());tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom) and n.module=='range_tuner')];code=compile(tree,str(source),'exec')
flags=engine_flags_of(str(R/'runtimes/strata-engine-0.1.59/strata'));records=[]
for model in ['flash','hybrid','gyro','flash_fp16','hybrid_fp16']:
 ns=dict(range_tuner.__dict__);ns['sys']=types.SimpleNamespace(argv=['range_strata.py',model]);captured=[];ns['tune']=lambda *a,**kw:captured.append((a,kw));exec(code,ns)
 assert len(captured)==1;args,kw=captured[0];assert kw['cache'] is False
 for tag,c in [('base',args[1]),*args[3]]:
  check_engine_flags(c['command'][4:],flags,model+'/'+tag)
 records.append(dict(model=model,planned_candidates=len(args[3]),cold_screens=True,native_flag_vocabulary='passed'))
for name in ['range_deepseek.py','range_deepseek_xs.py']:
 tree=ast.parse((W/name).read_text())
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tune':
   assert any(k.arg=='cache' and isinstance(k.value,ast.Constant) and k.value.value is False for k in node.keywords),name
record=dict(status='passed',updated_unix=time.time(),scope='Actual five-model Strata planner executed with tune replaced by capture-only spy; every base/candidate checked against installed native binary flags; all DeepSeek tune calls explicitly cold. No GPU processes launched.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),models=records)
(R/'outputs/strata-cold-screen-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
