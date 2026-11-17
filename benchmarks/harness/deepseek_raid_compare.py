"""Compare the system NVMe with the striped NVMe array using the same XXS pack."""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

work = Path(__file__).resolve().parent
scratch = work.parent
sys.path.insert(0, str(work / 'basalt-latest' / 'tools'))
from model_file import ModelFile
from deepseek_chat_turns import chat_codec

reference = json.loads((work / 'deepseek-warm-240-fixed-xxs.json').read_text())
encoder, _ = chat_codec(reference['deepseek_storage_evidence']['expert_files'][0]['path'])
short_ids = encoder([{'role':'user','content':
    'Write a long original story about a ferry captain who finds a sealed letter in an abandoned lighthouse. '
    'Begin in the middle of a storm. Keep developing scenes, characters and dialogue without wrapping up early.'}])
prompt = work / 'deepseek-raid-smoke-prompt.json'
prompt.write_text(json.dumps(short_ids)+'\n')
reference.update(depth=len(short_ids), prompt_file=str(prompt), workload='short-story-storage-smoke')
args = reference['command']
model_index = args.index('--model') + 1
source = Path(args[model_index])
engram = Path(args[args.index('--deepseek-engram-gguf') + 1])
target = scratch / 'packs' / 'deepseek-gsq-rco-iq2xxs-external-engram-raid-baseline.basalt'
pack = ModelFile(str(source))
skip, length = pack.section('engram')
size = source.stat().st_size
assert source.stat().st_dev != target.parent.stat().st_dev
assert engram.is_file() and engram.stat().st_dev == target.parent.stat().st_dev
assert all(name == 'engram' or off + count <= skip or off >= skip + length
           for name in pack.names() for off, count in [pack.section(name)])
assert shutil.disk_usage(target.parent).free > size - length + 8 * 2**30

def active_hash(handle, begin, end, out=None):
    digest = hashlib.sha256()
    handle.seek(begin)
    if out is not None:
        out.seek(begin)
    remaining = end - begin
    while remaining:
        data = handle.read(min(16 * 2**20, remaining))
        if not data:
            raise OSError('Unexpected EOF while staging the RAID pack')
        if out is not None:
            out.write(data)
        digest.update(data)
        remaining -= len(data)
    return digest.hexdigest()

ranges = ((0,skip),(skip+length,size))
pending = target.with_suffix('.partial')
if target.exists() or pending.exists():
    raise FileExistsError('Previous scratch RAID pack exists; keep existing evidence')
print('STAGING RAID pack with sparse unused Engram', flush=True)
with source.open('rb') as src, pending.open('xb') as dst:
    hashes = [active_hash(src,begin,end,dst) for begin,end in ranges]
    dst.truncate(size)
    dst.flush()
    os.fsync(dst.fileno())
with pending.open('rb') as dst:
    assert [active_hash(dst,begin,end) for begin,end in ranges] == hashes
    os.posix_fadvise(dst.fileno(),0,0,os.POSIX_FADV_DONTNEED)
with source.open('rb') as src:
    os.posix_fadvise(src.fileno(),0,0,os.POSIX_FADV_DONTNEED)
pending.replace(target)
assert target.stat().st_blocks * 512 < size - length + 2**30

summary = {'evidence': {'logical_size':size,'ondisk_bytes':target.stat().st_blocks*512,
                        'unused_embedded_engram_hole':[skip,length], 'hashed_ranges':ranges,
                        'matching_sha256s':hashes, 'shared_engram':str(engram)}}
report = scratch / 'outputs' / 'deepseek-raid-comparison.json'
order = [('A1-system-nvme',source),('B1-raid0',target),('B2-raid0',target),('A2-system-nvme',source)]
summary['evidence']['order'] = [name for name,_ in order]
summary['evidence']['initial_prompt_tokens'] = len(short_ids)
for label, model in order:
    config = copy.deepcopy(reference)
    config['command'][model_index] = str(model)
    case = scratch / 'bench' / f'deepseek-four-minute-storage-{label}'
    config['output'] = str(case)
    path = work / f'{case.name}.json'
    path.write_text(json.dumps(config,indent=2)+'\n')
    case.mkdir(parents=True,exist_ok=True)
    print('START',label,flush=True)
    with (case/'harness.log').open('w') as log:
        subprocess.run([sys.executable,str(work/'native_warm_240.py'),'--config',str(path)],
                       stdout=log,stderr=subprocess.STDOUT,check=False)
    result_path = case/'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else {
        'status':'failed','error':(case/'harness.log').read_text()[-1000:],
    }
    summary[label] = {k:result.get(k) for k in (
        'status','error','ttft_s','load_s','decode_windows_tok_s','storage_io_counters','generated','model_fds'
    )}
    summary[label].update(case=str(case),path=str(model))
    temp = report.with_suffix('.tmp')
    temp.write_text(json.dumps(summary,indent=2)+'\n')
    temp.replace(report)
    print(label,summary[label],flush=True)

from statistics import mean
comparison = {}
for arm, group in [('system-nvme',('A1-system-nvme','A2-system-nvme')),
                   ('raid0',('B1-raid0','B2-raid0'))]:
    rows = [summary[label] for label in group]
    if all(row['status']=='ok' for row in rows):
        comparison[arm] = {
            'mean_load_s':mean(row['load_s'] for row in rows),
            'mean_ttft_s':mean(row['ttft_s'] for row in rows),
            'mean_decode_180_to_240_tok_s':mean(row['decode_windows_tok_s']['180-240'] for row in rows),
        }
summary['ABBA_comparison'] = comparison
temp = report.with_suffix('.tmp')
temp.write_text(json.dumps(summary,indent=2)+'\n')
temp.replace(report)
print('ABBA comparison',comparison,flush=True)
