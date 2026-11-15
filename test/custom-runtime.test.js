import test from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { BasaltService } from "../lib/service.js";
import { temporary, modelFile } from "./helpers.js";

test("a custom pack refuses a stock runtime before starting any GPU process", async (t) => {
  const root = await temporary(t);
  let spawned = false;
  const service = new BasaltService(
    { dataDir: join(root, "state") },
    () => {},
    {
      runtimeStatus: async () => ({ ready: true, features: [] }),
      spawn() {
        spawned = true;
        throw new Error("must not spawn");
      },
    },
  );
  await service.init();
  t.after(() => service.dispose());
  const profile = await service.action("import", {
    path: await modelFile(join(root, "mixed.basalt"), "qwen4exp", {
      requiredEngineFeatures: ["mixed-nvfp4-q8"],
    }),
  });
  await assert.rejects(
    service.action("start", { id: profile.id }),
    /custom Basalt runtime.*mixed-nvfp4-q8/,
  );
  assert.equal(spawned, false);
  assert.equal(service.answering, 0);
});
