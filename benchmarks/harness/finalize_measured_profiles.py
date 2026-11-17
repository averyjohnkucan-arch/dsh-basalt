from pathlib import Path
import json,hashlib
r=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');summary={}
for engine,state,names in [('basalt','dsh-basalt-fp16-measured-state',['fp16-plugin-flash','fp16-plugin-hybrid']),('ninfer','dsh-ninfer-measured-state',['ninfer1616-measured-plugin'])]:
 path=r/'outputs'/state/'profiles.json';data=json.loads(path.read_text());profiles=data if isinstance(data,list) else data['profiles']
 for name in names:
  receipt=r/'validation'/name/'adapter-result.json';d=json.loads(receipt.read_text());assert d['status']=='ok' and d['arithmeticSanity'] and d['nativeCommandEvidence']['status']=='ok'
  p=next(x for x in profiles if x['id']==d['profile'])
  # Bind proof to the exact profile used; qualification metadata may be updated afterward.
  for k,v in d['savedProfile'].items():
   if k not in ['qualification','pluginValidation']:assert p.get(k)==v,(name,k)
  proof={'status':'passed','receipt':str(receipt),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'arithmeticSanity':True,'nativeControls':d['nativeCommandEvidence']['checkedControls'],'projectionModes':d.get('projectionModes',{}).get('status'),'scope':'Actual adapter GPU launch; exact measured native controls; not throughput remeasurement or general quality proof'}
  p['pluginValidation']=proof;p['qualification']='Measured candidate; actual DSH adapter GPU launch and native controls verified; no global maximum claim'+('; generated-function checks2/3 passed' if engine=='ninfer' else '')
  summary[p['id']]=proof
 path.write_text(json.dumps(data,indent=2)+'\n')
(r/'outputs/measured-profile-launch-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Verified and annotated',len(summary),'profiles')
