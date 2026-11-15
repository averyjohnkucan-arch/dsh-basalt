import test from "node:test";
import assert from "node:assert/strict";
import { Context } from "@deepseek-ai/cordis";
import * as plugin from "../index.js";
import { temporary } from "./helpers.js";

test("native Cordis activates and disposes adapter + authenticated management registration without inference", async (t) => {
  const ctx = new Context(),
    root = await temporary(t);
  let adapter,
    route,
    removed = 0;
  ctx.provide("llm", {
    registerAdapter(ids, value) {
      assert.deepEqual(ids, ["basalt"]);
      adapter = value;
      const dispose = () => {
        removed++;
      };
      dispose.replace = () => {};
      return dispose;
    },
  });
  ctx.provide("connection", {
    fetch: {
      register(value) {
        route = value;
        return () => {
          removed++;
        };
      },
    },
  });
  await ctx.plugin(plugin, { dataDir: root });
  assert.deepEqual(plugin.inject, ["llm", "connection"]);
  assert.equal((await adapter.listModels("basalt")).length, 0);
  assert.equal(route.path, "/api/dsh-basalt");
  assert.equal(route.requestBody, "buffered");
  const response = await route.fetch(
    new Request("http://localhost/api/dsh-basalt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"action":"state"}',
    }),
  );
  const state = (await response.json()).result;
  assert.equal(state.profiles.length, 0);
  assert.deepEqual(state.logs, []);
  await ctx.fiber.dispose();
  assert.equal(removed, 2);
});
