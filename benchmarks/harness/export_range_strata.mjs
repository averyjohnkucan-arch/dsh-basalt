import {nativeSignature,memoryEvidence,verifyPack,performanceQualified,codeFunctionalEvidence} from './profile_measurement_helpers.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,dirname} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createProfile,validateProfile,runConfig} from './dsh-strata/lib/profiles.js';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115',out=join(root,'outputs/dsh-strata-range-state');await mkdir(out,{recursive:true});
const seenConfigurations=new Set();
const get=async p=>JSON.parse(await readFile(p,'utf8')),s=await get(join(root,'outputs/range-selections.json')),profiles=[],inventories=new Map();
const control=join(root,'runtimes/strata-control-0.1.59.1'),python=join(control,'python/bin/python3'),round=x=>Number(x).toFixed(1).replace(/\.0$/,'');
for(const [key,label]of [['flash_strata','Qwen3.8 Flash Next NVFP4 GPTQ INT8'],['hybrid_strata','Qwen3.8 Flash Next NVFP4 Q8 Hybrid INT8'],['flash_fp16_strata','Qwen3.8 Flash Next NVFP4 GPTQ FP16'],['hybrid_fp16_strata','Qwen3.8 Flash Next NVFP4 Q8 Hybrid FP16'],['gyro_strata','Qwen3.8 Flash Next Gyro S FP16'],['deepseek_strata','DeepSeek V4.1 Flash IQ2_XXS GSQ-RCO']])for(const kind of ['long','short']){
 if(!await performanceQualified(root,key,s))continue;
 const metrics=s[key+'_'+kind+'_metrics'],selection=s[key+'_'+kind];if(!metrics||!selection)continue;
 const c=await get(join(root,'work',selection.selected+'.json')),a=c.command,option=n=>a.includes('--'+n)?a[a.indexOf('--'+n)+1]:undefined;
 const signature=nativeSignature(c);if(kind==='short'&&seenConfigurations.has(signature))continue;
 const deepseek=key.startsWith('deepseek'),native=option('native')||'/mnt/media/AI/Models/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF/DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XXS-00001-of-00004.gguf';
 if(!inventories.has(native)){
  const raw=execFileSync('taskset',['-c','22',python,'-B',join(root,'work/dsh-strata/python/scanner.py'),dirname(native),'--files',native],{encoding:'utf8',maxBuffer:16*1024*1024,env:{...process.env,TMPDIR:join(root,'tmp')}});
  const data=JSON.parse(raw),model=data.models.find(m=>m.files.some(f=>f.path===native));if(!model)throw Error('Model header was not found by inventory');inventories.set(native,model);
 }
 const model=structuredClone(inventories.get(native)),high=metrics.high.cases.find(x=>x.case===metrics.high.worst_case);if(!high||new Set(metrics.high.cases.map(x=>x.workload)).size!==3)throw Error('Incomplete high-context genre range');
 const p=createProfile(model,18500+profiles.length),id=`scratch-range-${key.replaceAll('_','-')}-${kind}`,name=`${key==='gyro_strata'?label.replace(' FP16','')+' '+(option('kv')||'fp16').toUpperCase():label} ${kind==='short'?'peak code':'long decode'} - p${round(metrics.low.prefill)}/d${round(metrics.low.decode)} - p${round(high.prefill)}/d${round(high.decode)}`;
 const args=[];for(let i=4;i<a.length;i++){if(a[i]==='--serve'||a[i]==='--stop-eos')continue;if(['--eos','--eos-ids','--draft-log','--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache'].includes(a[i])){i++;continue;}args.push(a[i]);}
 let kv=option('kv')||'engine';if(kv==='int8')kv='Q8/Q8';if(kv==='fp16')kv='FP16/FP16';
 Object.assign(p,{id,name,context:Number(option('max-context')),kv,gpu:0,cpuSet:'0-21',mtp:option('mtp')||'',vision:'off',extraArgs:[],environment:c.env||{},applyPreset:false,portableTuning:{},runtime:{controlDir:control,python,executable:a[3],tqp:false},config:{exe:a[3],cwd:control,arch:deepseek?'deepseek41':'qwen4exp',model_name:id,host:'127.0.0.1',port:18500+profiles.length,gpu:0,tokenizer:join(option('pack'),'tokenizer'),open_browser:false,lib_dirs:[dirname(a[3])],env:c.env||{},args}});p.model.name=name;
 p.verification8192={protocol:'8192 generated; final 4096 timed',referenceProtocol:'8192-token code input; floor(80% native context) text/chat/story input; native chat template; thinking off',pairedQualified:true,answerQualityTested:false,qualityQualification:'See separate small generated-function receipts; no BF16-reference perplexity qualification',namePairMeaning:'First pair: low code; second pair: paired P/D of slowest high-context genre',metrics,selection,engineBinarySha256:c.engine_binary_sha256,gpuPowerLimitW:95,gpuPowerLimitMeaning:"Requested/default; actual enforced limit is dynamic and may be lower under load",kvCache:p.kv,benchmarkEnvironmentId:c.benchmark_environment_id||'legacy',sourceConfig:selection.selected};
 p.verification8192.hostMemoryEvidence=await memoryEvidence(root,metrics);
 p.verification8192.codeFunctionalEvidence=await codeFunctionalEvidence(root,c);
 const validated=validateProfile(p);runConfig(validated);profiles.push(validated);seenConfigurations.add(signature);
}
await writeFile(join(out,'profiles.json'),JSON.stringify(profiles,null,2)+'\n');await writeFile(join(out,'settings.json'),JSON.stringify({controlDir:control,python,executable:join(root,'runtimes/strata-engine-0.1.59/strata'),helper:join(root,'work/dsh-strata/vendor/gguf-py')},null,2)+'\n');console.log(profiles.map(p=>({id:p.id,name:p.name})));
