import {readFile,writeFile,mkdir,realpath} from 'node:fs/promises';
import {join} from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';
const execFileAsync=promisify(execFile);
const root='/mnt/media/scratch/dsh-inference-tuning-20261115';
const [engine,id,destination]=process.argv.slice(2);
if(!['basalt','ninfer','strata'].includes(engine)||!id?.startsWith('scratch-range-')||!destination?.startsWith(root+'/validation/'))throw Error('Explicit scratch profile and output required');
const state=join(root,'outputs',`dsh-${engine}-range-state`),ctx={get:()=>undefined};
let service,adapter;
const originalFetch=globalThis.fetch,wireRequests=[];
globalThis.fetch=async(input,init)=>{
 try {
  const body=typeof init?.body==='string'?JSON.parse(init.body):null;
  if(body?.model===id&&Array.isArray(body.messages))wireRequests.push({effort:body.reasoning_effort,projection:body.experimental_speed_projection,messagesSha256:createHash('sha256').update(JSON.stringify(body.messages)).digest('hex')});
 } catch {}
 return originalFetch(input,init);
};
function nativeOptions(args){
 const flags={};
 for(let i=0;i<args.length;i++)if(args[i].startsWith('--'))flags[args[i]]=i+1<args.length&&!args[i+1].startsWith('--')?args[++i]:true;
 return flags;
}
async function verifyNativeCommand(profile){
 const selected=JSON.parse(await readFile(join(root,'work',profile.verification8192.sourceConfig+'.json'),'utf8'));
 const expectedExe=await realpath(selected.command[3]);
 const ownCgroup=(await readFile('/proc/self/cgroup','utf8')).trim().split('\n').find(x=>x.startsWith('0::')).slice(3);
 if(!ownCgroup.endsWith('.scope'))throw Error('GPU validation requires an explicitly owned systemd scope');
 const pids=(await readFile('/sys/fs/cgroup'+ownCgroup+'/cgroup.procs','utf8')).trim().split(/\s+/),matches=[];
 for(const pid of pids){
  try{if(await realpath('/proc/'+pid+'/exe')!==expectedExe)continue;
   const args=(await readFile('/proc/'+pid+'/cmdline','utf8')).split('\0').filter(Boolean);matches.push({pid:Number(pid),args});
  }catch(error){if(error.code!=='ENOENT')throw error;}
 }
 if(matches.length!==1)throw Error('Expected exactly one selected native engine in the owned validation scope');
 const actual=matches[0],expected=nativeOptions(selected.command.slice(4)),observed=nativeOptions(actual.args.slice(1));
 const transport=new Set(['--serve','--eos','--eos-ids','--stop-eos','--draft-log','--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache','--host','--port','--model-id','--api-key']);
 const checked={};
 for(const [flag,value]of Object.entries(expected)){
  if(transport.has(flag))continue;
  if(observed[flag]!==value)throw Error(`Plugin native control mismatch for ${flag}: expected ${value}, observed ${observed[flag]}`);
  checked[flag]=value;
 }
 if(engine==='ninfer'&&actual.args[1]!==selected.command[4])throw Error('Plugin launched a different NInfer model artifact');
 if(observed['--max-context']!==String(profile.context))throw Error('Plugin native context differs from exported capacity');
 const args=[...actual.args];if(args.includes('--api-key'))args[args.indexOf('--api-key')+1]='REDACTED';
 const {stdout:gpuProcesses}=await execFileAsync('nvidia-smi',['--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader,nounits'],{timeout:10000});
 const gpuProcess=gpuProcesses.split('\n').find(line=>Number(line.split(',')[0])===actual.pid);
 if(!gpuProcess)throw Error('Selected native engine PID is not present in the GPU process list');
 const {stdout:power}=await execFileAsync('nvidia-smi',['--id=0','-q','-d','POWER'],{timeout:10000});
 const reading=(label,optional=false)=>{const line=power.split(String.fromCharCode(10)).find(x=>x.trim().startsWith(label));const value=line?Number(line.slice(line.indexOf(':')+1).trim().split(' ')[0]):NaN;if(!Number.isFinite(value)){if(optional)return null;throw Error('Missing GPU power reading: '+label);}return value;};
 const requested=reading('Requested Power Limit',true),enforced=reading('Current Power Limit'),defaultLimit=reading('Default Power Limit');
 const maximum=reading('Max Power Limit');if(defaultLimit!==95||maximum!==110||enforced<=0||enforced>maximum+.5)throw Error('GPU default/maximum power policy changed from the qualified setup');
 return {status:'ok',pid:actual.pid,executable:expectedExe,args,checkedControls:checked,cgroup:ownCgroup,gpuProcess:gpuProcess.trim(),requestedPowerLimitW:requested,observedEnforcedPowerLimitW:enforced,defaultPowerLimitW:defaultLimit,maximumPowerLimitW:maximum};
}
if(engine==='ninfer'){
 const {Runtime}=await import('./dsh-ninfer/lib/runtime.js');
 const {LocalAdapter}=await import('./dsh-ninfer/lib/adapter.js');
 service=new Runtime('ninfer',{dataDir:state});adapter=new LocalAdapter(ctx,service,'NInfer');
}else{
 const name=engine==='basalt'?'Basalt':'Strata';
 const module=await import(`./dsh-${engine}/lib/service.js`),adapters=await import(`./dsh-${engine}/lib/adapter.js`);
 service=new module[name+'Service']({dataDir:state});adapter=new adapters[name+'Adapter'](ctx,service);
}
const started=Date.now(),record={schemaVersion:2,pluginSourceSha256:process.env.DSH_PLUGIN_SOURCE_SHA256,engine,profile:id,status:'failed',qualification:'Actual DSH adapter stream and plugin-owned GPU worker; tiny arithmetic sanity, not a model-quality or throughput benchmark'};
const timer=setTimeout(()=>process.exit(124),600000);timer.unref();
try{
 await service.init();
 const profile=service.profiles.find(p=>p.id===id);if(!profile)throw Error('Qualified exported profile missing');
 record.profileName=profile.name;record.savedContext=profile.context;record.savedVerification=profile.verification8192;
 record.savedProfile=profile;
 const signal=AbortSignal.timeout(540000),call=await adapter.prepareCall(engine,id,signal),chunks=[];
 for await(const chunk of call.stream({provider:engine,model:id,system:'Answer arithmetic briefly.',messages:[{role:'user',content:[{type:'text',text:'Calculate 2+2. Reply only with the single digit.'}]}],maxTokens:32,reasoningEffort:'off',signal}))chunks.push(chunk);
 record.chunks=chunks;record.text=chunks.filter(c=>c.type==='text-delta').map(c=>c.text).join('');
 record.arithmeticSanity=/^\s*4[.!]?\s*$/.test(record.text);
 record.finish=chunks.findLast(c=>c.type==='finish');
 if(!record.arithmeticSanity||!record.finish)throw Error('Arithmetic sanity or finish event missing');
 record.nativeCommandEvidence=await verifyNativeCommand(profile);
 const hasProjection=call.model?.reasoning?.efforts?.some(choice=>choice.id==='uncensored');
 record.projectionModes={status:hasProjection?'running':'not-applicable',cases:[]};
 if(hasProjection){
  const args=record.nativeCommandEvidence.args,at=args.indexOf('--control-vector-scaled');
  if(at<0||args[args.indexOf('--cvec-mode')+1]!=='project')throw Error('Projection mode has no loaded native direction');
  const scaled=args[at+1],vector=scaled.slice(0,scaled.lastIndexOf(':'));
  const vectorSha256=createHash('sha256').update(await readFile(vector)).digest('hex');
  if(vectorSha256!=='ef0724c5b79297e481017be85769832bc26eb220c984ecba2b0e1b0c8426312b')throw Error('Loaded projection direction differs from the verified Flash Next asset');
  record.projectionModes.vectorSha256=vectorSha256;
  for(const choice of [undefined,'low','medium','xhigh','uncensored','medium','uncensored']){
   const before=wireRequests.length,parts=[];
   for await(const part of call.stream({provider:engine,model:id,system:'Answer arithmetic briefly.',messages:[{role:'user',content:[{type:'text',text:'Calculate 2+2. Reply only with the single digit.'}]}],maxTokens:64,reasoningEffort:choice,signal}))parts.push(part);
   const wire=wireRequests.slice(before).findLast(row=>typeof row.projection==='boolean');
   const expected=choice==='uncensored'?'medium':choice||'medium';
   if(!wire||wire.effort!==expected||wire.projection!==(choice==='uncensored'))throw Error('GPU mode request did not retain the requested effort and native projection control');
   if(!parts.some(part=>part.type==='finish')||!parts.some(part=>part.type==='text-delta'||part.type==='reasoning-delta'))throw Error('GPU mode stream had no generated content or finish');
   record.projectionModes.cases.push({choice:choice||'default',...wire,finish:parts.findLast(part=>part.type==='finish')});
  }
  const medium=record.projectionModes.cases.filter(row=>['default','medium','uncensored'].includes(row.choice));
  if(new Set(medium.map(row=>row.messagesSha256)).size!==1)throw Error('Medium and Uncensored changed conversation text');
  record.projectionModes.status='passed';
 }
 record.status='ok';
}catch(error){record.error=error.stack||error.message;}
finally{
 try{await service.dispose();}catch(error){record.cleanupError=error.message;record.status='failed';}
 globalThis.fetch=originalFetch;
 clearTimeout(timer);record.elapsed_s=(Date.now()-started)/1000;
 await mkdir(destination,{recursive:true});await writeFile(join(destination,'adapter-result.json'),JSON.stringify(record,null,2)+'\n');
}
console.log(JSON.stringify({engine,id,status:record.status,text:record.text,error:record.error}));
if(record.status!=='ok')process.exitCode=1;
