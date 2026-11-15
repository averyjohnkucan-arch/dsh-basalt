"""Explicit immutable benchmark cohort selected only at an idle measurement boundary."""
from pathlib import Path
import json,re,subprocess
ROOT=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
def current_environment():
 path=ROOT/'outputs/active-benchmark-environment.json'
 if not path.exists():return None
 data=json.loads(path.read_text());assert re.fullmatch(r'[a-z0-9-]+',data['case_prefix'])and data['id']
 return data
def case_name(logical):
 data=current_environment();return 'range-'+(data['case_prefix']+'-'if data else'')+logical
def repeatability_plan(key):
 data=current_environment();return ROOT/'outputs'/(key+('-'+data['case_prefix']if data else'')+'-repeatability-plan.json')
def power_snapshot():
 values={}
 for key,path in [('firmware_profile','/sys/firmware/acpi/platform_profile'),('cpu_epp','/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference'),('ac_online','/sys/class/power_supply/AC/online')]:
  try:values[key]=Path(path).read_text().strip()
  except FileNotFoundError:values[key]=None
 return values
def ensure_environment():
 data=current_environment()
 if data and data.get('require_performance_policy'):
  state=power_snapshot();assert state['firmware_profile']=='performance'and state['cpu_epp']=='performance'and state['ac_online']=='1',f'Benchmark power policy changed: {state}'
  status=subprocess.run(['systemctl','is-active','--quiet','nvidia-powerd'],timeout=5)
  assert status.returncode==0,'NVIDIA power daemon stopped; inspect before continuing this performance cohort'
