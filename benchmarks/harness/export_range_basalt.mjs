import {nativeSignature,memoryEvidence,verifyPack,performanceQualified,codeFunctionalEvidence} from './profile_measurement_helpers.mjs';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {join,dirname} from 'node:path';
import {inspectModel,newProfile,validateProfile,serverConfig} from './dsh-basalt/lib/models.js';
import {runtimeStatus} from './dsh-basalt/lib/runtime.js';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115',out=join(root,'outputs/dsh-basalt-range-state');await mkdir(out,{recursive:true});
const archive=join(out,'validated-profiles');await mkdir(archive,{recursive:true});
const get=async p=>JSON.parse(await readFile(p,'utf8')),s=await get(join(root,'outputs/range-selections.json')),profiles=[],records=[];
const seenConfigurations=new Set();
const round=x=>Number(x).toFixed(1).replace(/\.0$/,'');
for(const [key,label]of [['flash_basalt','Flash Next NVFP4 GPTQ INT8'],['hybrid_basalt','Flash Next mixed NVFP4 Q8 INT8'],['flash_fp16_basalt','Flash Next NVFP4 GPTQ FP16'],['hybrid_fp16_basalt','Flash Next mixed NVFP4 Q8 FP16'],['27b_basalt','Qwen 3.8 27B NVFP4-full INT8 KV'],['deepseek_basalt','DeepSeek V4.1 Flash IQ2_XXS GSQ-RCO'],['deepseek_xs_basalt','DeepSeek V4.1 Flash IQ2_XS GSQ-RCO']]){
 for(const kind of ['long','short']){
  if(!await performanceQualified(root,key,s))continue;
 const metrics=s[key+'_'+kind+'_metrics'],selection=s[key+'_'+kind];if(!metrics||!selection)continue;
  const c=await get(join(root,'work',selection.selected+'.json')),args=c.command,option=n=>args.includes('--'+n)?args[args.indexOf('--'+n)+1]:undefined;
  const signature=nativeSignature(c);if(kind==='short'&&seenConfigurations.has(signature)){records.push({key,kind,status:'same controls as long preset'});continue;}
  const high=metrics.high.cases.find(x=>x.case===metrics.high.worst_case);if(!high||new Set(metrics.high.cases.map(x=>x.workload)).size!==3)throw Error('Incomplete high-context range');
  let model;try{model=await inspectModel(option('model'));}catch(error){const saved=join(archive,`scratch-range-${key.replaceAll('_','-')}-${kind}.json`);let archivedProfile;try{await stat(saved);archivedProfile=saved;}catch(e){if(e.code!=='ENOENT')throw e;}records.push({key,kind,status:'artifact unavailable; reconstruction recipe required',archivedProfile,error:error.message});continue;}
  await verifyPack(c);
  const p=newProfile(model),name=`${label} ${kind==='short'?'peak code':'long decode'} - p${round(metrics.low.prefill)}/d${round(metrics.low.decode)} - p${round(high.prefill)}/d${round(high.decode)}`;
  Object.assign(p,{id:`scratch-range-${key.replaceAll('_','-')}-${kind}`,name,context:Number(option('max-context')),kv:option('kv'),diskCacheMiB:0,ramCacheMiB:0,vision:false,defaultEffort:model.architecture==='deepseek41'?'high':'medium',engineOptions:{}});p.model={...model,name};
  const numeric=model.architecture==='qwen35'?['spec','kv-resident']:['spec','pool-workers','resident-budget-gib','kv-resident','prefill-cpu-share','draft-experts','adapt-swaps'];
  const textual=model.architecture==='qwen35'?[]:['pool-affinity','prefill','expert-profile',...(model.architecture==='deepseek41'?['deepseek-engram-gguf']:[])];
  for(const n of numeric)if(option(n)!==undefined)p.engineOptions[n]=Number(option(n));
  for(const n of textual)if(option(n)!==undefined)p.engineOptions[n]=n==='prefill'&&/^\d+$/.test(option(n))?Number(option(n)):option(n);
  p.runtimeDir=dirname(dirname(args[3]));
  p.vramReserveMiB=Number(option('vram-reserve-mib')||700);
  p.verification8192={protocol:'8192 generated; final 4096 timed',referenceProtocol:'8192-token code input; floor(80% native context) text/chat/story input; native chat template; thinking off',pairedQualified:true,answerQualityTested:false,qualityQualification:'Separate small independent generated-function receipts; no BF16-reference perplexity qualification',namePairMeaning:'First pair: low code; second pair: paired P/D of slowest high-context genre',metrics,selection,engineBinarySha256:c.engine_binary_sha256,artifactHeaderSha256:c.artifact_header_sha256,artifactBytes:c.artifact_bytes,gpuPowerLimitW:95,gpuPowerLimitMeaning:"Requested/default; actual enforced limit is dynamic and may be lower under load",kvCache:p.kv,benchmarkEnvironmentId:c.benchmark_environment_id||'legacy',sourceConfig:selection.selected};
  if(c.benchmark_memory_policy_id)p.verification8192.benchmarkMemoryPolicyId=c.benchmark_memory_policy_id;
  p.verification8192.hostMemoryEvidence=await memoryEvidence(root,metrics);
 p.verification8192.codeFunctionalEvidence=await codeFunctionalEvidence(root,c);
  validateProfile(p);profiles.push(p);seenConfigurations.add(signature);await writeFile(join(archive,p.id+'.json'),JSON.stringify(p,null,2)+'\n');await writeFile(join(out,p.id+'-native-config.json'),JSON.stringify(serverConfig(p,18081,join(root,'dsh-cache',p.id)),null,2)+'\n');records.push({key,kind,status:'available',profileId:p.id,name,archivedProfile:join(archive,p.id+'.json')});
 }
}
const settings={runtimeDir:join(root,'runtimes/basalt-custom-latest'),coresKeptFree:2,python:join(root,'tools/build-env/bin/python')},runtime=await runtimeStatus(settings.runtimeDir);if(!runtime.ready)throw Error(runtime.error);
await writeFile(join(out,'profiles.json'),JSON.stringify(profiles,null,2)+'\n');await writeFile(join(out,'settings.json'),JSON.stringify(settings,null,2)+'\n');await writeFile(join(root,'outputs/range-basalt-profile-status.json'),JSON.stringify({scope:'Scratch export only; installed DSH state untouched',runtime,profiles:records},null,2)+'\n');console.log(JSON.stringify(records));
