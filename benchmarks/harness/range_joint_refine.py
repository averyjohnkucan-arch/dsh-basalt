"""Targeted joint CPU/VRAM checks for the primary long-context MoE presets."""
from range_tuner import *
from range_identity import config_id
key,family=sys.argv[1:3]
if family!='qwen'or key.startswith('gyro')or'fp16'in key:raise SystemExit(0)
state=read(O/'range-selections.json');selection=state[key+'_long'];base=read(R/'bench'/selection['selected']/'result.json')['config'];ident=config_id(base)
row=next(x for x in selection['candidates']if x['identity']==ident);genre=row['worst_genre']
variants=[('reserve256',{'--vram-reserve-mib':256}),('reserve256-workers14',{'--vram-reserve-mib':256,'--pool-workers':14}),('reserve256-resident96k',{'--vram-reserve-mib':256,'--kv-resident':98304})]
plan=O/(key+'-repeatability-plan.json');data=read(plan);known={config_id(read(R/'bench'/x['case']/'result.json')['config'])for x in data['selection']['candidates']}
added=[]
for label,changes in variants:
 c=changed(base,changes);candidate=config_id(c)
 if candidate in known:continue
 r=run(c,key+'-joint-'+candidate+'-'+genre,family,genre)
 if r['status']!='ok':continue
 item=dict(case=name(r),prefill=r['prefill_tok_s'],decode=r['tail_decode_tok_s'],source='joint reserve/CPU/KV refinement');data['selection']['candidates'].append(item);known.add(candidate);added.append(item);plan.write_text(json.dumps(data,indent=2))
if added:subprocess.run([sys.executable,str(W/'range_repeatability.py'),key,family],check=True)
save(key+'_joint_refinements',state.get(key+'_joint_refinements',[])+added);print('JOINT REFINEMENT COMPLETE',key,flush=True)
