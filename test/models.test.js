import test from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { open, symlink, writeFile } from "node:fs/promises";
import {
  inspectModel,
  newProfile,
  scanModels,
  serverConfig,
  validateProfile,
} from "../lib/models.js";
import { thinkingInfo, thinkingPayload } from "../lib/thinking.js";
import { temporary, modelFile } from "./helpers.js";

test("native v2 header + metadata inspection handles every supported architecture", async (t) => {
  const root = await temporary(t);
  for (const arch of ["qwen4exp", "deepseek41", "qwen35"]) {
    const path = await modelFile(join(root, arch + ".basalt"), arch, {
      vision: true,
    });
    const model = await inspectModel(path),
      p = newProfile(model);
    assert.equal(model.architecture, arch);
    assert.equal(model.vision, true);
    assert.equal(p.context, arch === "deepseek41" ? 1048576 : 262144);
    assert.equal(validateProfile(p), p);
    const cfg = serverConfig(p, 18081, join(root, "cache"));
    assert.equal(cfg.version, 2);
    assert.equal(cfg.models[0].alias, p.id);
    assert.equal(cfg.models[0]["answer-room"], 0);
    assert.equal(cfg.models[0]["fit-max-tokens"], true);
    assert.equal(cfg.server.host, "127.0.0.1");
  }
});
test("rejects old packs, truncation, corrupted metadata, unknown architectures and invalid section offsets", async (t) => {
  const root = await temporary(t);
  await assert.rejects(
    inspectModel(
      await modelFile(join(root, "old.basalt"), "qwen4exp", { version: 1 }),
    ),
    /v2/,
  );
  await assert.rejects(
    inspectModel(await modelFile(join(root, "bad-arch.basalt"), "unknown")),
    /architecture/,
  );
  const path = await modelFile(join(root, "bad.basalt"));
  const f = await open(path, "r+");
  await f.write(Buffer.from("X"), 0, 1, 2097152);
  await f.close();
  await assert.rejects(inspectModel(path), /checksum/);
  await writeFile(join(root, "short.basalt"), "BASALTMF");
  await assert.rejects(inspectModel(join(root, "short.basalt")), /header/);
});
test("recursive inventory separates bad packs and avoids directory symlink cycles", async (t) => {
  const root = await temporary(t);
  await modelFile(join(root, "good.basalt"));
  await writeFile(join(root, "bad.basalt"), "bad");
  await symlink(root, join(root, "cycle"));
  const scan = await scanModels(root);
  assert.equal(scan.models.length, 1);
  assert.equal(scan.errors.length, 1);
  await assert.rejects(scanModels(root, { limit: 1 }), /limit/);
});
test("model-specific KV, context, GPU and image validation", async (t) => {
  const root = await temporary(t);
  const p = newProfile(
    await inspectModel(await modelFile(join(root, "q.basalt"))),
  );
  for (const patch of [
    { context: 1048576 },
    { kv: "fp8" },
    { gpu: "auto" },
    { gpu: "0,0" },
    { vision: true },
    { diskCacheMiB: -1 },
    { answerRoom: NaN },
    { id: "../escape" },
  ])
    assert.throws(() => validateProfile({ ...p, ...patch }));
  const dense = {
    ...p,
    model: { ...p.model, architecture: "qwen35" },
    gpu: "0,1",
  };
  assert.throws(() => validateProfile(dense), /one GPU/);
});
test("Qwen defaults to Medium, all models expose Off, and native effort payloads contain no prompt text", () => {
  for (const arch of ["qwen4exp", "qwen35", "deepseek41"]) {
    const p = { model: { architecture: arch } },
      info = thinkingInfo(p);
    assert.equal(info.defaultEffort, arch === "deepseek41" ? "high" : "medium");
    assert.ok(info.efforts.some((e) => e.id === "off"));
    assert.equal(thinkingPayload(p, "off").enable_thinking, false);
    assert.equal(
      thinkingPayload(p, "off").chat_template_kwargs.enable_thinking,
      false,
    );
    assert.equal(thinkingPayload(p).reasoning_effort, info.defaultEffort);
    assert.equal("messages" in thinkingPayload(p), false);
    assert.throws(() => thinkingPayload(p, "invented"), /Unsupported/);
  }
});
