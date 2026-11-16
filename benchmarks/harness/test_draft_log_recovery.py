"""Real interleaved log and actual persistence block, file-backed and GPU-free."""
from pathlib import Path
import hashlib,json,sys,tempfile,textwrap,types,time,shutil
from draft_log_diagnostics import parse_draft_windows
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');source=R/'work/native_bench.py';s=source.read_text();start=s.index(" result['gpu_telemetry_fields']",s.index('finally:'));block=textwrap.dedent(s[start:s.index(' print(json.dumps(result),flush=True)',start)])
log=R/'work/draft-log-recovery-fixture.txt';actual=parse_draft_windows(log.read_text());assert actual['malformed_window_records']==1 and actual['valid_window_records']==2
sample=parse_draft_windows('W 8 7 0 1 2 3\nW 2 1 0 0.002R temp=0 S=8\nW 8 7 0 nan 2 3\nW 2 1\n');assert sample['valid_window_records']==1 and sample['malformed_window_records']==3 and sample['windows']['mean_ms']==6
parent=R/'validation/draft-log-recovery';parent.mkdir(parents=True,exist_ok=True)
def exercise(fault=False):
 root=Path(tempfile.mkdtemp(dir=parent));(root/'draft.log').write_text(log.read_text());ns=dict(root=root,result={'status':'ok','generated':8192},tokens=[10,20],telemetry=[{'evidence':'preserved'}],json=json)
 original=sys.modules['draft_log_diagnostics']
 if fault:
  def injected(text):
   assert json.loads((root/'result.json').read_text())['status']=='ok'
   assert json.loads((root/'tokens.json').read_text())==[10,20]
   assert json.loads((root/'telemetry.json').read_text())==[{'evidence':'preserved'}]
   raise RuntimeError('injected optional-parser failure')
  sys.modules['draft_log_diagnostics']=types.SimpleNamespace(parse_draft_windows=injected)
 try:exec(compile(block,str(source),'exec'),ns)
 finally:sys.modules['draft_log_diagnostics']=original
 result=json.loads((root/'result.json').read_text());assert result['status']=='ok'and json.loads((root/'tokens.json').read_text())==[10,20]
 if fault:assert 'injected'in result['draft_log_diagnostics']['error']
 else:assert result['draft_log_diagnostics']['malformed_window_records']==1 and result['draft_windows']['count']==actual['valid_window_records']
 return dict(primary_result_retained=True,tokens_retained=True,optional_error_recorded=fault)
def isolation():
 root=Path(tempfile.mkdtemp(dir=parent));(root/'draft.log').write_text('preceding-attempt\n');requested=root.parent/(root.name+'-requested.log');requested.write_text('requested-log-untouched\n')
 cfg=dict(command=['taskset','-c','0-21','fixture-engine','--draft-log',str(requested)])
 start=s.index("if '--draft-log'in cfg['command']:");preflight=s[start:s.index('from benchmark_memory_guard import MemoryGuard',start)]
 exec(compile(preflight,str(source),'exec'),dict(cfg=cfg,root=root,Path=Path,time=time,shutil=shutil))
 assert not(root/'draft.log').exists()and cfg['command'][-1]==str(root/'draft.log')
 history=list((root/'prior-draft-logs').iterdir());assert len(history)==1 and history[0].read_text()=='preceding-attempt\n'
 (root/'draft.log').write_text('fresh-attempt\n');assert requested.read_text()=='requested-log-untouched\n'
 return dict(prior_log_preserved=True,active_log_fresh=True,requested_external_log_untouched=True)
checks=dict(real_malformed_log=exercise(),parser_exception=exercise(True),attempt_log_isolation=isolation())
receipt=dict(status='passed',scope='Actual native_bench postprocessing/persistence block; actual interleaved draft log, finite/incomplete-record checks, and injected optional-parser exception after primary files are verified durable. Fresh trace isolation also checked; no GPU.',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),malformed_rows=actual['malformed_window_records'],valid_rows=actual['valid_window_records'],checks=checks)
(R/'outputs/draft-log-recovery-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
