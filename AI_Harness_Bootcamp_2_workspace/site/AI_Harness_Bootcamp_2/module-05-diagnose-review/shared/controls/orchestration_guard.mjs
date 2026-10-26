import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { isDeepStrictEqual } from "node:util";
import { fileURLToPath } from "node:url";

export const digest = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const sourceFile = fileURLToPath(import.meta.url);
const require = (condition, message) => { if (!condition) throw new Error(message); };

function logicalPath(raw) {
  require(typeof raw === "string" && /^[A-Za-z0-9_./-]+$/.test(raw), "invalid logical path");
  const parts = raw.split("/");
  require(parts.every(part => part && part !== "." && part !== ".."), "path traversal/absolute path is forbidden");
  require(!parts.some(part => /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?$/i.test(part)), "device path is forbidden");
  return raw;
}

function noLinks(absolute, missing = false) {
  require(path.isAbsolute(absolute) && path.resolve(absolute) === absolute, "binding must be canonical and absolute");
  const parsed = path.parse(absolute);
  let cursor = parsed.root;
  for (const part of absolute.slice(parsed.root.length).split(path.sep)) {
    if (!part) continue;
    cursor = path.join(cursor, part);
    try {
      require(!fs.lstatSync(cursor).isSymbolicLink(), "linked path is forbidden");
    } catch (error) {
      if (missing && error.code === "ENOENT") return;
      throw error;
    }
  }
}

export function resolveCoursePath(raw, root) {
  const target = path.join(root, logicalPath(raw));
  const relative = path.relative(root, target);
  require(relative && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative), "path escapes work root");
  noLinks(target, true);
  return target;
}

function readRegular(file) {
  noLinks(file, true);
  const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
  try {
    require(fs.fstatSync(fd).isFile(), "only regular files can be read");
    return fs.readFileSync(fd);
  } finally {
    fs.closeSync(fd);
  }
}

