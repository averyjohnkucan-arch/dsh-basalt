import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { BasaltService } from "../lib/service.js";
import { BasaltAdapter } from "../lib/adapter.js";
import { temporary, modelFile } from "./helpers.js";

test(
  "Basalt v0.4.0 mock server: real launch contract, authenticated readiness, DSH stream, owned cleanup",
  { skip: !process.env.BASALT_SOURCE },
  async (t) => {
    const root = await temporary(t);
    let launch;
    const service = new BasaltService(
      { dataDir: join(root, "state") },
      () => {},
      {
        runtimeStatus: async () => ({ ready: true, libraryDirs: [] }),
        spawn(command, args, options) {
          launch = { command, args, options };
          const cfg = JSON.parse(
            readFileSync(args[args.indexOf("--config") + 1], "utf8"),
          );
          return spawn(
            process.env.BASALT_PYTHON || "python3",
            [
              "-m",
              "serve.server",
              "--mock-engine",
              "--port",
              String(cfg.server.port),
              "--alias",
              cfg.models[0].alias,
              "--api-key",
              args[args.indexOf("--api-key") + 1],
            ],
            {
              ...options,
              cwd: process.env.BASALT_SOURCE,
              env: { ...options.env, OPENBLAS_NUM_THREADS: "1" },
            },
          );
        },
      },
    );
    await service.init();
    t.after(() => service.dispose());
    const profile = await service.action("import", {
      path: await modelFile(join(root, "q.basalt")),
    });
    const adapter = new BasaltAdapter({ get: () => undefined }, service),
      call = await adapter.prepareCall("basalt", profile.id);
    const chunks = [];
    for await (const chunk of call.stream({
      provider: "basalt",
      model: profile.id,
      system: "Keep this instruction",
      messages: [{ role: "user", content: [{ type: "text", text: "Hello" }] }],
      maxTokens: 128,
    }))
      chunks.push(chunk);
    assert.ok(chunks.some((c) => c.type === "text-delta"));
    assert.ok(
      chunks.some((c) => c.type === "finish" && c.reason.kind === "stop"),
    );
    assert.equal(launch.options.detached, true);
    assert.equal(launch.args[0], "serve");
    assert.ok(launch.args.includes("--python"));
    assert.equal(service.answering, 0);
    const state = service.servers.get(profile.id);
    const denied = await fetch(`http://127.0.0.1:${state.port}/v1/models`);
    assert.equal(denied.status, 401);
    await service.action("stop", { id: profile.id });
    assert.equal(service.servers.size, 0);
    await assert.rejects(fetch(`http://127.0.0.1:${state.port}/health`));
  },
);
