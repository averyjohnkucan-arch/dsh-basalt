"""Retry the two converted quants with the same startup RAM reservation."""
import json, time, subprocess
from range_common import R,W,O,run
from deepseek_storage import storage_config

while subprocess.run(['systemctl','--user','is-active','--quiet','dsh-quick-basalt.service']).returncode==0:
    time.sleep(5)
f=dict(family='deepseek',workload='quick_code',depth=4096,prompt_file=str(W/'quick-basalt-deepseek.json'))
out=O/'quick-deepseek-matched-retry.json'
rows=[]
for quant in ('XXS','XS'):
    c=storage_config(dict(command=['taskset','-c','0-21','unused','--serve','--ram-reserve-mib','16384'],
                          cwd=str(W/'basalt-latest'),timeout=900),quant,basalt=True)
    r=run(c,'quick-basalt-deepseek-'+quant.lower()+'-reserve16','deepseek','quick_code',n=256,fixture=f,
          role='Matched short DeepSeek check with 16 GiB engine RAM reserve')
    rows.append(dict(quant=quant,status=r['status'],prefill=r.get('prefill_tok_s'),decode=r.get('tail_decode_tok_s'),
                     error=r.get('error'),case=r['config']['output']))
    out.write_text(json.dumps(rows,indent=2)+'\n')
