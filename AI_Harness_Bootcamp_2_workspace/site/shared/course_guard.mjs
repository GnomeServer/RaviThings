import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

export const digest = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const sourceFile = fileURLToPath(import.meta.url);
const modelId = "anthropic/claude-sonnet-4.6";
const toolNames = new Set(["course_read", "course_write"]);
const evalKeys = new Set(["language", "code", "title", "timeout", "reset"]);
const inside = (root, target) => { const rel = path.relative(root, target); return rel !== ".." && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel); };

export function resolveCoursePath(raw, root) {
  if (typeof raw !== "string" || !raw || raw.includes("\0")) throw new Error("empty path or NUL");
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) throw new Error("URI schemes are not permitted");
  if (/^(?:\\\\|\/\/)/.test(raw)) throw new Error("UNC/device paths are not permitted");
  if (/^[a-z]:(?![\\/])/i.test(raw)) throw new Error("drive-relative paths are not permitted");
  const drive = /^[a-z]:[\\/]/i.test(raw);
  if (drive && process.platform !== "win32") throw new Error("foreign drive path is outside the work root");
  if ((drive ? raw.slice(2) : raw).includes(":") || /[?#]/.test(raw)) throw new Error("selectors and alternate streams are not permitted");
  const parts = raw.split(/[\\/]/);
  if (parts.includes("..")) throw new Error("traversal is not permitted");
  if (parts.some(part => /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?$/i.test(part))) throw new Error("device paths are not permitted");
  if (process.platform !== "win32" && raw.includes("\\")) throw new Error("backslash path is not native");
  const realRoot = fs.realpathSync(root);
  const candidate = path.resolve(realRoot, raw);
  if (!inside(realRoot, candidate)) throw new Error("path is outside the work root");
  let cursor = candidate;
  const missing = [];
  while (!fs.existsSync(cursor)) {
    try { if (fs.lstatSync(cursor).isSymbolicLink()) throw new Error("broken link"); } catch (error) { if (error.code !== "ENOENT") throw error; }
    missing.unshift(path.basename(cursor));
    const parent = path.dirname(cursor);
    if (parent === cursor) throw new Error("path cannot be resolved");
    cursor = parent;
  }
  const resolved = path.join(fs.realpathSync(cursor), ...missing);
  if (!inside(realRoot, resolved)) throw new Error("link escapes the work root");
  return resolved;
}

function initialFiles(root) {
  const result = new Set();
  const visit = dir => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      result.add(file);
      if (entry.isDirectory() && !entry.isSymbolicLink()) visit(file);
    }
  };
  visit(root);
  return result;
}

export function authorize(policy, state, tool, args) {
  try {
    if (!state.ready) throw new Error("guard initialization is incomplete");
    if (!toolNames.has(tool) || !policy.tools.includes(tool)) throw new Error("tool is not declared");
    if (!args || typeof args !== "object" || Array.isArray(args)) throw new Error("invalid arguments");
    const expected = tool === "course_write" ? ["content", "path"] : ["path"];
    if (JSON.stringify(Object.keys(args).sort()) !== JSON.stringify(expected)) throw new Error("unexpected tool arguments");
    const resolved = resolveCoursePath(args.path, policy.work_root);
    const relative = path.relative(policy.work_root, resolved).split(path.sep).join("/");
    if (tool === "course_write") {
      if (typeof args.content !== "string") throw new Error("content must be UTF-8 text");
      const permitted = policy.write_files.includes(relative) || (policy.write_root && inside(resolveCoursePath(policy.write_root, policy.work_root), resolved));
      if (!permitted || !relative) throw new Error("write path is not authorized");
      if (state.protected.has(resolved)) throw new Error("existing input/control cannot be replaced");
      for (const descriptor of [policy.instruction, policy.declaration]) {
        if (descriptor && resolved === descriptor.path) throw new Error("control file cannot be replaced");
      }
      if (fs.existsSync(resolved) && !state.created.has(resolved)) throw new Error("existing output attempt cannot be replaced");
    }
    return { allow: true, resolved_path: resolved, relative_path: relative, reason: "authorized" };
  } catch (error) {
    return { allow: false, resolved_path: null, relative_path: null, reason: error.message };
  }
}

