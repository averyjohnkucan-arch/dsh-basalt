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
