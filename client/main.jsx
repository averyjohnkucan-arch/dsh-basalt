import React, { useEffect, useState } from "react";
import css from "./styles.css";

async function request(action, payload = {}) {
  const response = await fetch("/api/dsh-basalt", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, payload }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Basalt request failed");
  return body.result;
}
const repos = [
  "jesdga/Qwen3.8-Flash-Next-Basalt",
  "jesdga/DeepSeek-V4.1-Flash-1017-Basalt",
  "jesdga/Qwen3.8-27B-Basalt",
];
const gib = (bytes) => (bytes / 2 ** 30).toFixed(1) + " GiB";

function Profile({ profile, architectures, busy, act }) {
  const [p, set] = useState(profile);
  const edit = (key, value) => set((old) => ({ ...old, [key]: value }));
  const editEngine = (key, value) =>
    set((old) => {
      const engineOptions = { ...old.engineOptions };
      if (value === "") delete engineOptions[key];
      else engineOptions[key] = Number(value);
      return { ...old, engineOptions };
    });
  useEffect(() => set(profile), [profile.id]);
  return (
    <details className="basalt-model">
      <summary>
        {profile.name}{" "}
        <small>
          {profile.running
            ? profile.active
              ? "Answering"
              : "Loaded"
            : "Unloaded"}{" "}
          · {gib(profile.model.size)}
        </small>
      </summary>
      <p className="basalt-path">{profile.model.path}</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          act("save", { profile: p });
        }}
      >
        <fieldset disabled={busy} className="basalt-grid">
          <label>
            Name
            <input
              value={p.name}
              onChange={(e) => edit("name", e.target.value)}
              required
            />
          </label>
          <label>
            Context tokens
            <input
              type="number"
              min="1024"
              max={architectures[p.model.architecture].context}
              value={p.context}
              onChange={(e) => edit("context", Number(e.target.value))}
              required
            />
          </label>
          <label>
            KV cache
            <select value={p.kv} onChange={(e) => edit("kv", e.target.value)}>
              {architectures[p.model.architecture].kv.map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          <label>
            GPUs
            <input
              value={p.gpu}
              onChange={(e) => edit("gpu", e.target.value)}
              placeholder="0 or 0,1"
              required
            />
          </label>
          <label>
            Disk conversation cache (MiB)
            <input
              type="number"
              min="0"
              value={p.diskCacheMiB}
              onChange={(e) => edit("diskCacheMiB", Number(e.target.value))}
            />
          </label>
          <label>
            RAM conversation cache (MiB)
            <input
              type="number"
              min="0"
              value={p.ramCacheMiB}
              onChange={(e) => edit("ramCacheMiB", Number(e.target.value))}
            />
          </label>
          <label>
            VRAM kept free (MiB)
            <input
              type="number"
              min="256"
              value={p.vramReserveMiB}
              onChange={(e) => edit("vramReserveMiB", Number(e.target.value))}
            />
          </label>
          <label>
            Answer token reserve
            <input
              type="number"
              min="0"
              value={p.answerRoom}
              onChange={(e) => edit("answerRoom", Number(e.target.value))}
            />
            <small>
              0 keeps native thinking uncapped by an answer reserve.
            </small>
          </label>
          <label>
            Speculation window
            <select
              value={p.engineOptions?.spec ?? ""}
              onChange={(e) => editEngine("spec", e.target.value)}
            >
              <option value="">Automatic</option>
              {[
                0,
                2,
                4,
                6,
                8,
                ...(p.model.architecture === "qwen35" ? [12, 16] : []),
              ].map((value) => (
                <option key={value} value={value}>
                  {value === 0 ? "Off" : value}
                </option>
              ))}
            </select>
          </label>
          {p.model.architecture !== "qwen35" && (
            <label>
              CPU workers
              <input
                type="number"
                min="1"
                max="256"
                value={p.engineOptions?.["pool-workers"] ?? ""}
                placeholder="Automatic"
                onChange={(e) => editEngine("pool-workers", e.target.value)}
              />
            </label>
          )}
          {p.model.architecture === "qwen4exp" && (
            <label>
              Expert swaps per update
              <input
                type="number"
                min="0"
                max="96"
                step="1"
                value={p.engineOptions?.["adapt-swaps"] ?? ""}
                placeholder="Native default"
                onChange={(e) => editEngine("adapt-swaps", e.target.value)}
              />
              <small>0 keeps the GPU expert cache fixed.</small>
            </label>
          )}
          <label className="basalt-checkbox">
            <input
              type="checkbox"
              checked={p.vision}
              disabled={!p.model.vision || busy}
              onChange={(e) => edit("vision", e.target.checked)}
            />
            Image input
          </label>
          <div className="basalt-actions">
            <button type="submit">Save</button>
            <button
              type="button"
              onClick={() =>
                act(profile.running ? "stop" : "start", { id: p.id })
              }
            >
              {profile.running ? "Unload" : "Load on GPU"}
            </button>
            <button
              type="button"
              onClick={() => act("purge-cache", { id: p.id })}
            >
              Clear conversation cache
            </button>
            <button type="button" onClick={() => act("remove", { id: p.id })}>
              Remove profile
            </button>
          </div>
        </fieldset>
      </form>
    </details>
  );
}

