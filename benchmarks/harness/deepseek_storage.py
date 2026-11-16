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
        evidence['strata_tensor_files']=actual
    c['deepseek_storage_evidence']=evidence
    return c
