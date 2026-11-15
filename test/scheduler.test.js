import test from "node:test";
import assert from "node:assert/strict";
import { Context } from "@deepseek-ai/cordis";
import { BasaltService } from "../lib/service.js";
import { attachScheduler } from "../lib/scheduler.js";

const tick = () => new Promise((resolve) => setTimeout(resolve, 10));
function fixture() {
  const service = new BasaltService();
  service.profiles = [{ id: "s", name: "Gyro S", gpu: 0 }];
  service.startServer = async () => ({ active: 0, ready: true });
  service.prepare = async (id) => service.profile(id);
  return service;
}

test("optional scheduler attaches and detaches without a hard plugin dependency", async () => {
  const ctx = new Context(),
    service = fixture();
  const scope = ctx.plugin({
    name: "basalt-fixture",
    apply: (scope) => attachScheduler(scope, service),
  });
  await scope;
  assert.equal(service.scheduler, undefined);
  const events = [];
  const scheduler = {
    registerProvider(name, list) {
      events.push([name, list()[0].key]);
      return () => events.push("unregister");
    },
    async unload(key) {
      events.push("unload " + key);
    },
  };
  const remove = ctx.provide("modelScheduler", scheduler);
  await tick();
  assert.equal(service.scheduler, scheduler);
  assert.deepEqual(events[0], ["basalt", "basalt:s"]);
  await remove();
  assert.equal(service.scheduler, undefined);
  assert.deepEqual(events.slice(1), ["unregister", "unload basalt:s"]);
  await ctx.fiber.dispose();
});
