"""Owned native NInfer process, exact token-ID raw completion, uncached SSE timings."""
import argparse,json,pathlib,subprocess,time,os,signal,urllib.request,hashlib,re,threading
p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
base='http://127.0.0.1:'+str(cfg.get('port',18301));start=time.monotonic();result={'config':cfg,'status':'failed','started_unix':time.time()};events=[];telemetry=[];stop=threading.Event()
from benchmark_memory_guard import MemoryGuard
from benchmark_environment import power_snapshot
guard=MemoryGuard(cfg,out)
def monitor():
 while not stop.is_set():
  entry={'time':time.monotonic()};telemetry.append(entry)
  try:entry['host_memory']=guard.sample(proc)
  except Exception as e:entry['host_memory_error']=str(e)
  try:entry['power_policy']=power_snapshot()
  except Exception as e:entry['power_policy_error']=str(e)
  try:entry['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=timestamp,power.draw,temperature.gpu,clocks.current.graphics,memory.used,utilization.gpu,enforced.power.limit,power.default_limit','--format=csv,noheader,nounits'],text=True,timeout=5).strip()
  except Exception as e:entry['gpu_error']=str(e)
  entry['ac']={p.parent.name:p.read_text().strip()for p in pathlib.Path('/sys/class/power_supply').glob('*/online')}
  stop.wait(1)
def completion_payload(config,ids):
 # Preserve the established request exactly; record the effective controls rather
 # than assuming native GEN sampling options apply to the HTTP interface.
 return {'prompt':ids,'n_predict':config.get('generate',8192),'temperature':0,'seed':42,'ignore_eos':config.get('ignore_eos',True),'cache_prompt':False,'stream':True,'return_tokens':True,'return_progress':True}
def post(path,data,timeout=18000):
 return urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=timeout)
log=(out/'engine.log').open('w');env={**os.environ,**cfg.get('env',{})};env.pop('LD_LIBRARY_PATH',None)
proc=subprocess.Popen(guard.command(cfg['command']),stdout=log,stderr=subprocess.STDOUT,env=env,cwd=cfg.get('cwd'),start_new_session=True);thread=threading.Thread(target=monitor,daemon=True);thread.start()
try:
 while True:
  if proc.poll() is not None:raise RuntimeError('engine exited '+str(proc.returncode))
  try:
   with urllib.request.urlopen(base+'/health',timeout=2) as resp:
    if resp.status==200:break
  except Exception:pass
  if time.monotonic()-start>3600:raise TimeoutError('engine readiness')
  time.sleep(1)
 result['load_s']=time.monotonic()-start
 # Validate the exact vocabulary and framing before using a common fixture.
 from benchmark_prompts import load_prompt,prompt_record
 ids=load_prompt(cfg);depth=cfg['depth']
 (out/'prompt.json').write_text(json.dumps(prompt_record(ids,cfg)))
 request_body=completion_payload(cfg,ids);(out/'request.json').write_text(json.dumps(request_body));result['request_options']={k:v for k,v in request_body.items()if k!='prompt'}
 result['output_end_policy']='model stop tokens ignored; logits not biased'if request_body['ignore_eos']else'model stop tokens honored'
 request=time.monotonic();last={};content=[];previous=0;progress=0
 with post('/completion',request_body) as resp:
  for raw in resp:
   if not raw.startswith(b'data:'):continue
   value=json.loads(raw[5:]);now=time.monotonic()
   if 'error'in value:raise RuntimeError(str(value['error']))
   if value.get('content'):content.append(value['content'])
   count=value.get('tokens_predicted',0)
   if count>previous:
    events.append([count,now-request]);previous=count
    if count//1024>progress:progress=count//1024;print(json.dumps({'output':str(out),'generated':count,'elapsed':round(now-request,1)}),flush=True)
   if value.get('stop') or ('timings'in value and value.get('tokens')):last=value
 if not last:raise RuntimeError('missing terminal completion object')
 (out/'completion.json').write_text(json.dumps(last));(out/'content.txt').write_text(''.join(content));timings=last['timings'];generated=timings['predicted_n'];cached=last.get('tokens_cached',timings.get('cache_n',0))
 result.update(status='ok',timings=timings,prompt_tokens=depth,reused_tokens=cached,generated=generated,prefill_ms=timings['prompt_ms'],prefill_tok_s=timings['prompt_per_second'],decode_ms=timings['predicted_ms'],decode_tok_s=timings['predicted_per_second'],finish=last.get('stop_type'),wall_s=time.monotonic()-request,ttft_s=events[0][1] if events else None)
 if timings['prompt_n']!=depth or cached or (cfg.get('require_complete',True) and generated!=cfg.get('generate',8192)):raise RuntimeError('incomplete or cached benchmark')
 target=generated-cfg.get('timed_tail',4096);boundary=next((e for e in events if e[0]>=target),None)
 if boundary and events[-1][0]>boundary[0]:
  count=events[-1][0]-boundary[0];result.update(tail_decode_tok_s=count/(events[-1][1]-boundary[1]),tail_measured_tokens=count)
 tokens=last.get('tokens',[]);result['token_sha256']=hashlib.sha256(','.join(map(str,tokens)).encode()).hexdigest()
 forbidden={str(i):tokens.count(i)for i in cfg.get('forbidden_token_ids',[248044,248046]) if i in tokens};result['forbidden_token_counts']=forbidden
 if forbidden:raise RuntimeError('benchmark output contains stop/control tokens: '+str(forbidden))
except Exception as e:
 result['status']='failed';result['error']=guard.reason or str(e)
finally:
 if proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 stop.set();thread.join(timeout=6);log.close();result['total_s']=time.monotonic()-start
 result['gpu_telemetry_fields']=['timestamp','power.draw','temperature.gpu','clocks.current.graphics','memory.used','utilization.gpu','enforced.power.limit','power.default_limit']
 (out/'result.json').write_text(json.dumps(result,indent=2));(out/'telemetry.json').write_text(json.dumps(telemetry));(out/'arrival_events.json').write_text(json.dumps(events));print(json.dumps(result),flush=True)
if result['status']!='ok':raise SystemExit(1)
