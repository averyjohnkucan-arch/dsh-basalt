"""Offline inspection receipts; repetition is disclosed, never silently filtered from timing."""
from pathlib import Path
import collections,hashlib,json,sys
from prepare_range_fixtures import tokenizer_for
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');O=R/'outputs';B=R/'bench'
key,family=sys.argv[1:3];s=json.loads((O/'range-selections.json').read_text());tok,_=tokenizer_for(family)
old_keys={'flash_basalt':'flash_old_metrics','flash_strata':'flash_old_metrics','hybrid_basalt':'hybrid_old_metrics','hybrid_strata':'hybrid_old_metrics','flash_fp16_basalt':'flash_fp16_old_metrics','flash_fp16_strata':'flash_fp16_old_metrics','hybrid_fp16_basalt':'hybrid_fp16_old_metrics','hybrid_fp16_strata':'hybrid_fp16_old_metrics'}
metric_keys=[key+'_long_metrics',key+'_short_metrics',old_keys.get(key,key+'_old_metrics')];cases={}
for metric_key in metric_keys:
 metrics=s.get(metric_key)
 if not metrics:continue
 for item in [metrics['low'],*metrics['high']['cases']]:cases.setdefault(item['case'],[]).append(metric_key)
if len(sys.argv)>3:cases={case:['explicit diagnostic candidate; not a final selection']for case in sys.argv[3:]}
rows=[]
for case,roles in cases.items():
 folder=B/case;r=json.loads((folder/'result.json').read_text());assert r['status']=='ok'and r['generated']==8192
 if(folder/'tokens.json').exists():ids=json.loads((folder/'tokens.json').read_text());text=tok.decode(ids)
 else:
  completion=json.loads((folder/'completion.json').read_text());ids=completion.get('tokens',[]);text=(folder/'content.txt').read_text()
 assert len(ids)==8192 and hashlib.sha256(','.join(map(str,ids)).encode()).hexdigest()==r['token_sha256']
 (folder/'content.txt').write_text(text)
 paragraphs=[p.strip()for p in text.split('\n\n')if len(p.strip())>=160];counts=collections.Counter(paragraphs)
 duplicate_count=sum(n-1 for n in counts.values()if n>1)
 windows=[tuple(ids[i:i+16])for i in range(len(ids)-15)];repeated_fraction=(len(windows)-len(set(windows)))/len(windows)
 rows.append(dict(case=case,roles=roles,workload=r['config']['workload'],tokens=len(ids),text_sha256=hashlib.sha256(text.encode()).hexdigest(),token_sha256=r['token_sha256'],exact_duplicate_long_paragraphs=duplicate_count,long_paragraphs=len(paragraphs),duplicate_16_token_window_fraction=repeated_fraction,duplicate_16_token_windows=len(windows)-len(set(windows)),exact_long_paragraph_repetition_observed=duplicate_count>0,repeated_16_token_windows_observed=repeated_fraction>0,generated_content=str(folder/'content.txt'),start=text[:200],end=text[-200:]))
folder=O/'output-audits';folder.mkdir(exist_ok=True)
receipt=dict(schema_version=2,model_key=key,status='inspected',scope='Actual selected or explicitly named diagnostic continuation text only; not a semantic, BF16-reference or universal quality qualification. Exact repeated long paragraphs and repeated 16-token windows are separate diagnostics. Token-window repetition can reflect legitimate phrases as well as repetitive templates, and is not by itself a quality failure. Repetitive continuations remain included in measured throughput.',cases=rows,exact_repeated_long_paragraph_cases=[x['case']for x in rows if x['exact_long_paragraph_repetition_observed']],repeated_16_token_window_cases=[x['case']for x in rows if x['repeated_16_token_windows_observed']])
(folder/(key+'.json')).write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print('OUTPUT INSPECTION',key,len(rows),'cases;',len(receipt['exact_repeated_long_paragraph_cases']),'with exact repeated long paragraphs',flush=True)
