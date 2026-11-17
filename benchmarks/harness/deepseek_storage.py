"""Explicit shared storage contract for the matched DeepSeek benchmark stages."""
from pathlib import Path
import copy, hashlib, json
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs'
DESKTOP=Path('/home/user/Desktop')
MEDIA=Path('/mnt/media/AI/Models/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF')
ENGRAM=MEDIA/'DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf'
RUNTIME=R/'runtimes/basalt-deepseek-split'

def internal_artifact(quant='XXS'):
    assert quant in ('XXS','XS')
    root=DESKTOP/'DeepSeek-benchmark-scratch'/'packs';root.mkdir(parents=True,exist_ok=True)
    return root/('deepseek-gsq-rco-iq2'+quant.lower()+'.basalt')

def raw_storage_evidence(quant='XXS'):
    assert quant in ('XXS','XS')
    root=DESKTOP/('DeepSeek-IQ2_'+quant)
    files=sorted(root.glob('*IQ2_'+quant+'-*.gguf'))
    assert len(files)==4, 'All four verified shards must be present before DeepSeek benchmarking'
    device=DESKTOP.stat().st_dev
    move=json.loads((O/'deepseek-internal-move-status.json').read_text())
    assert move['status']=='complete'
    expected={Path(x['resolved']).name:x for x in move['files']}
    records=[]
    for path in files:
        assert path.resolve().stat().st_dev==device, 'Expert weights are not on the system SSD'
        if quant=='XXS':
            proof=expected[path.name];assert path.stat().st_size==proof['bytes'];sha=proof['sha256']
        else:
            proof=json.loads(path.with_name(path.name+'.download-receipt.json').read_text())
            plan=json.loads((O/'iq2-xs-download-plan.json').read_text())
            expected=next(x for x in plan['files'] if x['path']==path.name)
            assert proof['revision']==plan['revision'] and proof['sha256']==expected['lfs']['oid']
            assert path.stat().st_size==proof['bytes']==expected['size'];sha=proof['sha256']
        records.append(dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha,device=device))
    assert not ENGRAM.is_symlink() and ENGRAM.stat().st_dev!=device, 'Shared Engram must stay on the other drive'
    draft=DESKTOP/'DeepSeek-shared/support/dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf'
    assert draft.stat().st_dev==device
    return dict(quantization='IQ2_'+quant,expert_storage='internal-system-NVMe',expert_files=records,
                shared_engram=str(ENGRAM),shared_engram_device=ENGRAM.stat().st_dev,
                draft=str(draft),internal_device=device,layout='Experts and draft on system SSD; shared Engram on media')

def storage_config(config,quant='XXS',basalt=False):
    c=copy.deepcopy(config);evidence=raw_storage_evidence(quant)
    def option(flag,value):
        args=c['command']
        if flag in args:args[args.index(flag)+1]=str(value)
        else:args.extend([flag,str(value)])
    if basalt:
        receipt=json.loads((O/'basalt-split-engram-build.json').read_text())
        assert receipt['status']=='built-cpu-validated-gpu-parity-pending' or receipt['status']=='gpu-parity-passed'
        binary=RUNTIME/'bin/basalt'
        with binary.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==receipt['binary_sha256']
        artifact=internal_artifact(quant)
        assert artifact.is_file() and artifact.stat().st_dev==DESKTOP.stat().st_dev
        c['command'][3]=str(binary);option('--model',artifact);option('--deepseek-engram-gguf',ENGRAM)
        evidence['converted_pack']=str(artifact);evidence['engram_routing']='Native --deepseek-engram-gguf; embedded copy unused'
    else:
        args=c['command'];pack=Path(args[args.index('--pack')+1])
        lines=(pack/'ds4.txt').read_text().splitlines();model_dir=Path(next(x.split(' ',1)[1] for x in lines if x.startswith('model_dir ')))
        actual=[]
        for line in (pack/'tensors.txt').read_text().splitlines():
            if not line.startswith('file '):continue
            path=(model_dir/line.split(' ',2)[2]).resolve();actual.append(str(path))
            if 'engram' in path.name.lower():assert path==ENGRAM
            else:assert path.stat().st_dev==DESKTOP.stat().st_dev, 'Strata tensor source escaped the system SSD'
        expected=[row['path'] for row in evidence['expert_files']]+[evidence['shared_engram'],evidence['draft']]
        assert actual==expected, 'Strata tensor index did not select the exact requested shards, shared Engram and DSpark draft'
        evidence['strata_tensor_files']=actual
    c['deepseek_storage_evidence']=evidence
    return c

