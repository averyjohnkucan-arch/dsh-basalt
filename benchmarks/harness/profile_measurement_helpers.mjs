import {readFile,open} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
export async function performanceQualified(root,key,selections){
 let q;
 try{q=JSON.parse(await readFile(join(root,'outputs/performance-qualified',key+'.json'),'utf8'));}
 catch(error){if(error.code==='ENOENT')return false;throw error;}
 if(q.performance_qualified!==true)return false;
 for(const kind of ['long','short']){
  if(q[kind+'_selection']!==selections[key+'_'+kind]?.selected)return false;
  if(JSON.stringify(q[kind+'_metrics']??null)!==JSON.stringify(selections[key+'_'+kind+'_metrics']??null))return false;
 }
 return true;
}
export function nativeSignature(c){
 const a=c.command,flags={},position=[];let i=4;
 const omitted=new Set(['--draft-log','--conversation-cache-dir','--conversation-cache-disk-mib','--conversation-cache-mib','--prompt-cache','--eos','--eos-ids','--stop-eos']);
 while(i<a.length){const flag=a[i++];if(!flag.startsWith('--')){position.push(flag);continue;}let value=true;if(i<a.length&&!a[i].startsWith('--'))value=a[i++];if(!omitted.has(flag))flags[flag]=value;}
 if(flags['--expert-profile']&&c.expert_profile_source)flags['--expert-profile']=c.expert_profile_source;
 return JSON.stringify([a.slice(0,4),position,Object.entries(flags).sort(([a],[b])=>a.localeCompare(b)),c.artifact_header_sha256,c.engine_binary_sha256]);
}
export async function memoryEvidence(root,metrics){
 const cases=[metrics.low,...metrics.high.cases];const records=[];
 for(const item of cases){
  const folder=join(root,'bench',item.case),r=JSON.parse(await readFile(join(folder,'result.json'),'utf8'));
  if(r.status!=='ok'||!r.config.host_memory_policy||r.generated!==8192||r.cold_prefill_qualified===false||r.reused_tokens>0)throw Error('Final profile needs complete, uncached RAM-isolated measurements: '+item.case);
  if(item.prefill!==r.prefill_tok_s||item.decode!==r.tail_decode_tok_s)throw Error('Profile rates differ from the current paired measurement: '+item.case);
  const telemetry=JSON.parse(await readFile(join(folder,'telemetry.json'),'utf8')),memory=telemetry.map(x=>x.host_memory).filter(Boolean);
  if(!memory.length)throw Error('Missing RAM telemetry for '+item.case);
  records.push({case:item.case,policy:r.config.host_memory_policy,tailMeasuredTokens:r.tail_measured_tokens??r.config.timed_tail,peakWorkerBytes:Math.max(...memory.map(x=>x.scope_peak_bytes??0)),minimumHostAvailableBytes:Math.min(...memory.map(x=>x.host_available_bytes)),maximumMemoryPressureAvg10:Math.max(...memory.map(x=>x.pressure_some_avg10))});
 }
 return records;
}
export async function verifyPack(c){
 const a=c.command,at=a.indexOf('--model');if(at<0)return;
 const f=await open(a[at+1],'r');try{const b=Buffer.alloc(65536);const {bytesRead}=await f.read(b,0,b.length,0);if(bytesRead!==b.length||createHash('sha256').update(b).digest('hex')!==c.artifact_header_sha256||(await f.stat()).size!==c.artifact_bytes)throw Error('Measured pack identity changed; rebuild its own measurements before exporting');}finally{await f.close();}
}
