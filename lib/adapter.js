import {
  LlmAdapter,
  LlmError,
  resolveRetryPolicy,
  resolveImageAttachmentAccess,
} from "@deepseek-ai/dsh-llm";
import { PiAiAdapter } from "@deepseek-ai/dsh-llm-pi-ai";
import { createProvider } from "@earendil-works/pi-ai";
import { openAICompletionsApi } from "@earendil-works/pi-ai/api/openai-completions.lazy";
import { thinkingInfo, thinkingPayload } from "./thinking.js";

/** DSH owns wire conversion, tools, streaming and image attachment handling. */
export class BasaltAdapter extends LlmAdapter {
  constructor(ctx, service) {
    super();
    this.ctx = ctx;
    this.service = service;
  }
  providerInfo(provider) {
    return { id: provider, name: "Basalt" };
  }
  profile(id) {
    try {
      return this.service.profile(id);
    } catch {
      throw new LlmError("Saved Basalt model not found", "UNKNOWN_MODEL");
    }
  }
  async listModels(provider) {
    return this.service.profiles.map((p) => ({
      provider,
      id: p.id,
      name: p.name,
      inputModalities: p.vision ? ["text", "image"] : ["text"],
    }));
  }
  delegate(provider, p, state, effort) {
    const model = {
      id: p.id,
      name: p.name,
      api: "openai-completions",
      provider,
      baseUrl: `http://127.0.0.1:${state?.port || 1}/v1`,
      reasoning: true,
      thinkingLevelMap: { off: "", xhigh: "xhigh" },
      input: p.vision ? ["text", "image"] : ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: p.context,
      maxTokens: p.context,
      compat: { supportsDeveloperRole: false, supportsStore: false },
    };
    const api = openAICompletionsApi();
    const piProvider = createProvider({
      id: provider,
      name: "Basalt",
      baseUrl: model.baseUrl,
      auth: { apiKey: { name: "Basalt", resolve: async () => ({ auth: {} }) } },
      models: [model],
      api: {
        ...api,
        streamSimple(model, context, options) {
          return api.streamSimple(model, context, {
            ...options,
            // Keep DSH/pi-ai's wire conversion; add only Basalt's documented request controls.
            onPayload(payload) {
              return {
                ...payload,
                ...thinkingPayload(p, effort),
              };
            },
          });
        },
      },
    });
    const profiles = new Map([
      [
        provider,
        {
          provider,
          displayName: "Basalt",
          piProvider,
          modelErrors: new Map(),
          configuredMaxTokens: new Map(),
          streamIdleTimeoutMs: 900000,
          maxRequestImageBytes: 20 * 1024 * 1024,
          requestImagePixelBudget: 4 * 1024 * 1024,
          requestImageMaxBytes: 1024 * 1024,
          retryPolicy: resolveRetryPolicy(),
          headers: {},
        },
      ],
    ]);
    return new PiAiAdapter({
      profiles: () => profiles,
      resolveApiKey: async () => this.service.apiKey,
      auth: {
        credentials: {
          read: async () => undefined,
          list: async () => [],
          modify: async () => {
            throw new Error("Configure local engine credentials in Basalt");
          },
          delete: async () => {},
        },
        authContext: {
          env: async () => undefined,
          fileExists: async () => false,
        },
      },
      resolveAttachments: () => this.ctx.get("attachments"),
      resolveImageAccess: (attachments, ref) =>
        resolveImageAttachmentAccess(
          attachments,
          (path) => this.ctx.get("fs")?.processPathFromHostPath(path),
          ref,
        ),
    });
  }
  async resolveModel(provider, id, signal) {
    const profile = this.profile(id);
    const model = await this.delegate(provider, profile).resolveModel(
      provider,
      id,
      signal,
    );
    return { ...model, reasoning: thinkingInfo(profile) };
  }
  async prepareCall(provider, id, signal) {
    const adapter = this,
      service = this.service,
      profile = this.profile(id);
    const model = await this.resolveModel(provider, id, signal);
    return {
      model,
      async *stream(options) {
        const combined = options.signal
          ? AbortSignal.any([options.signal, service.shutdown.signal])
          : service.shutdown.signal;
        const lease = await service.acquire(id, combined);
        try {
          const call = await adapter
            .delegate(provider, profile, lease.state, options.reasoningEffort)
            .prepareCall(provider, id, lease.signal);
          yield* call.stream({
            ...options,
            signal: lease.signal,
            reasoningEffort:
              thinkingPayload(profile, options.reasoningEffort)
                .reasoning_effort === "none"
                ? "off"
                : thinkingPayload(profile, options.reasoningEffort)
                    .reasoning_effort,
          });
        } finally {
          lease.release();
        }
      },
    };
  }
  async *stream(options) {
    const call = await this.prepareCall(
      options.provider,
      options.model,
      options.signal,
    );
    yield* call.stream(options);
  }
}
