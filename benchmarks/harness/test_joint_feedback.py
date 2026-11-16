"""Execute the actual bounded feedback guard; nested repeats cannot recurse."""
from pathlib import Path
from types import SimpleNamespace
import ast,json,hashlib
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/range_repeatability.py';tree=ast.parse(source.read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='joint_feedback_required')
guard=next(x for x in tree.body if isinstance(x,ast.If)and isinstance(x.test,ast.Call)and isinstance(x.test.func,ast.Name)and x.test.func.id=='joint_feedback_required')
code=compile(ast.Module(body=[fn,guard],type_ignores=[]),str(source),'exec');results=[]
for key,args,expected in [('hybrid_basalt',['hybrid_basalt','qwen','--include-peak-code'],2),('hybrid_basalt',['hybrid_basalt','qwen'],0),('flash_basalt',['flash_basalt','qwen','--include-peak-code'],0),('hybrid_strata',['hybrid_strata','qwen','--include-peak-code'],0)]:
 calls=[];ns=dict(key=key,family='qwen',W=R/'work',sys=SimpleNamespace(argv=['driver',*args],executable='python'),subprocess=SimpleNamespace(run=lambda *a,**k:calls.append((a,k))))
 exec(code,ns);assert len(calls)==expected
 if calls:
  assert calls[0][0][0]==['python',str(R/'work/range_joint_refine.py'),key,'qwen']and calls[0][1]=={'check':True}
  assert calls[1][0][0]==['python',str(R/'work/range_low_peak.py'),key,'qwen','--skip-joint']and calls[1][1]=={'check':True}
 results.append(dict(key=key,args=args,child_calls=len(calls)))
# Child failure must stop qualification rather than silently publishing old controls.
def fail(*a,**k):raise RuntimeError('joint child failed')
ns.update(key='hybrid_basalt',sys=SimpleNamespace(argv=['driver','hybrid_basalt','qwen','--include-peak-code'],executable='python'),subprocess=SimpleNamespace(run=fail))
try:exec(code,ns)
except RuntimeError as error:assert str(error)=='joint child failed'
else:raise AssertionError('Feedback child failure was swallowed')
# Execute the actual peak-search skip guard as well.
peak_source=R/'work/range_low_peak.py';peak=ast.parse(peak_source.read_text());skip=next(n for n in peak.body if isinstance(n,ast.If)and '--skip-joint'in ast.unparse(n.test))
for args,wanted in [(['driver','hybrid_basalt','qwen'],1),(['driver','hybrid_basalt','qwen','--skip-joint'],0)]:
 calls=[];ns.update(sys=SimpleNamespace(argv=args,executable='python'),subprocess=SimpleNamespace(run=lambda *a,**k:calls.append((a,k))))
 exec(compile(ast.Module(body=[skip],type_ignores=[]),str(peak_source),'exec'),ns);assert len(calls)==wanted
(R/'outputs/joint-feedback-test.json').write_text(json.dumps(dict(status='passed',scope='Actual feedback guard, exact child invocation, nested no-feedback recursion prevention, other engines excluded and child failure propagation. No GPU performance claim.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=results,child_failure_propagated=True,peak_search_skip_joint_guard_passed=True,peak_source_sha256=hashlib.sha256(peak_source.read_bytes()).hexdigest()),indent=2)+'\n');print('Bounded joint feedback guard checks passed')
