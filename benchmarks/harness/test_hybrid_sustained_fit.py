"""Fault-inject the actual hybrid initial-fit control flow without GPU workers."""
from pathlib import Path
import hashlib,json
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/range_flash.py';s=source.read_text();block=s[s.index('initial=[]'):s.index('worst=min(initial')]
def check(kind):
 calls=[];saved={};base=dict(command=['engine','--resident-budget-gib','92'])
 def opt(c,k,v):c['command'][c['command'].index(k)+1]=str(v)
 def run(c,n,f,g,**kw):
  budget=int(c['command'][-1]);calls.append((budget,g))
  error='RAM safety stop: injected'if kind=='pressure'and budget==92 and g=='chat'else'cannot open pack/index.txt'if kind=='setup'and g=='chat'else None
  return dict(status='failed'if error else'ok',error=error,config=dict(output=n))
 ns=dict(base=base,model='hybrid',memory_fit=dict(safe_budgets_gib=[92])if kind!='flash'else None,run=run,opt=opt,save=lambda k,v:saved.update({k:v}),name=lambda x:x['config']['output'])
 error=None
 try:exec(compile(block,str(source),'exec'),ns)
 except AssertionError as e:error=str(e)
 if kind=='pressure':assert calls==[(92,'text'),(92,'chat'),(88,'text'),(88,'chat'),(88,'story')]and ns['memory_fit']['safe_budgets_gib']==[88]and error is None
 if kind=='setup':assert error and len(calls)==2 and int(base['command'][-1])==92
 if kind=='flash':assert error is None and len(calls)==3 and not saved
 return dict(calls=calls,raised=error)
checks={kind:check(kind)for kind in ['pressure','setup','flash']}
receipt=dict(status='passed',scope='Actual initial full-output fit block with injected worker responses; no GPU. Memory stop lowers the budget and restarts all genres; setup errors halt; ordinary Flash keeps a single pass.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checks=checks)
(R/'outputs/hybrid-sustained-fit-recovery-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Sustained-fit recovery checks passed')
