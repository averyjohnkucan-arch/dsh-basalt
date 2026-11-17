"""Run matched uninterrupted four-minute decode trials, with OS paging first."""
import json
import subprocess
import sys
import copy
from pathlib import Path

from deepseek_storage import storage_config

work = Path(__file__).resolve().parent
scratch = work.parent
baseline = json.loads((work / 'reproduce-deepseek-more-ram-xxs.json').read_text())
summary = {}
from deepseek_chat_turns import chat_codec
from gguf_reader import GGUFFile

def run(config, case):
    config['output'] = str(case)
    path = work / f'{case.name}.json'
    path.write_text(json.dumps(config, indent=2) + '\n')
    case.mkdir(parents=True, exist_ok=True)
    with (case / 'harness.log').open('w') as log:
        completed = subprocess.run(
            [sys.executable, str(work / 'native_warm_240.py'), '--config', str(path)],
            stdout=log, stderr=subprocess.STDOUT, check=False,
        )
    result_path = case / 'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else {
        'status': 'failed', 'error': (case / 'harness.log').read_text()[-1200:],
    }
    return completed, result

def record():
    target = scratch / 'outputs' / 'deepseek-warm-240.json'
    pending = target.with_suffix('.tmp')
    pending.write_text(json.dumps(summary, indent=2) + '\n')
    pending.replace(target)
for mode in ('paging', 'fixed'):
    for quant in ('XXS', 'XS'):
        config = storage_config(baseline, quant, basalt=True)
        command = config['command']
        if mode == 'paging':
            index = command.index('--resident-budget-gib')
            del command[index:index + 2]
            command.extend(['--diag-tier-ram', '0'])
            config.setdefault('env', {}).update(
                BASALT_TEST_BUFFERED_PACK=command[command.index('--model') + 1],
                LD_PRELOAD=str(work / 'deepseek_buffered_io_test.so'),
            )
        config['host_memory_policy']['pressure_avg10_limit'] = 100
        case = scratch / 'bench' / f'deepseek-warm-240-{mode}-{quant.lower()}'
        config.update(
            cwd=str(work / 'basalt-latest'), depth=8192, generate=16384,
            steady_decode_seconds=240, timeout=1800, output=str(case),
        )
        chat = copy.deepcopy(config)
        chat.pop('steady_decode_seconds')
        encode, _ = chat_codec(config['deepseek_storage_evidence']['expert_files'][0]['path'])
        eos = GGUFFile(config['deepseek_storage_evidence']['expert_files'][0]['path']).metadata.get('tokenizer.ggml.eos_token_id')
        if eos is not None:
            chat['command'][chat['command'].index('--eos-ids') + 1] = str(eos)
        ids = encode([{'role':'user', 'content': 'Count from 1 to 1000 in order as numerals separated by commas. Start immediately, without commentary.'}])
        prompt_file = work / 'deepseek-warm-count-prompt.json'
        prompt_file.write_text(json.dumps(ids))
        chat_case = case.with_name(case.name+'-chat')
        chat.update(chat_turns=True, prompt_file=str(prompt_file), depth=len(ids),
                    generate=1000, timed_tail=500, allow_reused=True)
        print(f'START chat {mode} IQ2_{quant}', flush=True)
        _, chat_result = run(chat, chat_case)
        summary[f'chat-{mode}-{quant}'] = {
            key:chat_result.get(key) for key in ('status','error','chat_turns','chat_plateau',
                                                 'prefill_tok_s','tail_decode_tok_s','reused_tokens')
        }
        record()
        print(f'START four-minute {mode} IQ2_{quant}', flush=True)
        completed, result = run(config, case)
        log_path = case / 'engine.log'
        log = log_path.read_text() if log_path.exists() else ''
        keys = ('status', 'error', 'finish', 'ttft_s', 'decode_observed_s',
                'decode_windows_tok_s', 'generated', 'storage_io_counters', 'model_fds')
        summary[f'{mode}-{quant}'] = {
            **{key: result.get(key) for key in keys},
            'case': str(case), 'engine_exit': completed.returncode,
            'engine_storage': [line for line in log.splitlines() if any(
                marker in line for marker in ('RAM expert tier', 'expert homes', 'file cache', 'O_DIRECT')
            )],
        }
        record()
        print(json.dumps(summary[f'{mode}-{quant}']), flush=True)

# Only the best low-context setting for each quant gets the expensive 90% test.
fixtures = json.loads((scratch / 'outputs' / 'range-percent-workloads.json').read_text())
prose = next(row for row in fixtures['cases'] if row['family']=='deepseek' and row['workload']=='chat90')
for quant in ('XXS','XS'):
    eligible = [
        (summary[f'chat-{mode}-{quant}']['tail_decode_tok_s'], mode)
        for mode in ('paging','fixed')
        if summary[f'chat-{mode}-{quant}']['status']=='ok'
        and summary[f'chat-{mode}-{quant}']['tail_decode_tok_s'] is not None
    ]
    if not eligible:
        print(f'SKIP final IQ2_{quant}: no qualified short result', flush=True)
        continue
    _, mode = max(eligible)
    path = work / f'deepseek-warm-240-{mode}-{quant.lower()}.json'
    config = json.loads(path.read_text())
    del config['steady_decode_seconds']
    config.update(prompt_file=prose['prompt_file'], depth=prose['depth'], generate=512,
                  timed_tail=256, timeout=7200, workload='chat90')
    case = scratch / 'bench' / f'deepseek-final-chat90-{quant.lower()}'
    print(f'START final 90% {mode} IQ2_{quant}', flush=True)
    _, result = run(config, case)
    summary[f'final-chat90-{quant}'] = {
        **{key: result.get(key) for key in (
            'status','error','prefill_tok_s','decode_tok_s','ttft_s','reused_tokens','generated'
        )}, 'case':str(case), 'selected_mode':mode,
    }
    record()
