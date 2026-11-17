"""Finish the 90% counts and screen two small fixed-residency variations."""
from pathlib import Path
import copy
import json
import subprocess
import sys

work = Path(__file__).resolve().parent
scratch = work.parent
report = scratch / 'outputs' / 'deepseek-followup.json'
summary = {}

def read(path):
    return json.loads(path.read_text())

def run(config, name):
    case = scratch / 'bench' / name
    case.mkdir(parents=True, exist_ok=True)
    config['output'] = str(case)
    path = work / (name + '.json')
    path.write_text(json.dumps(config, indent=2)+'\n')
    print('START', name, flush=True)
    with (case / 'harness.log').open('w') as log:
        done = subprocess.run([sys.executable, str(work / 'native_warm_240.py'),
                              '--config', str(path)], stdout=log, stderr=subprocess.STDOUT)
    result_path = case / 'result.json'
    if result_path.exists():
        return read(result_path)
    return {'status':'failed', 'error':(case / 'harness.log').read_text()[-1000:], 'exit':done.returncode}

def record(name, result):
    summary[name] = {key:result.get(key) for key in (
        'status','error','generated','prompt_tokens','reused_tokens','prefill_tok_s',
        'decode_tok_s','tail_decode_tok_s','ttft_s','warm_replay_series'
    )}
    temp = report.with_suffix('.tmp')
    temp.write_text(json.dumps(summary, indent=2)+'\n')
    temp.replace(report)
    print(name, summary[name]['status'], summary[name]['decode_tok_s'], summary[name]['tail_decode_tok_s'], flush=True)

def replace_option(command, flag, value):
    command[command.index(flag) + 1] = value

for quant in ('xxs','xs'):
    prose = scratch / 'bench' / ('deepseek-final-chat90-' + quant) / 'result.json'
    if not prose.is_file():
        record('count90-'+quant, {'status':'skipped','error':'No completed 90% prose case'})
        continue
    result = read(prose)
    if result['status'] != 'ok':
        record('count90-'+quant, {'status':'skipped','error':'90% prose failed: '+str(result.get('error'))})
        continue
    followup = result.get('count90_followup')
    if followup and followup.get('status')=='ok':
        record('count90-'+quant, followup)
        continue
    config = read(work / f'deepseek-final-chat90-{quant}.json')
    config.update(prompt_file=str(work / 'range-fixtures/deepseek-count90.json'),workload='count90')
    record('count90-'+quant, run(config,'deepseek-final-count90-'+quant))

for quant in ('xxs','xs'):
    baseline = read(work / f'deepseek-warm-240-fixed-{quant}-chat.json')
    del baseline['chat_turns']
    baseline.update(warm_same_prompt=True,warm_replays=2,warmup_tokens=1000,allow_reused=True,timeout=600)
    for label,flag,value in (
        ('fixed-control',None,None),
        ('extra-2gib','--resident-budget-gib','104.3'),
        ('workers-16','--pool-workers','16'),
    ):
        config = copy.deepcopy(baseline)
        if flag:
            replace_option(config['command'],flag,value)
        name = f'deepseek-count-tweak-{quant}-{label}'
        record(name,run(config,name))
