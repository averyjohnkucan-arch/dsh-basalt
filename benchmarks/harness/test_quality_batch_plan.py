"""Execute the actual complete-family plan against controlled file-backed receipts."""
from pathlib import Path
import ast,contextlib,copy,hashlib,io,json,subprocess,sys,tempfile
from benchmark_environment import current_environment
from range_identity import config_id
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/quality_range_selected.py';parent=R/'validation/functional-recovery';parent.mkdir(parents=True,exist_ok=True)
keys=['flash_basalt','hybrid_basalt','27b_basalt','27b_ninfer','flash_strata','hybrid_strata','gyro_strata','flash_fp16_basalt','hybrid_fp16_basalt','flash_fp16_strata','hybrid_fp16_strata','huihui_nvfp4_ninfer','huihui_int8_ninfer','huihui_fp8_ninfer']
environment=current_environment();env_id=environment['id']if environment else'legacy'
def exercise(count,peak=False,tamper=False):
 root=Path(tempfile.mkdtemp(prefix='plan-',dir=parent));w=root/'work';o=root/'outputs';w.mkdir();o.mkdir();proofs=o/'performance-qualified';proofs.mkdir();state={}
 for key in keys[:count]:
  c=dict(command=['taskset','-c','0-21','fixture-engine','--spec','8'],engine_binary_sha256='fixture-engine-sha',benchmark_environment_id=env_id)
  case=key+'-long';(w/(case+'.json')).write_text(json.dumps(c));short=case
  if peak and key==keys[0]:
   short=key+'-short';changed=copy.deepcopy(c);changed['command'][-1]='4';(w/(short+'.json')).write_text(json.dumps(changed))
  state[key+'_long']=dict(selected=case);state[key+'_short']=dict(selected=short)
  q=dict(performance_qualified=True,long_selection=case,short_selection=short,long_identity=config_id(c),short_identity=config_id(json.loads((w/(short+'.json')).read_text())),benchmark_environment_id=env_id)
  (proofs/(key+'.json')).write_text(json.dumps(q));(proofs/(key+'-plugin-gpu.json')).write_text(json.dumps(dict(status='ok',benchmark_environment_id=env_id)))
 if tamper:
  p=w/(keys[0]+'-long.json');c=json.loads(p.read_text());c['command'][-1]='6';p.write_text(json.dumps(c))
 (o/'range-selections.json').write_text(json.dumps(state));tree=ast.parse(source.read_text())
 for node in ast.walk(tree):
  if isinstance(node,ast.Constant)and node.value==str(R):node.value=str(root)
 old_argv=sys.argv;old_run=subprocess.run;calls=[]
 def forbidden(*args,**kwargs):calls.append(args);raise AssertionError('Plan attempted a worker')
 sys.argv=[str(source),'--plan'];subprocess.run=forbidden;captured=io.StringIO();code=None
 try:
  with contextlib.redirect_stdout(captured):
   try:exec(compile(tree,str(source),'exec'),{'__name__':'__main__'})
   except SystemExit as error:code=error.code
 finally:sys.argv=old_argv;subprocess.run=old_run
 result=json.loads(captured.getvalue());assert not calls
 if count<14 or tamper:assert code==1 and result['status']=='not-ready'
 else:assert code==0 and result['status']=='ready'and set(result['selections'])==set(keys)and len(result['configs'])==14+int(peak)
 return dict(exit_code=code,status=result['status'],planned_presets=len(result.get('configs',{})),missing=result.get('missing_qualified_families',[]),gpu_workers=0)
checks=dict(partial=exercise(1),complete=exercise(14),distinct_peak=exercise(14,True),tampered=exercise(14,tamper=True))
receipt=dict(status='passed',scope='Actual quality batch --plan AST with only scratch-root literal redirected to controlled receipts; full14-family, distinct-peak, partial and modified-controls cases. GPU launches explicitly forbidden. No real model qualification is claimed.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checks=checks)
(R/'outputs/quality-batch-plan-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
