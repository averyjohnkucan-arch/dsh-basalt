"""Short, serial Basalt baseline and one-change comparison."""
import copy, json, os, subprocess, sys
from pathlib import Path
from range_common import R,W,O,WORKLOADS,read,run
from deepseek_storage import internal_artifact,raw_storage_evidence,storage_config
from benchmark_memory_guard import MemoryGuard

def fixture(family):
    old=next(x for x in WORKLOADS['cases'] if x['family']==family and x['workload']=='code')
    ids=read(Path(old['prompt_file']))['ids']
    suffix=old['suffix_tokens']
    ids=ids[:4096-suffix]+ids[-suffix:]
    path=W/('quick-basalt-'+family+'.json')
    path.write_text(json.dumps({'ids':ids}))
    return dict(family=family,workload='quick_code',depth=len(ids),prompt_file=str(path))

def prepare(quant):
    path=internal_artifact(quant)
    if path.exists():return path
    storage=raw_storage_evidence(quant)
    command=[sys.executable,str(W/'basalt-latest/tools/convert/convert.py'),
             '--gguf',storage['expert_files'][0]['path'],'--engram-gguf',storage['shared_engram'],
             '--dspark',storage['draft'],'--out',str(path),'--name','DeepSeek IQ2_'+quant,'--no-vision']
    print('Preparing verified DeepSeek',quant,flush=True)
    guard=MemoryGuard({},W/('quick-convert-'+quant))
    with (W/('quick-convert-'+quant+'.log')).open('w') as log:
        subprocess.run(guard.command(['taskset','-c','22',*command]),stdout=log,stderr=subprocess.STDOUT,
                       env={**os.environ,'TMPDIR':str(R/'tmp')},check=True)
    return path

out=O/'quick-basalt-results.json'
rows=[]
for label,family,path,quant,change in [
    ('flash-next','qwen',R/'packs/qwen-nvfp4-gptq.basalt',None,('--spec','6')),
    ('27b','qwen27b',R/'packs/qwen27b-nvfp4full-experimental.basalt',None,('--spec','8')),
    ('flash-hybrid','qwen',R/'packs/qwen-nvfp4-q8-hybrid.basalt',None,('--resident-budget-gib','92')),
    ('deepseek-xxs','deepseek',None,'XXS',('--spec','0')),
    ('deepseek-xs','deepseek',None,'XS',('--spec','0')),
]:
    try:
        if quant:path=prepare(quant)
        bin=R/'runtimes/basalt-custom-latest/bin/basalt'
        cfg=dict(command=['taskset','-c','0-21',str(bin),'--serve','--model',str(path)],
                 cwd=str(W/'basalt-latest'),timeout=900)
        if quant:cfg=storage_config(cfg,quant,basalt=True)
        f=fixture(family)
        def measure(arm,c):
            res=run(c,'quick-basalt-'+label+'-'+arm,family,'quick_code',n=256,fixture=f,role='Short Basalt code screen')
            rows.append(dict(model=label,arm=arm,status=res['status'],prefill=res.get('prefill_tok_s'),
                             decode=res.get('tail_decode_tok_s'),error=res.get('error'),
                             case=Path(res['config']['output']).name,info=res.get('info')))
            out.write_text(json.dumps(rows,indent=2)+'\n')
            return res
        base=measure('defaults',cfg)
        tweak=copy.deepcopy(cfg)
        flag,value=change
        if flag=='--spec' and str(base.get('info',{}).get('mtp_max',base.get('info',{}).get('spec'))) == value:
            value='6' if value in ('0','8') else '0'
        tweak['command'] += [flag,value]
        measure(flag.removeprefix('--')+'-'+value,tweak)
    except Exception as err:
        rows.append(dict(model=label,status='failed',error=str(err)))
        out.write_text(json.dumps(rows,indent=2)+'\n')
