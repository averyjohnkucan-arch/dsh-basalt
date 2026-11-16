"""Exact prompt IDs, including the tokenizer's native chat framing."""
import hashlib,json,pathlib,re

def load_prompt(config):
 if config.get('prompt_file'):
  value=json.loads(pathlib.Path(config['prompt_file']).read_text());ids=value['ids']if isinstance(value,dict)else value
  if len(ids)!=config['depth']:raise ValueError('Prompt file does not match requested depth')
  return ids
 fixture=pathlib.Path(config['fixture']);parts=[[int(x)for x in re.split('[, ]+',line)if x]for line in fixture.read_text().strip().splitlines()]
 prefix,body,suffix=parts;n=config['depth']-len(prefix)-len(suffix)
 if n<0:raise ValueError('Prompt too short')
 ids=prefix+(body*((n+len(body)-1)//len(body)))[:n]+suffix
 assert len(ids)==config['depth']
 return ids

def prompt_record(ids,config):
 return dict(tokens=len(ids),sha256=hashlib.sha256(','.join(map(str,ids)).encode()).hexdigest(),
             fixture=config.get('prompt_file',config.get('fixture')),workload=config.get('workload'))
