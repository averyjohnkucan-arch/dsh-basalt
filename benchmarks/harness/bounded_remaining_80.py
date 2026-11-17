from pathlib import Path
import json,copy,subprocess,sys,hashlib
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');w=r/'work';o=r/'outputs';rows={};selection={}
def option(c,flag,value):
 a=c['command']
 if flag in a:a[a.index(flag)+1]=str(value)
 else:a.extend([flag,str(value)])
for family,source,tokenizer,variants in [
 ('ninfer27','ninfer-matched-latest-chat90.json','qwen27b',[('saved',None,None),('prefill512','--prefill-chunk',512),('prefill2048','--prefill-chunk',2048)]),
 ('gyro','latest-remaining-gyro-90.json','qwen',[('saved',None,None),('spec0','--spec',0),('spec4','--spec',4)])]:
 base=json.loads((w/source).read_text());fixture=w/'range-fixtures'/(tokenizer+'-chat.json');ids=json.loads(fixture.read_text())['ids'];assert len(ids)==209715
 seen=set();family_rows=[]
 for variant,flag,value in variants:
  c=copy.deepcopy(base)
  if flag:option(c,flag,value)
  sig=json.dumps(c['command'])
  if sig in seen:continue
  seen.add(sig);label=family+'-'+variant;case=r/'bench'/('bounded80-'+label)
  c.update(depth=209715,prompt_file=str(fixture),generate=4096,timed_tail=2048,require_complete=True,ignore_eos=True,output=str(case),measurement_role='Bounded80% chat tuning;4096 generated,final2048 decode; fixed prompt; no global maximum claim',host_memory_policy={'memory_high_gib':114,'memory_max_gib':114,'minimum_host_available_gib':0,'pressure_avg10_limit':100})
  path=w/('bounded80-'+label+'.json');path.write_text(json.dumps(c,indent=2)+'\n');print('START',label,flush=True)
  with (w/('bounded80-'+label+'.progress')).open('w')as log:
   proc=subprocess.run([sys.executable,str(w/('http_bench.py'if c.get('protocol')=='http'else'native_bench.py')),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
  p=case/'result.json';d=json.loads(p.read_text())if p.exists()else{'status':'failed','error':'No receipt'}
  row={k:d.get(k)for k in ['status','error','generated','prefill_tok_s','tail_decode_tok_s','reused_tokens']};row.update(case=str(case),config=str(path),variant=variant);rows[label]=row;family_rows.append(row);(o/'bounded-remaining80-results.json').write_text(json.dumps(rows,indent=2)+'\n');print(label,row,flush=True)
 valid=[x for x in family_rows if x['status']=='ok'and x['generated']==4096 and not x['reused_tokens']and x['tail_decode_tok_s']]
 if valid:
  peak=max(x['tail_decode_tok_s']for x in valid);eligible=[x for x in valid if x['tail_decode_tok_s']>=.95*peak];winner=max(eligible,key=lambda x:x['prefill_tok_s']);selection[family]={'scope':'Three-or-fewer distinct configurations on one matched80% chat workload;not all-genre or global maximum proof','peak_decode':peak,'decode_floor':.95*peak,'selected':winner,'trials':len(family_rows)}
 else:selection[family]={'status':'no valid candidates'}
 (o/'bounded-remaining80-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
