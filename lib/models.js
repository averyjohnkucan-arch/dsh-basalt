import { open, readdir, realpath, stat } from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import { basename, extname, isAbsolute, join, resolve } from "node:path";

import { supportsProjection } from "./projection.js";

export const architectures = {
  qwen4exp: {
    name: "Qwen3.8-Flash-Next",
    context: 262144,
    kv: ["fp16", "int8", "q4_0", "k8v4"],
  },
  deepseek41: {
    name: "DeepSeek-V4.1-Flash",
    context: 1048576,
    kv: ["fp8", "fp16"],
  },
  qwen35: { name: "Qwen3.8-27B", context: 262144, kv: ["fp16", "int8"] },
};

/** Inspect only the header and metadata; importing a pack never loads weights or starts CUDA. */
export async function inspectModel(path) {
  path = await realpath(path);
  if (extname(path).toLowerCase() !== ".basalt")
    throw new Error("Select a .basalt v2 model pack");
  const file = await open(path, "r");
  try {
    const size = (await file.stat()).size;
    const header = Buffer.alloc(65536);
    if (
      (await file.read(header, 0, header.length, 0)).bytesRead !==
        header.length ||
      header.subarray(0, 8).toString() !== "BASALTMF"
    )
      throw new Error("Invalid Basalt file header");
    if (header.readUInt32LE(8) !== 2)
      throw new Error(
        "Basalt v0.4.0 requires model format v2; convert older packs with the upstream migration tool",
      );
    if (header.readBigUInt64LE(16) !== BigInt(size))
      throw new Error("Truncated Basalt model file");
    const count = header.readUInt32LE(12);
    if (!count || count > 511) throw new Error("Invalid Basalt section count");
    const sections = new Map();
    for (let i = 0; i < count; i++) {
      const at = 64 + i * 128;
      const name = header
        .subarray(at, at + 64)
        .toString()
        .replace(/\0.*$/s, "");
      const offset = header.readBigUInt64LE(at + 64),
        bytes = header.readBigUInt64LE(at + 72);
      if (
        !name ||
        sections.has(name) ||
        offset < 65536n ||
        offset % 2097152n ||
        offset + bytes > BigInt(size)
      )
        throw new Error("Invalid Basalt section table");
      sections.set(name, {
        offset: Number(offset),
        bytes: Number(bytes),
        hash: header.subarray(at + 80, at + 112),
      });
    }
    const sorted = [...sections.values()].sort((a, b) => a.offset - b.offset);
    for (let i = 1; i < sorted.length; i++)
      if (sorted[i].offset < sorted[i - 1].offset + sorted[i - 1].bytes)
        throw new Error("Overlapping Basalt sections");
    const entry = sections.get("meta");
    if (!entry || entry.bytes > 64 * 1024 * 1024)
      throw new Error("Missing or oversized Basalt metadata");
    const bytes = Buffer.alloc(entry.bytes);
    if (
      (await file.read(bytes, 0, bytes.length, entry.offset)).bytesRead !==
      bytes.length
    )
      throw new Error("Truncated metadata");
    if (!createHash("sha256").update(bytes).digest().equals(entry.hash))
      throw new Error("Basalt metadata checksum mismatch");
    const meta = JSON.parse(bytes.toString("utf8"));
    const architecture = meta.gguf_kv?.["general.architecture"];
    if (!architectures[architecture])
      throw new Error("Unsupported Basalt architecture: " + architecture);
    return {
      path,
      size,
      architecture,
      name:
        meta.name ||
        meta.gguf_kv?.["general.name"] ||
        basename(path, ".basalt"),
      vision: sections.has("vision/mmproj"),
      layerCount: meta.gguf_kv?.["qwen4exp.block_count"],
      embeddingLength: meta.gguf_kv?.["qwen4exp.embedding_length"],
      sections: [...sections.keys()],
      requiredEngineFeatures: Array.isArray(meta.required_engine_features)
        ? meta.required_engine_features.filter(
            (value) => typeof value === "string",
          )
        : [],
    };
  } finally {
    await file.close();
  }
}

export async function scanModels(root, { limit = 5000, signal } = {}) {
  const models = [],
    errors = [],
    seen = new Set();
  let visited = 0;
  async function walk(path, depth) {
    signal?.throwIfAborted();
    if (depth > 32 || ++visited > limit)
      throw new Error("Model scan limit reached; select a narrower folder");
    const canonical = await realpath(path);
    if (seen.has(canonical)) return;
    seen.add(canonical);
    const info = await stat(canonical);
    if (!info.isDirectory()) {
      if (extname(canonical).toLowerCase() === ".basalt") {
        try {
          models.push(await inspectModel(canonical));
        } catch (error) {
          errors.push({ path: canonical, error: error.message });
        }
      }
      return;
    }
    for (const entry of await readdir(canonical, { withFileTypes: true })) {
      if (
        entry.name.startsWith(".") ||
        (!entry.isDirectory() && !entry.isFile())
      )
        continue;
      await walk(join(canonical, entry.name), depth + 1);
    }
  }
  await walk(resolve(root), 0);
  return { models, errors };
}

export function newProfile(model) {
  return {
    id: randomUUID(),
    name: model.name,
    model,
    context: architectures[model.architecture].context,
    kv: model.architecture === "deepseek41" ? "fp8" : "fp16",
    gpu: "0",
    vision: false,
    diskCacheMiB: 16384,
    ramCacheMiB: 0,
    vramReserveMiB: 700,
    answerRoom: 0,
  };
}

