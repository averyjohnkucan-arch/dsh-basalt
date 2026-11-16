"""Exercise real disk/range guards and partial relocation without network or GPU."""
from pathlib import Path
from types import SimpleNamespace
import ast,hashlib,json,os,tempfile
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/download_iq2_xs.py';tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['hold_reason','validate_resume_response']];root=Path(tempfile.mkdtemp(prefix='xs-download-',dir=R/'validation'));out=root/'outputs';out.mkdir();free=[50*2**30];ns=dict(O=out,plan=dict(minimum_free_gib=35),dest=root,json=json,shutil=SimpleNamespace(disk_usage=lambda p:SimpleNamespace(free=free[0])))
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
assert ns['hold_reason']()is None
free[0]=34*2**30;assert ns['hold_reason']()
free[0]=50*2**30;(out/'matrix-completion.json').write_text(json.dumps(dict(status='complete')));assert ns['hold_reason']()
ns['plan']['hold_during_original_deepseek']=False;assert ns['hold_reason']()is None
for status,header,offset,valid in [(200,'',0,True),(206,'bytes 100-199/200',100,True),(200,'',100,False),(206,'bytes 0-199/200',100,False)]:
 passed=True
 try:ns['validate_resume_response'](SimpleNamespace(status=status,headers={'Content-Range':header}),offset)
 except AssertionError:passed=False
 assert passed==valid
migration=R/'work/relocate_iq2xs_download.py';mt=ast.parse(migration.read_text());fn=next(n for n in mt.body if isinstance(n,ast.FunctionDef)and n.name=='paced_read_hash');loop=next(n for n in mt.body if isinstance(n,ast.For));calls=[]
for resumed in [False,True]:
 sandbox=root/('resume'if resumed else'fresh');media=sandbox/'media';dest=sandbox/'main';media.mkdir(parents=True);dest.mkdir();name='DeepSeek-IQ2_XS-00001.gguf';shared='DeepSeek-Engram-IQ4_NL.gguf';payload=b'partial-network-data'*200;engram=b'shared-engram-original';(media/(name+'.part')).write_bytes(payload);(media/shared).write_bytes(engram);sha=hashlib.sha256(engram).hexdigest();(media/(shared+'.done')).write_text('sha256 '+sha)
 if resumed:(dest/(name+'.part.migrating')).write_bytes(payload[:123])
 scope=dict(Path=Path,plan=dict(files=[dict(path=name),dict(path=shared,size=len(engram),lfs=dict(oid=sha))]),media=media,dest=dest,hashes={},hashlib=hashlib,os=os,time=SimpleNamespace(monotonic=lambda:0,time=lambda:1,sleep=lambda n:None),O=out,json=json)
 exec(compile(ast.Module(body=[fn,loop],type_ignores=[]),str(migration),'exec'),scope)
 assert(dest/(name+'.part')).read_bytes()==payload and not(media/(name+'.part')).exists()
 assert scope['hashes'][name].hexdigest()==hashlib.sha256(payload).hexdigest()
 assert(media/name).is_symlink()and(media/name).readlink()==dest/name
 assert(dest/shared).is_symlink()and(dest/shared).read_bytes()==engram and(media/shared).read_bytes()==engram
 assert(dest/(shared+'.done')).read_bytes()==(media/(shared+'.done')).read_bytes();calls.append('resume'if resumed else'fresh')
record=dict(status='passed',scope='Actual downloader disk/phase guards, HTTP range validation, and actual migration loop on file-backed NVMe fixtures. Fresh/resumed partial bytes and hash state preserved; common originals unchanged. No network/GPU.',migration_cases=calls,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [source,migration]})
(R/'outputs/iq2-xs-download-tests.json').write_text(json.dumps(record,indent=2)+'\n');print('Disk/range and fresh/resumed migration checks passed')
