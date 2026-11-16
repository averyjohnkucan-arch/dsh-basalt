"""Run after Qwen models and their plugin checks; rotates only owned derived packs."""
from range_tuner import *
import shutil,os
from benchmark_memory_guard import MemoryGuard
artifact=R/'packs/deepseek-gsq-rco-iq2xxs.basalt'
if not artifact.exists():
 # Rotation is irreversible for our derived copies: require completed native and
 # actual-plugin evidence before freeing packs needed by the earlier matrix.
 required_keys=['flash_basalt','hybrid_basalt','27b_basalt','27b_ninfer','flash_strata','hybrid_strata','gyro_strata','flash_fp16_basalt','hybrid_fp16_basalt','flash_fp16_strata','hybrid_fp16_strata','huihui_nvfp4_ninfer','huihui_int8_ninfer','huihui_fp8_ninfer']
 for key in required_keys:
  native=read(O/'performance-qualified'/(key+'.json'));plugin=read(O/'performance-qualified'/(key+'-plugin-gpu.json'))
  assert native['performance_qualified']and plugin['status']=='ok'
  environment=current_environment()
  if environment:assert native['benchmark_environment_id']==plugin['benchmark_environment_id']==environment['id']
 # Native speed/plugin receipts alone do not prove code-generation coverage.
 quality=read(O/'selected-code-quality-completion.json')
 assert quality['status']=='complete'and quality['all_generations_completed']
 if environment:assert quality['benchmark_environment_id']==environment['id']
 for key,identities in quality['selections'].items():
  native=read(O/'performance-qualified'/(key+'.json'))
  assert all(identities[kind]==native[kind+'_identity']for kind in ['long','short'])
 assert set(quality['selections'])==set(required_keys),'Every required pre-DeepSeek family must have matching generated-code evidence'
 receipt=read(O/'deepseek-pack-regeneration.json');command=receipt['command'];command[1]=str(W/'basalt-latest/tools/convert/convert.py')
 # Retain a complete reconstruction recipe before freeing any owned conversion.
 hybrid=read(O/'hybrid-pack-regeneration.json');hybrid['command'][1]=str(W/'basalt-latest/tools/convert/convert.py')
 pure=copy.deepcopy(hybrid)
 for flag,value in [('--strata-pack','/mnt/media/AI/Models/Scratch models/Maximilian228/Qwen3.8-Flash-Next-NVFP4-GPTQ-Strata/pack'),('--out',str(R/'packs/qwen-nvfp4-gptq.basalt')),('--name','Qwen3.8 Flash Next NVFP4 original projections')]:pure['command'][pure['command'].index(flag)+1]=value
 dense=dict(command=[sys.executable,str(W/'basalt-latest/tools/convert/convert.py'),'--ninfer','/mnt/media/AI/Models/Qwen3.8-27B/DSH-import/ninfer/qwen3.8-27b-nvfp4full/qwen3_8_27b_nvfp4full.ninfer','--out',str(R/'packs/qwen27b-nvfp4full-experimental.basalt')])
 for label,recipe in [('flash',pure),('hybrid',hybrid),('27b',dense)]:
  (O/(label+'-pack-regeneration-latest.json')).write_text(json.dumps(recipe,indent=2))
 # Free enough for a 239-GiB DeepSeek pack plus checkpoint and runtime headroom.
 removed=[]
 for pack in ['qwen-nvfp4-q8-hybrid.basalt','qwen27b-nvfp4full-experimental.basalt','qwen-nvfp4-gptq.basalt']:
  if shutil.disk_usage(R).free>290*1024**3:break
  p=R/'packs'/pack
  if p.exists():
   removed.append(dict(path=str(p),bytes=p.stat().st_size));p.unlink()
 for p in (R/'checkpoints').glob('range-*'):
  assert p.parent==R/'checkpoints';shutil.rmtree(p)
 (O/'range-deepseek-owned-pack-rotation.json').write_text(json.dumps(dict(removed=removed,source_weights_untouched=True,reason='2TB NVMe capacity; reconstruction recipes retained'),indent=2))
 assert shutil.disk_usage(R).free>260*1024**3, 'Need conversion/cache headroom without deleting source weights'
 print(time.strftime('%H:%M:%S'),'DEEPSEEK REGENERATE',flush=True)
 guard=MemoryGuard({},W/'range-deepseek-regeneration');samples=[]
 with(W/'range-deepseek-regeneration.log').open('w')as log:
  proc=subprocess.Popen(guard.command(command),cwd=W/'basalt-latest',env={**os.environ,'TMPDIR':str(R/'tmp')},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while proc.poll()is None:
    samples.append(dict(time=time.time(),host_memory=guard.sample(proc)))
    if guard.reason:break
    time.sleep(1)
   status=proc.wait(timeout=15)
  finally:
   guard.stop(proc);(O/'range-deepseek-conversion-memory.json').write_text(json.dumps(dict(policy=guard.policy,reason=guard.reason,samples=samples),indent=2))
  assert status==0 and not guard.reason,'DeepSeek conversion failed; inspect preserved log and memory telemetry'
# Verify immutable expert placement against the earlier exact 64-token probe.
frozen=latest(read(W/'deepseek-fetch-frozen-after.json'),'basalt');case='range-deepseek-frozen-identity-latest'
frozen.update(output=str(R/'bench'/case),engine_binary_sha256=digest(frozen['command'][3]),gpu_power_limit_w=95)
opt(frozen,'--draft-log',R/'bench'/case/'draft.log');path=W/(case+'.json');path.write_text(json.dumps(frozen,indent=2))
with(W/(case+'.progress')).open('w')as log:subprocess.run([sys.executable,str(W/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
actual=read(R/'bench'/case/'result.json');previous=read(R/'bench/deepseek-fetch-frozen-after/result.json')
assert actual['status']=='ok'and actual['generated']==64 and actual['token_sha256']==previous['token_sha256'],'Frozen-placement token identity failed; inspect before throughput tuning'
(O/'deepseek-latest-frozen-token-identity.json').write_text(json.dumps(dict(status='ok',current=case,reference='deepseek-fetch-frozen-after',tokens=64,token_sha256=actual['token_sha256'],scope='Frozen expert placement compatibility only; no quality or speed claim'),indent=2))
base=latest(read(R/'bench/final-deepseek-basalt-fast-90/result.json')['config'],'basalt')
opt(base,'--expert-profile',W/'saved-expert-profiles/deepseek-basalt.prof')
base['expert_profile_source']=str(W/'saved-expert-profiles/deepseek-basalt.prof')
candidates=[(tag,changed(base,changes))for tag,changes in [('workers14',{'--pool-workers':14}),('workers12',{'--pool-workers':12}),('workers8',{'--pool-workers':8}),('dspark4',{'--spec':4}),('dspark6',{'--spec':6}),('dspark6-exp64',{'--spec':6,'--draft-experts':64})]]
old=read(W/'final-deepseek-old-90.json')
tune('deepseek_basalt',base,'deepseek',candidates,[],[(f'spec{s}',{'--spec':s})for s in [0,4,6]],old=old)
strata=read(W/'final-deepseek-strata-90.json')
strata['expert_profile_source']=str(W/'saved-expert-profiles/deepseek-strata.bin')
candidates=[(tag,changed(strata,changes))for tag,changes in [('threads21',{'--cpu-threads':21}),('threads8',{'--cpu-threads':8}),('chunk8192',{'--prefill-chunk':8192}),('dspark-off',{'--dspark':'off'}),('dspark-conf85',{'--dspark-conf':.85})]]
tune('deepseek_strata',strata,'deepseek',candidates,[('chunk8192',{'--prefill-chunk':8192}),('chunk2048',{'--prefill-chunk':2048})],[(f'conf{c}',{'--dspark':'auto','--dspark-conf':c})for c in [.55,.65,.85]],cache=False)
