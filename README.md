# Basalt for DeepSeek Harness

Requires DeepSeek Harness 0.2.2-rc.4 and Node.js 24.9 or newer. In **Plugins → Add plugin**, paste `https://github.com/averyjohnkucan-arch/dsh-basalt` and enable it.

## Move or back up a saved profile

1. Save your settings, then choose **Export config** on the model. When the file check finishes, choose **Download config JSON**.
2. On the destination computer, open **Import config**, choose the JSON and enter the folder containing your model weights. Choose **Find files and import profile**.
3. Select the imported profile in chat. Import creates a separate saved profile and uses size and full-file MD5 to match existing weights. The JSON contains settings and file identities. Keep the weight files separately.

GPU device numbers, ports, runtime paths and credentials are local to the destination.

Run [Basalt](https://github.com/jesdga95/basalt) models from DSH's model picker. Basalt targets NVIDIA Blackwell GPUs (sm_120). This is a separate provider from Strata, with separate settings, model profiles, processes and conversation caches.

## Install

Install the `dsh-basalt-0.1.1.tgz` asset from this repository's releases using DSH's plugin installer. The package includes the built settings interface; installation needs no frontend build.

Requires DSH **0.2.2-rc.4**, Node **24.9+**, Linux x64 with AVX2, Python **3.12+**, an NVIDIA Blackwell GPU and NVIDIA driver **580.95.05+**. Managed engine preparation installs Basalt **0.4.0**, its pinned Python dependencies, and private NVIDIA CUDA 13 runtime/cuBLAS libraries. It does not change system CUDA or another provider's environment. Allow at least 1.5 GiB free during setup, plus model storage.

1. Open **Settings → Models → Basalt → Engine and CPU settings**.
2. Click **Prepare engine**. This downloads and verifies the pinned release and creates its Python environment. It starts no model and uses no GPU inference.
3. Inspect an existing `.basalt` file/folder and click **Add model**, or list and download an official model pack.
4. Set the context size, native KV format and GPU device numbers. Enable image input if the pack contains a projector.
5. Select the saved Basalt model in chat. It loads on the first request. **Load on GPU** is also available explicitly in settings.

Enabling the plugin, opening settings, listing models and inspecting packs never starts a GPU engine. Model downloads can be very large. The downloader checks available disk space, pins the Hugging Face commit, verifies the published size and SHA-256, and imports only a completed file. Cancellation discards the partial download.

## Models and settings

| Model               | Maximum context offered | Native KV choices      | Default thinking |
| ------------------- | ----------------------: | ---------------------- | ---------------- |
| Qwen3.8-Flash-Next  |                 262,144 | fp16, int8, q4_0, k8v4 | Medium           |
| DeepSeek-V4.1-Flash |               1,048,576 | fp8, fp16              | High             |
| Qwen3.8-27B         |                 262,144 | fp16, int8             | Medium           |

These are model limits, not a promise that the chosen context fits your available memory. Reduce context or choose an appropriate KV format when necessary. Dense Qwen3.8-27B uses one GPU; the MoE models can use explicit peer GPU numbers.

- **Cores kept free:** limits the entire server/engine/helper process tree with Linux affinity. Keeping 2 free out of 24 logical CPUs permits 22. This is an upper bound; Basalt's native expert pool may use fewer workers. Saving settings unloads this provider's idle models; the next load uses the new limit. Settings cannot interrupt an active Basalt answer.
- **Thinking:** Off is available for every model. Qwen Medium selects the native template's medium effort, which adds no effort instruction. Low and High use Basalt's native effort instructions; High maps to xhigh in its Qwen dialect. DeepSeek exposes its native Low, High and Max levels. The plugin adds no system messages or steering text.
- **Output:** no fixed 32K plugin cap. DSH's requested limit is forwarded, and Basalt clamps it to remaining context with `fit-max-tokens`. Answer token reserve defaults to 0, disabling Basalt's automatic answer-room restriction. An explicit DSH request limit still applies.
- **Conversation cache:** native Basalt cache, isolated per saved profile. Disk budget defaults to 16 GiB and RAM parking to 0. This is a maximum budget, not a reservation. Clearing a cache unloads its idle model first. Removing a profile leaves its model file untouched.
- **GPU scheduling:** integrates with `dsh-model-scheduler` when present. Admission lasts through the streamed answer; model switches wait. Without it, Basalt serializes its own requests. Unload other GPU providers before using the independent queue.

Profile edits, cache clearing, runtime setup and removal refuse to interrupt an active Basalt request. Unload and shutdown target only process groups started by this plugin. The engine listens on loopback with a generated API key; management actions use DSH's authenticated Connection route.

## Differences from Strata

Basalt reads native **`.basalt` v2 packs**, which combine weights, tokenizer, draft model and optional vision projector. A Strata GGUF profile cannot be reused directly. Import or download a Basalt pack instead; this plugin never converts, renames or deletes Strata's weights.

The plugin uses Basalt's native v2 configuration, model loading status, effort controls and conversation cache. Strata's old tuning scripts, engine flags, separate projector/MTP setup and checkpoint RPCs are not carried over. Basalt selects its own native execution defaults. No GPU autotuning or benchmark runs happen during setup.

Windows, Flash-Next context extension with YaRN, arbitrary engine flags, video/PDF chat attachments and Strata's experimental projection mode are not exposed by this release.

## Development and verification

```sh
npm ci
npm run build
npm test
```

Set `BASALT_SOURCE` to an upstream Basalt v0.4.0 checkout and `BASALT_PYTHON` to Python with its `requirements.txt` installed to run the native mock-server integration test. CI does this automatically. The integration starts Basalt's Python **mock** engine, checks authenticated model readiness, sends a DSH request and verifies owned-process cleanup. It never loads weights or creates a CUDA inference context.

This release has CPU, mock-server, DSH adapter and UI build validation. **Real GPU inference has not been tested.** The initial preparation deliberately leaves ongoing inference in other providers untouched. No performance claims are made.

Engine preparation is also available without DSH:

```sh
python3 scripts/prepare-engine.py /absolute/path/to/new/runtime
# Optional: --archive /path/to/basalt-v0.4.0-linux-x64.tar.gz
```

The runtime folder must be new. The installer refuses an existing destination. Source release URL and SHA-256 are recorded in `engine.json`; model weights are not included.

## License

MIT. DSH integration utilities adapted from `dsh-strata` retain its license. Basalt and its bundled upstream code have their own MIT and third-party notices. NVIDIA runtime wheels retain NVIDIA's licenses. Model licenses remain those of their respective model cards.
