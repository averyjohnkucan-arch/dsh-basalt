import { createHash, randomUUID } from "node:crypto";
import { mkdir, open, rename, rm, stat, statfs } from "node:fs/promises";
import { basename, join } from "node:path";

export const repositories = [
  "jesdga/Qwen3.8-Flash-Next-Basalt",
  "jesdga/DeepSeek-V4.1-Flash-1017-Basalt",
  "jesdga/Qwen3.8-27B-Basalt",
];
export async function listPacks(repo, { signal, fetcher = fetch } = {}) {
  if (!repositories.includes(repo))
    throw new Error("Select an official Basalt model repository");
  const response = await fetcher(
    "https://huggingface.co/api/models/" + repo + "?blobs=true",
    { signal },
  );
  if (!response.ok) throw new Error("Hugging Face returned " + response.status);
  const info = await response.json();
  if (!/^[a-f0-9]{40}$/.test(info.sha))
    throw new Error("Hugging Face did not return a pinned model revision");
  return (info.siblings || [])
    .filter(
      (file) =>
        file.rfilename.endsWith(".basalt") &&
        /^[a-f0-9]{64}$/.test(file.lfs?.sha256),
    )
    .map((file) => ({
      repo,
      revision: info.sha,
      file: file.rfilename,
      size: file.size ?? file.lfs.size,
      sha256: file.lfs.sha256,
    }));
}

/** Downloads finish with a size + SHA-256 check, then an atomic rename. No partial file is importable. */
export async function downloadPack(
  pack,
  folder,
  {
    signal,
    onProgress = () => {},
    fetcher = fetch,
    reserveBytes = 1024 ** 3,
  } = {},
) {
  if (
    !repositories.includes(pack.repo) ||
    !/^[a-f0-9]{40}$/.test(pack.revision) ||
    !/^[a-f0-9]{64}$/.test(pack.sha256) ||
    !Number.isSafeInteger(pack.size) ||
    pack.size <= 0 ||
    typeof pack.file !== "string" ||
    basename(pack.file) !== pack.file ||
    !pack.file.endsWith(".basalt")
  )
    throw new Error("Invalid model download");
  await mkdir(folder, { recursive: true, mode: 0o700 });
  const disk = await statfs(folder);
  if (disk.bavail * disk.bsize < pack.size + reserveBytes)
    throw new Error("Not enough disk space for this pack plus 1 GiB kept free");
  const target = join(folder, pack.sha256.slice(0, 12) + "-" + pack.file);
  try {
    await stat(target);
    throw new Error(
      "This model file already exists; import it from the Models folder",
    );
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const temporary = join(folder, "." + randomUUID() + ".partial");
  const out = await open(temporary, "wx", 0o600);
  try {
    const response = await fetcher(
      `https://huggingface.co/${pack.repo}/resolve/${pack.revision}/${encodeURIComponent(pack.file)}`,
      { signal },
    );
    if (!response.ok || !response.body)
      throw new Error("Model download failed: " + response.status);
    const hash = createHash("sha256");
    let written = 0;
    for await (const chunk of response.body) {
      signal?.throwIfAborted();
      written += chunk.length;
      if (written > pack.size)
        throw new Error("Downloaded model exceeds its published size");
      hash.update(chunk);
      let offset = 0;
      while (offset < chunk.length)
        offset += (await out.write(chunk, offset, chunk.length - offset))
          .bytesWritten;
      onProgress({ written, total: pack.size });
    }
    if (written !== pack.size || hash.digest("hex") !== pack.sha256)
      throw new Error("Downloaded model size or SHA-256 mismatch");
    await out.sync();
    await out.close();
    await rename(temporary, target);
    return target;
  } finally {
    await out.close().catch(() => {});
    await rm(temporary, { force: true });
  }
}
