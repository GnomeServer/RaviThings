import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { renderPanel } from "./panels.mjs";

const MODEL_ID = "anthropic/claude-sonnet-4.6";
const JUDGE = "openrouter/typesafe/jev-1.13";
const ALLOWED_ACTIONS = new Set(["inspect", "configure", "prepare", "replay", "show", "verify"]);
const ALLOWED_PATTERNS = new Set(["fan_out", "confidence", "scoring", "intent"]);
const ALLOWED_TARGETS = new Set(["controls", "source", "run"]);

function d(bytes) { return createHash("sha256").update(bytes).digest("hex"); }

async function loadGuardExports(policy) {
  const gpath = policy.shared_guard.path;
  const bytes = fs.readFileSync(gpath);
  if (d(bytes) !== policy.shared_guard.sha256) throw new Error("guard changed");
  const mod = await import(pathToFileURL(gpath).href);
  return { digest: mod.digest || (mod.default && mod.default.digest), resolveCoursePath: mod.resolveCoursePath || (mod.default && mod.default.resolveCoursePath) };
}

async function callAdapter(python, adapterPath, policyPath, request) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, [adapterPath, "control", "--policy", policyPath], { stdio: ["pipe", "pipe", "pipe"], env: { ...process.env, COURSE_GUARD_POLICY: policyPath } });
    let out = "", err = "";
    child.stdout.on("data", dd => { out += dd; });
    child.stderr.on("data", dd => { err += dd; });
    child.on("close", code => { if (code !== 0) return reject(new Error(err || out)); try { resolve(JSON.parse(out.trim())); } catch (e) { reject(e); } });
    child.stdin.write(JSON.stringify(request)); child.stdin.end();
  });
}

function loadPolicy() {
  const p = process.env.COURSE_GUARD_POLICY;
  if (!p) throw new Error("COURSE_GUARD_POLICY missing");
  const bytes = fs.readFileSync(p);
  const pol = JSON.parse(bytes.toString("utf8"));
  if (pol.schema_version !== 1 || pol.provider !== "openrouter" || pol.model !== MODEL_ID || pol.judge_selector !== JUDGE) throw new Error("invalid policy");
  return { path: p, policy: pol, hash: d(bytes) };
}

function checkIdentity(ctx, polInfo, gexp, ph) {
  if (!ctx.model || ctx.model.provider !== "openrouter" || ctx.model.id !== MODEL_ID) throw new Error("provider/model identity drift");
  const policyBytes = fs.readFileSync(polInfo.path);
  if (d(policyBytes) !== ph) throw new Error("policy changed");
  if (gexp && polInfo.policy.shared_guard) {
    const guardBytes = fs.readFileSync(polInfo.policy.shared_guard.path);
    if (d(guardBytes) !== polInfo.policy.shared_guard.sha256) throw new Error("guard source changed");
  }
  for (const [rel, expected] of Object.entries(polInfo.policy.protected || {})) {
    const full = gexp.resolveCoursePath(rel, polInfo.policy.work_root);
    if (fs.lstatSync(full).isSymbolicLink() || d(fs.readFileSync(full)) !== expected) throw new Error("protected changed: " + rel);
  }
  for (const key of ["instruction", "config", "extension", "runner", "adapter", "shared_launcher", "prepare_helper", "shared_guard"]) {
    const desc = polInfo.policy[key];
    if (desc && desc.path && desc.sha256) {
      const b = fs.readFileSync(desc.path);
      if (d(b) !== desc.sha256) throw new Error(key + " changed");
    }
  }
  assertEvidence(polInfo.policy);
}

