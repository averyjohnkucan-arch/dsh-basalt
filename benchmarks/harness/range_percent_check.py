"""Verify saved and tuned controls at the original exact context percentages."""
import argparse
import json
import sys

from benchmark_environment import current_environment
from range_common import O, R, read, run, name
from range_identity import config_id

# One saved baseline can serve several tuned engines for the same model/KV.
QWEN_FAMILIES = [
    ('flash_basalt', 'flash', 'qwen'), ('flash_strata', 'flash', 'qwen'),
    ('hybrid_basalt', 'hybrid', 'qwen'), ('hybrid_strata', 'hybrid', 'qwen'),
    ('flash_fp16_basalt', 'flash_fp16', 'qwen'), ('flash_fp16_strata', 'flash_fp16', 'qwen'),
    ('hybrid_fp16_basalt', 'hybrid_fp16', 'qwen'), ('hybrid_fp16_strata', 'hybrid_fp16', 'qwen'),
    ('gyro_strata', 'gyro_strata', 'qwen'),
    ('27b_basalt', '27b_ninfer', 'qwen27b'), ('27b_ninfer', '27b_ninfer', 'qwen27b'),
    ('huihui_nvfp4_ninfer', 'huihui_nvfp4_ninfer', 'qwen27b'),
    ('huihui_int8_ninfer', 'huihui_int8_ninfer', 'qwen27b'),
    ('huihui_fp8_ninfer', 'huihui_fp8_ninfer', 'qwen27b'),
]
STAGES = {
    'qwen': QWEN_FAMILIES,
    'xxs': [(key, 'deepseek_basalt', 'deepseek') for key in ('deepseek_basalt', 'deepseek_strata')],
    'xs': [(key, 'deepseek_xs_basalt', 'deepseek') for key in ('deepseek_xs_basalt', 'deepseek_xs_strata')],
}


def make_plan(stage):
    environment = current_environment()
    environment_id = environment['id'] if environment else 'legacy'
    selections = read(O / 'range-selections.json')
    fixtures = read(O / 'range-percent-workloads.json')['cases']
    jobs = {}
    for key, baseline, family in STAGES[stage]:
        marker = read(O / 'performance-qualified' / (key + '.json'))
        assert marker['performance_qualified'] and marker['benchmark_environment_id'] == environment_id
        old_case = selections[baseline + '_old_metrics']['low']['case']
        base = read(R / 'bench' / old_case / 'result.json')
        assert base['status'] == 'ok' and base['config'].get('benchmark_environment_id', 'legacy') == environment_id
        for kind, workload in [('short', 'code10'), ('long', 'chat90')]:
            fixture = next(f for f in fixtures if f['family'] == family and f['workload'] == workload)
            selected = marker[kind + '_selection']
            assert selected == selections[key + '_' + kind]['selected']
            result = read(R / 'bench' / selected / 'result.json')
            assert result['status'] == 'ok' and config_id(result['config']) == marker[kind + '_identity']
            for label, source, config in [('old-' + baseline, old_case, base['config']), ('tuned-' + key, selected, result['config'])]:
                args = config['command']
                assert int(args[args.index('--max-context') + 1]) == fixture['capacity']
                case = 'percent-' + label + '-' + workload
                jobs[case] = dict(config=config, source=source, fixture=fixture, label=label)
    return environment_id, jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=STAGES)
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    environment_id, jobs = make_plan(args.stage)
    if args.plan:
        print(json.dumps({'stage': args.stage, 'benchmark_environment_id': environment_id,
                          'cases': {job: value['source'] for job, value in jobs.items()}}, indent=2))
        return
    path = O / ('range-exact-percent-' + args.stage + '.json')
    state = dict(stage=args.stage, status='running', benchmark_environment_id=environment_id, cases=[])
    try:
        for job, item in jobs.items():
            f = item['fixture']
            result = run(item['config'], job, f['family'], f['workload'], fixture=f,
                         role='Exact context percentage confirmation for saved/selected controls')
            assert result['status'] == 'ok', f'{job}: {result.get("error")}'
            case = name(result)
            prompt = read(R / 'bench' / case / 'prompt.json')
            assert prompt['sha256'] == f['token_sha256'] and result['prompt_tokens'] == f['depth']
            assert result['generated'] == 8192 and result['prefill_tok_s'] > 0 and result['tail_decode_tok_s'] > 0
            assert not result.get('reused_tokens') and result.get('cold_prefill_qualified', True)
            state['cases'].append(dict(case=case, label=item['label'], source=item['source'],
                                       prompt_sha256=prompt['sha256'], percent=f['percent'],
                                       prefill=result['prefill_tok_s'], decode=result['tail_decode_tok_s']))
            path.write_text(json.dumps(state, indent=2) + '\n')
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=str(error))
        raise
    finally:
        path.write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    main()
