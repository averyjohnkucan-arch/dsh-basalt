import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile, rename, rm } from "node:fs/promises";
import { join } from "node:path";

export const projectionAsset = {
  url: "https://raw.githubusercontent.com/averyjohnkucan-arch/dsh-strata/3c11b90bcce34feb777a7be5a2271495a9504e65/vendor/gyro-l-control/data/experimental-speed-projection/Qwen3.8-Flash-Next-experimental-speed-projection.gguf",
  sha256: "ef0724c5b79297e481017be85769832bc26eb220c984ecba2b0e1b0c8426312b",
  bytes: 483520,
};
// Original Flash Next only; this direction does not apply to Swift or DeepSeek.
export function supportsProjection(profile) {
  const m = profile.model || {};
  if (m.architecture !== "qwen4exp" || /swift/i.test(m.name || ""))
    return false;
  if (m.layerCount !== undefined && m.layerCount !== 48) return false;
  if (m.embeddingLength !== undefined && m.embeddingLength !== 2560)
    return false;
  return (
    (m.layerCount === 48 && m.embeddingLength === 2560) ||
    /Qwen3\.8[- ]Flash[- ]Next/i.test(m.name || "")
  );
}
export async function prepareProjection(
  root,
  { fetcher = fetch, signal } = {},
) {
  const folder = join(root, "assets"),
    path = join(folder, "flash-next-refusal-direction.gguf");
  const valid = (b) =>
    b.length === projectionAsset.bytes &&
    createHash("sha256").update(b).digest("hex") === projectionAsset.sha256;
  try {
    if (valid(await readFile(path))) return path;
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
  const response = await fetcher(projectionAsset.url, { signal });
  if (!response.ok)
    throw Error("Cannot fetch Flash Next direction: HTTP " + response.status);
  const bytes = Buffer.from(await response.arrayBuffer());
  if (!valid(bytes)) throw Error("Flash Next direction checksum mismatch");
  await mkdir(folder, { recursive: true, mode: 0o700 });
  const tmp = path + "." + randomUUID() + ".tmp";
  try {
    await writeFile(tmp, bytes, { mode: 0o600 });
    await rename(tmp, path);
  } finally {
    await rm(tmp, { force: true });
  }
  return path;
}
export function withProjection(config, path) {
  return {
    ...config,
    models: config.models.map((m) => ({
      ...m,
      "control-vector-scaled": path + ":1.0",
      "control-vector-layer-range": [4, 44],
      "cvec-mode": "project",
      "cvec-dir": "per-layer",
    })),
  };
}
