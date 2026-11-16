"""A soft-limit trial cannot relax hard limits or bypass a demonstrated pressure failure."""
from pathlib import Path
import ast,copy,hashlib,json
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/range_joint_refine.py';node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='soft_pressure_variant');ns=dict(copy=copy);exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns);trial=ns['soft_pressure_variant']
c=dict(command=['taskset','-c','0-21','fixture-engine','--pool-workers','14'],generate=8192,engine_binary_sha256='engine',artifact_header_sha256='header',artifact_bytes=100,benchmark_environment_id='performance',benchmark_memory_policy_id='hybrid-high104-max108',host_memory_policy=dict(memory_high_gib=104,memory_max_gib=108,minimum_host_available_gib=12,swap_max_gib=1,pressure_avg10_limit=40,pressure_grace_s=6))
result=dict(status='failed',error='RAM safety stop: available=15.2GiB, memory-pressure avg10=55.9%',config=c)
telemetry=[dict(host_memory=dict(host_available_bytes=15*2**30,pressure_some_avg10=55.9,scope_events='high 4612\nmax 0\noom 0\noom_kill 0\noom_group_kill 0'))]
new=trial(result,telemetry,c);assert new and c['host_memory_policy']['memory_high_gib']==104 and new['host_memory_policy']['memory_high_gib']==106 and new['command']==c['command']
for key in ['memory_max_gib','minimum_host_available_gib','swap_max_gib','pressure_avg10_limit','pressure_grace_s']:assert new['host_memory_policy'][key]==c['host_memory_policy'][key]
checks={}
for kind in ['host-reserve','no-pressure','no-soft-events','hard-limit','wrong-engine','wrong-policy','successful-run','short-screen']:
 r=copy.deepcopy(result);t=copy.deepcopy(telemetry)
 if kind=='host-reserve':t[0]['host_memory']['host_available_bytes']=11*2**30
 if kind=='no-pressure':t[0]['host_memory']['pressure_some_avg10']=0
 if kind=='no-soft-events':t[0]['host_memory']['scope_events']='high 0\nmax 0\noom 0'
 if kind=='hard-limit':t[0]['host_memory']['scope_events']='high 10\nmax 1\noom 0'
 if kind=='wrong-engine':r['config']['engine_binary_sha256']='other'
 if kind=='wrong-policy':r['config']['host_memory_policy']['memory_max_gib']=110
 if kind=='successful-run':r['status']='ok'
 if kind=='short-screen':r['config']['generate']=2048
 assert trial(r,t,c)is None;checks[kind]='refused'
record=dict(status='passed',scope='Actual pure refinement gate; only demonstrated full-run soft-limit pressure with host reserve intact and no hard/OOM events permits104→106GiB. Native arguments,108GiB hard max,12GiB reserve, swap cap and pressure watchdog are unchanged. GPU experiment remains queued; no speed claim.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),positive_trial_memory_policy=new['host_memory_policy'],negative_cases=checks)
(R/'outputs/hybrid-soft-pressure-refinement-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Guarded soft-pressure refinement checks passed')

# Exercise the actual follow-up plan without importing/executing its GPU driver.
from range_tuner import changed
from range_identity import config_id
module=ast.parse(source.read_text());helper=next(n for n in module.body if isinstance(n,ast.FunctionDef)and n.name=='policy_prefill_variants')
ns=dict(changed=changed);exec(compile(ast.Module(body=[helper],type_ignores=[]),str(source),'exec'),ns)
variants=ns['policy_prefill_variants']
assert variants(c)==[]
controls=variants(new);assert len(controls)==9
for _,candidate in controls:
 assert candidate['host_memory_policy']==new['host_memory_policy']
 assert candidate['benchmark_memory_policy_id']==new['benchmark_memory_policy_id']
assert new['command']==c['command']
# Real post-selection loop: two winner/peak aliases are deduplicated; existing
# controls are skipped, failures stay excluded, full successful trials enter plan.
from types import SimpleNamespace
from pathlib import Path
parent_id=config_id(new);existing=controls[0][1];existing_id=config_id(existing)
assert existing_id!=parent_id
state=dict(selected='parent',peak_decode_identity=parent_id,candidates=[dict(identity=parent_id,worst_genre='chat')])
data=dict(selection=dict(candidates=[dict(case='parent'),dict(case='existing')]))
results={'parent':dict(config=new),'existing':dict(config=existing)}
class Plan:
 def __init__(self):self.writes=[]
 def write_text(self,text):self.writes.append(json.loads(text))
plan=Plan();attempts=[];calls=[];saved=[]
def fake_read(path):
 if path is plan:return copy.deepcopy(data)
 if str(path).endswith('range-selections.json'):return dict(hybrid_basalt_long=copy.deepcopy(state))
 return copy.deepcopy(results[Path(path).parent.name])
def fake_run(config,tag,family,genre):
 attempts.append((copy.deepcopy(config),tag,family,genre))
 return dict(status='failed')if len(attempts)==1 else dict(status='ok',prefill_tok_s=10,tail_decode_tok_s=20,case=tag)
block=source.read_text().split("current=read(O/'range-selections.json')[key+'_long'];data=read(plan)",1)[1]
block="current=read(O/'range-selections.json')[key+'_long'];data=read(plan)"+block
scope=dict(ns,read=fake_read,O=Path('/fixture/output'),R=Path('/fixture'),W=Path('/fixture/work'),key='hybrid_basalt',family='qwen',plan=plan,config_id=config_id,run=fake_run,name=lambda r:r['case'],json=json,subprocess=SimpleNamespace(run=lambda *a,**k:calls.append((a,k))),sys=SimpleNamespace(executable='python'),save=lambda *a:saved.append(a),state={},added=[])
exec(compile(block,str(source),'exec'),scope)
assert len(attempts)==8 and all(x[3]=='chat'for x in attempts)
assert len(plan.writes)==7 and len(plan.writes[-1]['selection']['candidates'])==9
assert len(calls)==1 and calls[0][0][0][-2:]==['hybrid_basalt','qwen'] and calls[0][1]['check']
record.update(policy_prefill_refit=dict(status='passed',variants=9,non106_policy_skipped=True,actual_driver_attempts=8,existing_controls_skipped=1,failed_trials_excluded=1,successful_trials_added=7,full_genre_repeatability_invocations=1),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(R/'outputs/hybrid-soft-pressure-refinement-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Policy-prefill follow-up actual driver checks passed')

# The user later clarified that12GiB is nonworker capacity, not unused RAM.
r=copy.deepcopy(result);t=copy.deepcopy(telemetry)
r['config']['host_memory_policy'].update(minimum_host_available_gib=0,minimum_nonworker_budget_gib=12)
t[0]['host_memory'].update(host_available_bytes=9*2**30,host_physical_bytes=122*2**30)
assert trial(r,t,c) is not None
t[0]['host_memory']['host_physical_bytes']=112*2**30
assert trial(r,t,c) is None
record['nonworker_budget_mode']='passed;9GiB free allowed with122GiB physical/108GiB cap, insufficient physical capacity refused'
(R/'outputs/hybrid-soft-pressure-refinement-test.json').write_text(json.dumps(record,indent=2)+'\n')
