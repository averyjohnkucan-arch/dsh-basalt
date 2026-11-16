"""Close saved profile ranges over all completed, same-controls, full-output observations."""
from range_common import R,W,O,read,read_case_mapping,summarize,name
from range_identity import config_id
import json,sys,time
key=sys.argv[1];path=O/'range-selections.json';state=read(path);rows=[]
for p in(R/'bench').glob('range-*/result.json'):
 r=read_case_mapping(p)
 if r is None:continue
 c=r.get('config',{})
 if r.get('status')=='ok'and r.get('generated')==8192 and c.get('generate')==8192 and c.get('host_memory_policy')and r.get('cold_prefill_qualified',True)and not r.get('reused_tokens',0)and name(r)==p.parent.name:rows.append(r)
by_case={name(r):r for r in rows};changes=[]
for kind in ['long','short']:
 selection=state.get(key+'_'+kind);old=state.get(key+'_'+kind+'_metrics')
 if not selection or not old:continue
 ident=config_id(read(R/'bench'/selection['selected']/'result.json')['config'])
 depths={x['workload']:by_case[x['case']]['config']['depth']for x in old['high']['cases']};depths['code']=by_case[old['low']['case']]['config']['depth']
 matched=[r for r in rows if config_id(r['config'])==ident and r['config'].get('depth')==depths.get(r['config'].get('workload'))]
 low=sorted([r for r in matched if r['config'].get('workload')=='code'],key=name)
 order={'text':0,'chat':1,'story':2};high=sorted([r for r in matched if r['config'].get('workload')in order],key=lambda r:(order[r['config']['workload']],name(r)))
 assert low and {r['config']['workload']for r in high}==set(order),'Incomplete same-controls observations'
 low_cases=[dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'])for r in low]
 updated=dict(old,low=min(low_cases,key=lambda r:r['decode']),low_cases=low_cases,high=summarize(high))
 changes.append(dict(kind=kind,identity=ident,changed=updated!=old,old_high_cases=[x['case']for x in old['high']['cases']],high_cases=[name(r)for r in high],old_high_decode_range=old['high']['decode_range'],high_decode_range=updated['high']['decode_range'],old_low=old['low'],low=updated['low']))
 state[key+'_'+kind+'_metrics']=updated
if any(x['changed']for x in changes):
 temp=path.with_suffix('.refresh.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(path)
folder=O/'range-metric-refresh';folder.mkdir(exist_ok=True)
(folder/(key+'.json')).write_text(json.dumps(dict(model_key=key,status='refreshed',at_unix=time.time(),scope='Measured range/name observations only; engine controls and tuning selection are unchanged. Includes completed repeat measurements at the same settings and exact workload depth.',changes=changes),indent=2)+'\n')
print('PROFILE RANGE OBSERVATIONS REFRESHED',key,json.dumps(changes),flush=True)
