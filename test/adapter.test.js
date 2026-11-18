import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { BasaltAdapter } from "../lib/adapter.js";

test("real DSH adapter preserves messages, streams tools + reasoning, honors output limits and authenticates", async (t) => {
  const captured = [];
  const server = http.createServer(async (req, res) => {
    let body = "";
    for await (const bytes of req) body += bytes;
    captured.push({ body: JSON.parse(body), auth: req.headers.authorization });
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    const base = {
      id: "fixture",
      object: "chat.completion.chunk",
      created: 1,
      model: "q",
    };
    const emit = (delta, reason = null) =>
      res.write(
        "data: " +
          JSON.stringify({
            ...base,
            choices: [{ index: 0, delta, finish_reason: reason }],
          }) +
          "\n\n",
      );
    emit({ role: "assistant", reasoning_content: "Let me check." });
    emit({ content: "OK" });
    emit({
      tool_calls: [
        {
          index: 0,
          id: "call_1",
          type: "function",
          function: { name: "lookup", arguments: '{"query":"hello"}' },
        },
      ],
    });
    emit({}, "tool_calls");
    res.end("data: [DONE]\n\n");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const profile = {
    samplingPresets: {
      instruct: { top_p: 0.8, presence_penalty: 1.5 },
      thinking: { top_p: 0.95, presence_penalty: 0 },
    },
    id: "q",
    name: "Test Qwen",
    context: 32768,
    vision: false,
    model: { architecture: "qwen4exp", layerCount: 48, embeddingLength: 2560 },
  };
  let releases = 0;
  const service = {
    profiles: [profile],
    profile: () => profile,
    apiKey: "test-private-key",
    shutdown: new AbortController(),
    acquire: async () => ({
      state: { port: server.address().port },
      release() {
        releases++;
      },
    }),
  };
  const adapter = new BasaltAdapter({ get: () => undefined }, service);
  const call = await adapter.prepareCall("basalt", "q");
  assert.equal(call.model.reasoning.defaultEffort, "medium");
  const messages = [
      { role: "user", content: [{ type: "text", text: "Say OK" }] },
    ],
    original = structuredClone(messages);
  for (const effort of [
    undefined,
    "off",
    "low",
    "medium",
    "high",
    "xhigh",
    "uncensored",
    "medium",
    "uncensored",
  ]) {
    const chunks = [];
    for await (const chunk of call.stream({
      provider: "basalt",
      model: "q",
      messages,
      system: "Original instructions",
      maxTokens: 47,
      reasoningEffort: effort,
      tools: [
        {
          name: "lookup",
          description: "Look up an item",
          inputSchema: {
            type: "object",
            properties: { query: { type: "string" } },
          },
        },
      ],
    }))
      chunks.push(chunk);
    const { body, auth } = captured.at(-1);
    assert.equal(auth, "Bearer test-private-key");
    assert.equal(body.top_p, effort === "off" ? 0.8 : 0.95);
    assert.equal(body.presence_penalty, effort === "off" ? 1.5 : 0);
    assert.equal(
      body.reasoning_effort,
      effort === "off"
        ? "none"
        : effort === "high"
          ? "xhigh"
          : effort === "uncensored"
            ? "medium"
            : effort || "medium",
    );
    assert.equal(body.max_completion_tokens ?? body.max_tokens, 47);
    assert.equal(body.experimental_speed_projection, effort === "uncensored");
    assert.deepEqual(
      body.messages.filter((m) => m.role === "system"),
      [{ role: "system", content: "Original instructions" }],
    );
    assert.ok(
      body.messages.some((m) => JSON.stringify(m.content).includes("Say OK")),
    );
    assert.ok(chunks.some((c) => c.type === "text-delta" && c.text === "OK"));
    assert.ok(
      chunks.some((c) => c.type === "finish" && c.reason.kind === "tool-calls"),
    );
    if (effort === "off")
      assert.equal(body.chat_template_kwargs.enable_thinking, false);
  }
  assert.deepEqual(messages, original);
  assert.equal(releases, 9);
});

test("failed/aborted streams always release GPU admission", async () => {
  const p = {
    id: "q",
    name: "Q",
    context: 32768,
    model: { architecture: "qwen35" },
  };
  let releases = 0;
  const shutdown = new AbortController();
  const service = {
    profiles: [p],
    profile: () => p,
    apiKey: "key",
    shutdown,
    acquire: async () => ({
      state: { port: 1 },
      signal: AbortSignal.abort(new Error("Aborted")),
      release() {
        releases++;
      },
    }),
  };
  const adapter = new BasaltAdapter({ get: () => undefined }, service);
  const call = await adapter.prepareCall("basalt", "q");
  try {
    for await (const _ of call.stream({
      provider: "basalt",
      model: "q",
      messages: [],
    }))
      void _;
  } catch {}
  assert.equal(releases, 1);
});
