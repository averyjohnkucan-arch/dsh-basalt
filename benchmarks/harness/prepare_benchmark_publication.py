"""Prepare reviewable benchmark sources and evidence; never publish model weights or prompts."""
from pathlib import Path
import ast,hashlib,json,shutil
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115');W=R/'work';O=R/'outputs';dest=W/'dsh-basalt/benchmarks';harness=dest/'harness';harness.mkdir(parents=True,exist_ok=True)
files=['range_model_progress.py','test_hybrid_sustained_fit.py','resume_hybrid_pipeline.py','refresh_range_metrics.py','fit_hybrid_memory.py','benchmark_resume_validity_test.py','range_objective.py','calibrate_performance_ninfer.py','benchmark_environment.py','performance_range_pipeline.py','range_queue.py','continue_after_range_queue.py','prepare_benchmark_publication.py','native_bench.py','http_bench.py','benchmark_prompts.py','benchmark_memory_guard.py','range_common.py','range_identity.py','range_tuner.py','range_repeatability.py','range_low_peak.py','range_joint_refine.py','range_flash.py','range_strata.py','range_ninfer.py','range_27b_basalt.py','range_deepseek.py','mark_performance_qualified.py','range_plugin_gpu_gate.py','range_plugin_adapter_smoke.mjs','profile_measurement_helpers.mjs','export_range_basalt.mjs','export_range_ninfer.mjs','export_range_strata.mjs','range_progress_report.py','range_progress_chart.py','prepare_range_fixtures.py','audit_range_outputs.py','quality_range_selected.py','code_function_eval.py','latest80_common.py','tune80_common.py']
manifest=[]
for name in files:
 source=W/name;data=source.read_bytes()
 if source.suffix=='.py':ast.parse(data,filename=name)
 (harness/name).write_bytes(data);manifest.append(dict(path='harness/'+name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
(dest/'source-manifest.json').write_text(json.dumps(dict(scope='Exact harness snapshot; scratch paths and sibling clone layout retained for audit. No weights, generated answers, credentials, or token-ID fixtures included.',files=manifest),indent=2)+'\n')
receipts=dest/'evidence';receipts.mkdir(exist_ok=True)
for name in ['model-progress-chart-verification.json','hybrid-compatibility-progress.json','hybrid-memory-fit-old-strata-high104.json','hybrid-memory-fit-strata-high104.json','hybrid-sustained-fit-recovery-test.json','strata-hybrid-overlay-validation.json','memory-policy-identity-test.json','hybrid-memory-fit-basalt-high104.json','profile-repeat-range-regression.json','queue-resume-plan-validation.json','hybrid-original-budget-pressure-stop.json','hybrid-memory-fit-basalt.json','benchmark-resume-validity-test.json','performance-cohort-resume-validity-audit.json','harness-dependency-closure-audit.json','flash-full-cpu-share-decode-floor-rejection.json','output-repetition-schema-regression.json','flash-zero-share-output-audit.json','flash-saved-ranking-runtime-copy.json','kv-attention-precision-audit.json','flash-decode-stage-costs.json','prose-corpus-sources.json','ninfer-saved-profile-fidelity.json','ninfer-native-framing-identity.json','oom-recovery.json','benchmark-memory-isolation-test.json','benchmark-memory-guard-fault-test.json','benchmark-power-reading-parser-test.json','per-genre-decode-floor-regression.json','expert-profile-copy-test.json','flash-saved-ranking-fidelity.json','recovery-memory-headroom-audit.json','power-profile-before.json','power-profile-after.json','power-policy-matched-comparison.json','deepseek-source-artifact-fidelity.json','deepseek-latest-frozen-token-identity.json']:
 source=O/name
 if source.exists():shutil.copy2(source,receipts/name)
status=O/'performance-qualified'
if status.exists():
 for p in status.glob('*.json'):shutil.copy2(p,receipts/p.name)
print('Prepared',len(files),'exact benchmark sources and available evidence at',dest)
