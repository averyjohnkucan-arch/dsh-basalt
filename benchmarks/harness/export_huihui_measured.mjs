import {readFile,writeFile,copyFile} from 'node:fs/promises';
import {freshProfile,normalizeProfile,ninferArgs} from './dsh-ninfer/lib/profiles.js';
import {qwen38Reasoning} from './dsh-ninfer/lib/reasoning.js';
const r='/mnt/media/scratch/dsh-inference-tuning-20261115',file=r+'/outputs/dsh-ninfer-measured-state/profiles.json';
const state=JSON.parse(await readFile(file,'utf8'));const report=[];
for(const kv of ['int8','fp8','nvfp4']){
 const id='scratch-measured-huihui-'+kv;
 if(state.profiles.some(p=>p.id===id))throw Error('Profile already exists: '+id);
 const base=kv==='int8'?'quiet-ninfer-huihui-int8-old':'latest-remaining-huihui-'+kv;
 const load=async depth=>{const path=r+'/bench/'+base+'-'+depth;const d=JSON.parse(await readFile(path+'/result.json','utf8'));if(d.status!=='ok'||d.generated!==1024)throw Error('Incomplete receipt');return {case:path,...Object.fromEntries(['status','prefill_tok_s','tail_decode_tok_s','generated','reused_tokens'].map(k=>[k,d[k]])),config:d.config};};
 const low=await load(10),high=await load(90),c=high.config,a=c.command,options={};
 for(let i=5;i<a.length;){const flag=a[i++];if(!flag.startsWith('--'))throw Error('Unexpected flag');options[flag]=i<a.length&&!a[i].startsWith('--')?a[i++]:true;}
 for(const flag of ['--host','--port','--max-context'])delete options[flag];options['--model-id']=id;
 const p=freshProfile('ninfer');Object.assign(p,{id,name:`Huihui IQ3_S ${kv.toUpperCase()} KV p${Math.round(low.prefill_tok_s)}/d${Math.round(low.tail_decode_tok_s)} p${Math.round(high.prefill_tok_s)}/d${Math.round(high.tail_decode_tok_s)}`,modelPath:a[4],executable:a[3],context:262144,port:18400,options,locks:[],environment:c.env||{},reasoning:qwen38Reasoning()});
 p.reasoning.defaultEffort='medium';delete low.config;delete high.config;
 p.measuredPerformance={protocol:'Saved matched fixture10%/90%;1024 output,final512 decode; thinking off during timing',low,high};p.qualification='Measured native configuration; actual exported adapter launch pending; no global maximum claim';p.selectionReason=kv==='int8'?'Retain saved engine/settings: latest candidate lost17.4% long decode':kv==='fp8'?'Latest candidate improved long prefill11.9% and decode2.5%':'Latest candidate improves long prefill13.5%, costs4.8% decode in single comparison';
 const normalized=normalizeProfile(p,'ninfer');ninferArgs(normalized);state.profiles.push(normalized);report.push({id,name:p.name,executable:p.executable,selectionReason:p.selectionReason});
}
await copyFile(file,file+'.before-huihui');await writeFile(file,JSON.stringify(state,null,2)+'\n');await writeFile(r+'/outputs/huihui-profile-export.json',JSON.stringify({status:'schema-validated',profiles:report},null,2)+'\n');console.log(report);
