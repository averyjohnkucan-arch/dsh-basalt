"""The actual Basalt v0.4 Python launcher retains numeric zero cache-swap options."""
import argparse,json,os,pathlib,sys,tempfile,unittest

@unittest.skipUnless(os.environ.get('BASALT_SOURCE'),'Set BASALT_SOURCE for the real launcher contract')
class AdaptiveOptions(unittest.TestCase):
 def test_numeric_values_reach_native_argv(self):
  sys.path.insert(0,os.environ['BASALT_SOURCE'])
  from serve.config import load_config_file,check_engine_flags,engine_flags_of
  parser=argparse.ArgumentParser();parser.add_argument('--model');parser.add_argument('--alias')
  binary=os.environ.get('BASALT_NATIVE_BINARY')
  known=engine_flags_of(binary)if binary else None
  if binary:self.assertIn('--adapt-swaps',known)
  with tempfile.TemporaryDirectory()as folder:
   path=pathlib.Path(folder)/'server.json'
   for count in [0,16,32,96]:
    path.write_text(json.dumps(dict(version=2,server={},models=[{'model':'fixture.basalt','alias':'fixture','adapt-swaps':count}])))
    config=load_config_file(str(path),parser);words=config.models[0].own_words
    self.assertEqual(words,['--adapt-swaps',str(count)])
    check_engine_flags(words,known,'test')

if __name__=='__main__':unittest.main()
