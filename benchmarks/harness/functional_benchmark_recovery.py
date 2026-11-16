"""Fresh functional generations and exact attempt/prompt provenance; no stale grading."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
from benchmark_environment import ensure_environment
from range_common import completed_input_matches,read_case_mapping
W=Path(__file__).resolve().parent

def run_functional_worker(config,config_path,output,progress,grade_only=False):
 output=Path(output);config_path=Path(config_path);result_path=output/'result.json'
 def validate(value,attempt):
  if not value or not completed_input_matches(value,config):raise RuntimeError('Functional result does not match planned input/settings')
  actual=value['config']
  if not attempt or actual.get('functional_attempt_id')!=attempt:raise RuntimeError('Functional result belongs to another generation attempt')
  if actual.get('functional_prompt_sha256')!=config['functional_prompt_sha256']or actual.get('functional_checks_sha256')!=config['functional_checks_sha256']or actual.get('functional_task_name')!=config['functional_task_name']:raise RuntimeError('Functional task or prompt fingerprint changed')
  if value['status']=='ok':
   prompt=read_case_mapping(output/'prompt.json')
   if not prompt or prompt.get('sha256')!=config['functional_prompt_sha256']or value.get('prompt_tokens')!=config['depth']:raise RuntimeError('Generated prompt evidence differs from the exact planned IDs')
  return value
 if grade_only:
  saved=read_case_mapping(config_path)or{}
  return validate(read_case_mapping(result_path),saved.get('functional_attempt_id'))
 # A valid same-controls generation can be graded again without another GPU
 # run. Exact prompt/check hashes, saved attempt and current binary must match.
 try:
  saved=read_case_mapping(config_path)or{}
  previous=validate(read_case_mapping(result_path),saved.get('functional_attempt_id'))
  if previous['status']=='ok'and hashlib.file_digest(Path(config['command'][3]).open('rb'),'sha256').hexdigest()==config['engine_binary_sha256']:
   return {**previous,'functional_generation_reused':True}
 except (OSError,RuntimeError,KeyError,ValueError):pass
 files=[p for p in output.iterdir()if p.is_file()]
 if files:
  archive=output/'prior-attempts'/str(time.time_ns());archive.mkdir(parents=True)
  for path in files:shutil.copy2(path,archive/path.name)
  if config_path.exists():shutil.copy2(config_path,archive/'input-config.json')
  for path in files:path.unlink()
 config['functional_attempt_id']=str(time.time_ns());config_path.write_text(json.dumps(config,indent=2)+'\n')
 value=None
 try:
  ensure_environment()
  binary=Path(config['command'][3])
  if hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()!=config['engine_binary_sha256']:raise RuntimeError('Functional engine binary changed since performance qualification')
  with Path(progress).open('w')as log:
   completed=subprocess.run([sys.executable,str(W/('http_bench.py'if config.get('protocol')=='http'else'native_bench.py')),'--config',str(config_path)],stdout=log,stderr=subprocess.STDOUT)
  value=validate(read_case_mapping(result_path),config['functional_attempt_id'])
  if completed.returncode or value['status']!='ok':raise RuntimeError(value.get('error')or'Functional worker exited unsuccessfully')
  ensure_environment()
 except Exception as error:
  if result_path.exists():shutil.copy2(result_path,output/'failed-worker-result.json')
  value={**(value or{}),'config':config,'status':'failed','error':'Functional generation not qualified: '+str(error)}
  result_path.write_text(json.dumps(value,indent=2)+'\n')
 return value
