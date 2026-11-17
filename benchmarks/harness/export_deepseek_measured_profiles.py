"""Export the measured Basalt names with their exact native benchmark controls."""
import json
from pathlib import Path

work = Path(__file__).resolve().parent
scratch = work.parent
result = json.loads((scratch/'outputs/deepseek-warm-240.json').read_text())
export = scratch/'outputs/deepseek-measured-profiles'
export.mkdir(exist_ok=True)
for quant in ('XXS','XS'):
    short = result[f'chat-fixed-{quant}']
    long = result[f'final-chat90-{quant}']
    assert short['status'] == long['status'] == 'ok'
    name = (f'DeepSeek V4.1 Flash 1017 IQ2_{quant} '
            f'p{short["prefill_tok_s"]:.0f}/d{short["tail_decode_tok_s"]:.0f} '
            f'p{long["prefill_tok_s"]:.0f}/d{long["decode_tok_s"]:.0f}')
    low_cfg = json.loads((work/f'deepseek-warm-240-fixed-{quant.lower()}-chat.json').read_text())
    high_cfg = json.loads((work/f'deepseek-final-chat90-{quant.lower()}.json').read_text())
    profile = {
        'name':name,'model':{'name':name,'quantization':'IQ2_'+quant,
            'path':high_cfg['command'][high_cfg['command'].index('--model')+1]},
        'engine':'Basalt custom split-Engram', 'scope':'Exact native scratch benchmark profile',
        'command':high_cfg['command'],'context':1048576,
        'metrics': {
            'low':{'workload':'warm counting, final 500 of 1000 output tokens',
                   'input_tokens':low_cfg['depth'],'prefill_tok_s':short['prefill_tok_s'],
                   'decode_tok_s':short['tail_decode_tok_s']},
            'high':{'workload':'native chat prose at 90% context, 512 output tokens',
                    'input_tokens':high_cfg['depth'],'prefill_tok_s':long['prefill_tok_s'],
                    'decode_tok_s':long['decode_tok_s']},
        },
        'benchmark_configs':{'low':str(work/f'deepseek-warm-240-fixed-{quant.lower()}-chat.json'),
                             'high':str(work/f'deepseek-final-chat90-{quant.lower()}.json')},
    }
    (export/f'deepseek-iq2-{quant.lower()}.json').write_text(json.dumps(profile,indent=2)+'\n')
    print(name)
