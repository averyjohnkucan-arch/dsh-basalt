import json,pathlib,subprocess,sys,time,copy,os
R=pathlib.Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
def read(p):return json.loads(pathlib.Path(p).read_text())
def opt(c,k,v):
 a=c['command']
 if k in a:
  i=a.index(k);del a[i:i+2]
 if v is not None:a.extend([k,str(v)])
def run(c,name,depth=209715,n=8192,cache=None,reuse=False):
 c=copy.deepcopy(c)
 if not name.startswith('regen80-'):
  name='code-'+name;c['fixture']=str(W/('code-deepseek.ids'if 'deepseek'in pathlib.Path(c.get('fixture','')).name else'code-qwen.ids'));c['workload']='code-generation'
 out=R/'bench'/name;c.update(output=str(out),depth=depth,generate=n,timed_tail=n//2,allow_reused=reuse,require_reuse_min=depth-32 if reuse else 0)
 if '--draft-log'in c['command']:opt(c,'--draft-log',out/'draft.log')
 for k in ['--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache']:opt(c,k,None)
 if cache:
  for k,v in [('--conversation-cache-dir',R/'checkpoints'/cache),('--conversation-cache-disk-mib',16384),('--conversation-cache-mib',0),('--prompt-cache',4)]:opt(c,k,v)
 p=W/(name+'.json');prior=read(p)if p.exists()else None;same=prior==c;p.write_text(json.dumps(c,indent=2));target=out/'result.json'
 if not same or not target.exists()or read(target).get('status')!='ok':
  print(time.strftime('%H:%M:%S'),'START',name,flush=True)
  with (W/(name+'.progress')).open('w')as log:subprocess.run([sys.executable,str(W/('http_bench.py'if c.get('protocol')=='http'else'native_bench.py')),'--config',str(p)],stdout=log,stderr=subprocess.STDOUT)
 x=read(target);print(time.strftime('%H:%M:%S'),'END',name,x.get('status'),x.get('prefill_tok_s'),x.get('tail_decode_tok_s'),x.get('error'),flush=True)
 return x

def choose(results):
 valid=[x for x in results if x['status']=='ok'and x.get('cold_prefill_qualified',True)and x.get('prefill_tok_s')]
 assert valid
 peak=max(x['tail_decode_tok_s']for x in valid)
 eligible=[x for x in valid if x['tail_decode_tok_s']>=.95*peak]
 chosen=max(eligible,key=lambda x:x['prefill_tok_s'])
 return {'objective':'80% context coding workload; maximum cold prefill with sustained late decode >=95% of highest qualified cold-run decode','peak_decode_tok_s':peak,'minimum_decode_tok_s':.95*peak,'selected':pathlib.Path(chosen['config']['output']).name,'eligible':[pathlib.Path(x['config']['output']).name for x in eligible],'candidates':[{'name':pathlib.Path(x['config']['output']).name,'prefill_tok_s':x['prefill_tok_s'],'tail_decode_tok_s':x['tail_decode_tok_s']}for x in valid]}

def save(key,value):
 p=O/'tuning80-selections.json';s=read(p)if p.exists()else{};s[key]=value;p.write_text(json.dumps(s,indent=2))
