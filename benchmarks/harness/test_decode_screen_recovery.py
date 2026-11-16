"""Exercise actual screen fallback: preserve controls, retry diagnostic cache failure only."""
from pathlib import Path
import ast,contextlib,hashlib,io,json,time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/range_common.py';tree=ast.parse(source.read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='decode_screen')
def check(error=None,cache='prefix',n=2048):
 calls=[];config={'command':['fixture-engine','--resident-budget-gib','92']}
 def worker(c,logical,family,genre,**kwargs):
  calls.append(dict(config=c.copy(),logical=logical,kwargs=kwargs))
  return dict(status='failed'if len(calls)==1 and error else'ok',error=error if len(calls)==1 else None)
 ns=dict(run=worker,time=time);exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),ns)
 raised=False
 with contextlib.redirect_stdout(io.StringIO()):
  try:result=ns['decode_screen'](config,'candidate','qwen','chat',n=n,cache=cache)
  except AssertionError:raised=True;result=None
 if n==8192:assert raised and not calls
 elif error and cache and any(x in error for x in ['RAM safety stop','cached screening attempted a cold prefill','required cached prefix was not restored']):
  assert len(calls)==2 and calls[0]['kwargs']['reuse']and not calls[1]['kwargs'].get('reuse',False)and calls[1]['kwargs'].get('cache')is None and result['status']=='ok'
  assert calls[0]['config']==calls[1]['config']==config and calls[1]['logical']=='candidate-cold-prefix-retry'
 else:assert len(calls)==1
 return dict(calls=calls,refused_final_length=raised,status=result['status']if result else None)
checks=dict(memory=check('RAM safety stop: injected'),missing_checkpoint=check('cached screening attempted a cold prefill; stopped'),failed_restore=check('required cached prefix was not restored'),unsupported=check('ERR unsupported flag'),already_cold=check('RAM safety stop: injected',cache=None),successful_restore=check(),final_length_rejected=check(n=8192))
receipt=dict(status='passed',scope='Actual diagnostic-screen function with simulated worker responses. Restored-prefix memory/protocol failures retry identical controls cold; unsupported errors and already-cold failures do not retry; final8192-output calls are refused. No GPU.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checks=checks)
(R/'outputs/decode-screen-recovery-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Decode-screen recovery checks passed')