const providerToolNames = event => {
  const payload = event?.payload;
  if (!payload || typeof payload !== "object") return null;
  if (payload.tools === undefined) return [];
  return Array.isArray(payload.tools) ? payload.tools.map(tool => String(tool?.function?.name ?? tool?.name ?? "")).sort() : null;
};

export default function courseGuard(pi) {
  const policyFile = process.env.COURSE_GUARD_POLICY;
  if (!policyFile) throw new Error("COURSE_GUARD_POLICY is missing");
  const policyBytes = fs.readFileSync(policyFile);
  const policyHash = digest(policyBytes);
  const policy = JSON.parse(policyBytes.toString("utf8"));
  const judge = policy.judge || null;
  const declaredTools = judge ? JSON.stringify(policy.tools) === JSON.stringify(["eval"]) : Array.isArray(policy.tools) && policy.tools.every(name => toolNames.has(name));
  if (policy.schema_version !== 1 || policy.provider !== "openrouter" || policy.model !== modelId || typeof policy.omp_version !== "string" || !/^omp\/[0-9]+\.[0-9]+\.[0-9]+$/.test(policy.omp_version) || !Array.isArray(policy.tools) || !declaredTools) throw new Error("invalid frozen course policy");
  if (judge && (typeof judge.cell_code !== "string" || !judge.cell_code || judge.selector !== "openrouter/typesafe/jev-1.13")) throw new Error("invalid frozen judge policy");
  if (digest(fs.readFileSync(sourceFile)) !== policy.guard_source_sha256) throw new Error("guard source identity changed");
  const mcp = policy.mcp || null;
  if (mcp && (!Array.isArray(mcp.allow_names) || !Array.isArray(mcp.known_names) || mcp.allow_names.some(name => !mcp.known_names.includes(name)))) throw new Error("invalid frozen MCP policy");
  const mcpFiles = mcp ? [mcp.script, mcp.config, mcp.authority].filter(Boolean) : [];
  const judgeFiles = judge ? [judge.config, judge.questions, judge.frozen_questions, judge.runner, judge.plan, ...Object.values(judge.states)] : [];
  const wantedTools = [...policy.tools, ...(mcp ? mcp.allow_names : [])];
  const state = { ready: false, sessionReady: false, protected: initialFiles(policy.work_root), created: new Set(), requests: 0, failed: false, evalUsed: false };
  const log = row => fs.appendFileSync(policy.guard_log, JSON.stringify({ run_id: policy.run_id, ...row }) + "\n", { encoding: "utf8" });
  const identity = ctx => {
    if (!ctx.model || ctx.model.provider !== policy.provider || ctx.model.id !== policy.model) throw new Error("provider/model identity drift");
    if (digest(fs.readFileSync(policyFile)) !== policyHash) throw new Error("resolved policy changed");
    if (digest(fs.readFileSync(sourceFile)) !== policy.guard_source_sha256) throw new Error("guard source changed");
    if (digest(fs.readFileSync(path.join(path.dirname(policyFile), "runtime-config.yml"))) !== policy.runtime_config_sha256) throw new Error("runtime configuration changed");
    for (const descriptor of [policy.instruction, policy.declaration, ...mcpFiles]) {
      if (descriptor && digest(fs.readFileSync(descriptor.path)) !== descriptor.sha256) throw new Error("saved instruction, declared policy, or MCP connection file changed");
    }
    for (const descriptor of judgeFiles) {
      if (digest(fs.readFileSync(descriptor.path)) !== descriptor.sha256) throw new Error(`judge input changed: ${descriptor.path}`);
    }
  };
  const fail = (ctx, error) => {
    state.ready = false;
    state.failed = true;
    log({ type: "guard_error", reason: error.message });
    ctx.abort();
    throw error;
  };
  pi.on("session_start", async (_event, ctx) => {
    try {
      identity(ctx);
      const registered = pi.getAllTools().map(tool => tool.name);
      const available = new Set(registered);
      if (policy.tools.some(name => !available.has(name))) throw new Error("explicit course tool did not register");
      const mcpRegistered = registered.filter(name => name.startsWith("mcp__")).sort();
      if (mcp) {
        const foreign = mcpRegistered.filter(name => !mcp.known_names.includes(name));
        if (foreign.length) throw new Error(`unexpected MCP tool registered: ${foreign.join(", ")}`);
        if (mcp.allow_names.some(name => !available.has(name))) throw new Error("explicit MCP tool did not register");
      } else if (mcpRegistered.length) {
        throw new Error("an MCP tool registered although the policy declares none");
      }
      await pi.setActiveTools(wantedTools);
      const active = pi.getActiveTools().sort();
      if (JSON.stringify(active) !== JSON.stringify([...wantedTools].sort())) throw new Error("active tools exceed declared policy");
      state.sessionReady = true;
      log({ type: "guard_ready", provider: ctx.model.provider, model: ctx.model.id, active_tools: active, mcp_tools_registered: mcpRegistered, policy_sha256: policyHash });
    } catch (error) { fail(ctx, error); }
  });
  pi.on("before_agent_start", async (_event, ctx) => {
    try {
      identity(ctx);
      if (!state.sessionReady || state.failed) throw new Error("guard session initialization failed");
      if (mcp) {
        // OMP activates MCP tools after session_start; declare the set again before the first turn.
        await pi.setActiveTools(wantedTools);
        if (JSON.stringify(pi.getActiveTools().sort()) !== JSON.stringify([...wantedTools].sort())) throw new Error("active tools exceed declared policy before the first turn");
      }
      if (policy.instruction) {
        const raw = fs.readFileSync(policy.instruction.path);
        if (digest(raw) !== policy.instruction.sha256) throw new Error("saved instruction changed");
        const text = raw.toString("utf8").trim();
        const resolved = ctx.getSystemPrompt();
        if (!text || !Array.isArray(resolved) || !resolved.every(block => typeof block === "string") || !resolved.some(block => block.trim().includes(text))) throw new Error("saved instruction absent from resolved system prompt");
        log({ type: "instruction_loaded", path: policy.instruction.path, file_sha256: digest(raw), loaded_text_sha256: digest(Buffer.from(text)), policy_sha256: policyHash });
      }
      state.ready = true;
    } catch (error) { fail(ctx, error); }
  });
  pi.on("before_provider_request", (event, ctx) => {
    try {
      identity(ctx);
      if (!state.ready || state.failed) throw new Error("provider request before guard readiness");
      const offered = providerToolNames(event);
      if (mcp && (offered === null || JSON.stringify(offered) !== JSON.stringify([...wantedTools].sort()))) throw new Error(`provider request offered tools outside the declaration: ${offered === null ? "tool list not visible" : offered.join(", ")}`);
      log({ type: "provider_request", sequence: ++state.requests, provider: ctx.model.provider, model: ctx.model.id, tools: offered });
    } catch (error) { fail(ctx, error); }
  });
  for (const eventName of ["auto_retry_start", "retry_fallback_applied", "model_changed"]) {
    pi.on(eventName, (_event, ctx) => fail(ctx, new Error(`forbidden runtime transition: ${eventName}`)));
  }
  pi.on("tool_call", (event, ctx) => {
    try { identity(ctx); } catch (error) { return fail(ctx, error); }
    if (String(event.toolName).startsWith("mcp__")) {
      const declared = Boolean(mcp) && state.ready && mcp.allow_names.includes(event.toolName);
      log({ type: "decision", call_id: event.toolCallId, tool: event.toolName, arguments: event.input, allow: declared, resolved_path: null, relative_path: null, reason: declared ? "declared MCP tool" : "MCP tool is not declared" });
      if (!declared) return { block: true, reason: "HOLD: MCP tool is not declared" };
      return;
    }
    if (event.toolName === "eval") {
      const input = event.input && typeof event.input === "object" && !Array.isArray(event.input) ? event.input : {};
      let reason = "eval is not declared";
      if (judge && state.ready) {
        if (state.evalUsed) reason = "the judge cell already ran once";
        else if (Object.keys(input).some(name => !evalKeys.has(name))) reason = "unexpected eval arguments";
        else if (input.language !== "js") reason = "the judge cell runs only as js";
        else if (input.code !== judge.cell_code) reason = "eval code differs from the frozen judge cell";
        else reason = "frozen judge cell";
      }
      const allow = reason === "frozen judge cell";
      if (allow) state.evalUsed = true;
      log({ type: "decision", call_id: event.toolCallId, tool: "eval", arguments: event.input, allow, resolved_path: null, relative_path: null, reason });
      if (!allow) return { block: true, reason: `HOLD: ${reason}` };
      return;
    }
    const decision = authorize(policy, state, event.toolName, event.input);
    log({ type: "decision", call_id: event.toolCallId, tool: event.toolName, arguments: event.input, ...decision });
    if (!decision.allow) return { block: true, reason: `HOLD: ${decision.reason}` };
  });
  const z = pi.zod;
  for (const name of policy.tools.filter(name => toolNames.has(name))) {
    pi.registerTool({
      name, label: name,
      description: name === "course_read" ? "Read UTF-8 files or list relative names/types inside the declared work root." : "Save UTF-8 text only to an authorized output inside the work root. Existing inputs are protected.",
      loadMode: "essential", approval: name === "course_read" ? "read" : "write",
      parameters: z.object(name === "course_write" ? { path: z.string(), content: z.string() } : { path: z.string() }),
      async execute(callId, args, signal, _onUpdate, ctx) {
        identity(ctx);
        if (signal?.aborted) throw new Error("HOLD: call aborted");
        const decision = authorize(policy, state, name, args);
        log({ type: "execution_check", call_id: callId, tool: name, arguments: args, ...decision });
        if (!decision.allow) throw new Error(`HOLD: ${decision.reason}`);
        let text;
        if (name === "course_read") {
          const target = decision.resolved_path;
          if (fs.statSync(target).isDirectory()) {
            text = JSON.stringify(fs.readdirSync(target, { withFileTypes: true }).map(entry => ({ name: entry.name, type: entry.isSymbolicLink() ? "link" : entry.isDirectory() ? "directory" : "file" })).sort((a, b) => a.name.localeCompare(b.name)));
          } else {
            text = new TextDecoder("utf-8", { fatal: true }).decode(fs.readFileSync(target));
          }
        } else if (name === "course_write") {
          fs.mkdirSync(path.dirname(decision.resolved_path), { recursive: true });
          const rechecked = authorize(policy, state, name, args);
          if (!rechecked.allow || rechecked.resolved_path !== decision.resolved_path) throw new Error("HOLD: write path changed");
          fs.writeFileSync(decision.resolved_path, args.content, { encoding: "utf8", flag: state.created.has(decision.resolved_path) ? "w" : "wx" });
          state.created.add(decision.resolved_path);
          text = `WROTE ${decision.relative_path}; sha256=${digest(fs.readFileSync(decision.resolved_path))}`;
        }
        log({ type: "executed", call_id: callId, tool: name, resolved_path: decision.resolved_path, output_sha256: name === "course_write" ? digest(fs.readFileSync(decision.resolved_path)) : null });
        return { content: [{ type: "text", text }], details: { course_run_id: policy.run_id, resolved_path: decision.resolved_path } };
      },
    });
  }
  pi.on("session_shutdown", () => log({ type: "guard_end", ready: state.ready, failed: state.failed, provider_requests: state.requests, policy_sha256: policyHash }));
}
