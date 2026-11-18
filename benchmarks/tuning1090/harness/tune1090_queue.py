"""Sequential bounded10/90 tuning; writes receipts and waits in native workers."""
from pathlib import Path
import json,sys,subprocess,time,copy,re,collections,fcntl,os
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';D=W/'tune1090';PY=R/'tools/build-env/bin/python'
lock=(D/'queue.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def write(p,x):
 q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def opt(c,k,v):
 a=c['command']
 if k in a:
  i=a.index(k)
  if v is None:del a[i:i+2]
  else:a[i+1]=str(v)
 elif v is not None:a.extend([k,str(v)])
state={'protocol':'10% counting then90% prose/chat;1024output,final512timed;no prefix reuse;nonthinking','status':'running','models':{},'started':time.time()}
statepath=O/'tune1090-progress.json'
if statepath.exists():state=json.loads(statepath.read_text());state['status']='running'
def run(c,label,family,percent):
 name='tune1090-'+label+'-'+str(percent);out=R/'bench'/name;p=out/'result.json'
 if p.exists():return json.loads(p.read_text())
 c=copy.deepcopy(c);c.update(depth=(1048576 if family=='deepseek' else 262144)*percent//100,prompt_file=str(D/f'{family}-{percent}.json'),generate=1024,timed_tail=512,require_complete=True,ignore_eos=False,output=str(out),allow_reused=False,require_reuse_min=0,workload=('count10'if percent==10 else'chat90'),timeout=18000,measurement_role=state['protocol'],host_memory_policy={'memory_high_gib':114,'memory_max_gib':114,'minimum_host_available_gib':0,'pressure_avg10_limit':100})
 for k in ['warm_same_prompt','warm_replays','warmup_tokens']:c.pop(k,None)
 cfg=D/(name+'.json');write(cfg,c);state['current']={'case':name,'started':time.time()};write(statepath,state);print('START',name,flush=True)
 harness='http_bench1090.py'if c.get('protocol')=='http'else'native_bench.py'
 with (D/(name+'.log')).open('w')as f:subprocess.run([str(PY),str(W/harness),'--config',str(cfg)],stdout=f,stderr=subprocess.STDOUT,timeout=20000)
 d=json.loads(p.read_text())if p.exists()else{'status':'failed','error':'no receipt','config':c}
 if d['status']=='ok':
  if c.get('protocol')=='http':text=(out/'content.txt').read_text()
  else:
   sys.path.insert(0,str(W));from prepare_range_fixtures import tokenizer_for,Tokenizer
   tok=Tokenizer.from_metadata(json.loads((W/'huihui-test-tokenizer-metadata.json').read_text()))if family=='huihui'else tokenizer_for(family)[0]
   text=tok.decode(json.loads((out/'tokens.json').read_text()));(out/'content.txt').write_text(text)
  words=re.findall(r'\w+',text.lower());grams=collections.Counter(tuple(words[i:i+8])for i in range(max(0,len(words)-7)))
  q={'words':len(words),'unique8gram_fraction':len(grams)/max(1,sum(grams.values())),'max8gram_repeat':max(grams.values(),default=0),'review_required':max(grams.values(),default=0)>3,'scope':'repetition screening only;not semantic quality proof'}
  if percent==10:
   numbers=[int(x)for x in re.findall(r'\d+',text)];q['counting_prefix_correct']=all(v==i+1 for i,v in enumerate(numbers[:-1]));q['numbers_observed']=len(numbers)
  d['output_screen']=q;write(p,d)
 print('DONE',name,d.get('status'),d.get('prefill_tok_s'),d.get('tail_decode_tok_s'),flush=True);return d
plan=json.loads((D/'plan.json').read_text())
for item in plan:
 key=item['key'];base=json.loads(Path(item['source']).read_text());family=item['family']
 if key in state['models']and state['models'][key].get('status')=='measured':continue
 # Use the saved instruct sampler consistently, explicitly, including penalties.
 if base.get('protocol')=='http':base['request_sampling']=item['sampling']
 else:base['sampling']=item['native_sampling']
 rows={};baseline={}
 for percent in [10,90]:baseline[str(percent)]=run(base,key+'-before',family,percent)
 rows['before']=baseline
 for variant in item.get('variants',[]):
  c=copy.deepcopy(base)
  for flag,value in variant['changes'].items():opt(c,flag,value)
  label=variant['name'];pair={}
  for percent in [10,90]:
   pair[str(percent)]=run(c,key+'-'+label,family,percent)
   if pair[str(percent)]['status']!='ok':break
  rows[label]=pair
  state['models'][key]={'status':'tuning','trials':rows};write(statepath,state)
 valid=[(name,pair)for name,pair in rows.items()if all(pair.get(str(p),{}).get('status')=='ok'and pair[str(p)].get('generated')==1024 and not pair[str(p)].get('reused_tokens',0)and pair[str(p)].get('tail_decode_tok_s')for p in [10,90])and not pair['90'].get('output_screen',{}).get('review_required',False)]
 if valid:
  peakname,peakpair=max(valid,key=lambda x:x[1]['90']['tail_decode_tok_s']);peak=peakpair['90'];eligible=[]
  for name,pair in valid:
   h=pair['90'];loss=max(0,1-h['tail_decode_tok_s']/peak['tail_decode_tok_s']);gain=h['prefill_tok_s']/peak['prefill_tok_s']-1
   if loss==0 or gain>=3*loss:eligible.append((name,pair))
  chosen,pair=max(eligible,key=lambda x:x[1]['90']['prefill_tok_s'])
  selected={'candidate':chosen,'low':pair['10'],'high':pair['90'],'peak_decode_candidate':peakname,'tradeoff':'relative to highest measured90%decode:prefillgain>=3*decodeloss'}
 else:selected={'error':'No candidate passed measurement and repetition screening;review required'}
 state['models'][key]={'status':'measured','trials':rows,'selected':selected};write(statepath,state);print('MODEL_COMPLETE',key,selected.get('candidate'),flush=True)
state['status']='measurements_complete_pending_review_export';state['finished']=time.time();write(statepath,state);print('QUEUE_COMPLETE',flush=True)
