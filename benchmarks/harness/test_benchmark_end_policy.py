"""Actual payload and marker diagnostics without importing server-launching scripts."""
from pathlib import Path
import ast,hashlib,json
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
def function(name,file):
 p=R/'work'/file;node=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)and n.name==name);ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns);return ns[name]
payload=function('completion_payload','http_bench.py');markers=function('end_marker_diagnostics','audit_range_outputs.py')
expected={'prompt':[10,20],'n_predict':8192,'temperature':0,'seed':42,'ignore_eos':True,'cache_prompt':False,'stream':True,'return_tokens':True,'return_progress':True}
assert payload({},[10,20])==expected
quality=payload({'ignore_eos':False,'generate':1024},[10,20]);assert not quality['ignore_eos']and quality['n_predict']==1024
special={'tokenizer.ggml.eos_token_id':7,'tokenizer.ggml.eot_token_id':9,'tokenizer.ggml.add_eos_token':True}
none=markers([1]*8,special,4);assert none['native_end_marker_ids_known']and none['tokens_after_first_native_end_marker']==0
past=markers([1,1,7,1,1,1,9,1],special,4);assert past['first_native_end_marker_index']==2 and past['tokens_after_first_native_end_marker']==5 and past['timed_tokens_after_first_native_end_marker']==4 and past['entire_timed_tail_after_native_end_marker']
last=markers([1]*7+[7],special,4);assert last['tokens_after_first_native_end_marker']==0 and not last['entire_timed_tail_after_native_end_marker']
unknown=markers([7]*8,{},4);assert not unknown['native_end_marker_ids_known']and unknown['first_native_end_marker_index']is None
record=dict(status='passed',scope='Actual AST-extracted HTTP request builder preserves the previous wire controls exactly; quality runs honor native stopping. Actual end-marker audit counts known EOS/EOT markers, suffix timing overlap and unknown metadata. No GPU or model-quality claim.',sources={f:hashlib.sha256((R/'work'/f).read_bytes()).hexdigest()for f in ['http_bench.py','audit_range_outputs.py']},checks=dict(default_request=expected,quality_request=quality,early_end=past,late_end=last,unknown_metadata=unknown))
(R/'outputs/benchmark-end-policy-test.json').write_text(json.dumps(record,indent=2)+'\n');print('HTTP request and end-marker audit checks passed')
