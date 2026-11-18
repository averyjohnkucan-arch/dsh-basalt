from pathlib import Path
import struct,json,hashlib
from prepare_range_fixtures import tokenizer_for,Tokenizer,framing
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');p=Path('/mnt/media/AI/Models/Qwen3.8-27B-abliterated/huihui-ai/GSQ-RCO-IQ3_S-MTP/huihui-qwen3_8-27b-iq3s-vision-mtp-dflash2.ninfer')
with p.open('rb') as f:
 h=f.read(32);assert h[:8]==b'NINFER\0\3';n=struct.unpack_from('<Q',h,8)[0];assert n<32*1024*1024;m=json.loads(f.read(n));objects={o['id']:o for o in m['objects']}
 def resource(name):
  o=objects[m['components']['text']['resources'][name]];assert o['kind']=='resource' and o['encoding']=='raw_bytes_v1' and o['offset']+o['bytes']<=m['files'][0]['payload_bytes'];f.seek(32+n+o['offset']);return f.read(o['bytes'])
 raw=resource('tokenizer.json');d=json.loads(raw);template=resource('chat_template.jinja').decode();generation=json.loads(resource('generation_config.json'))
ref,md=tokenizer_for('qwen27b');v=d['model']['vocab'].copy();v.update({x['content']:x['id'] for x in d['added_tokens']});assert all(ref.ids.get(k)==i for k,i in v.items());assert set(v.values())==set(range(len(v)))
merges=[' '.join(x) if isinstance(x,list) else x for x in d['model']['merges']];assert {tuple(x.split(' ',1)):i for i,x in enumerate(merges)}==ref.ranks
# All actual token IDs and BPE ranks agree; drop only absent GGUF vocabulary entries.
tokens=['']*len(v);types=[1]*len(v)
for k,i in v.items():tokens[i]=k
for x in d['added_tokens']:
 types[x['id']]=3 if x.get('special') else 4
md=dict(md);md.update({'tokenizer.ggml.tokens':tokens,'tokenizer.ggml.token_type':types,'tokenizer.ggml.merges':merges,'tokenizer.chat_template':template})
e=generation.get('eos_token_id');md['tokenizer.ggml.eos_token_id']=e[0] if isinstance(e,list) else e
assert isinstance(md['tokenizer.ggml.eos_token_id'],int)
t=Tokenizer.from_metadata(md);framing(t,md,'unit',task='Return Python code.')
out=r/'work/huihui-test-tokenizer-metadata.json';out.write_text(json.dumps(md)+'\n');(r/'outputs/huihui-test-tokenizer-verification.json').write_text(json.dumps({'source':str(p),'tokenizer_sha256':hashlib.sha256(raw).hexdigest(),'token_count':len(v),'all_actual_ids_match_reference':True,'bpe_ranks_match':True,'template_source':'packed artifact','removed_reference_only_tokens':len(ref.ids)-len(v),'metadata':str(out)},indent=2)+'\n');print('Verified actual Huihui tokenizer and template',len(v))
