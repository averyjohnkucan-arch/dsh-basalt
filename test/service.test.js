import test from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { BasaltService } from "../lib/service.js";
import { temporary, modelFile } from "./helpers.js";

test("activation, discovery, import, save and restart persist profiles without starting a process", async (t) => {
  const root = await temporary(t);
  let spawns = 0,
    changes = 0;
  const service = new BasaltService(
    { dataDir: join(root, "state") },
    () => changes++,
    {
      spawn() {
        spawns++;
        throw new Error("Must not start");
      },
    },
  );
  await service.init();
  const path = await modelFile(join(root, "test.basalt"));
  const p = await service.action("import", { path });
  assert.equal((await service.action("import", { path })).id, p.id);
  assert.equal((await service.action("scan", { path: root })).models.length, 1);
  await service.action("save", {
    profile: { ...p, name: "Saved model", context: 32768 },
  });
  const reload = new BasaltService({ dataDir: service.root });
  await reload.init();
  assert.equal(reload.profiles[0].name, "Saved model");
  assert.equal(spawns, 0);
  assert.ok(changes > 0);
  await assert.rejects(service.acquire(p.id), /Prepare/);
  await service.action("remove", { id: p.id });
  assert.equal(service.profiles.length, 0);
  await service.dispose();
  await reload.dispose();
});
test("GPU admission is FIFO, cancellation releases the queue, and active work prevents model removal", async (t) => {
  const root = await temporary(t),
    service = new BasaltService({ dataDir: root });
  await service.init();
  const state = { active: 0 };
  service.startServer = async () => state;
  service.profiles = [{ id: "a", name: "A", gpu: "0" }];
  const first = await service.acquire("a");
  const abort = new AbortController();
  const cancelled = service.acquire("a", abort.signal);
  abort.abort(new Error("User cancelled"));
  await assert.rejects(cancelled, /cancelled/);
  await assert.rejects(service.action("remove", { id: "a" }), /active/);
  let admitted = false;
  const third = service.acquire("a").then((x) => {
    admitted = true;
    return x;
  });
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(admitted, false);
  first.release();
  first.release();
  const next = await third;
  assert.equal(state.active, 1);
  next.release();
  assert.equal(service.answering, 0);
  assert.equal(state.active, 0);
  await service.dispose();
});
test("shared scheduler lease covers the whole request and is released after failure", async (t) => {
  const root = await temporary(t),
    service = new BasaltService({ dataDir: root });
  await service.init();
  service.profiles = [{ id: "a", name: "A", gpu: "0" }];
  let releases = 0;
  service.scheduler = {
    acquire: async (driver) => {
      assert.equal(driver.key, "basalt:a");
      return {
        state: { active: 0 },
        release() {
          releases++;
        },
      };
    },
    unload: async () => {},
  };
  const lease = await service.acquire("a");
  assert.equal(releases, 0);
  lease.release();
  assert.equal(releases, 1);
  service.scheduler.acquire = async () => {
    throw new Error("Load failure");
  };
  await assert.rejects(service.acquire("a"), /Load failure/);
  assert.equal(service.answering, 0);
  await service.dispose();
});
test("setup is explicit, reports failure and never falls through to GPU loading", async (t) => {
  const root = await temporary(t);
  let prepared = 0;
  const service = new BasaltService({ dataDir: root }, () => {}, {
    prepareRuntime: async () => {
      prepared++;
      throw new Error("Download failed");
    },
  });
  await service.init();
  assert.equal(prepared, 0);
  await service.action("setup");
  await service.jobPromise;
  assert.equal(prepared, 1);
  assert.equal(service.job.status, "failed");
  assert.match(service.job.error, /Download failed/);
  assert.equal(service.servers.size, 0);
  await service.dispose();
});