export default function orchestrationGuard(pi) {
  const policyFile = process.env.ORCHESTRATION_GUARD_POLICY;
  require(policyFile, "ORCHESTRATION_GUARD_POLICY is missing");
  const policyBytes = readRegular(policyFile);
  const policyHash = digest(policyBytes);
  const policy = JSON.parse(policyBytes.toString("utf8"));
  require(policy.schema_version === 1 && policy.provider === "openrouter" && policy.model === "anthropic/claude-sonnet-4.6" && typeof policy.omp_version === "string" && /^omp\/[0-9]+\.[0-9]+\.[0-9]+$/.test(policy.omp_version), "invalid frozen policy");
  require(digest(readRegular(sourceFile)) === policy.guard_source_sha256, "guard source identity differs");
  require(Array.isArray(policy.parent_tools) && policy.reads && policy.role_files, "missing context permissions");
  require(Number.isInteger(policy.max_provider_requests) && policy.max_provider_requests > 0, "invalid provider request bound");
  noLinks(policy.work_root);
  noLinks(policy.evidence_root);
  require(policy.guard_log === path.join(policy.evidence_root, "guard.jsonl"), "guard log is outside evidence root");

  const state = { agent: null, role: null, ready: false, sessionReady: false, failed: false,
    requests: 0, taskCalled: false, yielded: false, spawned: new Set(), reads: new Set(),
    writeCall: null, wrote: false, tools: [] };
  const log = row => fs.appendFileSync(policy.guard_log,
    JSON.stringify({ run_id: policy.run_id, stage: policy.stage, agent: state.agent, ...row }) + "\n", "utf8");
  const contextAgent = ctx => {
    const agent = ctx.agent;
    require(agent && ["main", "sub"].includes(agent.kind), "native ctx.agent is missing");
    return { kind: agent.kind, id: agent.id, name: agent.name, depth: agent.depth,
      ...(agent.parentId === undefined ? {} : { parentId: agent.parentId }) };
  };
  const identity = ctx => {
    require(ctx.model?.provider === policy.provider && ctx.model.id === policy.model, "provider/model identity drift");
    require(digest(readRegular(policyFile)) === policyHash, "policy changed");
    require(digest(readRegular(sourceFile)) === policy.guard_source_sha256, "guard changed");
    if (state.agent) require(isDeepStrictEqual(contextAgent(ctx), state.agent), "native agent identity drift");
    if (state.agent?.kind === "sub") {
      const role = policy.role_files[state.role];
      require(role && role.file === path.join(fs.realpathSync(ctx.cwd), ".omp", "agents", `${state.role}.md`), "role discovery path differs");
      require(digest(readRegular(role.file)) === role.sha256, "native role changed");
    }
  };
  const fail = (ctx, error) => {
    state.failed = true;
    state.ready = false;
    log({ type: "guard_error", reason: error.message });
    ctx.abort();
  };
  const bindings = () => policy.reads[state.role] || {};
  const requiredReadsAttempted = () => Object.keys(bindings()).every(name => state.reads.has(name));
  const authorizeFile = (tool, args, callId) => {
    require(state.ready && !state.failed, "guard is not ready");
    const keys = tool === "course_write" ? ["content", "path"] : ["path"];
    require(args && typeof args === "object" && !Array.isArray(args) && isDeepStrictEqual(Object.keys(args).sort(), keys), "unexpected file tool arguments");
    const logical = logicalPath(args.path);
    if (tool === "course_read") {
      const binding = bindings()[logical];
      require(binding && typeof binding.file === "string", "read outside assigned inputs");
      noLinks(binding.file, true);
      return { path: logical, file: binding.file, sha256: binding.sha256 };
    }
    require(state.agent.kind === "main" && policy.stage === "integrate" && logical === policy.write_file && logical === "out/status-brief.json", "only the coordinator may write the declared candidate");
    require(typeof args.content === "string" && !state.wrote && (!state.writeCall || state.writeCall === callId), "candidate may be written only once");
    require(requiredReadsAttempted(), "candidate write precedes required source reads");
    return { path: logical, file: resolveCoursePath(logical, policy.work_root) };
  };

  pi.on("session_start", async (_event, ctx) => {
    try {
      state.agent = contextAgent(ctx);
      if (state.agent.kind === "main") {
        require(state.agent.id === "Main" && state.agent.name === "main" && state.agent.depth === 0 && state.agent.parentId === undefined, "unexpected main identity");
        state.role = "main";
        state.tools = [...policy.parent_tools];
      } else {
        const matching = policy.task_call?.tasks.filter(item => item.agent === state.agent.name && item.name === state.agent.id) || [];
        require(matching.length === 1 && state.agent.depth === 1 && state.agent.parentId === "Main", "unrequested child/recursion");
        state.role = state.agent.name;
        state.tools = ["course_read", "yield"];
      }
      identity(ctx);
      log({ type: "session_start", cwd: ctx.cwd });
      await pi.setActiveTools(state.tools);
      const active = pi.getActiveTools().sort();
      require(isDeepStrictEqual(active, [...state.tools].sort()), "actual tools differ from context policy");
      state.sessionReady = true;
      log({ type: "guard_ready", provider: ctx.model.provider, model: ctx.model.id,
        active_tools: active, policy_sha256: policyHash,
        role_sha256: state.role === "main" ? null : policy.role_files[state.role].sha256 });
    } catch (error) { fail(ctx, error); throw error; }
  });
  pi.on("before_agent_start", (_event, ctx) => {
    try {
      identity(ctx);
      require(state.sessionReady && !state.failed, "session initialization failed");
      state.ready = true;
    } catch (error) { fail(ctx, error); throw error; }
  });
  pi.on("before_provider_request", (_event, ctx) => {
    try {
      identity(ctx);
      require(state.ready && !state.failed, "provider request before guard readiness");
      require(isDeepStrictEqual(pi.getActiveTools().sort(), [...state.tools].sort()), "active tools changed");
      require(state.requests < policy.max_provider_requests, "provider request bound exceeded");
      log({ type: "provider_request", sequence: ++state.requests, provider: ctx.model.provider, model: ctx.model.id });
    } catch (error) { fail(ctx, error); throw error; }
  });
  for (const name of ["auto_retry_start", "retry_fallback_applied", "model_changed"]) {
    pi.on(name, (_event, ctx) => {
      const error = new Error(`forbidden runtime transition: ${name}`);
      fail(ctx, error);
      throw error;
    });
  }
  pi.on("before_subagent_spawn", (event, ctx) => {
    const observation = { type: "subagent_spawn", requested_role: event.agent,
      spawnKey: event.spawnKey, invocationKind: event.invocationKind };
    try {
      identity(ctx);
      require(state.ready && !state.failed && state.agent.kind === "main" && state.taskCalled, "spawn without authorized main task");
      require(event.invocationKind === "task", "non-task spawn forbidden");
      const matches = policy.task_call.tasks.filter(item => item.agent === event.agent && item.name === event.spawnKey);
      require(matches.length === 1 && !state.spawned.has(event.spawnKey), "unrequested/duplicate spawn");
      state.spawned.add(event.spawnKey);
      log({ ...observation, allow: true });
    } catch (error) {
      log({ ...observation, allow: false, reason: error.message });
      fail(ctx, error);
      return { block: true, reason: error.message };
    }
  });
  pi.on("tool_call", (event, ctx) => {
    let decision;
    try {
      identity(ctx);
      require(state.ready && !state.failed && state.tools.includes(event.toolName), "tool outside ready context permissions");
      const args = event.input;
      if (event.toolName === "task") {
        require(state.agent.kind === "main" && !state.taskCalled && policy.task_call, "task is not authorized again");
        require(isDeepStrictEqual(args, policy.task_call), "task arguments differ from frozen delegation contracts");
        state.taskCalled = true;
      } else if (event.toolName === "yield") {
        require(state.agent.kind === "sub" && !state.yielded && args?.data && typeof args.data === "object" && !Array.isArray(args.data), "one structured child yield is required");
        require(args.type == null && args.error == null, "incremental/error yield is outside the handoff contract");
        require(requiredReadsAttempted(), "yield precedes assigned source reads");
        state.yielded = true;
      } else {
        authorizeFile(event.toolName, args, event.toolCallId);
        if (event.toolName === "course_write") state.writeCall = event.toolCallId;
      }
      decision = { allow: true, reason: "authorized by exact context policy" };
    } catch (error) {
      decision = { allow: false, reason: error.message };
    }
    log({ type: "decision", call_id: event.toolCallId, tool: event.toolName, arguments: event.input, ...decision });
    if (!decision.allow) return { block: true, reason: `HOLD: ${decision.reason}` };
  });
  pi.on("tool_result", (event) => {
    log({ type: "tool_result", call_id: event.toolCallId, tool: event.toolName,
      isError: Boolean(event.isError), details: event.details || {} });
  });

  const z = pi.zod;
  const fileTools = policy.stage === "integrate" ? ["course_read", "course_write"] : ["course_read"];
  for (const tool of fileTools) {
    pi.registerTool({
      name: tool, label: tool, loadMode: "essential", approval: tool === "course_read" ? "read" : "write",
      description: tool === "course_read" ? "Read only an exact assigned logical file; return its path, byte SHA256 and UTF-8 contents." : "Write the sole combined JSON brief once, after all required reads.",
      parameters: z.object(tool === "course_read" ? { path: z.string() } : { path: z.string(), content: z.string() }),
      async execute(callId, args, signal, _onUpdate, ctx) {
        let target;
        try {
          identity(ctx);
          require(!signal?.aborted, "call aborted");
          target = authorizeFile(tool, args, callId);
          log({ type: "execution_check", call_id: callId, tool, arguments: args, allow: true });
          if (tool === "course_read") {
            let bytes;
            try { bytes = readRegular(target.file); }
            finally { state.reads.add(target.path); }
            const hash = digest(bytes);
            require(target.sha256 !== null && hash === target.sha256, "source changed since the frozen assignment");
            const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
            log({ type: "execution_result", call_id: callId, tool, path: target.path, ok: true, sha256: hash });
            return { content: [{ type: "text", text: `PATH: ${target.path}\nSHA256: ${hash}\n${text}` }], details: { path: target.path, sha256: hash } };
          }
          const checkBefore = () => {
            noLinks(target.file, true);
            let hash = null;
            try { hash = digest(readRegular(target.file)); }
            catch (error) { if (error.code !== "ENOENT") throw error; }
            require(hash === policy.output_before_sha256, "candidate changed before the authorized write");
          };
          checkBefore();
          const directory = path.dirname(target.file);
          fs.mkdirSync(directory, { recursive: true });
          noLinks(directory);
          const temporary = path.join(directory, `.candidate-${crypto.randomUUID()}.tmp`);
          try {
            fs.writeFileSync(temporary, args.content, { encoding: "utf8", flag: "wx" });
            checkBefore();
            if (policy.output_before_sha256 === null) {
              // A hard-link installation refuses a concurrently created destination.
              fs.linkSync(temporary, target.file);
              fs.unlinkSync(temporary);
            } else {
              fs.renameSync(temporary, target.file);
            }
          } finally {
            if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
          }
          state.wrote = true;
          const hash = digest(readRegular(target.file));
          log({ type: "execution_result", call_id: callId, tool, path: target.path, ok: true, sha256: hash });
          return { content: [{ type: "text", text: `WROTE ${target.path}; SHA256: ${hash}` }], details: { path: target.path, sha256: hash } };
        } catch (error) {
          log({ type: "execution_result", call_id: callId, tool, path: target?.path || args.path,
            ok: false, code: error.code || "GUARD", error: error.message });
          throw error;
        }
      },
    });
  }
  pi.on("session_shutdown", () => log({ type: "guard_end" }));
}
