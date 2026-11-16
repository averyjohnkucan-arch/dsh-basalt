"""Exercise actual benchmark recovery code with file-backed fake workers; never use a GPU."""
from pathlib import Path
import ast,copy,contextlib,hashlib,io,json,shutil,sys,tempfile,time,types
ROOT=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
TESTROOT=ROOT/'validation/benchmark-resume-validity';TESTROOT.mkdir(parents=True,exist_ok=True)
source=Path(__file__).with_name('range_common.py')
def fixture(source_path,label):
 root=Path(tempfile.mkdtemp(prefix=label+'-',dir=TESTROOT));work=root/'work';work.mkdir();(root/'bench').mkdir()
 state=dict(checks=0,workers=0,fail_pre=False,fail_post=False)
 def read(path):return json.loads(Path(path).read_text())
 def ensure():
  state['checks']+=1
  if state['fail_pre']and state['checks']==1:raise RuntimeError('simulated AC disconnected before launch')
  if state['fail_post']and state['checks']==2:raise RuntimeError('simulated power daemon failed during run')
 def worker(argv,**kwargs):
  state['workers']+=1;c=read(argv[argv.index('--config')+1]);actual=copy.deepcopy(c)
  actual.setdefault('host_memory_policy',{}).update(memory_high_gib=96,memory_max_gib=108)
  if '--expert-profile'in actual['command']:
   at=actual['command'].index('--expert-profile')+1;actual['expert_profile_source']=actual['command'][at];actual['command'][at]=str(Path(c['output'])/'input-expert-profile.bin')
  out=Path(c['output']);out.mkdir(parents=True,exist_ok=True)
  (out/'result.json').write_text(json.dumps(dict(status='ok',config=actual,generated=8192,prefill_tok_s=1000,tail_decode_tok_s=100,synthetic_worker=state['workers'])))
  return types.SimpleNamespace(returncode=0)
 ns=dict(R=root,W=work,O=root/'outputs',read=read,copy=copy,json=json,pathlib=__import__('pathlib'),subprocess=types.SimpleNamespace(run=worker,STDOUT=-2),sys=sys,time=time,shutil=shutil,current_environment=lambda:None,case_name=lambda name:'range-'+name,ensure_environment=ensure,digest=lambda path:'fixture-engine-sha',opt=lambda *args:None,WORKLOADS=dict(cases=[dict(family='fixture',workload='code',prompt_file='fixture-token-ids.json',depth=8192)]))
 tree=ast.parse(source_path.read_text());functions=[x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name in ['completed_input_matches','run']]
 exec(compile(ast.Module(body=functions,type_ignores=[]),str(source_path),'exec'),ns)
 def run(config):
  with contextlib.redirect_stdout(io.StringIO()):return ns['run'](config,'case','fixture','code')
 old=dict(command=['taskset','-c','0-21','fixture-engine','--spec','4']);new=dict(command=['taskset','-c','0-21','fixture-engine','--spec','8'])
 return root,state,run,old,new

def inspect(source_path,label):
 rows={}
 root,state,run,old,new=fixture(source_path,label+'-pre');first=run(old);state.update(checks=0,fail_pre=True)
 try:run(new)
 except RuntimeError:pass
 else:raise AssertionError('pre-launch fixture did not fail')
 saved=list((root/'bench/range-case/prior-attempts').glob('*/result.json'));assert saved and json.loads(saved[-1].read_text())==first
 result=root/'bench/range-case/result.json';stale_present=result.exists()and json.loads(result.read_text())['status']=='ok';before=state['workers'];state.update(checks=0,fail_pre=False);recovered=run(new)
 rows['pre_launch_failure']=dict(stale_success_left_active=stale_present,relaunched=state['workers']>before,recovered_input_matches=recovered['config']['command']==new['command'],prior_success_preserved=True)
 root,state,run,old,new=fixture(source_path,label+'-post');state['fail_post']=True
 try:run(new)
 except RuntimeError:pass
 else:raise AssertionError('post-run fixture did not fail')
 failed=json.loads((root/'bench/range-case/result.json').read_text());before=state['workers'];state.update(checks=0,fail_post=False);run(new)
 rows['post_run_failure']=dict(stored_status=failed['status'],disqualified=failed.get('benchmark_environment_qualified')is False,relaunched=state['workers']>before,measurement_preserved=failed['generated']==8192 and failed['tail_decode_tok_s']==100)
 root,state,run,old,new=fixture(source_path,label+'-legacy');run(old);input_path=root/'work/range-case.json';planned=json.loads(input_path.read_text());planned['command']=new['command'];input_path.write_text(json.dumps(planned));before=state['workers'];value=run(new)
 rows['interrupted_legacy_attempt']=dict(relaunched=state['workers']>before,recovered_input_matches=value['config']['command']==new['command'])
 root,state,run,old,new=fixture(source_path,label+'-cache');new['command']+=['--expert-profile',str(root/'master.prof')];first=run(new);before=state['workers'];second=run(new)
 rows['valid_owned_profile_cache']=dict(reused=state['workers']==before,same_result=first==second,owned_profile_differs_from_planned=second['config']['command']!=new['command'])
 return rows

current=inspect(source,'fixed');assert not current['pre_launch_failure']['stale_success_left_active'];assert current['pre_launch_failure']['relaunched']and current['pre_launch_failure']['recovered_input_matches'];assert current['post_run_failure']['stored_status']=='failed'and current['post_run_failure']['disqualified']and current['post_run_failure']['relaunched']and current['post_run_failure']['measurement_preserved'];assert current['interrupted_legacy_attempt']['relaunched']and current['interrupted_legacy_attempt']['recovered_input_matches'];assert all(current['valid_owned_profile_cache'].values())
legacy=None
if len(sys.argv)>1:
 baseline=Path(sys.argv[1]);legacy=inspect(baseline,'before');assert legacy['pre_launch_failure']['stale_success_left_active']and not legacy['pre_launch_failure']['relaunched'];assert legacy['post_run_failure']['stored_status']=='ok'and not legacy['post_run_failure']['relaunched'];assert not legacy['interrupted_legacy_attempt']['relaunched']
out=dict(status='passed',scope='Actual run() and input-matching functions extracted without importing the GPU harness; only the worker and power checks are simulated. Files, archives and resume paths are real NVMe scratch operations.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),current=current,legacy_bug_reproduced=legacy,legacy_source_sha256=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()if legacy else None)
(ROOT/'outputs/benchmark-resume-validity-test.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
