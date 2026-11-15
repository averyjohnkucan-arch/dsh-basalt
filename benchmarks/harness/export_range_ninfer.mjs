import {nativeSignature,memoryEvidence,verifyPack,performanceQualified,codeFunctionalEvidence} from './profile_measurement_helpers.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
import {freshProfile,normalizeProfile,ninferArgs} from './dsh-ninfer/lib/profiles.js';
import {qwen38Reasoning} from './dsh-ninfer/lib/reasoning.js';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115',out=join(root,'outputs/dsh-ninfer-range-state');await mkdir(out,{recursive:true});
const seenConfigurations=new Set();
const get=async p=>JSON.parse(await readFile(p,'utf8')),s=await get(join(root,'outputs/range-selections.json')),profiles=[];
const round=x=>Number(x).toFixed(1).replace(/\.0$/,'');
for(const [key,label]of [['27b_ninfer','Qwen 3.8 27B NVFP4-full NVFP4 KV'],['huihui_nvfp4_ninfer','Qwen 3.8 27B IQ3_S Huihui NVFP4 KV'],['huihui_int8_ninfer','Qwen 3.8 27B IQ3_S Huihui INT8 KV'],['huihui_fp8_ninfer','Qwen 3.8 27B IQ3_S Huihui FP8 KV']])for(const kind of ['long','short']){
 if(!await performanceQualified(root,key,s))continue;
 const metrics=s[key+'_'+kind+'_metrics'],selection=s[key+'_'+kind];if(!metrics||!selection)continue;
 const c=await get(join(root,'work',selection.selected+'.json')),a=c.command,options={};let i=5;
 while(i<a.length){const flag=a[i++];if(!flag.startsWith('--'))throw Error('Unexpected positional engine argument');options[flag]=i<a.length&&!a[i].startsWith('--')?a[i++]:true;}
 const signature=nativeSignature(c);if(kind==='short'&&seenConfigurations.has(signature))continue;
 const high=metrics.high.cases.find(x=>x.case===metrics.high.worst_case);if(!high||new Set(metrics.high.cases.map(x=>x.workload)).size!==3)throw Error('Incomplete high-context genre range');
 const id=`scratch-range-${key.replaceAll('_','-')}-${kind}`,p=freshProfile('ninfer');
 Object.assign(p,{id,name:`${label} ${kind==='short'?'peak code':'long decode'} - p${round(metrics.low.prefill)}/d${round(metrics.low.decode)} - p${round(high.prefill)}/d${round(high.decode)}`,modelPath:a[4],executable:a[3],context:Number(options['--max-context']),port:18400+profiles.length,options,locks:[],environment:c.env||{}});
 delete options['--host'];delete options['--port'];delete options['--max-context'];options['--model-id']=id;
 p.reasoning=qwen38Reasoning();p.reasoning.defaultEffort='off';p.verification8192={protocol:'8192 generated; final 4096 timed',referenceProtocol:'8192-token code input; floor(80% native context) text/chat/story input; native chat template; thinking off',pairedQualified:true,answerQualityTested:false,qualityQualification:'Separate generated-function receipts; no full BF16-reference quality qualification',namePairMeaning:'First pair: low code; second pair: paired P/D of slowest high-context genre',metrics,selection,engineBinarySha256:c.engine_binary_sha256,gpuPowerLimitW:95,gpuPowerLimitMeaning:"Requested/default; actual enforced limit is dynamic and may be lower under load",kvCache:options['--kv-dtype'],benchmarkEnvironmentId:c.benchmark_environment_id||'legacy',sourceConfig:selection.selected};
 p.verification8192.hostMemoryEvidence=await memoryEvidence(root,metrics);
 p.verification8192.codeFunctionalEvidence=await codeFunctionalEvidence(root,c);
 const validated=normalizeProfile(p,'ninfer');ninferArgs(validated);profiles.push(validated);seenConfigurations.add(signature);
}
await writeFile(join(out,'profiles.json'),JSON.stringify({version:2,profiles},null,2)+'\n');await writeFile(join(out,'settings.json'),JSON.stringify({scope:'Scratch export only; latest executable and per-backend calibration overridden per profile; installed DSH state untouched'},null,2)+'\n');console.log(profiles.map(p=>({id:p.id,name:p.name,executable:p.executable})));
