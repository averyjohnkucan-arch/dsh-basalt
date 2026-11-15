import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdir, rm } from "node:fs/promises";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { createServer } from "node:net";
import { setTimeout as delay } from "node:timers/promises";
import { Store } from "./store.js";
import { cpuBudget, cpuLaunch, reservedCpuSet } from "./cpu-set.js";
import {
  inspectModel,
  newProfile,
  scanModels,
  serverConfig,
  validateProfile,
} from "./models.js";
import {
  prepareRuntime,
  runtimePaths,
  runtimeStatus,
  engineVersion,
} from "./runtime.js";
import { terminate } from "./process.js";
import { listPacks, downloadPack } from "./downloads.js";

export class BasaltService {
  constructor(config = {}, changed = () => {}, dependencies = {}) {
    this.root = resolve(
      config.dataDir ||
        join(process.env.DSH_HOME || join(homedir(), ".dsh"), "dsh-basalt"),
    );
    this.store = new Store(this.root);
    this.changed = changed;
    this.shutdown = new AbortController();
    this.requestTail = Promise.resolve();
    this.loadTail = Promise.resolve();
    this.servers = new Map();
    this.answering = 0;
    this.apiKey = randomBytes(32).toString("hex");
    this.spawn = dependencies.spawn || spawn;
    this.fetch = dependencies.fetch || fetch;
    this.prepareRuntime = dependencies.prepareRuntime || prepareRuntime;
    this.runtimeStatus = dependencies.runtimeStatus || runtimeStatus;
  }
  async init() {
    await mkdir(this.root, { recursive: true, mode: 0o700 });
    this.profiles = await this.store.read("profiles", []);
    this.settings = await this.store.read("settings", {
      runtimeDir: join(this.root, "runtime", "v" + engineVersion),
      coresKeptFree: 0,
      python: "python3",
    });
    for (const profile of this.profiles) validateProfile(profile);
    cpuBudget(this.settings.coresKeptFree);
  }
  profile(id) {
    const profile = this.profiles.find((p) => p.id === id);
    if (!profile) throw new Error("Saved Basalt model not found");
    return profile;
  }
  async state() {
    return {
      profiles: this.profiles.map((p) => ({
        ...p,
        running: !!this.servers.get(p.id)?.ready,
        active: this.servers.get(p.id)?.active || 0,
      })),
      settings: this.settings,
      cpuBudget: cpuBudget(this.settings.coresKeptFree),
      runtime: await this.runtimeStatus(this.settings.runtimeDir),
      architectures: (await import("./models.js")).architectures,
      job: this.job && { ...this.job },
      sharedScheduler: !!this.scheduler,
      logs: [...this.servers].map(([id, s]) => ({ id, text: s.logs })),
    };
  }
  busy() {
    return this.job?.status === "running";
  }
  assertIdle() {
    this.shutdown.signal.throwIfAborted();
    if (this.answering || this.busy())
      throw new Error("Wait for the active request or setup to finish");
  }
  async action(action, payload = {}) {
    if (action === "state") return this.state();
    if (action === "catalog")
      return listPacks(payload.repo, { signal: this.shutdown.signal });
    if (action === "cancel-job") {
      this.jobController?.abort(new Error("Cancelled by user"));
      await this.jobPromise;
      return { ok: true };
    }
    if (action === "start") {
      const lease = await this.acquire(payload.id);
      lease.release();
      return { ready: true };
    }
    // Serialize management writes; generation rejects while a management action is changing files.
    if (this.mutating)
      throw new Error("Another Basalt setting is being applied");
    this.assertIdle();
    this.mutating = true;
    try {
      if (action === "settings") {
        cpuBudget(payload.coresKeptFree);
        const settings = {
          ...this.settings,
          coresKeptFree: payload.coresKeptFree,
        };
        if (payload.runtimeDir !== undefined) {
          if (
            typeof payload.runtimeDir !== "string" ||
            !payload.runtimeDir.trim()
          )
            throw new Error("Runtime folder is required");
          settings.runtimeDir = resolve(payload.runtimeDir);
        }
        if (payload.python !== undefined) {
          if (typeof payload.python !== "string" || !payload.python.trim())
            throw new Error("Python executable is required");
          settings.python = payload.python;
        }
        await this.stopAll();
        await this.store.write("settings", settings);
        this.settings = settings;
      } else if (action === "setup") {
        await this.stopAll();
        const job = (this.job = { status: "running", log: "", error: "" });
        this.jobController = new AbortController();
        this.jobPromise = this.prepareRuntime(this.settings.runtimeDir, {
          python: this.settings.python,
          signal: AbortSignal.any([
            this.shutdown.signal,
            this.jobController.signal,
          ]),
          onData: (data) => {
            job.log = (job.log + data).slice(-16000);
          },
        })
          .then((result) => {
            if (!result.ready) throw new Error(result.error);
            job.status = "complete";
          })
          .catch((error) => {
            job.status = "failed";
            job.error = error.message;
          });
      } else if (action === "download") {
        // Re-read the pinned upstream identity, rather than trusting a browser-supplied digest.
        const pack = (
          await listPacks(payload.repo, { signal: this.shutdown.signal })
        ).find((p) => p.file === payload.file);
        if (!pack) throw new Error("This official model pack was not found");
        const job = (this.job = {
          status: "running",
          log: "Downloading " + pack.file,
          error: "",
        });
        this.jobController = new AbortController();
        this.jobPromise = downloadPack(pack, join(this.root, "models"), {
          signal: AbortSignal.any([
            this.shutdown.signal,
            this.jobController.signal,
          ]),
          onProgress: (progress) => {
            job.progress = progress;
          },
        })
          .then(async (path) => {
            const model = await inspectModel(path);
            const profile = newProfile(model);
            const profiles = [...this.profiles, profile];
            await this.store.write("profiles", profiles);
            this.profiles = profiles;
            job.status = "complete";
            this.changed();
          })
          .catch((error) => {
            job.status = "failed";
            job.error = error.message;
          });
      } else if (action === "scan") {
        return await scanModels(payload.path, { signal: this.shutdown.signal });
      } else if (action === "import") {
        const model = await inspectModel(payload.path);
        const existing = this.profiles.find((p) => p.model.path === model.path);
        if (existing) return existing;
        const profile = newProfile(model);
        const profiles = [...this.profiles, profile];
        await this.store.write("profiles", profiles);
        this.profiles = profiles;
        return profile;
      } else if (action === "save") {
        const old = this.profile(payload.profile?.id);
        const keys = [
          "name",
          "context",
          "kv",
          "gpu",
          "vision",
          "diskCacheMiB",
          "ramCacheMiB",
          "vramReserveMiB",
          "answerRoom",
        ];
        const profile = validateProfile({
          ...old,
          ...Object.fromEntries(
            keys.map((k) => [k, payload.profile[k] ?? old[k]]),
          ),
        });
        await this.unload(old.id);
        const profiles = this.profiles.map((p) =>
          p.id === profile.id ? profile : p,
        );
        await this.store.write("profiles", profiles);
        this.profiles = profiles;
      } else if (action === "remove") {
        this.profile(payload.id);
        await this.unload(payload.id);
        const profiles = this.profiles.filter((p) => p.id !== payload.id);
        await this.store.write("profiles", profiles);
        this.profiles = profiles;
      } else if (action === "stop") {
        await this.unload(payload.id);
      } else if (action === "purge-cache") {
        this.profile(payload.id);
        await this.unload(payload.id);
        await rm(join(this.root, "cache", payload.id), {
          recursive: true,
          force: true,
        });
      } else throw new Error("Unknown Basalt action");
      return { ok: true };
    } finally {
      this.mutating = false;
      this.changed();
    }
  }
  driver(id) {
    const p = this.profile(id);
    return {
      key: "basalt:" + id,
      name: p.name,
      gpu: p.gpu,
      fingerprint: JSON.stringify([p, this.settings]),
      load: (signal) => this.startServer(id, signal),
      unload: () => this.stopLocal(id),
      busy: () => !!this.servers.get(id)?.active,
    };
  }
  async acquire(id, signal = this.shutdown.signal) {
    if (this.busy() || this.mutating)
      throw new Error("Wait for Basalt setup or settings to finish");
    const previous = this.requestTail;
    let finish, admission, abort;
    const turn = new Promise((resolve) => {
      finish = resolve;
    });
    this.requestTail = previous.then(() => turn);
    this.answering++;
    const cancelled = new Promise((_, reject) => {
      abort = () => reject(signal.reason || new Error("Cancelled"));
      signal.addEventListener("abort", abort, { once: true });
    });
    try {
      signal.throwIfAborted();
      await Promise.race([previous, cancelled]);
      signal.throwIfAborted();
      const loading = this.loadTail.then(async () => {
        signal.throwIfAborted();
        admission = this.scheduler
          ? await this.scheduler.acquire(this.driver(id), signal)
          : { state: await this.startServer(id, signal), signal, release() {} };
        return admission.state;
      });
      this.loadTail = loading.then(
        () => {},
        () => {},
      );
      const state = await loading;
      state.active++;
      let released = false;
      return {
        state,
        signal: admission.signal || signal,
        release: () => {
          if (released) return;
          released = true;
          state.active--;
          this.answering--;
          try {
            admission.release();
          } finally {
            finish();
          }
        },
      };
    } catch (error) {
      this.answering--;
      try {
        admission?.release();
      } finally {
        finish();
      }
      throw error;
    } finally {
      signal.removeEventListener("abort", abort);
    }
  }
  async startServer(id, signal) {
    signal.throwIfAborted();
    if (this.servers.get(id)?.ready) return this.servers.get(id);
    for (const other of this.servers.keys())
      if (other !== id) await this.stopLocal(other);
    const p = this.profile(id);
    const status = await this.runtimeStatus(this.settings.runtimeDir);
    if (!status.ready)
      throw new Error(
        "Prepare the Basalt runtime in Settings → Models first: " +
          status.error,
      );
    const current = await inspectModel(p.model.path);
    const missing = (current.requiredEngineFeatures || []).filter(
      (feature) => !(status.features || []).includes(feature),
    );
    if (missing.length)
      throw new Error(
        "This pack needs the custom Basalt runtime (" +
          missing.join(", ") +
          "). Select its runtime folder under Engine and CPU settings.",
      );
    if (
      current.architecture !== p.model.architecture ||
      current.size !== p.model.size
    )
      throw new Error(
        "Model pack changed; remove its profile and import it again",
      );
    const port = await freePort();
    const cache = join(this.root, "cache", id);
    await mkdir(cache, { recursive: true, mode: 0o700 });
    const config = new Store(join(this.root, "configs"));
    await config.write(id, serverConfig(p, port, cache));
    const runtime = runtimePaths(this.settings.runtimeDir);
    const command = cpuLaunch(
      runtime.executable,
      [
        "serve",
        "--python",
        runtime.python,
        "--config",
        join(this.root, "configs", id + ".json"),
        "--api-key",
        this.apiKey,
      ],
      reservedCpuSet("", this.settings.coresKeptFree),
    );
    const child = this.spawn(command.executable, command.args, {
      cwd: runtime.root,
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        LD_LIBRARY_PATH: [
          ...(status.libraryDirs || []),
          process.env.LD_LIBRARY_PATH || "",
        ]
          .filter(Boolean)
          .join(":"),
      },
    });
    const state = { child, port, active: 0, ready: false, logs: "" };
    this.servers.set(id, state);
    for (const stream of [child.stdout, child.stderr])
      stream.on("data", (data) => {
        state.logs = (state.logs + data.toString()).slice(-16000);
      });
    child.on("error", (error) => {
      state.error = error;
    });
    child.on("exit", () => {
      state.ready = false;
      state.exited = true;
    });
    const headers = { Authorization: "Bearer " + this.apiKey };
    try {
      const deadline = Date.now() + 30 * 60 * 1000;
      while (Date.now() < deadline) {
        signal.throwIfAborted();
        if (state.error || state.exited || child.exitCode !== null)
          throw (
            state.error ||
            new Error("Basalt exited while loading: " + state.logs.slice(-4000))
          );
        try {
          const response = await this.fetch(
            `http://127.0.0.1:${port}/v1/models`,
            {
              headers,
              signal: AbortSignal.any([signal, AbortSignal.timeout(1500)]),
            },
          );
          if (
            response.ok &&
            (await response.json()).data?.some(
              (m) => m.id === id && m.status?.value === "loaded",
            )
          ) {
            state.ready = true;
            return state;
          }
        } catch (error) {
          if (signal.aborted) throw error;
        }
        await delay(250, undefined, { signal });
      }
      throw new Error(
        "Basalt did not finish loading within 30 minutes: " +
          state.logs.slice(-4000),
      );
    } catch (error) {
      await this.stopLocal(id);
      throw error;
    }
  }
  async unload(id) {
    if (this.scheduler) await this.scheduler.unload("basalt:" + id);
    await this.stopLocal(id);
  }
  async stopLocal(id) {
    const state = this.servers.get(id);
    if (!state) return;
    if (state.active) throw new Error("This Basalt model is answering");
    await terminate(state.child);
    this.servers.delete(id);
  }
  async stopAll() {
    for (const p of this.profiles) await this.unload(p.id);
  }
  async dispose() {
    this.shutdown.abort(new Error("Basalt plugin disposed"));
    await Promise.all([this.requestTail, this.loadTail, this.jobPromise]);
    await this.stopAll();
  }
}

export async function freePort() {
  const socket = createServer();
  await new Promise((resolve, reject) => {
    socket.once("error", reject);
    socket.listen(0, "127.0.0.1", resolve);
  });
  const port = socket.address().port;
  await new Promise((resolve, reject) =>
    socket.close((error) => (error ? reject(error) : resolve())),
  );
  return port;
}
