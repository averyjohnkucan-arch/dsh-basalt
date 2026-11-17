# Measured inference comparison

P and D are prefill and decode in tokens/s. Rows state their workload. Pending cells remain unverified. DeepSeek uses the final short counting and 90% prose protocol requested by the user. Flash rows retain their earlier code and 80% prose protocol.

| Model name | Old settings speed | Current measured Basalt speed |
| --- | --- | --- |
| DeepSeek V4.1 Flash IQ2_XXS / Basalt FP8 KV | Saved old engine: 10% P669.8/D13.8; 90% P525.6/D14.5 | Warm counting D43.20; 90% prose P575.21/D21.56. Different workload from saved baseline. |
| DeepSeek V4.1 Flash IQ2_XS / Basalt FP8 KV | New quant; no saved old profile | Warm counting D40.54; 90% prose P698.45/D13.21. Different workload from saved baseline. |
| Flash Next NVFP4 GPTQ / INT8 KV | 8K code P1,950.5/D47.3; 80% P2,022.0–2,023.4, D48.4–50.8 | Long preset: 8K code P3,013.6/D55.6; 80% P3,226.4–3,243.1, D63.2–71.6  /  Peak-code preset: 8K code P3,012.0/D57.2; 80% P3,223.2–3,256.8, D64.5–75.5 |
| Flash Next NVFP4 GPTQ / FP16 KV | Earlier saved-profile tests: 10% P1681.5/D49.5; 90% P1695.9/D48.6 | In progress: long-context and peak-code qualification |
| Flash Next NVFP4 Q8 hybrid / INT8 KV | 8K code P1,639.1/D32.2; 80% P1,636.3–1,639.6, D31.7–37.8 | Long preset: 8K code P1,987.9/D37.6; 80% P2,182.5–2,199.3, D38.9–43.8 |
| Flash Next NVFP4 Q8 hybrid / FP16 KV | Pending matched measurements | In progress: long-context and peak-code qualification |
| 27B NVFP4-full / old NVFP4 KV; Basalt INT8 KV | Earlier saved-profile tests: 10% P2668.5/D79.9; 90% P1189.9/D53.5 | 112K resident KV / DFlash2: 10% code P3794.8/D75.3; 90% prose P1563.2/D4.40. Different prompt from saved NInfer baseline; long-context speed remains poor. |
| 27B IQ3_S Huihui / INT8 KV | Earlier saved-profile tests: 10% P1193.1/D53.8; 90% P745.7/D54.6 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / FP8 KV | Earlier saved-profile tests: 10% P1120.8/D58.6; 90% P451.8/D40.0 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| 27B IQ3_S Huihui / NVFP4 KV | Earlier saved-profile tests: 10% P1201.4/D57.3; 90% P766.4/D46.2 | No Basalt measurement: this mixed GGUF IQ3 artifact is outside the finite import/kernel support |
| Gyro S / saved FP16 KV | Earlier saved-profile tests: 10% P1933.8/D95.6; 90% P1806.0/D86.7 | Kept on Strata; Basalt Hadamard expert support is unavailable |

## Validation and limits

The 27B NVFP4 pack passed the recorded tensor import checks. Basalt DFlash2 and NInfer native K7 each passed merge_intervals and verify_draft and failed lru_trace. The non-speculative Basalt import also failed lru_trace. These receipts do not establish full generated-code correctness.

The measured Basalt Flash Next projection challenge used one process and off/on/off requests. The off replies refused, the on reply quoted the requested term, and the final off reply matched the first. Raw samples were removed. DeepSeek projection remains unsupported by the inspected Basalt DeepSeek execution path. The available vector has width 5120, while the inspected Qwen projection kernel supports up to 4096 and is wired to the Qwen architecture. The released Strata 0.1.59 DeepSeek executable rejected --control-vector-scaled. Newer runtime support requires independent verification.

DeepSeek fixed residency is 102.3 GiB with 21 workers. The short extra-RAM and worker-count changes differed by less than 1%. The ABBA drive test measured 30.08 tok/s on system NVMe and 30.68 on RAID0 during the final minute of four-minute near-empty-context story generations.

DeepSeek DSH profiles passed actual plugin GPU launch validation. Basalt 0.1.3 is installed in the web profile and points to those scratch profiles. Configuration and startup checks passed; visibility in the running browser remains unverified. Latest-source full GPU coverage, incomplete model rows, and GitHub publication remain pending. The completed DeepSeek chart is available in deepseek-completed-progress.png. Local commit 7705533 contains the latest DeepSeek harness and evidence. The push failed because Git credentials were unavailable.

Raw evidence is in deepseek-warm-240.json, deepseek-followup.json, deepseek-raid-comparison.json, code-functional-27b-dflash-functional-configs.json, code-functional-27b-quality-configs.json, and flash-next-refusal-toggle-test.json.
