"""Sample the actual packed text weights against the source NInfer artifact."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

R = Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
TOOLS = R / 'work/basalt-latest/tools'
sys.path[:0] = [str(TOOLS / 'convert'), str(TOOLS)]
from model_file import ModelFile
from ninfer_qwen35 import Plan, Source, TYPE

SOURCE = Path('/mnt/media/AI/Models/Qwen3.8-27B/DSH-import/ninfer/qwen3.8-27b-nvfp4full/qwen3_8_27b_nvfp4full.ninfer')
PACK = R / 'packs/qwen27b-nvfp4full-experimental.basalt'


def packed_scale_offset(row, group, columns):
    tile = (row // 128) * (columns // 64) + group // 4
    return tile * 512 + (row % 32) * 16 + ((row // 32) % 4) * 4 + group % 4


def audit():
    model = ModelFile(str(PACK))
    meta_bytes = model.read('meta')
    meta = json.loads(meta_bytes)
    tensors = meta['tensors']
    gguf, gguf_bytes = model.section('gguf')
    assert meta['sources'] == [{'path': SOURCE.name, 'size': SOURCE.stat().st_size}]
    assert meta['arch'] == 'qwen35' and meta['dflash']['block_size'] == 8
    assert set(meta['required_engine_features']) == {'qwen35-bf16-projections', 'qwen35-nvfp4-dflash2'}
    source = Source(SOURCE)
    samples = Counter()
    try:
        plan = Plan(source)
        with PACK.open('rb') as file:
            def read_tensor(name, off, size):
                tensor = tensors[name]
                assert 0 <= off <= off + size <= tensor['bytes']
                file.seek(gguf + tensor['offset'] + off)
                data = file.read(size)
                assert len(data) == size
                return data

            expected_names = set()
            for spec in plan.specs:
                name, form = spec['name'], spec['form']
                expected_names.add(name)
                tensor = tensors[name]
                assert (tensor['type_id'], tensor['shape'], tensor['bytes']) == (TYPE[form], spec['shape'], spec['size'])
                assert tensor['offset'] + tensor['bytes'] <= gguf_bytes
                if form == 'NVFP4_PLANES':
                    scale = name.removesuffix('.weight') + '.scale'
                    expected_names.add(scale)
                    assert tensors[scale]['type_id'] == TYPE['F32'] and tensors[scale]['bytes'] == 4
                    assert read_tensor(scale, 0, 4) == plan.multiplier(spec)
                if spec['how'] != 'id':
                    continue
                obj, begin, end = source.binding(spec['roles'][0])
                cols = obj['shape'][1]
                first_row = begin // cols
                rows = (end - begin) // cols
                for row in (0, rows // 2, rows - 1):
                    if form == 'BF16':
                        off = row * cols * 2
                        assert read_tensor(name, off, 64) == source.read(obj, begin * 2 + off, 64), name
                    else:
                        off = row * cols // 2
                        assert read_tensor(name, off, 64) == source.read(obj, begin // 2 + off, 64), name
                        source_scales = (obj['shape'][0] * cols // 2 + 255) // 256 * 256
                        group = cols // 32
                        source_off = source_scales + packed_scale_offset(first_row + row, group, cols)
                        target_off = rows * cols // 2 + packed_scale_offset(row, group, cols)
                        assert read_tensor(name, target_off, 1) == source.read(obj, source_off, 1), name
                    samples[('DFlash2 ' if name.startswith('dflash.') else 'target ') + form] += 1

            head, begin, end = source.binding('text/output_head')
            rows, cols = head['shape']
            assert begin == 0 and end == rows * cols
            scale_offset = (rows * cols + 255) // 256 * 256
            for block in (0, end // 64, end // 32 - 1):
                original = source.read(head, scale_offset + 2 * block, 2) + source.read(head, 32 * block, 32)
                assert read_tensor('output.weight', 34 * block, 34) == original
                samples['target Q8 head'] += 1
            assert set(tensors) == expected_names
            file.seek(0)
            header = file.read(65536)
    finally:
        source.close()
    results = R / 'bench/latest-27b-basalt-dflash-probe/result.json'
    cold = json.loads(results.read_text())
    assert cold['status'] == 'ok' and cold['generated'] == 256
    assert cold['config']['command'][cold['config']['command'].index('--model') + 1] == str(PACK)
    done = cold['done_raw'].split()
    accepted, offered = map(int, done[6:8])
    assert 0 < accepted <= offered
    return dict(status='passed', artifact=str(PACK), source=str(SOURCE),
                metadata_sha256=sha256(meta_bytes).hexdigest(), header_sha256=sha256(header).hexdigest(),
                tensor_count=len(tensors), checked_samples=samples,
                previous_gpu_probe=dict(path=str(results), prompt_tokens=cold['prompt_tokens'],
                                        generated=cold['generated'], drafts_accepted=accepted, drafts_offered=offered),
                scope='Actual pack metadata and sampled unpermuted target/drafter weight bytes; numerical transform tests are separate. Historical GPU smoke is compatibility evidence. Full benchmark timing and generated-code grading are separate.',
                kv_support=['INT8', 'FP16'], excluded=['Vision', 'Source MTP', 'NVFP4 KV'])


if __name__ == '__main__':
    record = audit()
    (R / 'outputs/27b-basalt-pack-verification.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
