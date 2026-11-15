import { createHash } from "node:crypto";
import { open, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

export async function temporary(t) {
  const root = await mkdtemp(join(tmpdir(), "dsh-basalt-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  return root;
}
export async function modelFile(
  path,
  arch = "qwen4exp",
  { version = 2, vision = false } = {},
) {
  const entries = [
    [
      "meta",
      Buffer.from(
        JSON.stringify({
          name: "Test " + arch,
          gguf_kv: { "general.architecture": arch },
        }),
      ),
    ],
  ];
  if (vision) entries.push(["vision/mmproj", Buffer.from("projector fixture")]);
  const header = Buffer.alloc(65536);
  header.write("BASALTMF");
  header.writeUInt32LE(version, 8);
  header.writeUInt32LE(entries.length, 12);
  const f = await open(path, "w");
  let end;
  for (let i = 0; i < entries.length; i++) {
    const [name, bytes] = entries[i],
      offset = (i + 1) * 2097152,
      at = 64 + i * 128;
    header.write(name, at);
    header.writeBigUInt64LE(BigInt(offset), at + 64);
    header.writeBigUInt64LE(BigInt(bytes.length), at + 72);
    createHash("sha256")
      .update(bytes)
      .digest()
      .copy(header, at + 80);
    await f.write(bytes, 0, bytes.length, offset);
    end = offset + bytes.length;
  }
  header.writeBigUInt64LE(BigInt(end), 16);
  await f.write(header, 0, header.length, 0);
  await f.close();
  return path;
}
