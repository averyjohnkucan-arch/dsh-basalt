"""Compare engines with exactly sized pretokenized prompts, fresh processes and token arrival timings."""
import argparse,json,os,queue,re,subprocess,threading,time,hashlib,signal,statistics,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();cfg=json.loads(Path(a.config).read_text())
root=Path(cfg['output']);root.mkdir(parents=True,exist_ok=True)
from benchmark_prompts import load_prompt,prompt_record
ids=load_prompt(cfg);depth=cfg['depth']
(root/'prompt.json').write_text(json.dumps(prompt_record(ids,cfg)))
if cfg.get('expert_profile_source'):
 source=Path(cfg['expert_profile_source']);target=root/'input-expert-profile.bin';shutil.copy2(source,target)
 cfg['input_profile_sha256']=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
 cfg['command']=list(cfg['command']);cfg['command'][cfg['command'].index('--expert-profile')+1]=str(target)
from benchmark_memory_guard import MemoryGuard
from benchmark_environment import power_snapshot
guard=MemoryGuard(cfg,root)
q=queue.Queue();stop=threading.Event();telemetry=[]
def monitor():
 while not stop.is_set():
  entry={'time':time.monotonic()};telemetry.append(entry)
  try:entry['host_memory']=guard.sample(proc)
  except Exception as e:entry['host_memory_error']=str(e)
  try:entry['power_policy']=power_snapshot()
  except Exception as e:entry['power_policy_error']=str(e)
  try:
   entry['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=timestamp,power.draw,temperature.gpu,clocks.current.graphics,memory.used,utilization.gpu,enforced.power.limit,power.default_limit','--format=csv,noheader,nounits'],text=True,timeout=5).strip()
   entry['ac']={p.parent.name:p.read_text().strip()for p in Path('/sys/class/power_supply').glob('*/online')}
  except Exception as e:entry['gpu_error']=str(e)
  stop.wait(1)
log=(root/'engine.log').open('w');env={**os.environ,**cfg.get('env',{})};start=time.monotonic()
proc=subprocess.Popen(guard.command(cfg['command']),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1,env=env,cwd=cfg.get('cwd'),start_new_session=True)
def read():
 for line in proc.stdout:q.put(line)
 q.put(None)
threading.Thread(target=read,daemon=True).start();mon=threading.Thread(target=monitor,daemon=True);mon.start()
result={'config':cfg,'started_unix':time.time(),'info':{},'status':'failed'}
def line():
 left=start+cfg.get('timeout',7200)-time.monotonic()
 if left<=0:raise TimeoutError('benchmark deadline')
 value=q.get(timeout=min(left,7200))
 if value is None:raise RuntimeError('engine exited: '+str(proc.poll()))
 return value.strip()
try:
 while True:
  s=line()
  if s.startswith('INFO '):
   for key,value in re.findall(r'(\S+?)=(\S+)',s):result['info'][key]=value
  if s.startswith('ERR'):raise RuntimeError(s)
  if s.startswith('READY'):break
 result['load_s']=time.monotonic()-start
 if cfg.get('pin_host') is not None:
  result['host_affinity_before']=sorted(os.sched_getaffinity(proc.pid));os.sched_setaffinity(proc.pid,{int(cfg['pin_host'])})
 request=time.monotonic();proc.stdin.write('GEN '+str(cfg.get('generate',8192))+' '+cfg.get('sampling','temperature=0 seed=42')+' '+','.join(map(str,ids))+'\n');proc.stdin.flush()
 arrivals=[];tokens=[];progress=0;last_prefill_report=0
 while True:
  s=line();now=time.monotonic()
  if s.startswith('T '):
   tokens.append(int(s.split()[1]));arrivals.append(now)
   if len(tokens)//1024>progress:progress=len(tokens)//1024;print(json.dumps({'output':str(root),'generated':len(tokens),'elapsed':round(now-request,1)}),flush=True)
  elif s.startswith('DONE'):
   result['done_raw']=s;f=s.split();produced=int(f[1]);prompt=int(f[2]);pp=float(f[3]);dec=float(f[4]);cached=int(f[8])if len(f)>8 else 0
   result.update(status='ok',prompt_tokens=prompt,reused_tokens=cached,prefill_ms=pp,prefill_tok_s=(prompt-cached)/(pp/1000)if pp else 0,decode_ms=dec,decode_tok_s=produced/(dec/1000)if dec else 0,generated=produced,finish=f[5],wall_s=now-request,ttft_s=arrivals[0]-request if arrivals else None)
   tail=cfg.get('timed_tail',4096)
   if len(arrivals)>tail:result['tail_decode_tok_s']=tail/(arrivals[-1]-arrivals[-tail-1])
   result['token_sha256']=hashlib.sha256(','.join(map(str,tokens)).encode()).hexdigest()
   forbidden={str(i):tokens.count(i) for i in cfg.get('forbidden_token_ids',[]) if i in tokens}
   result['forbidden_token_counts']=forbidden
   if forbidden:raise RuntimeError('benchmark output contains forbidden stop tokens: '+str(forbidden))
   if prompt!=depth or (cached and not cfg.get('allow_reused')) or len(tokens)!=produced or (cfg.get('require_complete',True) and produced!=cfg.get('generate',8192)):raise RuntimeError('incomplete or unexpected cached benchmark')
   if cfg.get('require_reuse_min',0)>cached:raise RuntimeError('required cached prefix was not restored')
   result['cold_prefill_qualified']=cached==0
   if cached:result['prefill_tok_s']=None;result['qualification']='Decode-only restored-prefix screening; not a cold prefill result.'
   break
  elif s.startswith('PP '):
   if cfg.get('require_reuse_min') and now-request>cfg.get('max_uncached_prefill_s',60) and not tokens:raise RuntimeError('cached screening attempted a cold prefill; stopped')
   if now-last_prefill_report>=15:
    last_prefill_report=now;print(json.dumps({'output':str(root),'native_prefill_progress':s,'elapsed':round(now-request,1)}),flush=True)
  elif s.startswith('ERR'):raise RuntimeError(s)
 proc.stdin.write('QUIT\n');proc.stdin.flush();proc.stdin.close();proc.wait(timeout=120)
except Exception as e:
 result['status']='failed';result['error']=guard.reason or str(e)
finally:
 if proc.poll()is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 stop.set();mon.join(timeout=6);log.close();result['total_s']=time.monotonic()-start
 draft=root/'draft.log'
 if draft.exists():
  windows=[list(map(float,line.split()[1:7])) for line in draft.read_text().splitlines() if line.startswith('W ') and len(line.split())>=7]
  if windows:
   elapsed=[sum(w[3:6]) for w in windows];total=sum(elapsed)
   result['draft_windows']={'count':len(windows),'mean_width':statistics.mean(w[0] for w in windows),'mean_accepted':statistics.mean(w[1] for w in windows),'mean_ms':statistics.mean(elapsed),'passes_per_s':len(windows)*1000/total if total else None,'draft_ms':sum(w[3] for w in windows),'verify_ms':sum(w[4] for w in windows),'post_ms':sum(w[5] for w in windows)}
 result['gpu_telemetry_fields']=['timestamp','power.draw','temperature.gpu','clocks.current.graphics','memory.used','utilization.gpu','enforced.power.limit','power.default_limit']
 (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');(root/'telemetry.json').write_text(json.dumps(telemetry))
 (root/'tokens.json').write_text(json.dumps(tokens if 'tokens'in locals()else []))
 print(json.dumps(result),flush=True)
if result['status']!='ok':raise SystemExit(1)
