import test from "node:test";
import assert from "node:assert/strict";
import { mkdir, rename, open } from "node:fs/promises";
import { join } from "node:path";
import { BasaltService } from "../lib/service.js";
import { temporary, modelFile } from "./helpers.js";

test("portable Basalt config verifies the entire pack and creates an independent saved profile", async (t) => {
  const root = await temporary(t),
    weights = join(root, "weights");
  await mkdir(weights);
  const s = new BasaltService({ dataDir: root });
  await s.init();
  t.after(() => s.dispose());
  const path = await modelFile(join(weights, "old.basalt"), "qwen4exp", {
    vision: true,
  });
  const p = await s.action("import", { path });
  await s.action("save", {
    profile: {
      ...p,
      name: "My model",
      vision: true,
      kv: "int8",
      context: 32768,
    },
  });
  async function job(action, payload) {
    await s.action(action, payload);
    await s.jobPromise;
    return s.job;
  }
  const exported = await job("export-config", { id: p.id });
  assert.equal(exported.status, "complete", exported.error);
  const config = exported.result;
  assert.ok(!JSON.stringify(config).includes(root));
  assert.equal(config.files.length, 1);
  config.settings.gpu = "7";
  config.settings.id = p.id;
  const moved = join(weights, "renamed.data");
  await rename(path, moved);
  const imported = await job("import-config", { config, root: weights });
  assert.equal(imported.status, "complete", imported.error);
  const [original, q] = s.profiles;
  assert.equal(original.id, p.id);
  assert.notEqual(original.id, q.id);
  assert.equal(q.name, "My model");
  assert.equal(q.model.path, moved);
  assert.equal(q.gpu, "0");
  assert.equal(q.vision, true);
  assert.equal(q.kv, "int8");
  assert.equal(q.context, 32768);
  const restarted = new BasaltService({ dataDir: root });
  await restarted.init();
  assert.deepEqual(restarted.profile(q.id), q);
  await restarted.dispose();
  const file = await open(moved, "r+");
  try {
    await file.write(Buffer.from("X"), 0, 1, 1800);
  } finally {
    await file.close();
  }
  const bad = await job("import-config", { config, root: weights });
  assert.equal(bad.status, "failed");
  assert.match(bad.error, /No exact size and MD5 match/);
  assert.equal(s.profiles.length, 2);
});
