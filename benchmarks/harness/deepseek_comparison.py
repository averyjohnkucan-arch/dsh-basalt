"""Build same-engine, same-prompt comparison rows for the two DeepSeek quants."""
import json
import statistics


def comparison_rows(root, qualified):
    def read(path):
        return json.loads(path.read_text())

    def evidence(cases, quant):
        prompts, conditions = set(), set()
        for case in cases:
            folder = root / 'bench' / case
            result = read(folder / 'result.json')
            config = result['config']
            storage = config['deepseek_storage_evidence']
            prompt = read(folder / 'prompt.json')
            assert result['status'] == 'ok' and not result.get('reused_tokens')
            assert result['generated'] == 8192 and config['timed_tail'] == 4096
            assert result['prompt_tokens'] == config['depth'] == prompt['tokens']
            assert storage['quantization'] == quant
            assert all(row['device'] == storage['internal_device'] for row in storage['expert_files'])
            assert storage['shared_engram_device'] != storage['internal_device']
            prompts.add(prompt['sha256'])
            conditions.add((config['engine_binary_sha256'], config['benchmark_environment_id'],
                            storage['internal_device'], storage['shared_engram_device'],
                            storage['shared_engram'], storage['draft']))
        assert len(prompts) == len(conditions) == 1
        return prompts.pop(), conditions.pop()

    def summarize(cases, quant):
        proof = evidence(cases, quant)
        results = [read(root / 'bench' / case / 'result.json') for case in cases]
        return proof, (statistics.median(r['prefill_tok_s'] for r in results),
                       statistics.median(r['tail_decode_tok_s'] for r in results))

    def tuned_cases(marker, workload):
        long = marker['long_metrics']
        if workload == '8K code':
            metrics = marker.get('short_metrics') or long
            return [x['case'] for x in metrics.get('low_cases', [metrics['low']])]
        return [x['case'] for x in long['high']['cases'] if x['workload'] == workload]

    for engine in ('basalt', 'strata'):
        xxs_key, xs_key = 'deepseek_' + engine, 'deepseek_xs_' + engine
        xxs, xs = qualified(xxs_key), qualified(xs_key)
        for workload in ('8K code', 'text', 'chat', 'story', '10% code', '90% chat'):
            label = workload if workload not in {'text', 'chat', 'story'} else '80% ' + workload
            row = [engine.title() + ' · ' + label]
            if xxs and xs:
                if workload in {'10% code', '90% chat'}:
                    pct = int(workload.split('%')[0])
                    cases = []
                    for stage, key in [('xxs', xxs_key), ('xs', xs_key)]:
                        path = root / 'outputs' / ('range-exact-percent-' + stage + '.json')
                        rows = read(path)['cases'] if path.exists() else []
                        cases.append([r['case'] for r in rows if r['label'] == 'tuned-' + key and r['percent'] == pct])
                else:
                    cases = [tuned_cases(xxs, workload), tuned_cases(xs, workload)]
                if all(cases):
                    try:
                        left, right = (summarize(c, q) for c, q in zip(cases, ('IQ2_XXS', 'IQ2_XS')))
                        if left[0] != right[0]:
                            yield row + ['Benchmarks differ in prompt, engine, or storage', 'Pair excluded', '']
                            continue
                        (p1, d1), (p2, d2) = left[1], right[1]
                        yield row + [f'{p1:,.1f} / {d1:,.1f}', f'{p2:,.1f} / {d2:,.1f}',
                                     f'Prefill {(p2/p1-1):+.1%} · Decode {(d2/d1-1):+.1%}']
                        continue
                    except (AssertionError, KeyError, OSError, ValueError) as error:
                        yield row + ['Pair evidence incomplete', 'Pair excluded', str(error)]
                        continue
            yield row + ['Pending matched pair', 'Pending matched pair', '']
