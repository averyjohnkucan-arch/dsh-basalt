"""Pure normalized native-configuration identity; safe to import."""
from range_common import copy,opt,json
import hashlib
def config_id(config):
 c=copy.deepcopy(config)
 for flag in ['--draft-log','--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache']:opt(c,flag,None)
 a=c['command'];position=[];flags={};i=4
 while i<len(a):
  token=a[i];i+=1
  if not token.startswith('--'):position.append(token);continue
  flags[token]=a[i]if i<len(a)and not a[i].startswith('--')else True
  if flags[token]is not True:i+=1
 if '--expert-profile'in flags and c.get('expert_profile_source'):flags['--expert-profile']=c['expert_profile_source']
 identity=[a[:4],position,sorted(flags.items()),c.get('artifact_header_sha256'),c.get('engine_binary_sha256')]
 if c.get('benchmark_environment_id'):identity.append(c['benchmark_environment_id'])
 if c.get('benchmark_memory_policy_id'):identity.append(['memory-policy',c['benchmark_memory_policy_id']])
 return hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:12]
