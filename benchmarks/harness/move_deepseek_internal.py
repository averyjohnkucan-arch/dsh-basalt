"""Resume-safe, checksum-verified relocation of the authorized DeepSeek weights."""
from pathlib import Path
import hashlib, json, os, shutil, time

R = Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
O = R / 'outputs'
MEDIA = Path('/mnt/media/AI/Models/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF')
DESKTOP = Path('/home/user/Desktop')
STATUS = O / 'deepseek-internal-move-status.json'

def save(value):
    value['updated_unix'] = time.time()
    temp = STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(STATUS)

def sha_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def relocate(source, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert destination.parent.stat().st_dev == DESKTOP.stat().st_dev
    source_size = source.stat().st_size
    receipt = destination.with_name(destination.name + '.internal-move.json')
    if destination.exists():
        assert destination.stat().st_size == source_size
        if not receipt.exists() or json.loads(receipt.read_text()).get('sha256') != expected:
            assert sha_file(destination) == expected, 'Destination checksum mismatch'
    else:
        assert not source.is_symlink(), 'Unexpected missing target for relocated source'
        partial = destination.with_name(destination.name + '.moving')
        offset = partial.stat().st_size if partial.exists() else 0
        assert offset <= source_size
        assert shutil.disk_usage(destination.parent).free > source_size - offset + 100 * 2**30
        digest = hashlib.sha256()
        if offset:
            with partial.open('rb') as f:
                while chunk := f.read(8 * 2**20):
                    digest.update(chunk)
        with source.open('rb') as src, partial.open('ab') as dst:
            src.seek(offset)
            last = 0
            while chunk := src.read(8 * 2**20):
                dst.write(chunk)
                digest.update(chunk)
                offset += len(chunk)
                if time.monotonic() - last > 3:
                    state.update(current_file=str(source), current_bytes=offset, current_size=source_size)
                    save(state)
                    last = time.monotonic()
            dst.flush()
            os.fsync(dst.fileno())
        assert offset == source_size and digest.hexdigest() == expected, 'Source/copy checksum mismatch'
        state.update(phase='verifying-destination', current_file=str(destination))
        save(state)
        assert sha_file(partial) == expected, 'Independent destination checksum mismatch'
        shutil.copystat(source, partial)
        partial.replace(destination)
    receipt.write_text(json.dumps(dict(source=str(source), destination=str(destination), bytes=source_size,
                                      sha256=expected, verified_unix=time.time()), indent=2) + '\n')
    destination.with_name(destination.name + '.done').write_text('sha256 ' + expected + '\n')
    # Replacing the source with a symlink is authorized only after verification.
    if source.is_symlink():
        assert source.resolve() == destination.resolve()
    else:
        link = source.with_name(source.name + '.internal-link')
        assert not link.exists() and not link.is_symlink()
        link.symlink_to(destination)
        os.replace(link, source)
    assert source.resolve().stat().st_dev == DESKTOP.stat().st_dev
    return dict(source=str(source), resolved=str(source.resolve()), bytes=source_size, sha256=expected,
                device=source.resolve().stat().st_dev, status='verified-and-relocated')

if __name__ == '__main__':
    files = sorted(MEDIA.glob('*IQ2_XXS-*.gguf'))
    files += sorted((MEDIA / 'support').glob('*.gguf'))
    assert len(files) == 5, 'Expected four XXS shards and draft weights; shared Engram stays on media'
    state = dict(status='running', phase='copying', files=[], started_unix=time.time(),
                 authorization='User requested both DeepSeek quantizations on the internal system SSD')
    save(state)
    try:
        for source in files:
            expected = source.with_name(source.name + '.done').read_text().strip()
            assert expected.startswith('sha256 ') and len(expected.split()[1]) == 64
            root = DESKTOP / ('DeepSeek-IQ2_XXS' if 'IQ2_XXS-' in source.name else 'DeepSeek-shared')
            destination = root / ('support' if source.parent.name == 'support' else '') / source.name
            state.update(phase='copying')
            state['files'].append(relocate(source, destination, expected.split()[1]))
            save(state)
        for folder in ['DeepSeek-IQ2_XXS','DeepSeek-IQ2_XS']:
            root=DESKTOP/folder;root.mkdir(parents=True,exist_ok=True)
            for name,target in [('DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf',MEDIA/'DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf'),('support',DESKTOP/'DeepSeek-shared/support')]:
                link=root/name
                if link.is_symlink():assert link.resolve()==target.resolve()
                else:assert not link.exists();link.symlink_to(target,target_is_directory=target.is_dir())
        # Both quantizations deliberately share the unchanged Engram on the other drive.
        xs = DESKTOP / 'DeepSeek-IQ2_XS' / 'DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf'
        assert xs.resolve() == MEDIA / 'DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf'
        state.update(status='complete', phase='complete', completed_unix=time.time(),
                     internal_device=DESKTOP.stat().st_dev,
                     shared_engram='Unchanged on media by user request; separating its I/O may reduce contention')
        save(state)
    except BaseException as error:
        state.update(status='failed', error=str(error))
        save(state)
        raise
