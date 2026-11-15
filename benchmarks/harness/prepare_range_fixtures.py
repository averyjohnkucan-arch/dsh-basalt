from pathlib import Path
import hashlib,json,sys,re
import jinja2
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs'
sys.path.insert(0,str(W/'basalt-latest/tools'))
from tokenizer import Tokenizer
from gguf_reader import GGUFFile
from model_file import ModelFile

SENTINEL='BENCHMARK_REFERENCE_PACKET_771593_END'
CORPUS='\n\n'.join((W/'prose-corpus'/name).read_text(encoding='utf-8-sig')for name in ['war-and-peace.txt','moby-dick.txt'])
CODE_META=json.loads((O/'code-workload.json').read_text())
CODE='\n\n'.join((W/'basalt'/p).read_text()for p in CODE_META['source_files'])
TASKS={
 'code':CODE_META['task'],
 'text':'''Write an extensive original long-form essay for an educated general reader about how people reason, cooperate, exercise power, interpret evidence, manage uncertainty, and change their minds. Use the reference packet as context and contrast different perspectives rather than reproducing its sentences. Develop concrete examples, objections, counterarguments, and practical implications in fluent natural prose. Include no source code. Aim for more than 20,000 words across many substantive sections so the discussion remains in progress at the output limit. Begin the essay directly and keep developing new material without repeating paragraphs or offering a premature conclusion.''',
 'chat':'''Picking up our conversation, please give me a very thoughtful, expansive answer about how to turn a shared community-library idea into a welcoming, resilient place while respecting the people involved. Reflect on the reference packet where it helps, and keep a warm conversational voice. Talk through realistic tensions, examples, follow-up concerns, disagreements, and what you would say to different people. Do not output code or a checklist-only answer. I want a book-length conversation with you: develop more than 20,000 words of connected dialogue-style explanation, continuing to introduce useful new perspectives rather than closing the conversation early. Start your reply directly.''',
 'story':'''Write a completely original, richly developed near-future literary mystery, using the reference packet only for broad stylistic inspiration. Do not quote, continue, summarize, or retell either source novel. Set the story in a fictional coastal city where a retired lighthouse keeper, a transit engineer, a teenage cartographer and an unreliable archivist independently discover that the tide tables disagree with the memories of the town. Give the characters conflicting motives and distinctive dialogue. Alternate close viewpoints, build surprising but coherent consequences, and use vivid scenes rather than lists. Include no code. Develop a novel of more than 20,000 words, allowing the mystery to deepen across many scenes instead of rushing to resolve it. Begin with the first scene and continue the story until the output budget ends.'''
}
HISTORY=[
 ('I want to build a community library, but I am worried about imposing my own idea on the neighborhood.','Start by listening to what people already share and what they wish they could find nearby. A small reading room can begin with relationships before it becomes a building.'),
 ('Some neighbors want a quiet study space and others want lively events. Can both fit?','They can, with clear expectations about different times and spaces. Ask each group what a good visit would feel like, then design a trial schedule together rather than deciding by the loudest voice.'),
 ('We have a vacant storefront near the bus stop. The rent is manageable, but accessibility worries me.','Walk through an ordinary visit with people who use mobility aids, parents with strollers, and visitors who need a calmer environment. Those details should guide the budget before furniture or decoration.'),
 ('A volunteer offered a large donation if the collection reflects only their interests.','Thank them for the offer, then explain the shared collection policy. A contribution should strengthen a public purpose without giving one person control over whose experiences are represented.'),
 ('We will have volunteers of different ages. I want disagreements to feel safe.','Give people a clear way to ask for help, a fair process for making decisions, and room to admit mistakes. Write a few plain-language commitments together and revisit them after real situations teach you something.'),
 ('I am collecting a long reference packet about people, uncertainty, and cooperation. Can we use it to think this through?','Yes. Treat it as a source of questions and contrasting perspectives, while staying grounded in the lives of the people who would actually use the library.')
]

def tokenizer_for(family):
 if family=='qwen27b':
  model=ModelFile(str(R/'packs/qwen27b-nvfp4full-experimental.basalt'));md=json.loads(model.read('meta'))['gguf_kv']
 else:
  path='/mnt/media/AI/Models/Scratch models/Maximilian228/Qwen3.8-Flash-Next-NVFP4-GPTQ-Strata/qwen-nvfp4-gptq-dense.gguf'if family=='qwen'else'/mnt/media/AI/Models/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF/DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XXS-00001-of-00004.gguf'
  md=GGUFFile(path).metadata
 return Tokenizer.from_metadata(md),md

def framing(tok,metadata,workload,task=None):
 template=metadata.get('tokenizer.chat_template')
 if not isinstance(template,str)or not template:raise ValueError('Tokenizer lacks native chat template')
 env=jinja2.Environment(trim_blocks=True,lstrip_blocks=True)
 def reject(message):raise ValueError(message)
 env.globals['raise_exception']=reject
 env.globals['strftime_now']=lambda fmt:'2026-11-15'
 messages=[]
 if workload=='chat':
  for user,assistant in HISTORY:messages += [dict(role='user',content=user),dict(role='assistant',content=assistant)]
 content='Reference packet follows.\n\n'+SENTINEL+'\n\nTask:\n'+(task or TASKS[workload])
 messages.append(dict(role='user',content=content))
 for message in messages:
  if message['role']=='user':message['content_blocks']=[dict(type='text',text=message['content'])]
 rendered=env.from_string(template).render(messages=messages,add_generation_prompt=True,enable_thinking=False,thinking=False,thinking_mode='chat',tools=None)
 assert rendered.count(SENTINEL)==1
 before,after=rendered.split(SENTINEL)
 return tok.encode(before,parse_special=True),tok.encode(after,parse_special=True),rendered

def main():
 out=W/'range-fixtures';out.mkdir(exist_ok=True);receipt=dict(protocol='8192 short code input; floor(80% native context) long text/chat/story input; 8192 output, final4096timed; temperature0,seed42,thinkingoff; native tokenizer chat framing',sources=json.loads((O/'prose-corpus-sources.json').read_text()),cases=[])
 for family in['qwen','qwen27b','deepseek']:
  tok,metadata=tokenizer_for(family);corpus_ids=tok.encode(CORPUS);code_ids=tok.encode(CODE)
  depth=838860 if family=='deepseek' else 209715
  for workload,requested in [('code',8192),('text',depth),('chat',depth),('story',depth)]:
   prefix,suffix,rendered=framing(tok,metadata,workload);body=code_ids if workload=='code'else corpus_ids
   left=requested-len(prefix)-len(suffix);assert left>0
   repeats=(left+len(body)-1)//len(body);ids=prefix+(body*repeats)[:left]+suffix
   path=out/(family+'-'+workload+'.json');path.write_text(json.dumps(dict(ids=ids),separators=(',',':')))
   item=dict(family=family,workload=workload,depth=requested,prompt_file=str(path),token_sha256=hashlib.sha256(','.join(map(str,ids)).encode()).hexdigest(),corpus_tokens=len(body),body_repetitions=repeats,prefix_tokens=len(prefix),suffix_tokens=len(suffix),framing_preview=tok.decode(prefix[:25]),assistant_suffix=tok.decode(suffix[-45:]),synthetic=True)
   receipt['cases'].append(item);print(family,workload,requested,'body repeats',repeats,flush=True)
   (out/(family+'-'+workload+'-framing.txt')).write_text(rendered)
 (O/'range-workloads.json').write_text(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
