"""Move only our partial XS download to main NVMe, then resume checksum streaming."""
from pathlib import Path
import hashlib,json,os,time,runpy
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';plan=json.loads((O/'iq2-xs-download-plan.json').read_text());media=Path(plan['media_links_directory']);dest=Path(plan['destination']);dest.mkdir(parents=True,exist_ok=True);hashes={}
def paced_read_hash(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  while block:=f.read(1024*1024):
   t=time.monotonic();h.update(block);time.sleep(max(0,len(block)/(20*2**20)-(time.monotonic()-t)))
 return h
for entry in plan['files']:
 name=entry['path'];old=media/name;new=dest/name
 if 'IQ2_XS-'in name:
  previous=media/(name+'.part');partial=dest/(name+'.part');moving=dest/(name+'.part.migrating')
  if previous.is_file()and not previous.is_symlink()and not partial.exists():
   offset=moving.stat().st_size if moving.exists()else 0;assert offset<=previous.stat().st_size
   h=paced_read_hash(moving)if offset else hashlib.sha256()
   with previous.open('rb')as src,moving.open('ab')as dst:
    src.seek(offset)
    while block:=src.read(1024*1024):
     t=time.monotonic();dst.write(block);h.update(block);offset+=len(block)
     state=dict(status='moving-to-main-nvme',current_file=name,current_bytes=offset,migration_bytes=previous.stat().st_size,destination=str(dest),updated_unix=time.time())
     if offset%(32*2**20)==0:
      temp=O/'iq2-xs-download-status.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(O/'iq2-xs-download-status.json')
     time.sleep(max(0,len(block)/(20*2**20)-(time.monotonic()-t)))
    dst.flush();os.fsync(dst.fileno())
   assert offset==previous.stat().st_size
   moving.replace(partial);hashes[name]=h;previous.unlink()
  if old.is_symlink():assert old.resolve()==new.resolve()
  else:assert not old.exists();old.symlink_to(new)
 else:
  # Shared Engram stays on media; verify the existing published checksum receipt.
  assert old.stat().st_size==entry['size']and old.with_name(name+'.done').read_text().strip()=='sha256 '+entry['lfs']['oid']
  if not new.is_symlink():assert not new.exists();new.symlink_to(old)
  done=dest/(name+'.done')
  if not done.is_symlink():assert not done.exists();done.symlink_to(media/(name+'.done'))
runpy.run_path(str(R/'work/download_iq2_xs.py'),init_globals={'RESUME_HASHERS':hashes})
