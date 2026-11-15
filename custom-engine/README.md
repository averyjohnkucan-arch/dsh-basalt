# Native Strata tensor import preview

This source preview adds original Strata FP8 PLE and mixed NVFP4/Q8 expert import to a custom Basalt build. The plugin checks the runtime feature receipt before loading a pack that needs these features. Managed stock Basalt does not acquire the custom features.

The patch is pinned by `source.json`. Apply it to that exact upstream revision, build a Release engine for CUDA architecture `120a`, then select the custom runtime directory in the plugin. The feature receipt must list `fp8-ple` and `mixed-nvfp4-q8` under `features`. The normal managed installer remains available separately.

Validation on the latest pinned source: a complete Release build; six focused CPU/GPU tests; actual mixed-format expert parity on layers 0, 1, 3 and 14 with zero failures. Plugin validation: 26 JavaScript tests and three Python tests. Previous native long-context runs used an earlier upstream revision; their performance is not a latest-build claim. The final coding-workload tuning sweep, real plugin-owned GPU requests, and NVFP4-all dense-model experiment are pending. Vision and BF16-reference perplexity remain unqualified.

The initial managed-release inspection is recorded in `ENGINE-INSPECTION.md`. This preview is experimental and is not a completed tuned release.
