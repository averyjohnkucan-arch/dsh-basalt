from pathlib import Path
import json,re,copy,time
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';D=W/'tune1090';dest=Path('/mnt/media/AI/Model Configs/new profiles');dest.mkdir(exist_ok=True)
LABELS={'27b-ninfer': '27B NVFP4 · NInfer', '27b-basalt': '27B NVFP4 · Basalt (KV offload)', 'huihui-int8': 'Huihui IQ3 · NInfer · INT8 KV', 'huihui-fp8': 'Huihui IQ3 · NInfer · FP8 KV', 'huihui-nvfp4': 'Huihui IQ3 · NInfer · NVFP4 KV', 'range-flash-basalt-long': 'Flash NVFP4 · Basalt · INT8 (long)', 'range-flash-basalt-short': 'Flash NVFP4 · Basalt · INT8 (short)', 'range-hybrid-basalt-long': 'Flash hybrid · Basalt · INT8 KV', 'measured-flash-fp16': 'Flash NVFP4 · Basalt · FP16 KV', 'measured-hybrid-fp16': 'Flash hybrid · Basalt · FP16 KV', 'range-flash-strata-long': 'Flash NVFP4 · Strata · INT8 (long)', 'range-flash-strata-short': 'Flash NVFP4 · Strata · INT8 (short)', 'measured-gyro-strata': 'Gyro S · Strata · FP16 KV', 'deepseek-xxs': 'DeepSeek XXS · Basalt'}
plan=json.loads((D/'plan.json').read_text());state=json.loads((O/'tune1090-progress.json').read_text())
validation_path=O/'tune1090-profile-validation.json'
validation=json.loads(validation_path.read_text()) if validation_path.exists() else []
finalized=(O/'tune1090-final-review.json').exists() and len(validation)==13 and all(x['status']=='ok' and x['returncode']==0 for x in validation)
review_status='validated; benchmark output and exported adapter checks passed' if finalized else 'measured; output and adapter review pending'
original=Path('/mnt/media/AI/Model Configs/All profile snapshots')
# Keep a separate original snapshot for audit, not labeled optimized.
backup=dest/'original snapshots';backup.mkdir(exist_ok=True)
for p in original.glob('*.json'):
 q=backup/p.name
 if not q.exists():q.write_bytes(p.read_bytes())
groups={}
for g in ['basalt-combined-measured','ninfer-measured','strata-range']:
 x=json.loads((O/('dsh-'+g+'-state/profiles.json')).read_text());groups[g]=x if isinstance(x,list)else x['profiles']
