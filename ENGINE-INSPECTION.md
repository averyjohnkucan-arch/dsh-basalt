# Engine inspection

Inspected the upstream **Basalt v0.4.0** tag and its official Linux x64 release, including the CLI entry point, Python server, model format, native configuration validation, reasoning templates, router, authentication and serving lifecycle.

- Archive: `basalt-v0.4.0-linux-x64.tar.gz`, 66,128,201 bytes.
- SHA-256: `372206464e3d586406244b9745e1753cd2bc82006eb7a50e311d220c8b7f00c1`. The downloaded archive matches GitHub's published digest.
- Managed setup uses an isolated Python environment, upstream pinned requirements, `nvidia-cuda-runtime==13.0.96` and `nvidia-cublas==13.0.2.14`.
- Dependency validation passes. The native executable resolves its CUDA libraries privately and runs `--help` successfully. Source inspection confirms that help returns before GPU selection or inference initialization.
- The DSH integration was tested against the upstream Python mock engine, including API-key authentication, nested `status.value` model readiness, text/reasoning/tool streaming, output limits and owned-process cleanup.
- The plugin uses native model format v2 and server config v2. It does not reuse Strata's old flags, checkpoint API, preparer or tuning scripts.

## Upstream CPU checks

The configuration, reasoning-effort, security, router, tool-choice and context-overflow suites ran **158 tests**: **156 passed, 1 skipped, 1 failed**.

The failure is `serve.tests.test_router.Preload.test_the_first_entry_loads_through_the_queue`. `Router.preload()` enqueues a non-request `Turn(holds=False)`. The test's `queued()` helper counts every turn, then expects `["A"]` after enqueuing an actual request for A. While loading is held, the queue contains the preload marker and the request, so the intended observation is two turns, or one request-bearing turn. The test can pass accidentally before the chat request arrives; otherwise its ten-second start gate expires before the assertion succeeds.

A separate CPU probe filtered `queued()` to request-bearing turns for that assertion. The same preload scenario then passed, and the request completed normally. No upstream source or runtime file was patched. The plugin's own native mock integration also passes. This finding is a released test assertion issue; it is not being represented as a clean upstream suite run.

## Verification boundary

Engine preparation, archive verification, dependency inspection, CLI help, Python mock serving and plugin tests use no GPU inference. No model weights were downloaded or converted during preparation. No live Strata process or installed DSH plugin was changed or restarted.

**Real Blackwell inference, memory fit, model quality, vision encoding and performance remain untested.** They require an explicit GPU run once the current workload can be interrupted. The release makes no throughput or end-to-end GPU-validation claim.

References: [upstream release](https://github.com/jesdga95/basalt/releases/tag/v0.4.0), [model format](https://github.com/jesdga95/basalt/blob/v0.4.0/docs/model-file.md), [configuration](https://github.com/jesdga95/basalt/blob/v0.4.0/docs/configuration/index.md), [sampling and thinking](https://github.com/jesdga95/basalt/blob/v0.4.0/docs/configuration/sampling.md).