function buildStrictSchema(z) {
  const ins = z.object({ action: z.literal("inspect"), target: z.enum(Array.from(ALLOWED_TARGETS)), pattern: z.string().optional(), id: z.string().optional() }).strict();
  const cfg = z.object({ action: z.literal("configure"), pattern: z.enum(Array.from(ALLOWED_PATTERNS)), changes: z.record(z.unknown()) }).strict();
  const pre = z.object({ action: z.literal("prepare"), pattern: z.enum(Array.from(ALLOWED_PATTERNS)), revision: z.string(), mode: z.string() }).strict();
  const rep = z.object({ action: z.literal("replay"), pattern: z.enum(Array.from(ALLOWED_PATTERNS)), source_run: z.string(), revisions: z.array(z.string()).min(1) }).strict();
  const sho = z.object({ action: z.literal("show"), runs: z.array(z.string()).min(1).max(2) }).strict();
  const ver = z.object({ action: z.literal("verify") }).strict();
  const variants = z.union([ins, cfg, pre, rep, sho, ver]);
  return z.object({
    action: z.enum(Array.from(ALLOWED_ACTIONS)), target: z.enum(Array.from(ALLOWED_TARGETS)).optional(),
    pattern: z.enum(Array.from(ALLOWED_PATTERNS)).optional(), id: z.string().optional(),
    changes: z.record(z.unknown()).optional(), revision: z.string().optional(), mode: z.string().optional(),
    source_run: z.string().optional(), revisions: z.array(z.string()).min(1).max(8).optional(),
    runs: z.array(z.string()).min(1).max(2).optional()
  }).strict().superRefine((args, ctx) => {
    const result = variants.safeParse(args);
    if (!result.success) ctx.addIssue({ message: result.error.message });
  });
}

function renderResult(result, options, theme, args, native = {}) {
  const w = (theme && theme.columns) || (options && options.width) || 80;
  const det = result && result.details || {};
  const baseView = det.view || result && result.view || {};
  const view = {
    ...baseView,
    status: det.status || (result && result.status) || "unknown",
    message: det.message || (result && result.message) || "",
    revision: det.revision || baseView.revision || "",
    run_id: det.run_id || baseView.run_id || "",
    cell_code: det.cell_code || baseView.cell_code || "",
  };
  const fb = renderPanel(view, w, { theme }).join("\n");
  return {
    render(width = w) {
      const text = renderPanel(view, width, { theme }).join("\n");
      return native.Text ? new native.Text(text, 0, 0).render(width) : text.split("\n");
    },
    toString() { return fb; }
  };
}

function assertEvidence(policy) {
  const control = path.join(policy.evidence_root, "control.jsonl");
  if (!fs.existsSync(control)) return;
  for (const line of fs.readFileSync(control, "utf8").trim().split("\n")) {
    if (!line) continue;
    const row = JSON.parse(line);
    if (row.type === "configured") {
      const file = path.join(policy.evidence_root, "revisions", row.revision + ".json");
      if (d(fs.readFileSync(file)) !== row.sha256) throw new Error("saved configuration changed");
    }
    if (row.type === "prepared") {
      const file = path.join(policy.evidence_root, "runs", row.run_id, "plan.json");
      if (d(fs.readFileSync(file)) !== row.plan_sha256) throw new Error("saved prepared plan changed");
    }
    if (row.type === "finalized" || row.type === "replayed") {
      const folder = path.join(policy.evidence_root, "runs", row.run_id);
      const file = path.join(folder, "seal.json");
      if (d(fs.readFileSync(file)) !== row.seal_sha256) throw new Error("previous result seal changed");
      const seal = JSON.parse(fs.readFileSync(file, "utf8"));
      for (const [relative, expected] of Object.entries(seal.files)) {
        const target = path.resolve(folder, relative);
        if (!target.startsWith(folder + path.sep) || fs.lstatSync(target).isSymbolicLink() || d(fs.readFileSync(target)) !== expected) throw new Error("previous result changed: " + relative);
      }
    }
  }
}