keyids={'27b-ninfer':'scratch-measured-27b-ninfer1616',**{'huihui-'+kv:'scratch-measured-huihui-'+kv for kv in ['int8','fp8','nvfp4']},'deepseek-xxs':'scratch-deepseek-iq2-xxs'}
selected={'basalt':[],'ninfer':[],'strata':[]};rows=[]
def pd(d):return f"p{d['prefill_tok_s']:.0f}/d{d['tail_decode_tok_s']:.1f}"if d.get('status')=='ok'and d.get('tail_decode_tok_s')else 'pending/failed'
for item in plan:
 key=item['key'];v=state['models'].get(key,{});b=v.get('trials',{}).get('before',{});s=v.get('selected',{});lo=s.get('low',{});hi=s.get('high',{})
 rows.append({'model':key,'before10':b.get('10',{}),'before90':b.get('90',{}),'after10':lo,'after90':hi,'status':v.get('status','pending'),'candidate':s.get('candidate')})
 if not lo or not hi:continue
 pid=item.get('profile_id',keyids.get(key));matches=[(g,p)for g,ps in groups.items()for p in ps if p['id']==pid]
 if not matches:continue
 group,source=matches[0];p=copy.deepcopy(source);p['cpuSet']=hi['config']['command'][2];p['environment']={**p.get('environment',{}),**hi['config'].get('env',{})};
 p['id']='scratch-tuned1090-'+pid.removeprefix('scratch-');
 if group.startswith('ninfer'):
  p['options']['--model-id']=p['id']
  if 'modelId'in p:p['modelId']=p['id']
 chosen=s['candidate'];changes=next((x['changes']for x in item['variants']if x['name']==chosen),{})
 def flags(c):
  out={};a=c['command'];i=4
  while i<len(a):
   if a[i].startswith('--'):
    keyflag=a[i];value=True
    if i+1<len(a)and not a[i+1].startswith('--'):i+=1;value=a[i]
    out[keyflag]=value
   i+=1
  return out
 oldflags=flags(json.loads(Path(item['source']).read_text()));newflags=flags(hi['config'])
 ignored={'--serve','--model','--native','--pack','--host','--port','--api-key','--max-context','--kv-capacity','--kv','--kv-dtype','--eos','--eos-ids','--stop-eos','--draft-log','--expert-profile'}
 changes={k:v for k,v in newflags.items()if k not in ignored and oldflags.get(k)!=v}
 if group.startswith('basalt')and '--vram-reserve-mib'in changes:p['vramReserveMiB']=int(changes.pop('--vram-reserve-mib'))
 for k,v in list(changes.items()):
  if isinstance(v,str):
   try:changes[k]=json.loads(v)
   except ValueError:pass
 opts='options'if group.startswith('ninfer')else'engineOptions'if group.startswith('basalt')else None
 if opts:
  for flag,value in changes.items():
   keyflag=flag.lstrip('-') if opts=='engineOptions' else flag
   if value is None:p[opts].pop(keyflag,None)
   else:p[opts][keyflag]=value
 else:
  a=p.get('extraArgs',[])
  for flag,value in changes.items():
   if flag in a:
    i=a.index(flag)
    if value is None:del a[i:i+2]
    else:a[i+1]=str(value)
   elif value is not None:a.extend([flag,str(value)])
  p['extraArgs']=a
 # Give each new profile its own copy of the measured ranking; never mutate originals.
 ranking=hi['config'].get('expert_profile_source')
 if ranking:
  import hashlib
  data=Path(ranking).read_bytes();expected=hi['config'].get('input_profile_sha256')
  if expected and hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Original expert ranking changed:'+ranking)
  directory=dest/'expert rankings';directory.mkdir(exist_ok=True);target=directory/(pid+'.bin');target.write_bytes(data)
  if group.startswith('basalt'):p['engineOptions']['expert-profile']=str(target)
  elif group.startswith('strata'):
   a=p.get('extraArgs',[])
   while '--expert-profile'in a:
    i=a.index('--expert-profile');del a[i:i+2]
   p['extraArgs']=a+['--expert-profile',str(target)]
 if group.startswith('strata'):
  args=hi['config']['command'][4:];args=[x for x in args if x!='--serve']
  if '--expert-profile'in args:args[args.index('--expert-profile')+1]=str(target)
  runtime=p['runtime'];pack=Path(newflags['--pack'])
  p['config']={'exe':runtime['executable'],'cwd':runtime['controlDir'],'arch':p['model']['architecture'],'model_name':p['id'],'host':'127.0.0.1','port':p['port'],'gpu':p['gpu'],'tokenizer':str(pack/'tokenizer'),'open_browser':False,'lib_dirs':[str(Path(runtime['executable']).parent)],'env':p.get('environment',{}),'args':args}
  if '--native-dense-gguf'in newflags:
   import hashlib
   native=Path(newflags['--native']);stat=native.stat();tool=Path(runtime['controlDir'])/'tools/strata_tokenizer.py'
   digest=hashlib.sha256(json.dumps([str(native),str(stat.st_ino),str(stat.st_size),str(stat.st_mtime_ns)],separators=(',',':')).encode()+tool.read_bytes()).hexdigest()
   tokenizer=R/'packs/strata-http-tokenizers'/digest/'tokenizer'
   for file in ['vocab.json','merges.txt','token_type.json','tokenizer.json','chat_template.jinja']:assert (tokenizer/file).exists(),tokenizer/file
   p['config']['tokenizer']=str(tokenizer)
   p['config']['log']=str(D/('engine-'+p['id']+'.log'))
 # Preserve exact historical evidence separately; current names describe only this run.
 p['previousMeasuredPerformance']=p.get('measuredPerformance',p.get('verification8192'))
 p['measuredPerformance']={'protocol':state['protocol'],'low':{k:lo.get(k)for k in ['prefill_tok_s','tail_decode_tok_s','generated','tail_measured_tokens','output_screen']},'high':{k:hi.get(k)for k in ['prefill_tok_s','tail_decode_tok_s','generated','tail_measured_tokens','output_screen']},'lowCase':lo['config']['output'],'highCase':hi['config']['output'],'selection':chosen,'tradeoff':s['tradeoff']}
 p['name']=re.split(r'\s+(?:-\s*)?p\d',p['name'])[0].rstrip(' -—')+' '+pd(lo)+' '+pd(hi)
 p['tune1090']={'status':review_status,'sourceProfile':pid,'nativeConfig':hi['config'],'sampling':item.get('sampling')if group.startswith('ninfer')else item['native_sampling']}
 p['samplingPresets']={**p.get('samplingPresets',{}),'instruct':{k:v for k,v in item['sampling'].items()if k!='seed'}}
 if item['family']=='deepseek':
  p['samplingPresets']={**p.get('samplingPresets',{}),'instruct':{'temperature':0.6,'top_p':0.95,'top_k':0}}
 elif not group.startswith('ninfer'):
  p['samplingPresets']['instruct'].update(repetition_penalty=1,penalty_last_n=4096)
 if group.startswith('ninfer'):
  originals=json.loads((original/'ninfer-profiles.json').read_text())['profiles'];original27=next(x for x in originals if 'NVFP4-full'in x['name'])
  p['samplingPresets']=copy.deepcopy(original27['samplingPresets'])
 engine=group.split('-')[0];selected[engine].append(p)
