"""Bounded source-snapshot audit; does not reconstruct packages, weights or fixtures."""
from pathlib import Path
import ast,json,hashlib,datetime,sys
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
p=W/'dsh-basalt/benchmarks/source-manifest.json';manifest=json.loads(p.read_text());names={Path(x['path']).name for x in manifest['files']};checks=[]
assert len(names)==len(manifest['files']), 'Duplicate source basenames'
for entry in manifest['files']:
 name=Path(entry['path']).name;src=W/name
 assert hashlib.sha256(src.read_bytes()).hexdigest()==entry['sha256'], 'Snapshot differs: '+name
 if src.suffix!='.py':continue
 for node in ast.walk(ast.parse(src.read_text())):
  modules=[node.module.split('.')[0]]if isinstance(node,ast.ImportFrom)and node.module else[a.name.split('.')[0]for a in node.names]if isinstance(node,ast.Import)else[]
  for module in modules:
   dependency=module+'.py'
   if(W/dependency).is_file():
    assert dependency in names,(name,dependency)
    checks.append(dict(source=name,dependency=dependency,kind='local import',passed=True))
  if isinstance(node,ast.Constant)and isinstance(node.value,str)and node.value.endswith(('.py','.mjs','.txt','.cpp','.hpp'))and'/'not in node.value and(W/node.value).is_file():
   assert node.value in names,(name,node.value)
   checks.append(dict(source=name,dependency=node.value,kind='existing literal sibling',passed=True))
assert(W/'dsh-basalt/benchmarks/evidence/user-host-memory-policy.json').is_file()
record=dict(at=datetime.datetime.now().astimezone().isoformat(),status='passed',prepared_from_base_commit=sys.argv[1]if len(sys.argv)>1 else None,manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_count=len(names),scope='Python AST local imports and existing flat literal py/mjs/txt/cpp/hpp sibling references checked against the exact source manifest. External engine/plugin clone layout remains required; dynamic references, packages, weights and fixtures excluded.',checks=checks,user_memory_policy_published=True)
(O/'harness-dependency-closure-audit.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS',len(names),'exact source snapshots;',len(checks),'dependency edges')
