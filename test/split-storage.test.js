import test from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import {
  inspectModel,
  newProfile,
  validateProfile,
  serverConfig,
} from "../lib/models.js";
import { BasaltService } from "../lib/service.js";
import { temporary, modelFile } from "./helpers.js";

test("external Engram is a DeepSeek-only absolute path and survives native config export", async (t) => {
  const root = await temporary(t),
    p = newProfile(
      await inspectModel(
        await modelFile(join(root, "ds.basalt"), "deepseek41"),
      ),
    );
  p.runtimeDir = join(root, "measured-runtime");
  p.engineOptions = { "deepseek-engram-gguf": join(root, "shared.gguf") };
  assert.equal(validateProfile(p), p);
  assert.equal(
    serverConfig(p, 18081, join(root, "cache")).models[0][
      "deepseek-engram-gguf"
    ],
    p.engineOptions["deepseek-engram-gguf"],
  );
  for (const value of ["relative.gguf", "/bad\0file", 42])
    assert.throws(() =>
      validateProfile({
        ...p,
        engineOptions: { "deepseek-engram-gguf": value },
      }),
    );
  for (const value of ["relative", 42, "/bad\0folder"])
    assert.throws(() => validateProfile({ ...p, runtimeDir: value }));
  assert.throws(() =>
    validateProfile({
      ...p,
      model: { ...p.model, architecture: "qwen4exp" },
      kv: "int8",
      context: 262144,
    }),
  );
});
test("saved profile selects its measured runtime before a GPU worker can launch", async (t) => {
  const root = await temporary(t),
    seen = [],
    service = new BasaltService({ dataDir: root }, () => {}, {
      runtimeStatus: async (path) => {
        seen.push(path);
        return { ready: false, error: "test stop" };
      },
    });
  await service.init();
  const p = await service.action("import", {
    path: await modelFile(join(root, "ds.basalt"), "deepseek41"),
  });
  p.runtimeDir = join(root, "measured-runtime");
  await assert.rejects(
    service.startServer(p.id, new AbortController().signal),
    /test stop/,
  );
  assert.equal(seen.at(-1), p.runtimeDir);
  assert.equal(service.servers.size, 0);
  await service.dispose();
});
test("external Engram profile rejects a runtime lacking the implementation feature", async (t) => {
  const root = await temporary(t),
    service = new BasaltService({ dataDir: root }, () => {}, {
      runtimeStatus: async () => ({ ready: true, features: [] }),
    });
  await service.init();
  const p = await service.action("import", {
    path: await modelFile(join(root, "ds.basalt"), "deepseek41"),
  });
  p.engineOptions = { "deepseek-engram-gguf": join(root, "shared.gguf") };
  await assert.rejects(
    service.startServer(p.id, new AbortController().signal),
    /external-Engram runtime/,
  );
  assert.equal(service.servers.size, 0);
  await service.dispose();
});