export function BasaltCard() {
  const [state, setState] = useState(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false);
  const [path, setPath] = useState(""),
    [scan, setScan] = useState(null),
    [cores, setCores] = useState(null),
    [runtime, setRuntime] = useState(null);
  const [repo, setRepo] = useState(repos[0]),
    [packs, setPacks] = useState([]),
    [file, setFile] = useState("");
  useEffect(() => {
    let live = true;
    const refresh = () =>
      request("state")
        .then((s) => {
          if (live) setState(s);
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    refresh();
    const timer = setInterval(refresh, 2500);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);
  async function act(action, payload) {
    setPending(true);
    setError("");
    try {
      const result = await request(action, payload);
      setState(await request("state"));
      return result;
    } catch (e) {
      setError(e.message);
    } finally {
      setPending(false);
    }
  }
  const busy = pending || state?.job?.status === "running";
  return (
    <section className="basalt-card" aria-label="Basalt">
      <style>{css}</style>
      <h3>
        Basalt <small>0.1.0 · Blackwell</small>
      </h3>
      <p>
        Saved local models.{" "}
        {state?.sharedScheduler
          ? "Shared GPU scheduler connected."
          : "Independent queue; unload other GPU providers before loading Basalt."}
      </p>
      {error && <p role="alert">{error}</p>}
      {!state ? (
        <p>Connecting to Basalt…</p>
      ) : (
        <>
          <details>
            <summary>Engine and CPU settings</summary>
            <p>
              Engine {state.runtime.version}:{" "}
              {state.runtime.ready ? "prepared" : "not prepared"}. Preparing
              downloads the engine and dependencies; it starts no model.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                act("settings", {
                  coresKeptFree: cores ?? state.settings.coresKeptFree,
                  runtimeDir: runtime ?? state.settings.runtimeDir,
                });
              }}
            >
              <fieldset disabled={busy} className="basalt-grid">
                <label>
                  Runtime folder
                  <input
                    value={runtime ?? state.settings.runtimeDir}
                    onChange={(e) => setRuntime(e.target.value)}
                  />
                </label>
                <label>
                  Cores kept free
                  <input
                    type="number"
                    min="0"
                    max={state.cpuBudget.available - 1}
                    value={cores ?? state.settings.coresKeptFree}
                    onChange={(e) => setCores(Number(e.target.value))}
                  />
                  <small>
                    {state.cpuBudget.limit} of {state.cpuBudget.available}{" "}
                    logical CPUs allowed. Applies after saving and reloading a
                    model.
                  </small>
                </label>
                <div className="basalt-actions">
                  <button type="submit">Save engine settings</button>
                  <button
                    type="button"
                    disabled={state.runtime.ready}
                    onClick={() => act("setup")}
                  >
                    Prepare engine
                  </button>
                </div>
              </fieldset>
            </form>
            <p>
              Linux x64, AVX2, NVIDIA Blackwell sm_120 and driver 580.95.05 or
              newer. CUDA 13 libraries are installed privately.
            </p>
          </details>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await act("scan", { path });
              if (result) setScan(result);
            }}
          >
            <fieldset disabled={busy}>
              <label>
                Model file or folder
                <input
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="/path/to/models"
                  required
                />
              </label>
              <button>Inspect files</button>
            </fieldset>
          </form>
          {scan && (
            <div>
              {scan.models.map((m) => (
                <p key={m.path}>
                  {m.name} · {gib(m.size)}{" "}
                  <button
                    disabled={busy}
                    onClick={() => act("import", { path: m.path })}
                  >
                    Add model
                  </button>
                </p>
              ))}
              {!scan.models.length && (
                <p>No supported .basalt v2 packs found.</p>
              )}
              {scan.errors.map((e) => (
                <p key={e.path} role="alert">
                  {e.path}: {e.error}
                </p>
              ))}
            </div>
          )}
          <details>
            <summary>Download an official model pack</summary>
            <p>
              Model packs can be hundreds of gigabytes. The download verifies
              the published size and SHA-256 before importing.
            </p>
            <fieldset disabled={busy}>
              <label>
                Repository
                <select
                  value={repo}
                  onChange={(e) => {
                    setRepo(e.target.value);
                    setPacks([]);
                    setFile("");
                  }}
                >
                  {repos.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={async () => {
                  const result = await act("catalog", { repo });
                  if (result) {
                    setPacks(result);
                    setFile(result[0]?.file || "");
                  }
                }}
              >
                List packs
              </button>
              {!!packs.length && (
                <>
                  <label>
                    Pack
                    <select
                      value={file}
                      onChange={(e) => setFile(e.target.value)}
                    >
                      {packs.map((p) => (
                        <option key={p.file} value={p.file}>
                          {p.file} ({gib(p.size)})
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    onClick={() => act("download", { repo, file })}
                  >
                    Download and add
                  </button>
                </>
              )}
            </fieldset>
          </details>
          <div>
            {state.profiles.map((profile) => (
              <Profile
                key={profile.id}
                {...{ profile, architectures: state.architectures, busy, act }}
              />
            ))}
          </div>
          {!state.profiles.length && (
            <p>
              Import a Basalt model pack to make it available in the model
              picker. Strata GGUF profiles are kept separately.
            </p>
          )}
          {state.job && (
            <div role="status">
              <p>
                {state.job.status}
                {state.job.progress &&
                  ` · ${gib(state.job.progress.written)} / ${gib(state.job.progress.total)}`}
              </p>
              {state.job.status === "running" && (
                <button disabled={pending} onClick={() => act("cancel-job")}>
                  Cancel operation
                </button>
              )}
              <pre>{state.job.log}</pre>
              {state.job.error && <p role="alert">{state.job.error}</p>}
            </div>
          )}
          {state.logs.map((log) => (
            <details key={log.id}>
              <summary>Engine log</summary>
              <pre>{log.text}</pre>
            </details>
          ))}
        </>
      )}
    </section>
  );
}
export const inject = ["slots"];
export function apply(ctx) {
  ctx.slots.inject("settings.models.footer", () =>
    ctx.slots.register(
      { name: "settings.models.footer", id: "dsh-basalt", order: 11 },
      BasaltCard,
    ),
  );
}
