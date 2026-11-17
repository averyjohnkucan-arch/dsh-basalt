import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {dirname} from 'node:path';
import {inspectModel,newProfile,validateProfile,serverConfig} from './dsh-basalt/lib/models.js';
const r='/mnt/media/scratch/dsh-inference-tuning-20261115',out=r+'/outputs/dsh-basalt-fp16-measured-state';
await mkdir(out,{recursive:true});
const rows=JSON.parse(await readFile(r+'/outputs/flash-fp16-matched-depths.json','utf8')),profiles=[];
for(const family of ['flash','hybrid']){
 const low=rows[family+'-basalt-code10'],high=rows[family+'-basalt-chat90'];
 if(low.status!=='ok'||high.status!=='ok')throw Error('Incomplete measurements');
 const c=JSON.parse(await readFile(high.case+'/result.json','utf8')).config,a=c.command;
 const option=n=>{const i=a.indexOf('--'+n);return i<0?undefined:a[i+1]};
 const model=await inspectModel(option('model'));const p=newProfile(model);
 const name=`Flash Next ${family==='hybrid'?'NVFP4 Q8 hybrid':'NVFP4 GPTQ'} FP16 p${Math.round(low.prefill_tok_s)}/d${Math.round(low.tail_decode_tok_s)} p${Math.round(high.prefill_tok_s)}/d${Math.round(high.tail_decode_tok_s)}`;
 Object.assign(p,{id:'scratch-measured-'+family+'-fp16',name,model:{...model,name},context:262144,kv:'fp16',vision:false,defaultEffort:'medium',runtimeDir:dirname(dirname(a[3])),ramCacheMiB:0,diskCacheMiB:0,vramReserveMiB:700,engineOptions:{},measuredPerformance:{protocol:'10% code and90% prose;512 output; final256 decode; thinking off during timing',low,high},qualification:'Measured candidate, not proven maximum; schema/launch config validated; plugin GPU launch pending'});
 for(const key of ['spec','pool-workers','resident-budget-gib','kv-resident'])if(option(key)!==undefined)p.engineOptions[key]=Number(option(key));
 validateProfile(p);const launch=serverConfig(p,18081,out+'/cache/'+p.id);
 if(launch.models[0].model!==option('model'))throw Error('Model changed');
 profiles.push(p);await writeFile(out+'/'+p.id+'-server.json',JSON.stringify(launch,null,2)+'\n');
}
await writeFile(out+'/profiles.json',JSON.stringify(profiles,null,2)+'\n');
console.log(profiles.map(p=>p.name).join('\n'));
