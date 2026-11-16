"""Pinned, resumable IQ2_XS download with checksums and benchmark disk headroom."""
from pathlib import Path
import hashlib,json,os,shutil,time,urllib.request,http.client
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';plan=json.loads((O/'iq2-xs-download-plan.json').read_text());dest=Path(plan['destination']);dest.mkdir(parents=True,exist_ok=True)
status_path=O/'iq2-xs-download-status.json';state=dict(status='starting',repository=plan['repository'],revision=plan['revision'],destination=str(dest),files=[],rate_limit_mib_s=plan['rate_limit_mib_s'],minimum_free_gib=plan['minimum_free_gib']);last_write=0

def save(status,**values):
 global last_write
 state.update(status=status,updated_unix=time.time(),**values);temp=status_path.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(status_path);last_write=time.monotonic()

def hold_reason():
 # After the original matrix finishes, reserve the space for XXS conversion
 # and inference. Final XS work explicitly releases this hold after rotation.
 p=O/'matrix-completion.json'
 if plan.get('hold_during_original_deepseek',True)and p.exists()and json.loads(p.read_text()).get('status')=='complete'and not(O/'iq2-xs-final-stage-ready.json').exists():return 'original DeepSeek conversion/inference owns the disk headroom'
 if shutil.disk_usage(dest).free<plan['minimum_free_gib']*2**30:return 'waiting for scratch rotation; preserving benchmark disk headroom'
 return None

def wait_for_space():
 while True:
  reason=hold_reason()
  if not reason:return
  save('waiting-for-space',reason=reason);time.sleep(10)

def validate_resume_response(response,offset):
 if offset:assert response.status==206 and response.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-'),'Server did not honor resume range'

for entry in plan['files']:
 name=entry['path'];expected=entry['size'];sha=entry['lfs']['oid'];target=dest/name;partial=dest/(name+'.part');receipt=dest/(name+'.download-receipt.json')
 if target.exists():
  assert target.stat().st_size==expected,'Existing file has wrong size: '+name
  legacy=target.with_name(target.name+'.done')
  verified=(receipt.exists()and json.loads(receipt.read_text()).get('sha256')==sha)or(legacy.exists()and legacy.stat().st_mtime>=target.stat().st_mtime and legacy.read_text().strip()=='sha256 '+sha)
  assert verified,'Existing file needs independent checksum verification: '+name
  state['files'].append(dict(name=name,status='reused-verified-checksum-receipt',bytes=expected,sha256=sha));save('downloading');continue
 resumed_hash=globals().get('RESUME_HASHERS',{}).get(name)
 hasher=resumed_hash if resumed_hash is not None else hashlib.sha256();offset=partial.stat().st_size if partial.exists()else 0;assert offset<=expected
 if offset and resumed_hash is None:
  with partial.open('rb')as f:
   while block:=f.read(1024*1024):
    begin=time.monotonic();hasher.update(block);time.sleep(max(0,len(block)/(plan['rate_limit_mib_s']*2**20)-(time.monotonic()-begin)))
 save('downloading',current_file=name,current_bytes=offset,current_size=expected,reason=None)
 failures=0
 while offset<expected:
  wait_for_space()
  url='https://huggingface.co/'+plan['repository']+'/resolve/'+plan['revision']+'/'+name+'?download=true'
  headers={'User-Agent':'dsh-nvme-model-download/1.0'}
  if offset:headers['Range']='bytes='+str(offset)+'-'
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60)as response:
    validate_resume_response(response,offset)
    with partial.open('ab')as f:
     while offset<expected:
      # Close the connection before a long storage hold; resume by exact range.
      reason=hold_reason()
      if reason:break
      begin=time.monotonic();block=response.read(min(1024*1024,expected-offset))
      if not block:break
      f.write(block);hasher.update(block);offset+=len(block)
      if time.monotonic()-last_write>=5:save('downloading',current_bytes=offset,reason=None)
      time.sleep(max(0,len(block)/(plan['rate_limit_mib_s']*2**20)-(time.monotonic()-begin)))
     f.flush();os.fsync(f.fileno())
   if offset<expected and not hold_reason():
    failures+=1;save('retrying',current_bytes=offset,reason='Connection ended before expected length');time.sleep(min(60,5*failures))
  except (OSError,AssertionError,http.client.HTTPException)as error:
   failures+=1;save('retrying',current_bytes=offset,reason=str(error));time.sleep(min(60,5*failures))
 assert hasher.hexdigest()==sha,'SHA256 mismatch: '+name
 partial.replace(target);receipt.write_text(json.dumps(dict(repository=plan['repository'],revision=plan['revision'],name=name,bytes=expected,sha256=sha,verified_unix=time.time()),indent=2)+'\n');state['files'].append(dict(name=name,status='downloaded-sha256-verified',bytes=expected,sha256=sha));save('downloading',current_bytes=expected)
save('complete',current_file=None,current_bytes=None,reason=None)
