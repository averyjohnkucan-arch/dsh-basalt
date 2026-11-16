"""Targeted joint CPU/VRAM checks for the primary long-context MoE presets."""
from range_tuner import *
from range_identity import config_id
def soft_pressure_variant(result,telemetry,base):
 """Trial only a higher soft threshold after demonstrated104GiB reclaim pressure."""
 c=result.get('config',{});policy=c.get('host_memory_policy',{})
 if result.get('status')=='ok'or'RAM safety stop'not in str(result.get('error',''))or c.get('generate')!=8192:return None
 if c.get('benchmark_memory_policy_id')!='hybrid-high104-max108':return None
 if any(policy.get(k)!=v for k,v in [('memory_high_gib',104),('memory_max_gib',108)]):return None
 legacy_free=policy.get('minimum_host_available_gib')==12
 budget_mode=policy.get('minimum_host_available_gib')==0 and policy.get('minimum_nonworker_budget_gib')==12
 if not(legacy_free or budget_mode):return None
 if any(not c.get(k)or c.get(k)!=base.get(k)for k in ['engine_binary_sha256','artifact_header_sha256','artifact_bytes','benchmark_environment_id']):return None
 memory=[row['host_memory']for row in telemetry if 'host_memory'in row]
 if not memory:return None
 if legacy_free and min(row.get('host_available_bytes',0)for row in memory)<12*2**30:return None
 if budget_mode and min(row.get('host_physical_bytes',0)for row in memory)<120*2**30:return None
 if max(row.get('pressure_some_avg10',0)for row in memory)<=policy.get('pressure_avg10_limit',40):return None
 try:events=[dict(line.split()for line in row['scope_events'].splitlines())for row in memory if 'scope_events'in row]
 except(ValueError,TypeError):return None
 if not events or not any(int(row.get('high',0))>0 for row in events):return None
 if any(int(row.get(k,0))for row in events for k in ['max','oom','oom_kill','oom_group_kill']):return None
 trial=copy.deepcopy(c);trial['host_memory_policy']['memory_high_gib']=106;trial['benchmark_memory_policy_id']='hybrid-high106-max108'
 return trial

def policy_prefill_variants(base):
 """Recheck prefill/cache tradeoffs on an actually selected106GiB policy."""
 if base.get('benchmark_memory_policy_id')!='hybrid-high106-max108':return []
 variants=[('prefill32k',{'--prefill':'auto:32768'}),('prefill4k',{'--prefill':'4096'})]
 variants += [(f'prefill-share-{share}',{'--prefill-cpu-share':share})for share in [0,.3,1]]
 variants += [(f'adapt-swaps-{count}',{'--adapt-swaps':count})for count in [0,16,32,96]]
 return [(label,changed(base,changes))for label,changes in variants]

key,family=sys.argv[1:3]
if family!='qwen'or key.startswith('gyro'):raise SystemExit(0)
state=read(O/'range-selections.json');selection=state[key+'_long'];base=read(R/'bench'/selection['selected']/'result.json')['config'];ident=config_id(base)
row=next(x for x in selection['candidates']if x['identity']==ident);genre=row['worst_genre']
variants=[('reserve256',{'--vram-reserve-mib':256}),('reserve256-workers14',{'--vram-reserve-mib':256,'--pool-workers':14}),('reserve256-resident96k',{'--vram-reserve-mib':256,'--kv-resident':98304})]
if'fp16'in key:variants=[]
if key.endswith('_basalt'):
 # This control affects prefill expert placement; verify sustained decode too.
 if'fp16'not in key:variants += [(f'prefill-cpu-share-{share}',{'--prefill-cpu-share':share})for share in [0,.3,1]]
 variants.append(('saved-ranking',{'--expert-profile':W/'saved-expert-profiles/flash-basalt.prof'}))
if key.startswith('hybrid')and key.endswith('_basalt'):
 variants += [(f'adapt-swaps-{count}',{'--adapt-swaps':count})for count in [0,16,32]]
plan=repeatability_plan(key);data=read(plan);known={config_id(read(R/'bench'/x['case']/'result.json')['config'])for x in data['selection']['candidates']}
configured=[]
for label,changes in variants:
 c=changed(base,changes)
 if label=='saved-ranking':c['expert_profile_source']=str(W/'saved-expert-profiles/flash-basalt.prof')
 configured.append((label,c))
if key.startswith('hybrid')and key.endswith('_basalt'):
 failed_case=case_name(key.removesuffix('_basalt')+'-basalt-confirm-workers14');folder=R/'bench'/failed_case
 failed=read_case_mapping(folder/'result.json');telemetry_path=folder/'telemetry.json'
 if failed and telemetry_path.exists():
  try:trial=soft_pressure_variant(failed,read(telemetry_path),base)
  except (OSError,ValueError,TypeError,KeyError)as error:
   print('SOFT-LIMIT TRIAL INPUT UNAVAILABLE',failed_case,str(error),flush=True);trial=None
  if trial:
   configured.append(('high106-recover-workers14',trial))
   joint=changed(base,{'--pool-workers':14});joint['host_memory_policy']=copy.deepcopy(trial['host_memory_policy']);joint['benchmark_memory_policy_id']=trial['benchmark_memory_policy_id'];configured.append(('high106-selected-controls-workers14',joint))
added=[]
for label,c in configured:
 candidate=config_id(c)
 if candidate in known:continue
 r=run(c,key+'-joint-'+candidate+'-'+genre,family,genre)
 if r['status']!='ok':continue
 item=dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'],source='joint reserve/CPU/KV or explicitly guarded soft-limit refinement',refinement=label);data['selection']['candidates'].append(item);known.add(candidate);added.append(item);plan.write_text(json.dumps(data,indent=2))
if added:subprocess.run([sys.executable,str(W/'range_repeatability.py'),key,family],check=True)
# A higher soft policy can make formerly failing prefill batches viable. Refit
# against its measured winner/peak, then use the same all-genre95% selection gate.
current=read(O/'range-selections.json')[key+'_long'];data=read(plan)
known={config_id(read(R/'bench'/x['case']/'result.json')['config'])for x in data['selection']['candidates']}
selected_id=config_id(read(R/'bench'/current['selected']/'result.json')['config'])
targets={selected_id,current['peak_decode_identity']};post_added=[]
for item in list(data['selection']['candidates']):
 parent=read(R/'bench'/item['case']/'result.json')['config'];parent_id=config_id(parent)
 if parent_id not in targets:continue
 targets.remove(parent_id)
 limiting=next(row['worst_genre']for row in current['candidates']if row['identity']==parent_id)
 for label,c in policy_prefill_variants(parent):
  candidate=config_id(c)
  if candidate in known:continue
  r=run(c,key+'-policy-prefill-'+candidate+'-'+limiting,family,limiting)
  if r['status']!='ok':continue
  extra=dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'],source='prefill/cache refit after measured106GiB policy selection',refinement=label)
  data['selection']['candidates'].append(extra);known.add(candidate);post_added.append(extra);plan.write_text(json.dumps(data,indent=2))
if post_added:subprocess.run([sys.executable,str(W/'range_repeatability.py'),key,family],check=True)
save(key+'_joint_refinements',state.get(key+'_joint_refinements',[])+added+post_added);print('JOINT REFINEMENT COMPLETE',key,flush=True)
