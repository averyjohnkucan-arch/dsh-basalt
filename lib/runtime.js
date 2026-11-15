import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { execute } from "./process.js";

export const packageRoot = fileURLToPath(new URL("../", import.meta.url));
export const engineVersion = "0.4.0";
export function runtimePaths(root) {
  return {
    root,
    executable: join(root, "bin/basalt"),
    python: join(root, ".venv/bin/python"),
  };
}
export async function runtimeStatus(root) {
  try {
    const paths = runtimePaths(root);
    await access(paths.executable, constants.X_OK);
    await access(paths.python, constants.X_OK);
    const receipt = JSON.parse(
      await readFile(join(root, "dsh-engine.json"), "utf8"),
    );
    if (receipt.version !== engineVersion)
      throw new Error("Expected Basalt " + engineVersion);
    if (!Array.isArray(receipt.libraryDirs) || !receipt.libraryDirs.length)
      throw new Error("Missing private CUDA 13 libraries");
    for (const dir of receipt.libraryDirs) {
      if (typeof dir !== "string" || dir.includes("..") || dir.startsWith("/"))
        throw new Error("Invalid CUDA library folder");
      await access(join(root, dir));
    }
    for (const library of [
      "libcudart.so.13",
      "libcublas.so.13",
      "libcublasLt.so.13",
    ]) {
      const found = await Promise.all(
        receipt.libraryDirs.map((dir) =>
          access(join(root, dir, library)).then(
            () => true,
            () => false,
          ),
        ),
      );
      if (!found.some(Boolean))
        throw new Error("Missing private CUDA library: " + library);
    }
    return {
      ready: true,
      version: receipt.version,
      root,
      libraryDirs: receipt.libraryDirs.map((dir) => join(root, dir)),
    };
  } catch (error) {
    return { ready: false, version: engineVersion, root, error: error.message };
  }
}
export async function prepareRuntime(
  root,
  { python = "python3", signal, onData } = {},
) {
  await execute(
    python,
    [join(packageRoot, "scripts/prepare-engine.py"), root],
    { signal, onData, timeout: 1800000 },
  );
  return runtimeStatus(root);
}
