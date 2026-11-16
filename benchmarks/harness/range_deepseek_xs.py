"""Mandatory final model stage: larger IQ2_XS under the same measured protocol."""
from range_tuner import *
from deepseek_storage import internal_artifact,storage_config,raw_storage_evidence,ENGRAM,DESKTOP,xs_pack_command,validate_xs_pack
from benchmark_memory_guard import MemoryGuard
import os,time,shutil

def guarded(command,label,cwd):
    guard=MemoryGuard({},R/'validation'/label);samples=[]
    with (W/(label+'.log')).open('w') as log:
        proc=subprocess.Popen(guard.command(command),cwd=cwd,env={**os.environ,'TMPDIR':str(R/'tmp')},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while proc.poll() is None:
                samples.append(dict(time=time.time(),host_memory=guard.sample(proc)))
                if guard.reason:break
                time.sleep(1)
            status=proc.wait(timeout=15)
        finally:
            guard.stop(proc)
            (O/(label+'-memory.json')).write_text(json.dumps(dict(policy=guard.policy,reason=guard.reason,samples=samples),indent=2))
        assert status==0 and not guard.reason,label+' failed; preserved log must be inspected'

if __name__=='__main__' and '--plan' in sys.argv:
    print(json.dumps(dict(stage='final-model-IQ2_XS',requires=['original matrix and generated-code QA','original XXS DeepSeek tuning, plugin GPU and generated-code QA','SHA256-complete four-shard XS download','matched internal expert/external Engram storage'],jobs=['metadata pack','guarded Basalt conversion','Basalt XS tuning and original-engine baseline','Strata XS tuning','repeatability/low-peak/final qualification for both engines','actual generated-function execution','refresh profiles and report'],gpu_workers_started=0),indent=2))

if __name__=='__main__' and '--plan' not in sys.argv:
    stage=O/'iq2-xs-tuning-stage.json'
    state=dict(status='starting',last_model_stage=True,started_unix=time.time(),baseline_meaning='Existing tuned XXS controls applied to XS on the original engine; there was no original user XS profile')
    stage.write_text(json.dumps(state,indent=2)+'\n')
    try:
        selections=read(O/'range-selections.json')
        for key in ['deepseek_basalt','deepseek_strata']:
            assert read(O/'performance-qualified'/(key+'.json'))['performance_qualified']
            assert read(O/'performance-qualified'/(key+'-plugin-gpu.json'))['status']=='ok'
        # Original DeepSeek generated-function execution must precede the final quant stage.
        qa=read(O/'code-functional-range-deepseek-selected-functional-configs.json')
        assert len(qa)==12 and all(row.get('status')=='ok' and row.get('generation_token_sha256') and row.get('functional_attempt_id') for row in qa), 'Original DeepSeek generated-function evidence incomplete'
        while read(O/'iq2-xs-download-status.json')['status']!='complete':
            active=subprocess.run(['systemctl','--user','is-active','--quiet','dsh-iq2-xs-download-main-20261116.service'])
            assert active.returncode==0, 'XS download stopped before SHA256 completion; inspect its preserved status/log'
            state.update(status='waiting-for-download');stage.write_text(json.dumps(state,indent=2)+'\n');time.sleep(10)
        raw_storage_evidence('XS');state.update(status='preparing');stage.write_text(json.dumps(state,indent=2)+'\n')
        source=DESKTOP/'DeepSeek-IQ2_XS';draft=DESKTOP/'DeepSeek-shared/support/dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf'
        pack=R/'strata-deepseek-xs/data/packs/deepseek-v4.1-flash-iq2-xs'
        guarded(xs_pack_command(sys.executable,pack),'deepseek-xs-strata-pack',W)
        validate_xs_pack(pack)
        artifact=internal_artifact('XS')
        if not artifact.exists():
            assert shutil.disk_usage(artifact.parent).free>275*2**30,'Preserve internal SSD conversion headroom; no automatic source deletion'
            command=list(read(O/'deepseek-pack-regeneration.json')['command']);command[1]=str(W/'basalt-latest/tools/convert/convert.py')
            for flag,value in [('--gguf',source/'DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XS-00001-of-00004.gguf'),('--engram-gguf',ENGRAM),('--dspark',draft),('--out',artifact),('--name','DeepSeek V4.1 Flash GSQ-RCO IQ2_XS')]:
                command[command.index(flag)+1]=str(value)
            (O/'deepseek-xs-conversion-command.json').write_text(json.dumps(dict(command=command),indent=2)+'\n')
            guarded(command,'deepseek-xs-basalt-conversion',W/'basalt-latest')
        selections=read(O/'range-selections.json')
        original=read(R/'bench'/selections['deepseek_basalt_old_metrics']['low']['case']/'result.json')['config']
        old=copy.deepcopy(original);opt(old,'--pack',pack);old=storage_config(old,'XS')
        base=read(W/(selections['deepseek_basalt_long']['selected']+'.json'));base=storage_config(base,'XS',basalt=True)
        candidates=[(tag,changed(base,changes))for tag,changes in [('workers14',{'--pool-workers':14}),('workers12',{'--pool-workers':12}),('workers8',{'--pool-workers':8}),('dspark4',{'--spec':4}),('dspark6',{'--spec':6}),('dspark6-exp64',{'--spec':6,'--draft-experts':64})]]
        tune('deepseek_xs_basalt',base,'deepseek',candidates,[],[(f'spec{s}',{'--spec':s})for s in [0,4,6]],old=old,cache=False)
        strata=read(W/(selections['deepseek_strata_long']['selected']+'.json'));opt(strata,'--pack',pack);strata=storage_config(strata,'XS')
        candidates=[(tag,changed(strata,changes))for tag,changes in [('threads21',{'--cpu-threads':21}),('threads8',{'--cpu-threads':8}),('chunk8192',{'--prefill-chunk':8192}),('dspark-off',{'--dspark':'off'}),('dspark-conf85',{'--dspark-conf':.85})]]
        tune('deepseek_xs_strata',strata,'deepseek',candidates,[('chunk8192',{'--prefill-chunk':8192}),('chunk2048',{'--prefill-chunk':2048})],[(f'conf{v}',{'--dspark':'auto','--dspark-conf':v})for v in [.55,.65,.85]],old=old,cache=False)
        for key in ['deepseek_xs_basalt','deepseek_xs_strata']:
            for args in [('range_repeatability.py',key,'deepseek'),('range_low_peak.py',key,'deepseek'),('range_repeatability.py',key,'deepseek','--include-peak-code')]:
                subprocess.run([sys.executable,str(W/args[0]),*args[1:]],check=True)
        selections=read(O/'range-selections.json');configs={}
        for key in ['deepseek_xs_basalt','deepseek_xs_strata']:
            for kind in ['long','short']:configs[key+'-'+kind]=dict(config=str(W/(selections[key+'_'+kind]['selected']+'.json')),family='deepseek')
        path=W/'range-deepseek-xs-selected-functional-configs.json';path.write_text(json.dumps(configs,indent=2)+'\n')
        subprocess.run([sys.executable,str(W/'code_function_eval.py'),str(path)],check=True)
        qa=read(O/'code-functional-range-deepseek-xs-selected-functional-configs.json')
        assert len(qa)==12 and all(row.get('status')=='ok' and row.get('generation_token_sha256') and row.get('functional_attempt_id') for row in qa), 'XS generated-function evidence incomplete; semantic failures are separately reported'
        for key in ['deepseek_xs_basalt','deepseek_xs_strata']:
            subprocess.run([sys.executable,str(W/'range_plugin_gpu_gate.py'),key],check=True)
        subprocess.run([sys.executable,str(W/'range_progress_report.py')],check=True)
        state.update(status='model-stage-complete-final-report-and-publication-remain',completed_unix=time.time(),quantizations_retained=True)
    except BaseException as error:
        state.update(status='failed',error=str(error));raise
    finally:stage.write_text(json.dumps(state,indent=2)+'\n')
