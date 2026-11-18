from pathlib import Path
import json,subprocess,time,copy,sys,re,collections
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';D=W/'tune1090';py=R/'tools/build-env/bin/python'
while True:
 v=json.loads((O/'tune1090-profile-validation.json').read_text())
 if len(v)==13 and all(x['status']=='ok' for x in v):break
 if time.time()-Path('/tmp/recheck_strata_no_thp.py').stat().st_mtime>600:raise RuntimeError('Validation incomplete')
 time.sleep(5)
state=json.loads((O/'tune1090-progress.json').read_text());key='range-flash-strata-long';pair={}
sys.path.insert(0,str(W));from prepare_range_fixtures import tokenizer_for
tok=tokenizer_for('qwen')[0]
for pct,side in [(10,'low'),(90,'high')]:
 cfg=copy.deepcopy(state['models'][key]['selected'][side]['config']);cfg['env']['STRATA_NO_ARENA_THP']='1';cfg['host_memory_policy'].update(memory_high_gib=110,memory_max_gib=110,pressure_avg10_limit=10,pressure_grace_s=1,minimum_host_available_gib=3)
 out=R/'bench'/f'tune1090-strata-no-thp-{pct}';cfg['output']=str(out);path=D/f'strata-no-thp-{pct}.json';path.write_text(json.dumps(cfg,indent=2))
 print('START',pct,flush=True)
 with (D/f'strata-no-thp-{pct}.log').open('w') as log:proc=subprocess.run([str(py),str(W/'native_bench.py'),'--config',str(path)],stdout=log,stderr=subprocess.STDOUT)
 d=json.loads((out/'result.json').read_text());assert d['status']=='ok',d.get('error');assert d['generated']==1024
 text=tok.decode(json.loads((out/'tokens.json').read_text()));(out/'content.txt').write_text(text);words=re.findall(r'\w+',text.lower());grams=collections.Counter(tuple(words[i:i+8])for i in range(max(0,len(words)-7)))
 screen={'words':len(words),'unique8gram_fraction':len(grams)/max(1,sum(grams.values())),'max8gram_repeat':max(grams.values(),default=0),'review_required':max(grams.values(),default=0)>3}
 if pct==10:
  nums=[int(x)for x in re.findall(r'\d+',text)];screen['counting_prefix_correct']=all(n==i+1 for i,n in enumerate(nums[:-1]));assert screen['counting_prefix_correct']
 assert not screen['review_required'];d['output_screen']=screen;(out/'result.json').write_text(json.dumps(d,indent=2));pair[str(pct)]=d;print('DONE',pct,d['prefill_tok_s'],d['tail_decode_tok_s'],flush=True)
for key in ['range-flash-strata-long','range-flash-strata-short']:
 model=state['models'][key];model['trials']['no-thp']=pair;model['selected'].update(candidate='no-thp',sourceProfileKey='range-flash-strata-long',sourceCandidate='no-thp',low=pair['10'],high=pair['90'],stabilityFix='Disable expert-arena huge-page request after compaction pressure killed desktop; remeasured both depths')
(O/'tune1090-progress.json').write_text(json.dumps(state,indent=2)+'\n');print('RECHECK_COMPLETE',flush=True)