export function validateProfile(p) {
  const cap = architectures[p.model?.architecture];
  if (!cap || typeof p.id !== "string" || !/^[a-zA-Z0-9-]{1,64}$/.test(p.id))
    throw new Error("Invalid saved model");
  if (typeof p.name !== "string" || !p.name.trim() || p.name.length > 160)
    throw new Error("Model name must contain 1–160 characters");
  if (typeof p.model.path !== "string") throw new Error("Missing model path");
  if (
    p.runtimeDir !== undefined &&
    (typeof p.runtimeDir !== "string" ||
      !isAbsolute(p.runtimeDir) ||
      p.runtimeDir.includes("\0") ||
      p.runtimeDir.length > 4096)
  )
    throw new Error("Invalid profile runtime folder");
  const efforts =
    p.model.architecture === "deepseek41"
      ? ["off", "low", "high", "max"]
      : [
          "off",
          "low",
          "medium",
          "high",
          "xhigh",
          ...(supportsProjection(p) ? ["uncensored"] : []),
        ];
  if (p.defaultEffort !== undefined && !efforts.includes(p.defaultEffort))
    throw new Error("Unsupported default reasoning effort");
  if (
    !Number.isInteger(p.context) ||
    p.context < 1024 ||
    p.context > cap.context
  )
    throw new Error("Context must be 1024–" + cap.context);
  if (!cap.kv.includes(p.kv))
    throw new Error("Unsupported KV format for " + cap.name);
  if (
    typeof p.gpu !== "string" ||
    !/^\d+(?:,\d+)*$/.test(p.gpu) ||
    new Set(p.gpu.split(",")).size !== p.gpu.split(",").length
  )
    throw new Error("GPUs must be distinct device numbers, such as 0 or 0,1");
  if (p.model.architecture === "qwen35" && p.gpu.includes(","))
    throw new Error("The dense 27B model uses one GPU");
  if (typeof p.vision !== "boolean" || (p.vision && !p.model.vision))
    throw new Error("This pack has no vision projector");
  for (const [key, min, max] of [
    ["diskCacheMiB", 0, 1048576],
    ["ramCacheMiB", 0, 1048576],
    ["vramReserveMiB", 256, 1048576],
    ["answerRoom", 0, 1048576],
  ])
    if (!Number.isInteger(p[key]) || p[key] < min || p[key] > max)
      throw new Error("Invalid " + key);
  validateEngineOptions(p.engineOptions, p.model.architecture, p.context);
  if (p.kv === "k8v4" && p.engineOptions?.["kv-resident"] > 0)
    throw new Error("k8v4 does not support native KV streaming");
  return p;
}

/** Only native execution controls measured during tuning may enter the server configuration. */
export function validateEngineOptions(options = {}, architecture, context) {
  if (!options || Array.isArray(options) || typeof options !== "object")
    throw new Error("Invalid native engine options");
  const common = {
    spec: (value) =>
      Number.isInteger(value) &&
      value >= 0 &&
      value <= (architecture === "qwen35" ? 16 : 8),
  };
  const cpu = {
    "resident-budget-gib": (value) =>
      typeof value === "number" &&
      Number.isFinite(value) &&
      value > 0 &&
      value <= 1048576,
    "expert-profile": (value) =>
      typeof value === "string" &&
      value.length <= 4096 &&
      !value.includes("\0") &&
      isAbsolute(value),
    "pool-workers": (value) =>
      Number.isInteger(value) && value >= 1 && value <= 256,
  };
  const flash = {
    "adapt-swaps": (value) =>
      Number.isInteger(value) && value >= 0 && value <= 96,
    "pool-affinity": (value) => ["auto", "all", "p-cores"].includes(value),
    "prefill-cpu-share": (value) =>
      typeof value === "number" &&
      Number.isFinite(value) &&
      value >= 0 &&
      value <= 1,
    prefill: (value) =>
      ["auto", "auto:8192", "auto:16384", "auto:32768"].includes(value) ||
      (Number.isInteger(value) && value >= 256 && value <= 32768),
    "kv-resident": (value) =>
      Number.isInteger(value) &&
      (value === 0 || value >= 20480) &&
      value <= context,
  };
  const deepseek = {
    "deepseek-engram-gguf": (value) =>
      typeof value === "string" &&
      value.length <= 4096 &&
      !value.includes("\0") &&
      isAbsolute(value),
    "draft-experts": (value) => [0, 32, 64, 96, 128].includes(value),
  };
  const dense = {
    "kv-resident": (value) =>
      Number.isInteger(value) &&
      (value === 0 || value >= 1024) &&
      value <= context,
  };
  const rules = {
    ...common,
    ...(architecture === "qwen35" ? {} : cpu),
    ...(architecture === "qwen4exp"
      ? flash
      : architecture === "deepseek41"
        ? deepseek
        : dense),
  };
  for (const [name, value] of Object.entries(options))
    if (!Object.hasOwn(rules, name) || !rules[name](value))
      throw new Error("Unsupported native engine option: " + name);
  return options;
}

export function serverConfig(p, port, cacheDir) {
  validateProfile(p);
  return {
    version: 2,
    models: [
      {
        model: p.model.path,
        alias: p.id,
        gpu: p.gpu,
        kv: p.kv,
        "max-context": p.context,
        vision: p.vision ? "dynamic" : "off",
        "fit-max-tokens": true,
        "answer-room": p.answerRoom,
        "conversation-cache-disk-mib": p.diskCacheMiB,
        "conversation-cache-mib": p.ramCacheMiB,
        "conversation-cache-dir": cacheDir,
        "vram-reserve-mib": p.vramReserveMiB,
        ...(p.engineOptions || {}),
      },
    ],
    server: { host: "127.0.0.1", port },
  };
}
