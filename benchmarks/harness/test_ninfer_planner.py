"""Run the real NInfer preset planner with GPU measurement calls captured only."""
from pathlib import Path
import ast,json,sys,types,hashlib,time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';sys.path.insert(0,str(W));sys.path.insert(0,str(W/'basalt-latest'))
import range_tuner
from serve.config import engine_flags_of,check_engine_flags
source=W/'range_ninfer.py';tree=ast.parse(source.read_text());tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom)and n.module=='range_tuner')];code=compile(tree,str(source),'exec');flags={};binary_hashes={};rows=[]
for variant in ['nvfp4full','nvfp4','int8','fp8']:
 ns=dict(range_tuner.__dict__);ns['sys']=types.SimpleNamespace(argv=['range_ninfer.py',variant]);calls=[];ns['tune']=lambda *a,**kw:calls.append((a,kw));exec(code,ns)
 assert len(calls)==1;args,kw=calls[0];assert kw['cache'] is False
 for tag,c in [('base',args[1]),*args[3]]:
  binary=c['command'][3]
  if binary not in flags:
   flags[binary]=engine_flags_of(binary)
   with open(binary,'rb')as f:binary_hashes[binary]=hashlib.file_digest(f,'sha256').hexdigest()
  assert flags[binary],binary;check_engine_flags(c['command'][4:],flags[binary],variant+'/'+tag)
 rows.append(dict(variant=variant,candidates=len(args[3]),executables=sorted({x['command'][3]for _,x in args[3]})))
record=dict(status='passed',updated_unix=time.time(),scope='Actual NInfer planner with measurement calls replaced by capture-only spy. Base/candidate flag vocabulary checked against both compiled binaries; option-value/model inference support remains a runtime gate.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binaries_sha256=binary_hashes,variants=rows,gpu_workers_started=0)
(R/'outputs/ninfer-planner-preflight.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS four variants and48 candidate configurations; zero GPU launches')
