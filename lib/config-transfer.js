import { exportManifest, locateFiles, validateManifest } from "./portable.js";
import { inspectModel, newProfile, validateProfile } from "./models.js";

const fields = [
  "context",
  "kv",
  "vision",
  "diskCacheMiB",
  "ramCacheMiB",
  "vramReserveMiB",
  "answerRoom",
];
const settings = (p) =>
  Object.fromEntries(
    fields.filter((k) => Object.hasOwn(p, k)).map((k) => [k, p[k]]),
  );

export function exportConfig(profile, signal, report) {
  return exportManifest(
    "basalt",
    profile.name,
    settings(profile),
    [{ role: "model", path: profile.model.path }],
    { signal, report },
  );
}

export async function importConfig(config, root, signal, report) {
  const manifest = validateManifest(config, "basalt");
  if (manifest.files.length !== 1 || manifest.files[0].role !== "model")
    throw Error("A Basalt config must identify exactly one model pack.");
  const [match] = await locateFiles(manifest, root, { signal, report });
  const model = await inspectModel(match.path);
  signal.throwIfAborted();
  return validateProfile({
    ...newProfile(model),
    ...settings(manifest.settings),
    name: manifest.name,
  });
}
