import test from "node:test";
import assert from "node:assert/strict";
import { handler, actionPath } from "../lib/http.js";
test("management uses authenticated DSH Connection routing and validates JSON requests", async () => {
  let calls = 0;
  const route = handler({
    action: async (action, payload) => {
      calls++;
      if (action === "bad") throw new Error("Invalid");
      return payload;
    },
  });
  assert.equal(actionPath, "/api/dsh-basalt");
  const request = (body, method = "POST", type = "application/json") =>
    new Request("http://localhost/api/dsh-basalt", {
      method,
      headers: { "Content-Type": type },
      ...(method === "GET" ? {} : { body }),
    });
  assert.equal((await route(request("", "GET"))).status, 405);
  assert.equal((await route(request("{}", "POST", "text/plain"))).status, 405);
  assert.equal((await route(request("{"))).status, 400);
  assert.equal(
    (await route(request(JSON.stringify({ action: "bad" })))).status,
    400,
  );
  const response = await route(
    request(JSON.stringify({ action: "state", payload: { ok: true } })),
  );
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { result: { ok: true } });
  assert.equal(calls, 2);
  assert.equal(
    (await route(request("x".repeat(4 * 1024 * 1024 + 1)))).status,
    413,
  );
});
