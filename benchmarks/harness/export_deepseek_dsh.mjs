import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {inspectModel,newProfile,validateProfile,serverConfig} from './dsh-basalt/lib/models.js';
import {runtimeStatus} from './dsh-basalt/lib/runtime.js';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115';
const output=root+'/outputs/dsh-basalt-deepseek-measured-state';
await mkdir(output,{recursive:true});
const runtimeDir=root+'/runtimes/basalt-deepseek-split';
const runtime=await runtimeStatus(runtimeDir);
if(!runtime.ready || !runtime.features.includes('deepseek_external_engram'))
 throw Error('Required tested runtime unavailable');
const profiles=[];
for(const quant of ['xxs','xs']){
 const source=JSON.parse(await readFile(root+'/outputs/deepseek-measured-profiles/deepseek-iq2-'+quant+'.json','utf8'));
 const model=await inspectModel(source.model.path);
 const profile=newProfile(model);
 const option=flag=>source.command[source.command.indexOf(flag)+1];
 Object.assign(profile,{
  id:'scratch-deepseek-iq2-'+quant,
  name:source.name,model:{...model,name:source.name},
  context:1048576,kv:'fp8',vision:false,defaultEffort:'off',
  runtimeDir,diskCacheMiB:0,ramCacheMiB:0,vramReserveMiB:700,
  engineOptions:{spec:0,'pool-workers':21,'resident-budget-gib':102.3,
   'expert-profile':option('--expert-profile'),
   'deepseek-engram-gguf':option('--deepseek-engram-gguf')},
  measuredPerformance:source.metrics,
  qualification:'Measured native controls; DSH launch configuration validated, full plugin GPU launch pending',
 });
 validateProfile(profile);
 const launch=serverConfig(profile,18081,output+'/cache/'+profile.id);
 if(launch.models[0]['resident-budget-gib']!==102.3 || launch.models[0].model!==source.model.path)
  throw Error('Launch controls changed');
 profiles.push(profile);
 await writeFile(output+'/'+profile.id+'-server.json',JSON.stringify(launch,null,2)+'\n');
}
await writeFile(output+'/profiles.json',JSON.stringify(profiles,null,2)+'\n');
await writeFile(output+'/validation.json',JSON.stringify({
 status:'schema-and-launch-config-passed',runtime,profiles:profiles.map(p=>({id:p.id,name:p.name})),
 thinking:'Off matches benchmark; native DeepSeek effort vocabulary retained',
 liveInstallation:'pending',gpuPluginValidation:'pending'
},null,2)+'\n');
console.log(profiles.map(p=>p.name).join('\n'));
