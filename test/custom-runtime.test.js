import test from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { BasaltService } from "../lib/service.js";
import { temporary, modelFile } from "./helpers.js";

for (const [architecture, feature] of [
  ["qwen4exp", "mixed-nvfp4-q8"],
  ["qwen35", "qwen35-bf16-projections"],
  ["qwen35", "qwen35-nvfp4-dflash2"],
])
  test(`a ${feature} pack refuses a stock runtime before starting any GPU process`, async (t) => {
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
      path: await modelFile(join(root, "mixed.basalt"), architecture, {
        requiredEngineFeatures: [feature],
      }),
    });
    await assert.rejects(
      service.action("start", { id: profile.id }),
      new RegExp(`custom Basalt runtime.*${feature}`),
    );
    assert.equal(spawned, false);
    assert.equal(service.answering, 0);
  });
