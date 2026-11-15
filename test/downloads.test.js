import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { downloadPack, listPacks, repositories } from "../lib/downloads.js";
import { temporary } from "./helpers.js";
const bytes = Buffer.from("pack fixture");
const pack = {
  repo: repositories[0],
  revision: "a".repeat(40),
  file: "test.basalt",
  size: bytes.length,
  sha256: createHash("sha256").update(bytes).digest("hex"),
};
test("catalog restricts to official sources and pins the commit, size and LFS digest", async () => {
  await assert.rejects(listPacks("elsewhere/repo"), /official/);
  const result = await listPacks(pack.repo, {
    fetcher: async () =>
      Response.json({
        sha: pack.revision,
        siblings: [
          {
            rfilename: pack.file,
            size: pack.size,
            lfs: { sha256: pack.sha256 },
          },
        ],
      }),
  });
  assert.deepEqual(result, [pack]);
});
test("successful download verifies bytes and atomically publishes only the finished file", async (t) => {
  const root = await temporary(t);
  let progress;
  const path = await downloadPack(pack, root, {
    reserveBytes: 0,
    fetcher: async (url) => {
      assert.ok(url.includes(pack.revision));
      return new Response(bytes);
    },
    onProgress: (p) => {
      progress = p;
    },
  });
  assert.deepEqual(await readFile(path), bytes);
  assert.equal(progress.written, bytes.length);
  assert.equal((await readdir(root)).length, 1);
  await assert.rejects(
    downloadPack(pack, root, { reserveBytes: 0 }),
    /already exists/,
  );
});
test("bad size, digest and cancellation remove partial downloads", async (t) => {
  const root = await temporary(t);
  for (const corrupt of [
    Buffer.from("too many bytes for the expected size"),
    Buffer.from("bad fixture!"),
  ]) {
    await assert.rejects(
      downloadPack(pack, root, {
        reserveBytes: 0,
        fetcher: async () => new Response(corrupt),
      }),
      /size|SHA-256/,
    );
    assert.deepEqual(await readdir(root), []);
  }
  const controller = new AbortController();
  controller.abort(new Error("Cancelled"));
  await assert.rejects(
    downloadPack(pack, root, {
      reserveBytes: 0,
      signal: controller.signal,
      fetcher: async () => new Response(bytes),
    }),
    /Cancelled/,
  );
  assert.deepEqual(await readdir(root), []);
  await assert.rejects(
    downloadPack({ ...pack, file: "../escape.basalt" }, root),
    /Invalid/,
  );
});