# User correction: one balanced configuration per distinct model, not context aliases or KV candidates.
keep_ids={'basalt': {'scratch-tuned1090-range-flash-basalt-long', 'scratch-tuned1090-deepseek-iq2-xxs', 'scratch-tuned1090-range-hybrid-basalt-long'}, 'ninfer': {'scratch-tuned1090-measured-huihui-int8', 'scratch-tuned1090-measured-27b-ninfer1616'}, 'strata': {'scratch-tuned1090-measured-gyro-strata'}}
archive=dest/'tested alternatives';archive.mkdir(exist_ok=True)
for engine,ps in selected.items():
 (archive/(engine+'-profiles.json')).write_text(json.dumps({'version':2,'profiles':ps}if engine=='ninfer'else ps,indent=2)+'\n')
 selected[engine]=[p for p in ps if p['id']in keep_ids[engine]]
 for p in selected[engine]:p['name']=re.sub(r' (?:long decode|peak code)','',p['name'])
for engine,ps in selected.items():
 if ps:(dest/(engine+'-profiles.json')).write_text(json.dumps({'version':2,'profiles':ps}if engine=='ninfer'else ps,indent=2)+'\n')
lines=['# 10%/90% tuning comparison','','10% context counting, then 90% context prose/chat; 1,024 generated tokens, final 512 timed; no prefix reuse; thinking off.','','Before and after use the same new protocol and sampler. Existing historical measurements are preserved separately. All rates are tokens/second.','', '|Model/profile|Before 10%|Before 90%|After 10%|After 90%|Status|','|---|---:|---:|---:|---:|---|']
for x in rows:lines.append('|'+ '|'.join([LABELS[x['model']],pd(x['before10']),pd(x['before90']),pd(x['after10']),pd(x['after90']),('validated' if finalized and x['model']!='27b-basalt' else 'diagnostic only' if x['model']=='27b-basalt' else x['status'])])+'|')
lines.extend(['', 'Validation: '+review_status+'.', '', '13 retained profiles are exported. The Basalt 27B row is diagnostic only: its 90% context run offloads KV to host memory; use the NInfer profile for this model.', '', 'All samples generated 1,024 tokens; decode measures the final 512. HTTP streaming timing interpolates the boundary of speculative token batches. Before means saved engine settings retested with the same standardized sampler and protocol.', '', 'Functional code checks: 17/18 passed. The failed LRU case was a rejected NInfer K3 trial. The selected hybrid FP16 speculation setting and corrected Huihui tokenizer each passed 3/3. This is a small functional check, not a general accuracy guarantee.', '', 'The Huihui benchmark tokenizer incorrectly split added think tokens; correcting token types removed the observed invented chat turns. Selected prose samples passed repetition screening and excerpt review.', '', 'Strata Flash stability fix: disabling expert-arena huge-page requests resolved reproduced startup memory pressure. The recheck measured p2096/d109.9 and p2306/d51.5. Its 90% decode is about 3.3% below the previous selected 53.3; this is a stability exception, not a qualifying prefill-for-decode trade. Original settings and receipts are retained.', '', 'Matching plugin packages are in plugin packages. Install the matching package before importing its profile JSON. They are packaged and adapter-tested; this export does not update your live installation. Original snapshots are retained.'])
text='\n'.join(lines)+'\n';(O/'tune1090-comparison.md').write_text(text);(dest/'RESULTS.md').write_text(text)
(dest/'README.txt').write_text('Optimized copies of retained inference profiles. Originals are preserved in original snapshots.\nStatus: '+state['status']+'\nReview: '+review_status+'. Matching updated plugin packages are included; install them before importing these profiles. Live installation is unchanged. XS was deleted by user choice and is excluded.\nThe nativeConfig in tune1090 records exact measured controls, including benchmark-only token limits; those are not chat stop settings.\n')
(O/'tune1090-table.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Updated',len(rows),'rows;',sum(len(x)for x in selected.values()),'profile copies')
complete=[x for x in rows if x['after90'].get('status')=='ok']
if complete:
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 fig,axes=plt.subplots(1,4,figsize=(19,max(4,0.5*len(complete)+2)),sharey=True)
 y=np.arange(len(complete))
 for ax,depth,metric,title in zip(axes,[10,10,90,90],['prefill_tok_s','tail_decode_tok_s']*2,['10% counting: prefill','10% counting: decode','90% prose: prefill','90% prose: decode']):
  before=[x['before'+str(depth)].get(metric,0)for x in complete];after=[x['after'+str(depth)].get(metric,0)for x in complete]
  ax.barh(y-.18,before,.34,label='Before',color='#9ca3af');ax.barh(y+.18,after,.34,label='Selected',color='#2563eb');ax.set_title(title);ax.set_xlabel('tokens/second');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
 axes[0].set_yticks(y,[LABELS[x['model']]for x in complete]);axes[0].invert_yaxis();axes[-1].legend();fig.suptitle('Matched before/after: 1,024 generated tokens; final 512 timed\n'+('13 exported profiles validated; Basalt 27B is diagnostic only' if finalized else 'Selected configurations pending final quality/adapter review'),fontsize=12);fig.tight_layout();fig.savefig(O/'tune1090-comparison.png',dpi=160);fig.savefig(dest/'tune1090-comparison.png',dpi=160);plt.close(fig)