def xs_pack_command(python,output):
    """Keep the same legacy Engram interpretation and DSpark constants as XXS."""
    source=DESKTOP/'DeepSeek-IQ2_XS'
    meta=R/'strata-deepseek/data/models/deepseek-v4.1-flash-shared/DeepSeek-V4.1-Flash-1017-UD-Q8_K_XL-00001-of-00009.gguf'
    assert meta.is_file(), 'Required shared Engram metadata header is missing'
    shards=sorted(source.glob('*IQ2_XS-*.gguf'));assert len(shards)==4
    draft=DESKTOP/'DeepSeek-shared/support/dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf'
    return ['taskset','-c','22',str(python),str(R/'work/dsh-strata/vendor/gyro-l-control/tools/dsv41/pack_gguf.py'),
            '--model',str(source),'--shards',*[x.name for x in shards],
            '--engram',str(ENGRAM),'--engram-meta',str(meta),'--dspark-gguf',str(draft),
            '--dspark-noise-token','128799','--dspark-markov-rank','256','--out',str(output)]

def validate_xs_pack(pack):
    """Validate actual token/hash data, not just matching metadata field names."""
    import sys
    sys.path.insert(0,str(R/'work/basalt-latest/tools'))
    from gguf_reader import GGUFFile
    pack=Path(pack);old=R/'strata-deepseek/data/packs/deepseek-v4.1-flash-ist-das-2.00bpw'
    hashes={}
    for name in ['engram.bin','tokenizer/vocab.json','tokenizer/merges.txt','tokenizer/token_type.json','tokenizer/tokenizer.json','tokenizer/chat_template.jinja']:
        a=(old/name).read_bytes();b=(pack/name).read_bytes();assert a==b,'XS changes shared model metadata: '+name
        hashes[name]=hashlib.sha256(a).hexdigest()
    def geometry(folder):
        return '\n'.join(x for x in(folder/'ds4.txt').read_text().splitlines()if not x.startswith('model_dir '))
    assert geometry(old)==geometry(pack),'XS model geometry/DSpark constants differ from XXS'
    wanted={'engram_'+name+'.weight'for name in ['token_map','primes','offsets','multipliers']}
    raw=[]
    for quant in ['XXS','XS']:
        values={}
        for path in sorted((DESKTOP/('DeepSeek-IQ2_'+quant)).glob('*IQ2_'+quant+'-*.gguf')):
            g=GGUFFile(path)
            with path.open('rb')as f:
                for tensor in g.tensors:
                    if tensor.name not in wanted:continue
                    assert tensor.type_id in (26,27)and tensor.name not in values
                    size=tensor.expected_bytes();assert size and size<4*2**20
                    f.seek(g.data_start+tensor.offset);data=f.read(size);assert len(data)==size
                    values[tensor.name]=data
        assert set(values)==wanted,'Missing source Engram integer tensors'
        raw.append(values)
    assert raw[0]==raw[1],'XS changes source Engram hash data'
    config={'command':['taskset','-c','0-21','unused','--pack',str(pack)]}
    record=dict(status='passed',scope='Metadata-only; no XS inference. Exact shared tokenizer, geometry, Engram lookup bytes and original integer tensor payloads; indexed files on required drives.',files_sha256=hashes,source_integer_tensors_sha256={name:hashlib.sha256(data).hexdigest()for name,data in raw[0].items()},storage=storage_config(config,'XS')['deepseek_storage_evidence'])
    (O/'deepseek-xs-metadata-preflight.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
