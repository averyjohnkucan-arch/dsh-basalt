from pathlib import Path
import json,sys,subprocess
from range_identity import config_id
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
s=json.loads((O/'range-selections.json').read_text());configs={}
for key,family in [('flash_basalt','qwen'),('hybrid_basalt','qwen'),('27b_basalt','qwen27b'),('27b_ninfer','qwen27b'),('flash_strata','qwen'),('hybrid_strata','qwen'),('gyro_strata','qwen'),('flash_fp16_basalt','qwen'),('hybrid_fp16_basalt','qwen'),('flash_fp16_strata','qwen'),('hybrid_fp16_strata','qwen'),('huihui_nvfp4_ninfer','qwen27b'),('huihui_int8_ninfer','qwen27b'),('huihui_fp8_ninfer','qwen27b')]:
 selected=s.get(key+'_long')
 if selected:
  config=W/(selected['selected']+'.json');configs[key.replace('_','-')]=dict(config=str(config),family=family)
  short=s.get(key+'_short')
  if short:
   short_config=W/(short['selected']+'.json')
   if config_id(json.loads(config.read_text()))!=config_id(json.loads(short_config.read_text())):
    configs[key.replace('_','-')+'-peak-code']=dict(config=str(short_config),family=family)
p=W/'range-selected-functional-configs.json';p.write_text(json.dumps(configs,indent=2))
subprocess.run([sys.executable,str(W/'code_function_eval.py'),str(p)],check=True)