export default function patternsExtension(pi) {
  const z = pi.zod;
  let polInfo = null;
  let gexp = null;
  let phash = null;
  let guardLogPath = null;
  let ready = false;
  const preparedModes = new Set();

  function appendGuardLog(row) {
    if (guardLogPath) {
      fs.appendFileSync(guardLogPath, JSON.stringify({ ts: new Date().toISOString(), ...row }) + "\n");
    }
  }

  function getSessionInfo(ctx) {
    try {
      const sm = ctx && ctx.sessionManager;
      return {
        session_file: sm && typeof sm.getSessionFile === "function" ? sm.getSessionFile() : null,
        session_id: sm && typeof sm.getSessionId === "function" ? sm.getSessionId() : null,
      };
    } catch { return { session_file: null, session_id: null }; }
  }

  pi.on("session_start", async (_e, ctx) => {
    try {
      polInfo = loadPolicy();
      gexp = await loadGuardExports(polInfo.policy);
      phash = polInfo.hash;
      guardLogPath = polInfo.policy.guard_log || path.join(path.dirname(polInfo.path), "guard.jsonl");
      checkIdentity(ctx, polInfo, gexp, phash);
      if (polInfo.policy.instruction) {
        const raw = fs.readFileSync(polInfo.policy.instruction.path);
        if (d(raw) !== polInfo.policy.instruction.sha256) throw new Error("instruction changed");
      }
      await pi.setActiveTools(["eval", "blue_gauge"]);
      const available = new Set(pi.getAllTools().map(tool => tool.name));
      if (!available.has("eval") || !available.has("blue_gauge") || JSON.stringify(pi.getActiveTools().sort()) !== JSON.stringify(["blue_gauge", "eval"])) throw new Error("declared native tools did not register");
      const sess = getSessionInfo(ctx);
      appendGuardLog({ type: "guard_ready", ...sess, policy_sha256: phash, active_tools: ["eval", "blue_gauge"] });
      pi.appendEntry("blue_gauge", { type: "guard_ready", ...sess });
    } catch (e) {
      appendGuardLog({ type: "guard_error", reason: String(e && e.message || e) });
      ctx.abort();
      throw e;
    }
  });

  pi.on("before_agent_start", async (_e, ctx) => {
    try {
      checkIdentity(ctx, polInfo, gexp, phash);
      const act = (pi.getActiveTools() || []).sort();
      preparedModes.clear();
      if (JSON.stringify(act) !== JSON.stringify(["blue_gauge", "eval"])) throw new Error("active tools drift");
      if (polInfo.policy.instruction) {
        const raw = fs.readFileSync(polInfo.policy.instruction.path);
        if (d(raw) !== polInfo.policy.instruction.sha256) throw new Error("instruction changed");
        const text = raw.toString("utf8").trim();
        const resolved = ctx.getSystemPrompt();
        if (!text || !Array.isArray(resolved) || !resolved.some(block => typeof block === "string" && block.trim().includes(text))) throw new Error("saved instruction absent from resolved system prompt");
        appendGuardLog({ type: "instruction_loaded", path: polInfo.policy.instruction.path });
        pi.appendEntry("blue_gauge", { type: "instruction_loaded" });
      }
      ready = true;
    } catch (e) {
      appendGuardLog({ type: "guard_error", reason: String(e && e.message || e) });
      ctx.abort();
      throw e;
    }
  });

  pi.on("before_provider_request", (event, ctx) => {
    try {
      checkIdentity(ctx, polInfo, gexp, phash);
      const payload = event && event.payload;
      const offered = payload && payload.tools ? payload.tools.map(t => (t && (t.name || (t.function && t.function.name))) || "").filter(Boolean).sort() : null;
      if (offered && JSON.stringify(offered) !== JSON.stringify(["blue_gauge", "eval"])) throw new Error("offered tools outside declared set");
      const sess = getSessionInfo(ctx);
      appendGuardLog({ type: "provider_request", ...sess, provider: ctx.model && ctx.model.provider, model: ctx.model && ctx.model.id });
    } catch (e) {
      appendGuardLog({ type: "guard_error", reason: String(e && e.message || e) });
      ctx.abort();
      throw e;
    }
  });

  for (const b of ["auto_retry_start", "retry_fallback_applied", "model_changed"]) {
    pi.on(b, (_e, ctx) => {
      appendGuardLog({ type: "guard_error", reason: "forbidden " + b });
      ctx.abort();
      throw new Error("forbidden runtime transition: " + b);
    });
  }

  pi.on("tool_call", async (ev, ctx) => {
    try {
      checkIdentity(ctx, polInfo, gexp, phash);
      if (!ready) throw new Error("guard initialization is incomplete");
      const sess = getSessionInfo(ctx);
      if (ev.toolName === "eval") {
        const inp = ev.input || {};
        const keys = Object.keys(inp);
        const allowedKeys = new Set(["language", "code", "title", "timeout", "reset"]);
        const bad = inp.language !== "js" || inp.reset === true || keys.some(k => !allowedKeys.has(k)) || (inp.timeout != null && inp.timeout !== 250);
        if (bad) {
          appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: "eval", arguments: inp, allow: false, reason: "exact js/allowlist/timeout only", ...sess });
          pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: "eval", allow: false, reason: "exact js/allowlist/timeout only" });
          return { block: true, reason: "HOLD" };
        }
        const resp = await callAdapter(polInfo.policy.python, polInfo.policy.adapter.path, polInfo.path, { action: "authorize_eval", code: inp.code });
        const allow = !!(resp && resp.status === "PASS");
        appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: "eval", arguments: inp, allow, reason: allow ? "authorized cell" : "not authorized or consumed", ...sess });
        pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: "eval", allow, reason: allow ? "authorized cell" : "not authorized or consumed" });
        if (!allow) return { block: true, reason: "HOLD" };
        appendGuardLog({ type: "eval_admitted", call_id: ev.toolCallId, tool: "eval", ...sess });
        return;
      }
      if (ev.toolName !== "blue_gauge") {
        appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: ev.toolName || "unknown", arguments: ev.input, allow: false, reason: "undeclared tool", ...sess });
        pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: ev.toolName || "unknown", allow: false, reason: "undeclared tool" });
        return { block: true, reason: "HOLD undeclared" };
      }
      const a = ev.input || {};
      if (!a || typeof a.action !== "string" || !ALLOWED_ACTIONS.has(a.action)) {
        appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", arguments: a, allow: false, reason: "unknown action", ...sess });
        pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", allow: false, reason: "unknown action" });
        return { block: true, reason: "HOLD" };
      }
      if (a.action === "prepare" && preparedModes.has(a.pattern + "/" + a.mode)) {
        const reason = "one plan per pattern/mode per user request; HOLD cannot trigger an automatic paid retry";
        appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", arguments: a, allow: false, reason, ...sess });
        pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", allow: false, reason });
        return { block: true, reason: "HOLD: " + reason };
      }
      appendGuardLog({ type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", arguments: a, allow: true, reason: "public action admitted to execute", ...sess });
      pi.appendEntry("blue_gauge", { type: "decision", call_id: ev.toolCallId, tool: "blue_gauge", allow: true });
    } catch (e) {
      appendGuardLog({ type: "guard_error", reason: String(e && e.message || e) });
      ctx.abort();
      throw e;
    }
  });

  pi.on("session_shutdown", () => {
    appendGuardLog({ type: "guard_end" });
    pi.appendEntry("blue_gauge", { type: "guard_end" });
  });

  const schema = buildStrictSchema(z);
  pi.registerTool({
    name: "blue_gauge",
    label: "Blue Gauge",
    description: "Operate supplied Blue Gauge controls: inspect revisions/sources/runs; configure documented pattern settings; prepare one exact native eval cell; replay saved answers without model or handler calls; show numeric evidence; verify native receipts. No paths, executable code, model selectors, release authority, baseline modes or completion helpers.",
    loadMode: "essential",
    approval: "exec",
    parameters: schema,
    async execute(callId, args, signal, onUpd, ctx) {
      if (signal && signal.aborted) return { content: [{ type: "text", text: "HOLD" }], details: { status: "HOLD", view: null } };
      if (!ready) throw new Error("HOLD: guard initialization is incomplete");
      checkIdentity(ctx, polInfo, gexp, phash);
      const act = args && args.action;
      const sess = getSessionInfo(ctx);
      appendGuardLog({ type: "execution_check", call_id: callId, tool: "blue_gauge", arguments: args, ...sess });
      pi.appendEntry("blue_gauge", { type: "execution_check", call_id: callId, action: act });
      if (!ALLOWED_ACTIONS.has(act)) throw new Error("HOLD: private/unregistered action");
      const resp = await callAdapter(polInfo.policy.python, polInfo.policy.adapter.path, polInfo.path, { ...args });
      if (act === "prepare" && resp.status === "PASS") preparedModes.add(args.pattern + "/" + args.mode);
      appendGuardLog({ type: "executed", call_id: callId, tool: "blue_gauge", action: act, status: resp && resp.status, ...sess });
      pi.appendEntry("blue_gauge", { type: "executed", call_id: callId, action: act, status: resp && resp.status });
      const payload = [resp.status + ": " + resp.message];
      if (resp.revision) payload.push("revision: " + resp.revision);
      if (resp.run_id) payload.push("run_id: " + resp.run_id);
      if (resp.cell_code) payload.push("Exact eval cell (js; timeout 250; reset false):\n" + resp.cell_code);
      if (resp.view) {
        payload.push(renderPanel(resp.view, 80, { theme: ctx.ui?.theme }).join("\n"));
        if (args.action === "inspect" && args.target === "run") payload.push("Inspectable saved values:\n" + JSON.stringify(resp.view));
      }
      return { content: [{ type: "text", text: payload.join("\n") }], details: { ...resp, message: resp.message } };
    },
    renderResult(result, options, theme, args) { return renderResult(result, options, theme, args, pi.pi); },
  });
}

export { renderResult, renderPanel };