from tune80_common import read,opt,choose
import json,pathlib,subprocess,sys,time,copy,os,hashlib,functools
from benchmark_environment import current_environment
R=pathlib.Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
PREFIX='latest-code-'
@functools.lru_cache(None)
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def latest(c,engine):
 c=copy.deepcopy(c);a=c['command']
 if engine=='basalt':a[3]=str(R/'runtimes/basalt-custom-latest/bin/basalt');c['cwd']=str(W/'basalt-latest')
 elif engine=='strata':
  binary=R/'runtimes/strata-engine-0.1.59/strata';a[3]=str(binary);c['env']={**c.get('env',{}),'LD_LIBRARY_PATH':str(binary.parent)}
 elif engine=='ninfer':
  a[3]=str(R/'build/ninfer-latest/apps/ninfer-serve');opt(c,'--device-profile-path',W/('ninfer-device-profile-latest-custom-performance.json'if current_environment()else'ninfer-device-profile-latest-custom.json'));opt(c,'--output-head-residency',None)
 else:raise ValueError(engine)
 c['engine_channel']='latest-custom'if engine!='strata'else'latest-official-0.1.59'
 return c

def run(c,name,depth=209715,n=8192,cache=None,reuse=False):
 c=copy.deepcopy(c);name=PREFIX+name
 c['fixture']=str(W/('code-deepseek.ids'if 'deepseek'in pathlib.Path(c.get('fixture','')).name else'code-qwen.ids'));c['workload']='code-generation'
 out=R/'bench'/name;c.update(output=str(out),depth=depth,generate=n,timed_tail=n//2,allow_reused=reuse,require_reuse_min=depth-32 if reuse else 0)
 c['engine_binary_sha256']=digest(c['command'][3]);c['gpu_power_limit_w']=95
 if '--model'in c['command']:
  artifact=pathlib.Path(c['command'][c['command'].index('--model')+1])
  with artifact.open('rb')as f:c['artifact_header_sha256']=hashlib.sha256(f.read(65536)).hexdigest()
  c['artifact_bytes']=artifact.stat().st_size
 if '--draft-log'in c['command']:opt(c,'--draft-log',out/'draft.log')
 for k in ['--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache']:opt(c,k,None)
 if cache:
  for k,v in [('--conversation-cache-dir',R/'checkpoints'/(PREFIX+cache)),('--conversation-cache-disk-mib',16384),('--conversation-cache-mib',0),('--prompt-cache',4)]:opt(c,k,v)
 p=W/(name+'.json');prior=read(p)if p.exists()else None;same=prior==c;p.write_text(json.dumps(c,indent=2));target=out/'result.json'
 if not same or not target.exists()or read(target).get('status')!='ok':
  print(time.strftime('%H:%M:%S'),'START',name,flush=True)
  with(W/(name+'.progress')).open('w')as log:
   subprocess.run([sys.executable,str(W/('http_bench.py'if c.get('protocol')=='http'else'native_bench.py')),'--config',str(p)],stdout=log,stderr=subprocess.STDOUT)
 x=read(target);print(time.strftime('%H:%M:%S'),'END',name,x.get('status'),x.get('prefill_tok_s'),x.get('tail_decode_tok_s'),x.get('error'),flush=True)
 return x

def save(key,value):
 p=O/'latest-tuning80-selections.json';s=read(p)if p.exists()else{};s[key]=value;p.write_text(json.dumps(s,indent=2))
def selection(key,results):
 selected=choose(results);save(key,selected);return read(W/(selected['selected']+'.json'))
def cases(pattern):return[read(p)for p in(R/'bench').glob(PREFIX+pattern+'/result.json')]
def select(key,pattern):return selection(key,cases(pattern))
