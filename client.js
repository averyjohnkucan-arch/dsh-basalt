// Generated from client/ by npm run build. Edit the source modules.
window.__ModuleLoader__.load({id:'dsh-basalt',factory(require){
const module={exports:{}};const exports=module.exports;
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// client/main.jsx
var main_exports = {};
__export(main_exports, {
  BasaltCard: () => BasaltCard,
  apply: () => apply,
  inject: () => inject
});
module.exports = __toCommonJS(main_exports);

// client/EngineHeader.jsx
var import_react = __toESM(require("react"), 1);

// client/engine-panel.css
var engine_panel_default = '.dsh-engine-panel[class] {\n  box-sizing: border-box;\n  margin-top: 16px;\n  padding: 18px;\n  min-width: 0;\n  border: 1px solid var(--dsw-alias-border-l3, currentColor);\n  border-radius: 12px;\n  background: var(--dsw-alias-settings-card-fill, transparent);\n  color: var(--dsw-alias-label-primary, inherit);\n  font: inherit;\n}\n.dsh-engine-panel .dsh-engine-header {\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n  flex-wrap: wrap;\n  gap: 12px;\n  padding-bottom: 12px;\n  margin-bottom: 14px;\n  border-bottom: 1px solid var(--dsw-alias-border-l3, currentColor);\n}\n.dsh-engine-header h3 {\n  margin: 0;\n  font-size: 1.1rem;\n  font-weight: 650;\n}\n.dsh-engine-panel .dsh-engine-header h3 small {\n  display: inline;\n  font-size: 0.8rem;\n  font-weight: 400;\n  color: var(--dsw-alias-label-secondary, inherit);\n}\n.dsh-engine-status {\n  margin-top: 4px;\n  font-size: 0.875rem;\n  color: var(--dsw-alias-label-secondary, inherit);\n}\n.dsh-engine-panel[class] button,\n.dsh-engine-panel[class] select,\n.dsh-engine-panel[class]\n  input:not([type="checkbox"]):not([type="radio"]):not([type="range"]) {\n  border-radius: 7px;\n  padding: 7px 10px;\n  font: inherit;\n  border: 1px solid var(--dsw-alias-border-l3, currentColor);\n}\n.dsh-engine-panel button:focus-visible,\n.dsh-engine-panel input:focus-visible,\n.dsh-engine-panel select:focus-visible {\n  outline: 2px solid currentColor;\n  outline-offset: 2px;\n}\n/* First model */\n.dsh-engine-panel .dsh-engine-guide {\n  margin: 0 0 12px;\n}\n.dsh-engine-guide summary {\n  cursor: pointer;\n}\n.dsh-engine-guide li {\n  margin: 5px 0;\n}\n';

// package.json
var package_default = {
  name: "dsh-basalt",
  version: "0.1.1-rc4.1",
  description: "Basalt Blackwell model provider for DSH: native model packs, saved profiles, reasoning controls, CPU reservation and shared GPU scheduling.",
  type: "module",
  license: "MIT",
  engines: {
    node: ">=24.9.0",
    dsh: "0.2.2-rc.4"
  },
  repository: {
    type: "git",
    url: "git+https://github.com/averyjohnkucan-arch/dsh-basalt.git"
  },
  exports: {
    ".": "./index.js",
    "./client": "./client.js"
  },
  files: [
    "index.js",
    "client.js",
    "lib/*.js",
    "scripts/prepare-engine.py",
    "engine.json",
    "cordis.patch.yml",
    "README.md",
    "LICENSE",
    "ENGINE-INSPECTION.md"
  ],
  scripts: {
    build: "node build.mjs",
    test: 'node --test --test-concurrency=1 test/*.test.js && python3 -m unittest discover -s test -p "*_test.py"',
    check: "prettier --check index.js lib client test/*.js build.mjs"
  },
  peerDependencies: {
    "@deepseek-ai/schemastery": "~3.19.0",
    "@deepseek-ai/dsh-llm": "0.2.2-rc.4",
    "@deepseek-ai/dsh-llm-pi-ai": "0.2.2-rc.4",
    "@earendil-works/pi-ai": "^1.3.0"
  },
  devDependencies: {
    esbuild: "0.28.2",
    prettier: "3.9.10",
    "@deepseek-ai/schemastery": "~3.19.0",
    "@deepseek-ai/dsh-llm": "0.2.2-rc.4",
    "@deepseek-ai/dsh-llm-pi-ai": "0.2.2-rc.4",
    "@earendil-works/pi-ai": "1.3.0",
    "@deepseek-ai/dsh-launch-environment": "0.2.2-rc.4",
    "@deepseek-ai/cordis": "~4.1.0",
    "@deepseek-ai/dsh-attachment": "0.2.2-rc.4",
    "@deepseek-ai/dsh-authorization": "0.2.2-rc.4",
    "@deepseek-ai/dsh-credentials": "0.2.2-rc.4",
    "@deepseek-ai/dsh-fs": "0.2.2-rc.4",
    "@deepseek-ai/dsh-timeout": "0.2.2-rc.4",
    "@deepseek-ai/cordis-plugin-loader": "~1.1.0"
  },
  dsh: {
    bundle: {
      patch: "./cordis.patch.yml"
    },
    client: {
      platform: "web",
      immediately: true,
      inject: [
        "@deepseek-ai/dsh-client-ui-settings-models"
      ]
    }
  }
};

// client/first-run.json
var first_run_default = [
  "Open Engine and CPU settings and prepare the runtime.",
  "Import a .basalt pack or choose Download and add.",
  "Choose the saved model in the chat model picker."
];

// client/EngineHeader.jsx
function EngineHeader({ name, status, children }) {
  return /* @__PURE__ */ import_react.default.createElement(import_react.default.Fragment, null, /* @__PURE__ */ import_react.default.createElement("header", { className: "dsh-engine-header" }, /* @__PURE__ */ import_react.default.createElement("style", null, engine_panel_default), /* @__PURE__ */ import_react.default.createElement("div", null, /* @__PURE__ */ import_react.default.createElement("h3", null, name, " ", /* @__PURE__ */ import_react.default.createElement("small", null, package_default.version)), /* @__PURE__ */ import_react.default.createElement("div", { className: "dsh-engine-status" }, status)), children), /* @__PURE__ */ import_react.default.createElement("details", { className: "dsh-engine-guide" }, /* @__PURE__ */ import_react.default.createElement("summary", null, "Set up your first model"), /* @__PURE__ */ import_react.default.createElement("ol", null, first_run_default.map((step) => /* @__PURE__ */ import_react.default.createElement("li", { key: step }, step)))));
}

// client/main.jsx
var import_react2 = __toESM(require("react"), 1);

// client/styles.css
var styles_default = '.basalt-card {\n  border: 1px solid var(--border-color, #5555);\n  border-radius: 12px;\n  padding: 18px;\n  margin-block: 16px;\n  color: inherit;\n}\n.basalt-card h3 {\n  margin: 0 0 8px;\n}\n.basalt-card small {\n  font-size: 12px;\n  opacity: 0.7;\n  font-weight: normal;\n}\n.basalt-card details {\n  border-top: 1px solid #8884;\n  margin-top: 14px;\n  padding-top: 12px;\n}\n.basalt-card summary {\n  cursor: pointer;\n  padding: 4px 0;\n}\n.basalt-card fieldset {\n  border: 0;\n  padding: 12px 0;\n  display: flex;\n  gap: 12px;\n  flex-wrap: wrap;\n  align-items: end;\n}\n.basalt-card .basalt-grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));\n}\n.basalt-card label {\n  display: flex;\n  flex-direction: column;\n  gap: 6px;\n  flex: 1;\n  min-width: 160px;\n  font-size: 13px;\n}\n.basalt-card input,\n.basalt-card select {\n  box-sizing: border-box;\n  color: inherit;\n  background: transparent;\n  border: 1px solid #8886;\n  border-radius: 6px;\n  padding: 8px;\n  width: 100%;\n}\n.basalt-card select option {\n  color: #ddd;\n  background: #262626;\n}\n.basalt-card button {\n  border: 1px solid #8886;\n  border-radius: 6px;\n  padding: 8px 12px;\n  background: transparent;\n  color: inherit;\n  cursor: pointer;\n}\n.basalt-card button:disabled {\n  opacity: 0.45;\n  cursor: default;\n}\n.basalt-card [role="alert"] {\n  color: #ed8e85;\n}\n.basalt-card .basalt-actions {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 8px;\n  grid-column: 1 / -1;\n}\n.basalt-card .basalt-checkbox {\n  flex-direction: row;\n  align-items: center;\n}\n.basalt-card .basalt-checkbox input {\n  width: auto;\n}\n.basalt-card pre,\n.basalt-card .basalt-path {\n  white-space: pre-wrap;\n  overflow-wrap: anywhere;\n  font-size: 12px;\n  max-height: 240px;\n  overflow: auto;\n}\n';

// client/main.jsx
async function request(action, payload = {}) {
  const response = await fetch("/api/dsh-basalt", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, payload })
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Basalt request failed");
  return body.result;
}
var repos = [
  "jesdga/Qwen3.8-Flash-Next-Basalt",
  "jesdga/DeepSeek-V4.1-Flash-1017-Basalt",
  "jesdga/Qwen3.8-27B-Basalt"
];
var gib = (bytes) => (bytes / 2 ** 30).toFixed(1) + " GiB";
function Profile({ profile, architectures, busy, act }) {
  const [p, set] = (0, import_react2.useState)(profile);
  const edit = (key, value) => set((old) => ({ ...old, [key]: value }));
  (0, import_react2.useEffect)(() => set(profile), [profile.id]);
  return /* @__PURE__ */ import_react2.default.createElement("details", { className: "basalt-model" }, /* @__PURE__ */ import_react2.default.createElement("summary", null, profile.name, " ", /* @__PURE__ */ import_react2.default.createElement("small", null, profile.running ? profile.active ? "Answering" : "Loaded" : "Unloaded", " ", "\xB7 ", gib(profile.model.size))), /* @__PURE__ */ import_react2.default.createElement("p", { className: "basalt-path" }, profile.model.path), /* @__PURE__ */ import_react2.default.createElement(
    "form",
    {
      onSubmit: (event) => {
        event.preventDefault();
        act("save", { profile: p });
      }
    },
    /* @__PURE__ */ import_react2.default.createElement("fieldset", { disabled: busy, className: "basalt-grid" }, /* @__PURE__ */ import_react2.default.createElement("label", null, "Name", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        value: p.name,
        onChange: (e) => edit("name", e.target.value),
        required: true
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "Context tokens", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "1024",
        max: architectures[p.model.architecture].context,
        value: p.context,
        onChange: (e) => edit("context", Number(e.target.value)),
        required: true
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "KV cache", /* @__PURE__ */ import_react2.default.createElement("select", { value: p.kv, onChange: (e) => edit("kv", e.target.value) }, architectures[p.model.architecture].kv.map((k) => /* @__PURE__ */ import_react2.default.createElement("option", { key: k }, k)))), /* @__PURE__ */ import_react2.default.createElement("label", null, "GPUs", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        value: p.gpu,
        onChange: (e) => edit("gpu", e.target.value),
        placeholder: "0 or 0,1",
        required: true
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "Disk conversation cache (MiB)", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "0",
        value: p.diskCacheMiB,
        onChange: (e) => edit("diskCacheMiB", Number(e.target.value))
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "RAM conversation cache (MiB)", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "0",
        value: p.ramCacheMiB,
        onChange: (e) => edit("ramCacheMiB", Number(e.target.value))
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "VRAM kept free (MiB)", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "256",
        value: p.vramReserveMiB,
        onChange: (e) => edit("vramReserveMiB", Number(e.target.value))
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "Answer token reserve", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "0",
        value: p.answerRoom,
        onChange: (e) => edit("answerRoom", Number(e.target.value))
      }
    ), /* @__PURE__ */ import_react2.default.createElement("small", null, "0 keeps native thinking uncapped by an answer reserve.")), /* @__PURE__ */ import_react2.default.createElement("label", { className: "basalt-checkbox" }, /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "checkbox",
        checked: p.vision,
        disabled: !p.model.vision || busy,
        onChange: (e) => edit("vision", e.target.checked)
      }
    ), "Image input"), /* @__PURE__ */ import_react2.default.createElement("div", { className: "basalt-actions" }, /* @__PURE__ */ import_react2.default.createElement("button", { type: "submit" }, "Save"), /* @__PURE__ */ import_react2.default.createElement(
      "button",
      {
        type: "button",
        onClick: () => act(profile.running ? "stop" : "start", { id: p.id })
      },
      profile.running ? "Unload" : "Load on GPU"
    ), /* @__PURE__ */ import_react2.default.createElement(
      "button",
      {
        type: "button",
        onClick: () => act("purge-cache", { id: p.id })
      },
      "Clear conversation cache"
    ), /* @__PURE__ */ import_react2.default.createElement("button", { type: "button", onClick: () => act("remove", { id: p.id }) }, "Remove profile")))
  ));
}
function BasaltCard() {
  const [state, setState] = (0, import_react2.useState)(null), [error, setError] = (0, import_react2.useState)(""), [pending, setPending] = (0, import_react2.useState)(false);
  const [path, setPath] = (0, import_react2.useState)(""), [scan, setScan] = (0, import_react2.useState)(null), [cores, setCores] = (0, import_react2.useState)(null), [runtime, setRuntime] = (0, import_react2.useState)(null);
  const [repo, setRepo] = (0, import_react2.useState)(repos[0]), [packs, setPacks] = (0, import_react2.useState)([]), [file, setFile] = (0, import_react2.useState)("");
  (0, import_react2.useEffect)(() => {
    let live = true;
    const refresh = () => request("state").then((s) => {
      if (live) setState(s);
    }).catch((e) => {
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
  return /* @__PURE__ */ import_react2.default.createElement("section", { className: "basalt-card dsh-engine-panel", "aria-label": "Basalt" }, /* @__PURE__ */ import_react2.default.createElement("style", null, styles_default), /* @__PURE__ */ import_react2.default.createElement(
    EngineHeader,
    {
      name: "Basalt",
      status: state?.sharedScheduler ? "Blackwell \xB7 Shared GPU scheduler" : "Blackwell \xB7 Independent queue. Unload other GPU providers before loading Basalt."
    }
  ), error && /* @__PURE__ */ import_react2.default.createElement("p", { role: "alert" }, error), !state ? /* @__PURE__ */ import_react2.default.createElement("p", null, "Connecting to Basalt\u2026") : /* @__PURE__ */ import_react2.default.createElement(import_react2.default.Fragment, null, /* @__PURE__ */ import_react2.default.createElement("details", null, /* @__PURE__ */ import_react2.default.createElement("summary", null, "Engine and CPU settings"), /* @__PURE__ */ import_react2.default.createElement("p", null, "Engine ", state.runtime.version, ":", " ", state.runtime.ready ? "prepared" : "not prepared", ". Preparing downloads the engine and dependencies; it starts no model."), /* @__PURE__ */ import_react2.default.createElement(
    "form",
    {
      onSubmit: (e) => {
        e.preventDefault();
        act("settings", {
          coresKeptFree: cores ?? state.settings.coresKeptFree,
          runtimeDir: runtime ?? state.settings.runtimeDir
        });
      }
    },
    /* @__PURE__ */ import_react2.default.createElement("fieldset", { disabled: busy, className: "basalt-grid" }, /* @__PURE__ */ import_react2.default.createElement("label", null, "Runtime folder", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        value: runtime ?? state.settings.runtimeDir,
        onChange: (e) => setRuntime(e.target.value)
      }
    )), /* @__PURE__ */ import_react2.default.createElement("label", null, "Cores kept free", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        type: "number",
        min: "0",
        max: state.cpuBudget.available - 1,
        value: cores ?? state.settings.coresKeptFree,
        onChange: (e) => setCores(Number(e.target.value))
      }
    ), /* @__PURE__ */ import_react2.default.createElement("small", null, state.cpuBudget.limit, " of ", state.cpuBudget.available, " ", "logical CPUs allowed. Applies after saving and reloading a model.")), /* @__PURE__ */ import_react2.default.createElement("div", { className: "basalt-actions" }, /* @__PURE__ */ import_react2.default.createElement("button", { type: "submit" }, "Save engine settings"), /* @__PURE__ */ import_react2.default.createElement(
      "button",
      {
        type: "button",
        disabled: state.runtime.ready,
        onClick: () => act("setup")
      },
      "Prepare engine"
    )))
  ), /* @__PURE__ */ import_react2.default.createElement("p", null, "Linux x64, AVX2, NVIDIA Blackwell sm_120 and driver 580.95.05 or newer. CUDA 13 libraries are installed privately.")), /* @__PURE__ */ import_react2.default.createElement(
    "form",
    {
      onSubmit: async (e) => {
        e.preventDefault();
        const result = await act("scan", { path });
        if (result) setScan(result);
      }
    },
    /* @__PURE__ */ import_react2.default.createElement("fieldset", { disabled: busy }, /* @__PURE__ */ import_react2.default.createElement("label", null, "Model file or folder", /* @__PURE__ */ import_react2.default.createElement(
      "input",
      {
        value: path,
        onChange: (e) => setPath(e.target.value),
        placeholder: "/path/to/models",
        required: true
      }
    )), /* @__PURE__ */ import_react2.default.createElement("button", null, "Inspect files"))
  ), scan && /* @__PURE__ */ import_react2.default.createElement("div", null, scan.models.map((m) => /* @__PURE__ */ import_react2.default.createElement("p", { key: m.path }, m.name, " \xB7 ", gib(m.size), " ", /* @__PURE__ */ import_react2.default.createElement(
    "button",
    {
      disabled: busy,
      onClick: () => act("import", { path: m.path })
    },
    "Add model"
  ))), !scan.models.length && /* @__PURE__ */ import_react2.default.createElement("p", null, "No supported .basalt v2 packs found."), scan.errors.map((e) => /* @__PURE__ */ import_react2.default.createElement("p", { key: e.path, role: "alert" }, e.path, ": ", e.error))), /* @__PURE__ */ import_react2.default.createElement("details", null, /* @__PURE__ */ import_react2.default.createElement("summary", null, "Download an official model pack"), /* @__PURE__ */ import_react2.default.createElement("p", null, "Model packs can be hundreds of gigabytes. The download verifies the published size and SHA-256 before importing."), /* @__PURE__ */ import_react2.default.createElement("fieldset", { disabled: busy }, /* @__PURE__ */ import_react2.default.createElement("label", null, "Repository", /* @__PURE__ */ import_react2.default.createElement(
    "select",
    {
      value: repo,
      onChange: (e) => {
        setRepo(e.target.value);
        setPacks([]);
        setFile("");
      }
    },
    repos.map((r) => /* @__PURE__ */ import_react2.default.createElement("option", { key: r }, r))
  )), /* @__PURE__ */ import_react2.default.createElement(
    "button",
    {
      type: "button",
      onClick: async () => {
        const result = await act("catalog", { repo });
        if (result) {
          setPacks(result);
          setFile(result[0]?.file || "");
        }
      }
    },
    "List packs"
  ), !!packs.length && /* @__PURE__ */ import_react2.default.createElement(import_react2.default.Fragment, null, /* @__PURE__ */ import_react2.default.createElement("label", null, "Pack", /* @__PURE__ */ import_react2.default.createElement(
    "select",
    {
      value: file,
      onChange: (e) => setFile(e.target.value)
    },
    packs.map((p) => /* @__PURE__ */ import_react2.default.createElement("option", { key: p.file, value: p.file }, p.file, " (", gib(p.size), ")"))
  )), /* @__PURE__ */ import_react2.default.createElement(
    "button",
    {
      type: "button",
      onClick: () => act("download", { repo, file })
    },
    "Download and add"
  )))), /* @__PURE__ */ import_react2.default.createElement("div", null, state.profiles.map((profile) => /* @__PURE__ */ import_react2.default.createElement(
    Profile,
    {
      key: profile.id,
      ...{ profile, architectures: state.architectures, busy, act }
    }
  ))), !state.profiles.length && /* @__PURE__ */ import_react2.default.createElement("p", null, "Import a Basalt model pack to make it available in the model picker. Strata GGUF profiles are kept separately."), state.job && /* @__PURE__ */ import_react2.default.createElement("div", { role: "status" }, /* @__PURE__ */ import_react2.default.createElement("p", null, state.job.status, state.job.progress && ` \xB7 ${gib(state.job.progress.written)} / ${gib(state.job.progress.total)}`), state.job.status === "running" && /* @__PURE__ */ import_react2.default.createElement("button", { disabled: pending, onClick: () => act("cancel-job") }, "Cancel operation"), /* @__PURE__ */ import_react2.default.createElement("pre", null, state.job.log), state.job.error && /* @__PURE__ */ import_react2.default.createElement("p", { role: "alert" }, state.job.error)), state.logs.map((log) => /* @__PURE__ */ import_react2.default.createElement("details", { key: log.id }, /* @__PURE__ */ import_react2.default.createElement("summary", null, "Engine log"), /* @__PURE__ */ import_react2.default.createElement("pre", null, log.text)))));
}
var inject = ["slots"];
function apply(ctx) {
  ctx.slots.inject(
    "settings.models.footer",
    () => ctx.slots.register(
      { name: "settings.models.footer", id: "dsh-basalt", order: 11 },
      BasaltCard
    )
  );
}

return module.exports;
}});
