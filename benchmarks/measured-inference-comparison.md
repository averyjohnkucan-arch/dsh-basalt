# Measured inference comparison

P and D are prefill and decode in tokens/s. Rows state their workload. Pending cells remain unverified. DeepSeek uses the final short counting and 90% prose protocol requested by the user. Flash and hybrid table rows use matched 10% code and 90% prose prompts,512 output tokens,and final256 decode. The independently audited80% sweeps are separate evidence.

| Model name | Old settings speed | Current measured Basalt speed |
| --- | --- | --- |
| DeepSeek V4.1 Flash IQ2_XXS / Basalt FP8 KV | Saved old engine: 10% P669.8/D13.8; 90% P525.6/D14.5 | Warm counting D43.20; 90% prose P575.21/D21.56. Different workload from saved baseline. |
| DeepSeek V4.1 Flash IQ2_XS / Basalt FP8 KV | New quant; no saved old profile | Warm counting D40.54; 90% prose P698.45/D13.21. New quant; no old baseline exists. |
| Flash Next NVFP4 GPTQ / INT8 KV | Matched saved Strata: 10% code P1908.0/D68.58; 90% prose P2002.4/D28.08. | Matched Basalt: 10% code P3296.5/D58.07; 90% prose P3241.4/D59.06. |
| Flash Next NVFP4 GPTQ / FP16 KV | Matched saved Strata: 10% code P1667.0/D53.87; 90% prose P1741.2/D43.24. | Current Basalt candidate: 10% code P2613.7/D83.1; 90% prose P2550.1/D47.93. Matched prompt IDs; 512 output, final256 decode. |
| Flash Next NVFP4 Q8 hybrid / INT8 KV | Matched saved Strata: 10% code P1511.4/D39.29; 90% prose P1599.9/D23.25. | Matched Basalt: 10% code P1982.9/D36.40; 90% prose P2447.3/D30.60. |
| Flash Next NVFP4 Q8 hybrid / FP16 KV | Matched saved Strata: 10% code P1345.5/D32.4; 90% prose P1418.9/D23.97. | Matched Basalt: 10% code P1858.2/D33.08; 90% prose P2040.7/D34.01. 512 output; final256 decode. |
| 27B NVFP4-full / old NVFP4 KV; Basalt INT8 KV | Prior NInfer, matched prompts: 10% code P2979.3/D100.8; 90% prose P1390.6/D43.73. NVFP4 KV; different stop handling from Basalt. | 112K resident KV / DFlash2: 10% code P3794.8/D75.3; 90% prose P1563.2/D4.40. Same prompt IDs as prior NInfer; INT8 KV and different stop handling; long-context speed remains poor. |
| 27B IQ3_S Huihui / INT8 KV | Earlier saved-profile tests: 10% P1193.1/D53.8; 90% P745.7/D54.6 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / FP8 KV | Earlier saved-profile tests: 10% P1120.8/D58.6; 90% P451.8/D40.0 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / NVFP4 KV | Earlier saved-profile tests: 10% P1201.4/D57.3; 90% P766.4/D46.2 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| Gyro S / saved FP16 KV | Earlier saved-profile tests: 10% P1933.8/D95.6; 90% P1806.0/D86.7 | Kept on Strata; Basalt Hadamard expert support is unavailable |

## Validation and limits

Latest NInfer matched comparison completed on the same prompts and settings: 10% code P2965.47/D104.08 versus prior P2979.30/D100.84; 90% prose P1409.76/D43.55 versus prior P1390.56/D43.73. D is final256 of512 output tokens, with no prompt reuse. Long-context decode changed by -0.4% and prefill by +1.4% in this single comparison; no meaningful long-context speed gain is established. Raw receipts: ninfer-matched-depths.json. Latest source a3171940 and DFlash2 NVFP4 routes passed; fresh generated-code checks on this same binary passed merge_intervals and verify_draft, and failed lru_trace (2/3); no old generations were reused.

The 27B NVFP4 pack passed the recorded tensor import checks. Basalt DFlash2 and NInfer native K7 each passed merge_intervals and verify_draft and failed lru_trace. The non-speculative Basalt import also failed lru_trace. These receipts do not establish full generated-code correctness.

The measured Basalt Flash Next projection challenge used one process and off/on/off requests. The off replies refused, the on reply quoted the requested term, and the final off reply matched the first. Raw samples were removed. DeepSeek projection remains unsupported by the inspected Basalt DeepSeek execution path. The available vector has width 5120, while the inspected Qwen projection kernel supports up to 4096 and is wired to the Qwen architecture. The released Strata 0.1.59 DeepSeek executable rejected --control-vector-scaled. The inspected newer Strata source explicitly retires DeepSeek execution; its Qwen projection support does not apply to DeepSeek. The inspected newer Basalt source still has no DeepSeek projection hooks.

DeepSeek fixed residency is 102.3 GiB with 21 workers. The short extra-RAM and worker-count changes differed by less than 1%. The ABBA drive test measured 30.08 tok/s on system NVMe and 30.68 on RAID0 during the final minute of four-minute near-empty-context story generations.

DeepSeek DSH profiles passed actual plugin GPU launch validation. Basalt 0.1.3 is installed in the web profile and points to those scratch profiles. Configuration and startup checks passed; visibility in the running browser remains unverified. Latest-source full GPU coverage, incomplete model rows, and GitHub publication remain pending. The completed DeepSeek chart is available in deepseek-completed-progress.png. Local commits contain the DeepSeek harness and evidence. The push failed because Git credentials were unavailable.

