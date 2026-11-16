"""Fresh, exact native-chat prompts and separately qualified decode screens."""
from latest80_common import R,W,O,read,opt,latest,digest
import copy,json,pathlib,subprocess,sys,time,shutil
from benchmark_environment import current_environment,case_name,repeatability_plan,ensure_environment
WORKLOADS=read(O/'range-workloads.json')

def completed_input_matches(value,planned):
 actual=value.get('config',{})
 for field in ['engine_binary_sha256','artifact_header_sha256','artifact_bytes','benchmark_environment_id','protocol','prompt_file','depth','generate','timed_tail','workload','sampling']:
  if field in planned and actual.get(field)!=planned[field]:return False
 for field,value in planned.get('host_memory_policy',{}).items():
  if actual.get('host_memory_policy',{}).get(field)!=value:return False
 def command(config):
  argv=list(config.get('command',[]))
  if '--expert-profile'in argv and config.get('expert_profile_source'):
   argv[argv.index('--expert-profile')+1]=config['expert_profile_source']
  return argv
 return command(actual)==command(planned)

def run(config,name,family,workload,n=8192,cache=None,reuse=False,role='qualified'):
 c=copy.deepcopy(config);name=case_name(name);out=R/'bench'/name
 environment=current_environment()
 if environment:c['benchmark_environment_id']=environment['id']
 fixture=next(x for x in WORKLOADS['cases']if x['family']==family and x['workload']==workload)
 c.update(output=str(out),prompt_file=fixture['prompt_file'],depth=fixture['depth'],generate=n,timed_tail=n//2,allow_reused=reuse,require_reuse_min=fixture['depth']-32 if reuse else 0,
          workload=workload,measurement_role=role,engine_binary_sha256=digest(c['command'][3]),gpu_power_limit_w=95,framing='native-tokenizer-chat-template; thinking off')
 for flag in ['--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache']:opt(c,flag,None)
 if '--draft-log'in c['command']:opt(c,'--draft-log',out/'draft.log')
 if cache:
  for flag,value in [('--conversation-cache-dir',R/'checkpoints'/('range-'+cache)),('--conversation-cache-disk-mib',16384),('--conversation-cache-mib',0),('--prompt-cache',4)]:opt(c,flag,value)
 if '--model'in c['command']:
  artifact=pathlib.Path(c['command'][c['command'].index('--model')+1])
  with artifact.open('rb')as f:c['artifact_header_sha256']=__import__('hashlib').sha256(f.read(65536)).hexdigest()
  c['artifact_bytes']=artifact.stat().st_size
 path=W/(name+'.json');result=out/'result.json'
 same=path.exists()and read(path)==c and(not result.exists()or completed_input_matches(read(result),c))
 if out.exists()and(not same or not result.exists()or read(result).get('status')!='ok'):
  files=[f for f in out.iterdir()if f.is_file()]
  if files:
   archive=out/'prior-attempts'/str(time.time_ns());archive.mkdir(parents=True)
   for f in files:shutil.copy2(f,archive/f.name)
   if path.exists():shutil.copy2(path,archive/'input-config.json')
  # The archived result belongs to the previous attempt. A failure before the
  # new worker starts must not make that old success reusable under the new input.
  result.unlink(missing_ok=True)
 path.write_text(json.dumps(c,indent=2))
 if not same or not result.exists()or read(result).get('status')!='ok':
  ensure_environment()
  if cache and not reuse:
   folder=R/'checkpoints'/('range-'+cache)
   assert folder.parent==R/'checkpoints'and folder.name.startswith('range-')
   if folder.exists():shutil.rmtree(folder)
  print(time.strftime('%H:%M:%S'),'START',name,flush=True)
  with(W/(name+'.progress')).open('w')as log:subprocess.run([sys.executable,str(W/('http_bench.py'if c.get('protocol')=='http'else'native_bench.py')),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
  try:ensure_environment()
  except Exception as error:
   # A worker may finish successfully after AC/power policy changes. Preserve
   # its measurements, but disqualify them before any resume or selection scan.
   if result.exists():
    value=read(result);value.update(status='failed',error='Post-run benchmark environment check failed: '+str(error),benchmark_environment_qualified=False)
    result.write_text(json.dumps(value,indent=2)+'\n')
   raise
 value=read(result);print(time.strftime('%H:%M:%S'),'END',name,value.get('status'),value.get('prefill_tok_s'),value.get('tail_decode_tok_s'),value.get('error'),flush=True)
 return value

def save(key,value):
 path=O/'range-selections.json';data=read(path)if path.exists()else{};data[key]=value;path.write_text(json.dumps(data,indent=2))
def name(result):return pathlib.Path(result['config']['output']).name

def select(results):
 qualified=[r for r in results if r.get('status')=='ok'and r.get('cold_prefill_qualified',True)and r.get('prefill_tok_s')and r['config']['generate']==8192]
 if not qualified:raise RuntimeError('No qualified full-output cold result')
 peak=max(r['tail_decode_tok_s']for r in qualified);eligible=[r for r in qualified if r['tail_decode_tok_s']>=.95*peak]
 chosen=max(eligible,key=lambda r:r['prefill_tok_s'])
 return dict(objective='Maximize cold prefill subject to sustained late decode >=95% of the fastest qualified 8192-output result on the same workload',peak_decode_tok_s=peak,decode_floor_tok_s=.95*peak,selected=name(chosen),candidates=[dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'])for r in qualified]),chosen

def summarize(results):
 valid=[r for r in results if r.get('status')=='ok'];assert valid
 worst=min(valid,key=lambda r:r['tail_decode_tok_s']);best=max(valid,key=lambda r:r['tail_decode_tok_s'])
 return dict(cases=[dict(case=name(r),workload=r['config']['workload'],prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'])for r in valid],
             worst_case=name(worst),best_case=name(best),prefill_range=[min(r['prefill_tok_s']for r in valid),max(r['prefill_tok_s']for r in valid)],decode_range=[worst['tail_decode_tok_s'],best['tail_decode_tok_s']])
