import {codeFunctionalEvidence} from './profile_measurement_helpers.mjs';
import {mkdtemp,mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const parent='/mnt/media/scratch/dsh-inference-tuning-20261115/validation/functional-recovery';await mkdir(parent,{recursive:true});
const root=await mkdtemp(parent+'/export-');await mkdir(root+'/outputs');await mkdir(root+'/bench');
const config={command:['taskset','-c','0-21','fixture-engine','--spec','8'],engine_binary_sha256:'engine-sha',benchmark_environment_id:'performance-powerd-20261115'};
const rows=[],results=[],tasks=['merge_intervals','lru_trace','verify_draft'];
const save=async(p,v)=>writeFile(p,JSON.stringify(v));
for(const task of tasks){
 const name='quality-'+task;await mkdir(root+'/bench/'+name);
 const c={...config,functional_attempt_id:'attempt-'+task,functional_prompt_sha256:'prompt-'+task,functional_checks_sha256:'checks-'+task,functional_task_name:task};
 const result={status:'ok',config:c,token_sha256:'tokens-'+task};results.push(result);await save(root+'/bench/'+name+'/result.json',result);
 rows.push({function:task,case:name,passed:true,status:'ok',grade_schema:2,functional_attempt_id:c.functional_attempt_id,generation_prompt_sha256:c.functional_prompt_sha256,functional_checks_sha256:c.functional_checks_sha256,generation_token_sha256:result.token_sha256});
}
const receipt=root+'/outputs/code-functional-test.json';await save(receipt,rows);
const checks={};checks.valid=await codeFunctionalEvidence(root,config);if(checks.valid.status!=='tested'||checks.valid.passed!==3)throw Error('Valid generation grades rejected');
results[0].config.functional_attempt_id='new-attempt';await save(root+'/bench/'+rows[0].case+'/result.json',results[0]);checks.stale=await codeFunctionalEvidence(root,config);if(checks.stale.status==='tested'||checks.stale.total!==2)throw Error('Stale grade accepted');
results[0].config.functional_attempt_id=rows[0].functional_attempt_id;await save(root+'/bench/'+rows[0].case+'/result.json',results[0]);rows[1].passed=false;await save(receipt,rows);checks.semanticFailure=await codeFunctionalEvidence(root,config);if(checks.semanticFailure.status!=='tested'||checks.semanticFailure.passed!==2)throw Error('Semantic failure concealed');
results[2].status=rows[2].status='failed';rows[2].passed=false;await save(root+'/bench/'+rows[2].case+'/result.json',results[2]);await save(receipt,rows);checks.workerFailure=await codeFunctionalEvidence(root,config);if(checks.workerFailure.status!=='incomplete')throw Error('Failed worker called complete');
for(const row of rows)delete row.grade_schema;await save(receipt,rows);checks.legacy=await codeFunctionalEvidence(root,config);if(checks.legacy.total!==0)throw Error('Unproven historical rows accepted');
const source=await readFile('/mnt/media/scratch/dsh-inference-tuning-20261115/work/profile_measurement_helpers.mjs');
await save('/mnt/media/scratch/dsh-inference-tuning-20261115/outputs/functional-export-recovery-test.json',{status:'passed',scope:'Actual JS profile evidence helper: fresh provenance, overwritten attempts, genuine semantic failure, failed generation and legacy rows; no GPU.',sourceSha256:createHash('sha256').update(source).digest('hex'),checks});
console.log('Functional export provenance checks passed');
