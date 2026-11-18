from pathlib import Path
import json,subprocess,time,shutil
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';D=W/'tune1090';dest=Path('/mnt/media/AI/Model Configs/new profiles')
rows=json.loads((O/'tune1090-profile-validation.json').read_text());node=R/'tools/node-v24.11.1-linux-x64/bin/node'
shutil.copy2(dest/'strata-profiles.json',O/'tune1090-strata-state/profiles.json')
for row in rows:
 if row['status']=='ok':continue
 assert row['engine']=='strata'
 unit='dsh-validate1090-'+row['id'];out=Path(row['receipt']);out.unlink(missing_ok=True)
 cmd=['systemd-run','--user','--scope','--quiet','--collect','--unit='+unit,'-p','MemoryMax=110G','-p','MemorySwapMax=1G',str(node),str(W/'tune1090_adapter_smoke.mjs'),'strata',row['id'],str(out.parent)]
 print('START',row['id'],flush=True)
 with (D/('resume-'+row['id']+'.log')).open('w')as f:
  p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT);start=time.monotonic();reason=None
  while p.poll()is None:
   mem={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}
   pressure=float(Path('/proc/pressure/memory').read_text().splitlines()[1].split('avg10=')[1].split()[0])
   if pressure>10 or mem['MemAvailable']<3*1024**2 or time.monotonic()-start>600:
    reason=f'Validation stopped early: memory pressure {pressure}, available {mem["MemAvailable"]} KiB'
    subprocess.run(['systemctl','--user','stop',unit+'.scope']);p.wait(timeout=30);break
   time.sleep(1)
 if out.exists():x=json.loads(out.read_text())
 else:x={'status':'failed','error':reason or f'Worker exited {p.returncode} without receipt'}
 row.update(status=x['status'],error=x.get('error'),returncode=p.returncode)
 (O/'tune1090-profile-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('DONE',row['id'],row['status'],row['error'],flush=True)
 if row['status']!='ok':break
