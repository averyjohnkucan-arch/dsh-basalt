# Measured inference comparison

P and D are prefill and decode in tokens/s. Rows state their workload. Pending cells remain unverified. DeepSeek uses the final short counting and 90% prose protocol requested by the user. Flash rows retain their earlier code and 80% prose protocol.

| Model name | Old settings speed | Current measured Basalt speed |
| --- | --- | --- |
| DeepSeek V4.1 Flash IQ2_XXS / Basalt FP8 KV | Saved old engine: 10% P669.8/D13.8; 90% P525.6/D14.5 | Warm counting D43.20; 90% prose P575.21/D21.56. Different workload from saved baseline. |
| DeepSeek V4.1 Flash IQ2_XS / Basalt FP8 KV | New quant; no saved old profile | Warm counting D40.54; 90% prose P698.45/D13.21. Different workload from saved baseline. |
| Flash Next NVFP4 GPTQ / INT8 KV | 8K code P1,950.5/D47.3; 80% P2,022.0–2,023.4, D48.4–50.8 | Long preset: 8K code P3,013.6/D55.6; 80% P3,226.4–3,243.1, D63.2–71.6  /  Peak-code preset: 8K code P3,012.0/D57.2; 80% P3,223.2–3,256.8, D64.5–75.5 |
| Flash Next NVFP4 GPTQ / FP16 KV | Earlier saved-profile tests: 10% P1681.5/D49.5; 90% P1695.9/D48.6 | Current Basalt candidate: 10% code P2613.7/D83.1; 90% prose P2550.1/D47.93. Old matched retry pending; historical baseline prompt differs. |
| Flash Next NVFP4 Q8 hybrid / INT8 KV | 8K code P1,639.1/D32.2; 80% P1,636.3–1,639.6, D31.7–37.8 | Long preset: 8K code P1,987.9/D37.6; 80% P2,182.5–2,199.3, D38.9–43.8 |
| Flash Next NVFP4 Q8 hybrid / FP16 KV | Matched saved Strata: 10% code P1345.5/D32.4; 90% prose P1418.9/D23.97. | Matched Basalt: 10% code P1858.2/D33.08; 90% prose P2040.7/D34.01. 512 output; final256 decode. |
| 27B NVFP4-full / old NVFP4 KV; Basalt INT8 KV | Prior NInfer, matched prompts: 10% code P2979.3/D100.8; 90% prose P1390.6/D43.73. NVFP4 KV; different stop handling from Basalt. | 112K resident KV / DFlash2: 10% code P3794.8/D75.3; 90% prose P1563.2/D4.40. Same prompt IDs as prior NInfer; INT8 KV and different stop handling; long-context speed remains poor. |
| 27B IQ3_S Huihui / INT8 KV | Earlier saved-profile tests: 10% P1193.1/D53.8; 90% P745.7/D54.6 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / FP8 KV | Earlier saved-profile tests: 10% P1120.8/D58.6; 90% P451.8/D40.0 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / NVFP4 KV | Earlier saved-profile tests: 10% P1201.4/D57.3; 90% P766.4/D46.2 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| Gyro S / saved FP16 KV | Earlier saved-profile tests: 10% P1933.8/D95.6; 90% P1806.0/D86.7 | Kept on Strata; Basalt Hadamard expert support is unavailable |

## Validation and limits

Latest NInfer matched comparison completed on the same prompts and settings: 10% code P2965.47/D104.08 versus prior P2979.30/D100.84; 90% prose P1409.76/D43.55 versus prior P1390.56/D43.73. D is final256 of512 output tokens, with no prompt reuse. Long-context decode changed by -0.4% and prefill by +1.4% in this single comparison; no meaningful long-context speed gain is established. Raw receipts: ninfer-matched-depths.json. Latest source a3171940 and DFlash2 NVFP4 routes passed; generated-code quality remains separately qualified by the earlier tests.

The 27B NVFP4 pack passed the recorded tensor import checks. Basalt DFlash2 and NInfer native K7 each passed merge_intervals and verify_draft and failed lru_trace. The non-speculative Basalt import also failed lru_trace. These receipts do not establish full generated-code correctness.

The measured Basalt Flash Next projection challenge used one process and off/on/off requests. The off replies refused, the on reply quoted the requested term, and the final off reply matched the first. Raw samples were removed. DeepSeek projection remains unsupported by the inspected Basalt DeepSeek execution path. The available vector has width 5120, while the inspected Qwen projection kernel supports up to 4096 and is wired to the Qwen architecture. The released Strata 0.1.59 DeepSeek executable rejected --control-vector-scaled. The inspected newer Strata source explicitly retires DeepSeek execution; its Qwen projection support does not apply to DeepSeek. The inspected newer Basalt source still has no DeepSeek projection hooks.

DeepSeek fixed residency is 102.3 GiB with 21 workers. The short extra-RAM and worker-count changes differed by less than 1%. The ABBA drive test measured 30.08 tok/s on system NVMe and 30.68 on RAID0 during the final minute of four-minute near-empty-context story generations.

DeepSeek DSH profiles passed actual plugin GPU launch validation. Basalt 0.1.3 is installed in the web profile and points to those scratch profiles. Configuration and startup checks passed; visibility in the running browser remains unverified. Latest-source full GPU coverage, incomplete model rows, and GitHub publication remain pending. The completed DeepSeek chart is available in deepseek-completed-progress.png. Local commit 7705533 contains the latest DeepSeek harness and evidence. The push failed because Git credentials were unavailable.

Raw evidence is in deepseek-warm-240.json, deepseek-followup.json, deepseek-raid-comparison.json, code-functional-27b-dflash-functional-configs.json, code-functional-27b-quality-configs.json, and flash-next-refusal-toggle-test.json.

Official Basalt0.4.1 GPU loading rejected the hybrid with "NVFP4 gate/up and down come together" and 27B with "blk.3.attn_q.weight is BF16; the dense kernels read Q8_0, NVFP4_PLANES and F8_E4M3". The measured custom support is necessary for these exact packs. This does not establish that every alternative stock format is unsupported.

Official Basalt0.4.1 completed the DeepSeek XXS 4096-token code smoke: P454.76, overall D22.21, final128 D27.73, 256 output. Embedded Engram placement differs from the custom split runtime; this is compatibility evidence, not a matched speed verdict. One four-minute stock warm run is queued. Hybrid and27B exact-pack loading rejected as documented above.
