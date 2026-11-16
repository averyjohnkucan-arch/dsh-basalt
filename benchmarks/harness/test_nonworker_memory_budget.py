"""A nonworker budget includes OS-used RAM; verify actual guard and cache semantics."""
from pathlib import Path
from types import SimpleNamespace
import copy,json,hashlib
import benchmark_memory_guard as m
from range_common import completed_input_matches
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');request=dict(mode='nonworker-budget',reserved_gib=12,requested_by_user=True)
base=dict(command=['taskset','-c','0-21','engine','--spec','8'],host_memory_policy=dict(memory_high_gib=104,memory_max_gib=108,swap_max_gib=1,minimum_host_available_gib=12,pressure_avg10_limit=40,pressure_grace_s=6))
planned=m.apply_user_host_budget(copy.deepcopy(base),request,122*m.GIB);p=planned['host_memory_policy'];assert p['memory_max_gib']==108 and p['memory_high_gib']==104 and p['minimum_nonworker_budget_gib']==12 and p['minimum_host_available_gib']==0
assert completed_input_matches(dict(config=base),planned)
wrong=copy.deepcopy(base);wrong['command'][-1]='4';assert not completed_input_matches(dict(config=wrong),planned)
wrong=copy.deepcopy(base);wrong['host_memory_policy']['memory_max_gib']=120;assert not completed_input_matches(dict(config=wrong),planned)
large=copy.deepcopy(base);large['host_memory_policy']['memory_max_gib']=120;large=m.apply_user_host_budget(large,request,122*m.GIB);assert large['host_memory_policy']['memory_max_gib']==110
assert m.apply_user_host_budget(copy.deepcopy(large),request,122*m.GIB)==large
# The actual sampler allows2GiB currently free while OS uses its budget, but
# still stops sustained pressure. Never launch a worker or send a real signal.
guard=m.MemoryGuard(copy.deepcopy(planned),R/'validation/nonworker-budget-fixture');stops=[];guard.stop=lambda proc:stops.append('stopped');pressure=[0];now=[100]
old_path=m.Path;old_clock=m.time.monotonic
class Text:
 def __init__(self,path):self.path=path
 def read_text(self):
  if self.path=='/proc/meminfo':return f'MemTotal: {122*1024**2} kB\nMemAvailable: {2*1024**2} kB\nSwapTotal: {8*1024**2} kB\nSwapFree: {4*1024**2} kB\n'
  if self.path=='/proc/pressure/memory':return f'some avg10={pressure[0]} avg60=0 avg300=0 total=0\n'
  raise FileNotFoundError(self.path)
try:
 m.Path=lambda path:Text(path);m.time.monotonic=lambda:now[0]
 proc=SimpleNamespace(poll=lambda:None);sample=guard.sample(proc);assert not stops and sample['host_available_bytes']==2*m.GIB
 pressure[0]=45;guard.sample(proc);now[0]+=7;guard.sample(proc);assert stops==['stopped']
finally:m.Path=old_path;m.time.monotonic=old_clock
record=dict(status='passed',scope='Actual user-budget normalization, legacy stricter-success compatibility, rejection of changed native controls/larger old cap, physical cap enforcement and actual sampler with2GiB free/OS swap allowed. Sustained PSI still stops. No GPU.',worker_max_gib=p['memory_max_gib'],physical_gib=122,nonworker_capacity_gib=14,required_unused_ram_gib=0,sampler_low_available_allowed=True,sampler_sustained_pressure_stopped=True,source_sha256={name:hashlib.sha256((R/'work'/name).read_bytes()).hexdigest()for name in ['benchmark_memory_guard.py','range_common.py']})
(R/'outputs/nonworker-memory-budget-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Nonworker RAM budget and actual watchdog checks passed')
