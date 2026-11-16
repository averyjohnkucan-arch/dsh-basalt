from pathlib import Path
import sys, subprocess, shutil, json, hashlib, time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';S=W/'basalt-latest'
sys.path.insert(0,str(S/'tools'))
from gguf_writer import GGUFWriter
root=R/'validation/external-engram';root.mkdir(parents=True,exist_ok=True)
def fixture(name,width=256,layers=(1,14),typ='IQ4_NL'):
    w=GGUFWriter();w.add('general.architecture','deepseek41')
    for layer in layers:w.add_raw(f'blk.{layer}.engram_embd.weight',[width,4],typ,bytes(576))
    w.write(root/name)
fixture('valid.gguf');fixture('wrong-width.gguf',width=128);fixture('wrong-layers.gguf',layers=(1,13));fixture('wrong-type.gguf',typ='Q8_0')
data=(root/'valid.gguf').read_bytes();(root/'truncated.gguf').write_bytes(data[:-8]);(root/'trailing.gguf').write_bytes(data+b'junk')
binary=root/'external-engram-test'
subprocess.run(['g++','-std=c++17','-O2','-I'+str(S/'include'),'-I'+str(S/'src'),str(W/'test_external_engram.cpp'),str(S/'src/ngram/ple_reader.cpp'),str(R/'build/basalt-latest/libplatform.a'),'-pthread','-o',str(binary)],check=True)
engram=Path('/mnt/media/AI/Models/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF/DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf')
run=subprocess.run([str(binary),str(root),str(engram)],capture_output=True,text=True,check=True)
receipt=dict(status='passed',scope='Actual C++ GGUF header validator, ten synthetic/fault cases plus actual direct SSD first/last/middle/page-straddling rows versus buffered ground truth, cache off/on; no GPU output parity or speed claim',stdout=run.stdout.strip(),header_sha256=hashlib.sha256((S/'src/models/deepseek41/engram_external.hpp').read_bytes()).hexdigest(),updated_unix=time.time())
(R/'outputs/external-engram-cpu-tests.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
