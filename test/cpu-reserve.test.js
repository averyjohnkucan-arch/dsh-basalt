import test from "node:test";
import assert from "node:assert/strict";
import { cpuBudget, reservedCpuSet, availableCpuIds } from "../lib/cpu-set.js";
import { BasaltService } from "../lib/service.js";
import { temporary } from "./helpers.js";
test("two reserved CPUs out of 24 leaves 22, respecting noncontiguous host affinity", () => {
  const ids = Array.from({ length: 24 }, (_, i) => i);
  assert.deepEqual(cpuBudget(2, ids), {
    available: 24,
    coresKeptFree: 2,
    limit: 22,
    cpuSet: "0-21",
  });
  assert.equal(reservedCpuSet("", 2, [2, 4, 6, 8]), "2,4");
  assert.equal(reservedCpuSet("20-23", 2, ids), "20-21");
  assert.throws(() => reservedCpuSet("22-23", 2, ids), /overlap/);
  for (const n of [-1, 24, 1.5, "2", NaN, null])
    assert.throws(() => cpuBudget(n, ids));
});
test("CPU setting survives reload and applies without changing another provider", async (t) => {
  const root = await temporary(t),
    service = new BasaltService({ dataDir: root });
  await service.init();
  const coresKeptFree = Math.min(2, availableCpuIds().length - 1);
  await service.action("settings", { coresKeptFree });
  const reload = new BasaltService({ dataDir: root });
  await reload.init();
  assert.equal((await reload.state()).cpuBudget.coresKeptFree, coresKeptFree);
  assert.equal(
    (await reload.state()).cpuBudget.limit,
    availableCpuIds().length - coresKeptFree,
  );
  await service.dispose();
  await reload.dispose();
});
