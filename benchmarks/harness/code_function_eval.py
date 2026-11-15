"""Independent generated-function checks; generated code runs only inside bwrap."""
import json,pathlib,subprocess,sys,copy,re,time
from prepare_range_fixtures import framing,tokenizer_for
R=pathlib.Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
TASKS={
 'merge_intervals':('Implement def merge_intervals(intervals): for a list of integer (start,end) pairs with start<=end. Return sorted disjoint intervals as a list of tuples, merging overlaps and touching endpoints. Do not mutate input.', 'assert f([])==[]\nassert f([(5,7),(1,3),(3,6),(10,10)])==[(1,7),(10,10)]\nassert f([(2,2),(2,2),(-4,-1)])==[(-4,-1),(2,2)]\nassert f([(0,100),(2,3)])==[(0,100)]'),
 'lru_trace':('Implement def lru_trace(capacity, accesses): simulate an initially empty LRU cache of integer keys. Return (number_of_misses, keys_ordered_MRU_to_LRU). Hits refresh recency. Capacity zero stores nothing and every access misses. Capacity is a nonnegative integer.', 'assert f(0,[1,1,2])==(3,[])\nassert f(2,[1,2,1,3,2])==(4,[2,3])\nassert f(1,[1,1,2,2,1])==(3,[1])\nassert f(3,[])==(0,[])'),
 'verify_draft':('Implement def verify_draft(target, draft): target and draft are lists of integers. Count the longest matching prefix k, stopping at either list end or first mismatch. Return (k, emitted). emitted starts with draft[:k]. If target has token target[k], append that one target token; otherwise append nothing. No mutation or imports.', 'assert f([1,2,3],[1,9])==(1,[1,2])\nassert f([1,2,3],[1,2])==(2,[1,2,3])\nassert f([1],[1,2])==(1,[1])\nassert f([],[])==(0,[])\nassert f([4],[])==(0,[4])\nassert f([1],[9])==(0,[1])')}
configs=json.loads(pathlib.Path(sys.argv[1]).read_text());rows=[]
for label,item in configs.items():
 cbase=json.loads(pathlib.Path(item['config']).read_text());tok,metadata=tokenizer_for(item.get('family','qwen27b'))
 for function,(task,checks)in TASKS.items():
  name='quality-'+label+'-'+function;out=R/'bench'/name;out.mkdir(parents=True,exist_ok=True);c=copy.deepcopy(cbase)
  prompt=task+' Output only the Python function implementation. No Markdown, no examples, no tests, no imports, and no prose. Stop after the function.'
  prefix,suffix,_=framing(tok,metadata,'unit',task=prompt);ids=prefix+tok.encode('No additional reference material.')+suffix
  fixture=W/(name+'-prompt.json');fixture.write_text(json.dumps(dict(ids=ids)))
  c.update(prompt_file=str(fixture),depth=len(ids),generate=1024,timed_tail=32,require_complete=False,ignore_eos=False,allow_reused=False,require_reuse_min=0,forbidden_token_ids=[],output=str(out),measurement_role='functional correctness only; not a throughput result',sampling='temperature=0 seed=42')
  for flag in ['--eos-ids','--eos','--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache','--draft-log']:
   if flag in c['command']:
    at=c['command'].index(flag);del c['command'][at:at+2]
  if pathlib.Path(c['command'][3]).name.startswith('basalt')and '--stop-eos'not in c['command']:c['command'].append('--stop-eos')
  config=W/(name+'.json');config.write_text(json.dumps(c,indent=2));print('START',name,flush=True)
  if '--grade-only'not in sys.argv:
   with(W/(name+'.progress')).open('w')as log:subprocess.run([sys.executable,str(W/('http_bench.py'if c.get('protocol')=='http'else'native_bench.py')),'--config',str(config)],stdout=log,stderr=subprocess.STDOUT)
  result=json.loads((out/'result.json').read_text());row=dict(model=label,function=function,status=result['status'],case=name,passed=False)
  if result['status']=='ok':
   if c.get('protocol')=='http':
    text=(out/'content.txt').read_text()
   else:
    tokens=json.loads((out/'tokens.json').read_text());eos=tok.special_ids.get('tokenizer.ggml.eos_token_id')
    (out/'raw-protocol-text.txt').write_text(tok.decode(tokens))
    if result.get('finish')in('stop','eos')and tokens and tokens[-1]==eos:
     row['removed_protocol_terminator']=tokens[-1];tokens=tokens[:-1]
    text=tok.decode(tokens)
   (out/'generated.py.txt').write_text(text);code=text.strip();fenced=re.search(r'```(?:python)?\s*\n(.*?)```',code,re.S)
   if fenced:code=fenced.group(1)
   harness='import resource\nresource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))\nresource.setrlimit(resource.RLIMIT_CPU,(3,3))\nresource.setrlimit(resource.RLIMIT_NPROC,(16,16))\nresource.setrlimit(resource.RLIMIT_FSIZE,(4194304,4194304))\n'+code+'\nf='+function+'\n'+checks+'\nprint("INDEPENDENT_CHECKS_PASSED")\n'
   cmd=['bwrap','--unshare-all','--die-with-parent','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/work','--chdir','/work','/usr/bin/python3','-I','-S','-']
   try:
    with(out/'unit.log').open('w')as log:proc=subprocess.run(cmd,input=harness,text=True,stdout=log,stderr=subprocess.STDOUT,timeout=8)
    row.update(passed=proc.returncode==0 and 'INDEPENDENT_CHECKS_PASSED'in(out/'unit.log').read_text(),returncode=proc.returncode)
   except subprocess.TimeoutExpired:row['error']='sandbox timeout'
  rows.append(row);print(row,flush=True)
  (O/('code-functional-'+pathlib.Path(sys.argv[1]).stem+'.json')).write_text(json.dumps(rows,indent=2))
