# Native mixed-tensor source preview

This custom build imports original Strata scaled FP8 PLE, independently mixed NVFP4/Q8 experts, legacy DeepSeek Engram tensors, and experimental single-file dense Qwen NInfer v3 artifacts. GPU fetch can use completed pinned-RAM expert misses while disk reads remain pending; CPU Q8 dispatch uses a guarded AVX-VNNI-INT8 route.

The NInfer route preserves target NVFP4 planes/scales and BF16 attention projections, losslessly repacks the Q8G32 head, and materializes the semantic BF16 embedding. Its included DFlash2 projections stay NVFP4. Small proposal selector codebooks are materialized as BF16 for Basalt's selector; target weights are unchanged. Vision and source MTP are excluded on this route. Basalt uses INT8 or FP16 KV on the dense path, even when the source NInfer profile uses NVFP4 KV. See the patched upstream model-file documentation for exact import scope.

## Build and runtime

Clone `source.json`'s upstream, check out its exact revision, and apply `patches/basalt-native-strata-support.patch` with `git apply --index`. `git write-tree` must match `source_tree`. Configure a Release CMake build with `-DCMAKE_CUDA_ARCHITECTURES=120a`, then build target `basalt`. Follow that pinned source's toolchain/dependency instructions. The tested private toolchain was CUDA 13.1.115 on Linux SM120.

A custom runtime directory needs `bin/basalt`, the matching `serve` and `data` trees, `.venv/bin/python` with the server dependencies, and its private CUDA 13 libraries. Select it in the plugin's runtime-directory setting. Its `dsh-engine.json` must name version `0.4.0`, relative `libraryDirs`, and the applicable features from `source.json`. Do not give a stock runtime a custom feature receipt. The plugin refuses required custom features before starting a GPU process; dense KV residency is an explicit model-specific control. Managed stock installation remains separate.

## Qualification

Focused validation includes a complete latest-source build; mixed-expert CPU/GPU checks on actual layers 0, 1, 3 and 14; independent BF16 product references at real attention shapes; window row-invariance checks; exact finite-import mapping/code/scale tests; and real dense text plus DFlash2 serving. Small generated-function checks passed 2 of 3 tasks; an LRU ordering error is retained as a quality limitation. Full BF16-reference perplexity, dense vision, Windows and other architectures remain unqualified.

Sustained 8K-code and 80%-full text/chat/story measurements are in progress. Restored-prefix screens and short compatibility smokes are not cold-prefill or final tuned-throughput claims. This is a source preview, not a binary release or completed tuned release.
