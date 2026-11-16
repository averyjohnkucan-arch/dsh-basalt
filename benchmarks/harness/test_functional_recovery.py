"""File-backed failure injection for the actual functional-worker recovery helper."""
from pathlib import Path
import copy,hashlib,json,tempfile,types
import functional_benchmark_recovery as recovery
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');parent=R/'validation/functional-recovery';parent.mkdir(parents=True,exist_ok=True)
def exercise(kind):
 root=Path(tempfile.mkdtemp(prefix=kind+'-',dir=parent));out=root/'case';out.mkdir();binary=root/'engine';binary.write_bytes(b'fixture-engine')
 config_path=root/'input.json';base=dict(command=['taskset','-c','0-21',str(binary),'--spec','8'],engine_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),prompt_file=str(root/'prompt.json'),output=str(out),depth=3,generate=1024,timed_tail=32,sampling='temperature=0 seed=42',functional_prompt_sha256='prompt-sha',functional_checks_sha256='checks-sha',functional_task_name='merge_intervals')
 stale={**base,'command':base['command'][:-1]+['4'],'functional_attempt_id':'old-attempt'}
 (out/'result.json').write_text(json.dumps(dict(status='ok',config=stale)));(out/'tokens.json').write_text('[99]');config_path.write_text(json.dumps(stale))
 state=dict(power_checks=0,workers=0)
 def ensure():
  state['power_checks']+=1
  if kind=='pre-launch'and state['power_checks']==1:raise RuntimeError('injected pre-launch power failure')
  if kind=='post-run'and state['power_checks']==2:raise RuntimeError('injected post-run power failure')
 def worker(*args,**kwargs):
  state['workers']+=1;c=json.loads(config_path.read_text())
  if kind=='missing-result':return types.SimpleNamespace(returncode=2)
  if kind=='wrong-attempt':c['functional_attempt_id']='old-attempt'
  (out/'result.json').write_text(json.dumps(dict(status='ok',config=c,prompt_tokens=3,token_sha256='generated-token-sha')))
  (out/'prompt.json').write_text(json.dumps(dict(sha256='prompt-sha')));(out/'tokens.json').write_text('[10,20]')
  return types.SimpleNamespace(returncode=0)
 recovery.ensure_environment=ensure;recovery.subprocess=types.SimpleNamespace(run=worker,STDOUT=-2)
 if kind=='binary-changed':binary.write_bytes(b'new-unqualified-engine')
 result=recovery.run_functional_worker(base,config_path,out,root/'progress.log')
 archives=list((out/'prior-attempts').iterdir());assert len(archives)==1 and json.loads((archives[0]/'result.json').read_text())['config']['functional_attempt_id']=='old-attempt'
 if kind=='success':
  assert result['status']=='ok'and state['workers']==1
  assert recovery.run_functional_worker(base,config_path,out,root/'progress.log',grade_only=True)['status']=='ok'
  cached=recovery.run_functional_worker(base,config_path,out,root/'progress.log');assert cached['functional_generation_reused']and state['workers']==1
  changed=copy.deepcopy(base);changed['functional_prompt_sha256']='new-prompt'
  try:recovery.run_functional_worker(changed,config_path,out,root/'progress.log',grade_only=True)
  except RuntimeError:pass
  else:raise AssertionError('Changed prompt was graded')
 else:
  assert result['status']=='failed'and result['config']['functional_attempt_id']!='old-attempt'
  assert json.loads((out/'result.json').read_text())['status']=='failed'
  if kind in ['pre-launch','binary-changed']:assert not state['workers']and not(out/'tokens.json').exists()
  if kind=='post-run':assert(out/'failed-worker-result.json').exists()
 return dict(status=result['status'],old_success_archived=True,workers=state['workers'],power_checks=state['power_checks'])
checks={kind:exercise(kind)for kind in ['pre-launch','missing-result','wrong-attempt','post-run','binary-changed','success']}
receipt=dict(status='passed',scope='Actual functional-worker helper and input matching; file-backed old-result archival, exact attempt/prompt checks and real binary hashing. Only power checks and GPU workers are simulated.',source_sha256=hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest(),checks=checks)
(R/'outputs/functional-recovery-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
