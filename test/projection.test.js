import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { temporary } from "./helpers.js";
import {
  projectionAsset,
  supportsProjection,
  prepareProjection,
  withProjection,
} from "../lib/projection.js";
import { thinkingInfo, thinkingPayload } from "../lib/thinking.js";
const model = {
  architecture: "qwen4exp",
  name: "Qwen3.8-Flash-Next NVFP4",
  layerCount: 48,
  embeddingLength: 2560,
};
test("Medium default, native Xhigh, and Uncensored=Medium with an engine-only flag", () => {
  const p = { model, defaultEffort: "high" };
  assert.equal(thinkingInfo(p).defaultEffort, "medium");
  assert.deepEqual(
    thinkingInfo(p).efforts.map((x) => x.id),
    ["off", "low", "medium", "xhigh", "uncensored"],
  );
  assert.deepEqual(thinkingPayload(p, "medium"), {
    reasoning_effort: "medium",
    enable_thinking: true,
    experimental_speed_projection: false,
  });
  assert.deepEqual(thinkingPayload(p, "uncensored"), {
    reasoning_effort: "medium",
    enable_thinking: true,
    experimental_speed_projection: true,
  });
  assert.equal(thinkingPayload(p, "high").reasoning_effort, "xhigh");
  for (const m of [
    { ...model, architecture: "deepseek41" },
    { ...model, embeddingLength: 4096 },
    { ...model, name: "Swift 1.5" },
    { architecture: "qwen4exp", name: "Unknown" },
  ])
    assert.equal(supportsProjection({ model: m }), false);
  assert.throws(
    () =>
      thinkingPayload({ model: { architecture: "deepseek41" } }, "uncensored"),
    /Unsupported/,
  );
});
test("projection launch options are immutable and include the exact layer range", () => {
  const config = { models: [{ model: "/model.basalt" }] };
  const before = structuredClone(config);
  const actual = withProjection(config, "/vector.gguf");
  assert.deepEqual(config, before);
  assert.equal(actual.models[0]["control-vector-scaled"], "/vector.gguf:1.0");
  assert.deepEqual(actual.models[0]["control-vector-layer-range"], [4, 44]);
  assert.equal(actual.models[0]["cvec-mode"], "project");
});
test("bad downloaded direction is never installed", async (t) => {
  const root = await temporary(t);
  await assert.rejects(
    prepareProjection(root, {
      fetcher: async () => new Response("bad vector"),
    }),
    /checksum/,
  );
});
test("the pinned real direction is fetched once, verified, and repaired after corruption", async (t) => {
  const fixture = process.env.BASALT_PROJECTION_FIXTURE;
  if (!fixture) {
    t.skip("Set BASALT_PROJECTION_FIXTURE for the real asset");
    return;
  }
  const bytes = await readFile(fixture);
  assert.equal(bytes.length, projectionAsset.bytes);
  let calls = 0;
  const root = await temporary(t);
  const fetcher = async (url) => {
    assert.equal(url, projectionAsset.url);
    calls++;
    return new Response(bytes);
  };
  const path = await prepareProjection(root, { fetcher });
  assert.deepEqual(await readFile(path), bytes);
  assert.equal(await prepareProjection(root, { fetcher }), path);
  assert.equal(calls, 1);
  await writeFile(path, "corrupt");
  await prepareProjection(root, { fetcher });
  assert.equal(calls, 2);
  assert.deepEqual(await readFile(path), bytes);
});