Raw evidence is in deepseek-warm-240.json, deepseek-followup.json, deepseek-raid-comparison.json, code-functional-27b-dflash-functional-configs.json, code-functional-27b-quality-configs.json, and flash-next-refusal-toggle-test.json.

Official Basalt0.4.1 GPU loading rejected the hybrid with "NVFP4 gate/up and down come together" and 27B with "blk.3.attn_q.weight is BF16; the dense kernels read Q8_0, NVFP4_PLANES and F8_E4M3". The measured custom support is necessary for these exact packs. This does not establish that every alternative stock format is unsupported.

Official Basalt0.4.1 completed the DeepSeek XXS 4096-token code smoke: P454.76, overall D22.21, final128 D27.73, 256 output. Embedded Engram placement differs from the custom split runtime; this is compatibility evidence, not a matched speed verdict. The completed four-minute stock warm result is reported below. Hybrid and27B exact-pack loading rejected as documented above.

Official Basalt0.4.1 four-minute XXS story test completed3986 tokens: D22.2 in first30s, D16.37 at60–90s, D15.58 at120–180s and D15.77 in the final minute. Existing custom split-drive ABBA system-NVMe runs sustained about30.08. Same43-token prompt and fixed expert controls, but Engram placement differs; this does not isolate a release regression. Retain the measured custom split setup. Evidence: basalt-stock041-warm-summary.json.

Earlier Flash INT8 8K/80% summaries are preserved in flash-int8-earlier-80percent-summary.json; the main row now uses exact10/90 matched prompts,512 output and final256 decode. Basalt improved near-full prose but regressed on the measured short-code tail.

Gyro S latest Strata0.1.60 completed10% P2220.40/D88.15 and90% P2129.82/D84.33. Original saved baseline was10% P1933.81/D95.59 and90% P1806.02/D86.73. Prompt hashes match and both generated4096/final2048. Latest90% decode is2.8% lower, within the5% allowance, while prefill is17.9% higher; short decode is7.8% lower. Basalt remains unsupported for this Hadamard artifact. Huihui INT8 results follow below.

Huihui INT8 latest NInfer candidate completed10% P1291.04/D68.99 vs saved P1193.11/D53.81;90% P874.48/D45.11 vs saved P745.74/D54.62. Prompt hashes and1024 output lengths match; final512 decode. Near-full decode regressed17.4%, exceeding the5% allowance despite17.3% better prefill. Retain saved long-context settings pending diagnosis; this is a settings/runtime comparison, not an isolated release regression. FP8 results follow below.

Huihui FP8 latest NInfer completed:10% P1151.02/D65.29 vs saved P1120.76/D58.60;90% P505.69/D41.02 vs saved P451.81/D40.02. Both configurations use the same prompt fixture and depth,1024 output/final512 decode. Near-full prefill improved11.9% and decode2.5% in this comparison. This candidate meets the decode-loss constraint against the saved baseline, but is not proof of a global maximum. NVFP4 checks follow automatically.

Independent receipt audit verified the recorded80% decode-first selections for Flash Basalt(7 complete candidates),hybrid Basalt(5),and Flash Strata(4). Every included receipt passed status,209715 prompt tokens,8192 output and zero prefix-reuse checks. Recomputed genre medians select the same maximum-minimum-prefill candidate retaining≥95% of each peak-decode genre median. Evidence: decode-first-receipt-audit.json; reproducible via work/audit_range_receipts.py. This verifies the recorded sweep, not a global maximum or every latest release.

Huihui NVFP4 latest NInfer completed10% P1270.74/D68.32 and90% P870.11/D43.99, compared with saved10% P1201.44/D57.31 and90% P766.39/D46.21. Same configured fixture/depth,1024 output/final512 decode. Near-full prefill improved13.5%; decode fell4.8%, narrowly within the5% threshold in this single comparison. Both engine and prefill chunk differ from saved settings, so this is not an isolated release comparison. All eight latest Gyro/Huihui checks completed successfully; actual plugin validation follows.

Actual DSH adapter validation passed for Flash FP16,hybrid FP16,and latest NInfer27B. Each matched the measured native executable and expected flags,appeared as the owned GPU PID,and streamed the arithmetic sanity response. Both Basalt profiles passed default/low/medium/xhigh/uncensored projection-mode routing with unchanged conversation text. Exported profile metadata now binds the validation receipt SHA256. Evidence: measured-profile-launch-validation.json. This is launch/routing validation,not a new throughput or general quality test.

All three Huihui exported profiles passed actual NInfer adapter GPU launch,measured-native-control and arithmetic sanity checks. INT8 retains the faster saved engine/settings; its private glibc loader and actual engine binary are checked explicitly. FP8/NVFP4 use the latest measured build. Profile names contain the measured10/90 P/D pairs. Evidence: huihui-profile-launch-validation.json. This does not replace generated-function correctness tests.

Gyro S and all three Huihui profiles now have measured speed names and passed actual adapter/native-control launch checks. Basalt0.1.3,NInfer0.4.5,and Strata0.8.3 are installed through DSH plugin commands and point to scratch profile states. Seven Basalt,four NInfer,and three Strata profiles are saved. Running UI visibility remains unverified because local browser control is disabled. NInfer final package tests:84 JS and11 Python passed;Strata:88 JS and43 Python passed.
