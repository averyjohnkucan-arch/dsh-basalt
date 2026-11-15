import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115';
const [engine,id,destination]=process.argv.slice(2);
if(!['basalt','ninfer','strata'].includes(engine)||!id?.startsWith('scratch-range-')||!destination?.startsWith(root+'/validation/'))throw Error('Explicit scratch profile and output required');
const state=join(root,'outputs',`dsh-${engine}-range-state`),ctx={get:()=>undefined};
let service,adapter;
if(engine==='ninfer'){
 const {Runtime}=await import('./dsh-ninfer/lib/runtime.js');
 const {LocalAdapter}=await import('./dsh-ninfer/lib/adapter.js');
 service=new Runtime('ninfer',{dataDir:state});adapter=new LocalAdapter(ctx,service,'NInfer');
}else{
 const name=engine==='basalt'?'Basalt':'Strata';
 const module=await import(`./dsh-${engine}/lib/service.js`),adapters=await import(`./dsh-${engine}/lib/adapter.js`);
 service=new module[name+'Service']({dataDir:state});adapter=new adapters[name+'Adapter'](ctx,service);
}
const started=Date.now(),record={engine,profile:id,status:'failed',qualification:'Actual DSH adapter stream and plugin-owned GPU worker; tiny arithmetic sanity, not a model-quality or throughput benchmark'};
const timer=setTimeout(()=>process.exit(124),600000);timer.unref();
try{
 await service.init();
 const profile=service.profiles.find(p=>p.id===id);if(!profile)throw Error('Qualified exported profile missing');
 record.profileName=profile.name;record.savedContext=profile.context;record.savedVerification=profile.verification8192;
 const signal=AbortSignal.timeout(540000),call=await adapter.prepareCall(engine,id,signal),chunks=[];
 for await(const chunk of call.stream({provider:engine,model:id,system:'Answer arithmetic briefly.',messages:[{role:'user',content:[{type:'text',text:'Calculate 2+2. Reply only with the single digit.'}]}],maxTokens:32,reasoningEffort:'off',signal}))chunks.push(chunk);
 record.chunks=chunks;record.text=chunks.filter(c=>c.type==='text-delta').map(c=>c.text).join('');
 record.arithmeticSanity=/^\s*4[.!]?\s*$/.test(record.text);
 record.finish=chunks.findLast(c=>c.type==='finish');
 if(!record.arithmeticSanity||!record.finish)throw Error('Arithmetic sanity or finish event missing');
 record.status='ok';
}catch(error){record.error=error.stack||error.message;}
finally{
 try{await service.dispose();}catch(error){record.cleanupError=error.message;record.status='failed';}
 clearTimeout(timer);record.elapsed_s=(Date.now()-started)/1000;
 await mkdir(destination,{recursive:true});await writeFile(join(destination,'adapter-result.json'),JSON.stringify(record,null,2)+'\n');
}
console.log(JSON.stringify({engine,id,status:record.status,text:record.text,error:record.error}));
if(record.status!=='ok')process.exitCode=1;
