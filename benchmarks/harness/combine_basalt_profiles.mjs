import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {BasaltService} from '/home/user/.dsh/profiles/web/node_modules/dsh-basalt/lib/service.js';
import {BasaltAdapter} from '/mnt/media/scratch/dsh-inference-tuning-20261115/work/dsh-basalt/lib/adapter.js';
const root='/mnt/media/scratch/dsh-inference-tuning-20261115/outputs',dest=root+'/dsh-basalt-combined-measured-state';
await mkdir(dest,{recursive:true});
const profiles=[];
for(const name of ['dsh-basalt-deepseek-measured-state','dsh-basalt-range-state','dsh-basalt-fp16-measured-state']){
 const list=JSON.parse(await readFile(root+'/'+name+'/profiles.json','utf8'));
 for(const p of list){if(!p.runtimeDir)throw Error('Missing explicit runtime');profiles.push(p);}
}
if(new Set(profiles.map(p=>p.id)).size!==profiles.length)throw Error('Duplicate model IDs');
await writeFile(dest+'/profiles.json',JSON.stringify(profiles,null,2)+'\n');
await copyFile(root+'/dsh-basalt-deepseek-measured-state/settings.json',dest+'/settings.json');
const service=new BasaltService({dataDir:dest});
try{
 await service.init();const adapter=new BasaltAdapter({get:()=>undefined},service);const models=await adapter.listModels('basalt');
 if(models.length!==7)throw Error('Incomplete model list');
 await writeFile(root+'/combined-basalt-list-validation.json',JSON.stringify({status:'ok',source:'Installed DSH Basalt service plus validated scratch adapter source',dataDir:dest,models,scope:'Installed adapter enumeration; running browser visibility not established'},null,2)+'\n');
 console.log(models.map(m=>m.name).join('\n'));
}finally{await service.dispose();}
