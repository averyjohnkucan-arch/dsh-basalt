"""Actual native launcher/vector key and template semantics; no GPU process."""
import argparse,ast,json,os,pathlib,sys,tempfile,unittest
@unittest.skipUnless(os.environ.get('BASALT_SOURCE'),'Set BASALT_SOURCE for actual launcher/template checks')
class ProjectionContract(unittest.TestCase):
 def test_real_native_flag_translation(self):
  sys.path.insert(0,os.environ['BASALT_SOURCE'])
  from serve.config import load_config_file,check_engine_flags,engine_flags_of
  parser=argparse.ArgumentParser();parser.add_argument('--model');parser.add_argument('--alias')
  native={'model':'fixture.basalt','control-vector-scaled':'/vector.gguf:1.0','control-vector-layer-range':[4,44],'cvec-mode':'project','cvec-dir':'per-layer'}
  with tempfile.TemporaryDirectory()as folder:
   p=pathlib.Path(folder)/'config.json';p.write_text(json.dumps(dict(version=2,models=[native],server={})));words=load_config_file(str(p),parser).models[0].own_words
  self.assertEqual(words,['--control-vector-scaled','/vector.gguf:1.0','--control-vector-layer-range','4','44','--cvec-mode','project','--cvec-dir','per-layer'])
  if os.environ.get('BASALT_NATIVE_BINARY'):check_engine_flags(words,engine_flags_of(os.environ['BASALT_NATIVE_BINARY']),'projection-test')
 def test_actual_template_medium_has_no_effort_instruction(self):
  import jinja2
  p=pathlib.Path(os.environ['BASALT_SOURCE'])/'serve/chat_template.jinja';template=jinja2.Environment().from_string(p.read_text())
  args=dict(messages=[dict(role='system',content='Original instructions'),dict(role='user',content='Hello')],enable_thinking=True,add_generation_prompt=True)
  medium=template.render(**args,reasoning_effort='medium');self.assertNotIn('Reasoning effort is set',medium)
  self.assertIn('Reasoning effort is set to low',template.render(**args,reasoning_effort='low'))
  self.assertIn('Reasoning effort is set to xhigh',template.render(**args,reasoning_effort='xhigh'))
 def test_actual_native_projection_wire_key(self):
  p=pathlib.Path(os.environ['BASALT_SOURCE'])/'serve/engine/process.py';node=next(n for n in ast.walk(ast.parse(p.read_text()))if isinstance(n,ast.FunctionDef)and n.name=='projection_key');node.decorator_list=[];ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
  self.assertEqual(ns['projection_key']({'experimental_speed_projection':False}),' cvec=0');self.assertEqual(ns['projection_key']({'experimental_speed_projection':True}),' cvec=1')
