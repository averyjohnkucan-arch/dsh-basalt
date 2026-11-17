"""Per-worker cgroup isolation and an early RAM-pressure stop; no global OS changes."""
from pathlib import Path
import os,hashlib,signal,time,subprocess,json,math
GIB=1024**3
USER_BUDGET_FILE=Path('/mnt/media/scratch/dsh-inference-tuning-20261115/outputs/user-host-memory-policy.json')
def apply_user_host_budget(cfg,request=None,total_bytes=None):
 """Reserve capacity for other processes, including the RAM they already use."""
 if request is None:request=cfg.get('user_host_budget_override')
 if request is None:
  if not USER_BUDGET_FILE.exists():return cfg
  request=json.loads(USER_BUDGET_FILE.read_text())
 assert request.get('requested_by_user')and request['mode']=='nonworker-budget'
 reserve=request['reserved_gib'];assert isinstance(reserve,(int,float))and reserve>=0
 if total_bytes is None:
  total_bytes=int(next(line.split()[1]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemTotal:')))*1024
 cap=math.floor(total_bytes/GIB-reserve);assert cap>0
 policy=dict(isolation='separate systemd user scope',memory_high_gib=96,memory_max_gib=108,swap_max_gib=1,minimum_host_available_gib=12,pressure_avg10_limit=40,pressure_grace_s=6)
 if 'default_worker_max_gib' in request:
  policy['memory_high_gib']=policy['memory_max_gib']=request['default_worker_max_gib']
 policy.update(cfg.get('host_memory_policy',{}));previous_max=policy['memory_max_gib']
 policy['memory_max_gib']=min(previous_max,cap);policy['memory_high_gib']=min(policy['memory_high_gib'],policy['memory_max_gib'])
 policy['minimum_host_available_gib']=0;policy['minimum_nonworker_budget_gib']=reserve
 if request.get('disable_pressure_watchdog'):policy['pressure_avg10_limit']=100
 cfg['host_memory_policy']=policy
 if policy['memory_max_gib']!=previous_max:
  cfg['benchmark_memory_policy_id']=cfg.get('benchmark_memory_policy_id','default')+'-physical-cap'+str(policy['memory_max_gib'])
 return cfg

class MemoryGuard:
 def __init__(self,cfg,output):
  apply_user_host_budget(cfg)
  self.policy={'isolation':'separate systemd user scope','memory_high_gib':96,'memory_max_gib':108,'swap_max_gib':1,'minimum_host_available_gib':12,'pressure_avg10_limit':40,'pressure_grace_s':6}
  self.policy.update(cfg.get('host_memory_policy',{}));cfg['host_memory_policy']=self.policy
  self.unit='dsh-bench-'+hashlib.sha256(str(output).encode()).hexdigest()[:12]+'-'+str(os.getpid())
  parent=Path(Path('/proc/self/cgroup').read_text().strip().split('::',1)[1]).parent
  self.cgroup=Path('/sys/fs/cgroup')/str(parent).lstrip('/')/(self.unit+'.scope');self.reason=None;self.since=None
 def command(self,argv):
  p=self.policy
  return ['systemd-run','--user','--scope','--quiet','--collect','--unit',self.unit,'--slice=app.slice','-p','MemoryAccounting=yes','-p',f'MemoryHigh={p["memory_high_gib"]}G','-p',f'MemoryMax={p["memory_max_gib"]}G','-p',f'MemorySwapMax={p["swap_max_gib"]}G',*argv]
 def stop(self,proc):
  # A plugin may detach its native server. Stop our entire owned cgroup.
  try:subprocess.run(['systemctl','--user','stop','--no-block',self.unit+'.scope'],timeout=5,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  except (OSError,subprocess.TimeoutExpired):pass
  try:os.killpg(proc.pid,signal.SIGTERM)
  except ProcessLookupError:pass
 def sample(self,proc):
  mem={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()if len(line.split())>=3 and line.split()[1].isdigit()}
  pressure=Path('/proc/pressure/memory').read_text();some=next(x for x in pressure.splitlines()if x.startswith('some '));avg=float(next(x.split('=')[1]for x in some.split()if x.startswith('avg10=')))
  value={'host_physical_bytes':mem['MemTotal'],'host_available_bytes':mem['MemAvailable'],'host_swap_used_bytes':mem['SwapTotal']-mem['SwapFree'],'pressure_some_avg10':avg,'unit':self.unit}
  for key,file in [('scope_current_bytes','memory.current'),('scope_peak_bytes','memory.peak'),('scope_swap_bytes','memory.swap.current')]:
   try:value[key]=int((self.cgroup/file).read_text())
   except FileNotFoundError:pass
  try:value['scope_events']=(self.cgroup/'memory.events').read_text().strip()
  except FileNotFoundError:pass
  bad=mem['MemAvailable']<self.policy['minimum_host_available_gib']*GIB or avg>self.policy['pressure_avg10_limit']
  self.since=(self.since or time.monotonic())if bad else None
  if bad and time.monotonic()-self.since>=self.policy['pressure_grace_s']and proc.poll()is None:
   self.reason=f'RAM safety stop: available={mem["MemAvailable"]/GIB:.1f}GiB, memory-pressure avg10={avg:.1f}%';value['safety_stop']=self.reason
   self.stop(proc)
  return value
