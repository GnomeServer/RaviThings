import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import guard, { digest, resolveCoursePath } from "../shared/controls/orchestration_guard.mjs";

// These isolated hook fixtures exercise the real guard's filesystem effects.
// They are not native OMP sessions or provider-backed execution evidence.
const guardFile = fileURLToPath(new URL("../shared/controls/orchestration_guard.mjs", import.meta.url));

async function fixture(t, { child = false, stage = "fanout", missing = false, cwdAlias = false, ompVersion = "omp/99.2.0" } = {}) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "copper-guard-test-")));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const work = path.join(root, "work"), evidence = path.join(root, "evidence"), cwd = path.join(root, "home", "cwd");
  fs.mkdirSync(path.join(work, "shared", "case"), { recursive: true });
  fs.mkdirSync(evidence);
  fs.mkdirSync(path.join(cwd, ".omp", "agents"), { recursive: true });
  const input = "shared/case/inventory.json", inputFile = path.join(work, input);
  if (!missing) fs.writeFileSync(inputFile, '{"count":72}\n');
  const roleFile = path.join(cwd, ".omp", "agents", "inventory.md");
  fs.writeFileSync(roleFile, "read-only fixture role\n");
  const task = { context: "fixture context", tasks: [{ name: "Inventory", agent: "inventory", task: "read the assigned file", solutionSpace: "one input" }] };
  const binding = { [input]: { file: inputFile, sha256: missing ? null : digest(fs.readFileSync(inputFile)) } };
  const policy = { schema_version: 1, run_id: "deterministic-guard-fixture", stage, work_root: work,
    evidence_root: evidence, provider: "openrouter", model: "anthropic/claude-sonnet-4.6", omp_version: ompVersion,
    guard_source_sha256: digest(fs.readFileSync(guardFile)), guard_log: path.join(evidence, "guard.jsonl"),
    parent_tools: stage === "integrate" ? ["course_read", "course_write"] : ["task"],
    reads: { main: stage === "integrate" ? binding : {}, inventory: binding },
    task_call: stage === "integrate" ? null : task, write_file: stage === "integrate" ? "out/status-brief.json" : null,
    output_before_sha256: null, max_provider_requests: 12,
    role_files: { inventory: { file: roleFile, sha256: digest(fs.readFileSync(roleFile)) } } };
  const policyFile = path.join(evidence, "policy.json");
  fs.writeFileSync(policyFile, JSON.stringify(policy));
  const previous = process.env.ORCHESTRATION_GUARD_POLICY;
  process.env.ORCHESTRATION_GUARD_POLICY = policyFile;
  t.after(() => { if (previous === undefined) delete process.env.ORCHESTRATION_GUARD_POLICY; else process.env.ORCHESTRATION_GUARD_POLICY = previous; });
  let active = [], aborted = false;
  const hooks = new Map(), tools = new Map();
  guard({ on: (name, callback) => hooks.set(name, callback), registerTool: tool => tools.set(tool.name, tool),
    setActiveTools: names => { active = [...names]; }, getActiveTools: () => [...active],
    zod: { object: shape => shape, string: () => ({}) } });
  let reportedCwd = cwd;
  if (cwdAlias) {
    reportedCwd = path.join(root, "cwd-alias");
    fs.symlinkSync(cwd, reportedCwd, "dir");
  }
  const ctx = { cwd: reportedCwd, model: { provider: policy.provider, id: policy.model },
    agent: child ? { kind: "sub", id: "Inventory", name: "inventory", depth: 1, parentId: "Main" }
      : { kind: "main", id: "Main", name: "main", depth: 0 }, abort: () => { aborted = true; } };
  await hooks.get("session_start")({}, ctx);
  await hooks.get("before_agent_start")({}, ctx);
  return { root, work, evidence, input, inputFile, policy, ctx, tools, hooks,
    aborted: () => aborted,
    call: (toolName, input, toolCallId = "fixture-call") => hooks.get("tool_call")({ toolName, input, toolCallId }, ctx),
    execute: (name, args, callId = "fixture-call") => tools.get(name).execute(callId, args, undefined, undefined, ctx),
    records: () => fs.readFileSync(policy.guard_log, "utf8").trim().split("\n").map(line => JSON.parse(line)) };
}

test("a list containing a version is rejected before the guard can authorize work", async t => {
  await assert.rejects(fixture(t, { ompVersion: ["omp/99.2.0"] }), /invalid .*policy/);
});

test("a child reads its assigned bytes but cannot read another in-root source or write", async t => {
  const f = await fixture(t, { child: true });
  fs.writeFileSync(path.join(f.work, "shared/case/authority.json"), "private other assignment");
  assert.equal(f.call("course_read", { path: f.input }), undefined);
  const result = await f.execute("course_read", { path: f.input });
  assert.equal(result.details.sha256, digest(fs.readFileSync(f.inputFile)));
  assert.match(result.content[0].text, /"count":72/);
  assert.equal(f.call("course_read", { path: "shared/case/authority.json" }, "other-read").block, true);
  assert.equal(f.call("course_write", { path: "out/status-brief.json", content: "unsafe" }, "write").block, true);
  assert.equal(fs.existsSync(path.join(f.work, "out/status-brief.json")), false);
});

test("missing input produces real ENOENT before one blocked yield is allowed", async t => {
  const f = await fixture(t, { child: true, missing: true });
  const payload = { data: { status: "blocked", source_path: f.input } };
  assert.equal(f.call("yield", payload, "early-yield").block, true);
  await assert.rejects(f.execute("course_read", { path: f.input }, "missing-read"), { code: "ENOENT" });
  const attempt = f.records().find(row => row.type === "execution_result");
  assert.equal(attempt.ok, false);
  assert.equal(attempt.code, "ENOENT");
  assert.equal(attempt.agent.id, "Inventory");
  assert.equal(f.call("yield", payload, "final-yield"), undefined);
  assert.equal(f.call("yield", payload, "second-yield").block, true);
});

test("a changed or newly appeared source cannot satisfy a frozen read", async t => {
  for (const missing of [false, true]) {
    const f = await fixture(t, { child: true, missing });
    fs.writeFileSync(f.inputFile, "changed after freeze");
    await assert.rejects(f.execute("course_read", { path: f.input }), /source changed/);
    assert.equal(f.records().filter(row => row.type === "execution_result" && row.ok).length, 0);
  }
});

test("source symlinks and traversal are refused without reading outside content", async t => {
  const f = await fixture(t, { child: true });
  const outside = path.join(f.root, "outside.txt");
  fs.writeFileSync(outside, "outside secret");
  fs.unlinkSync(f.inputFile);
  fs.symlinkSync(outside, f.inputFile);
  await assert.rejects(f.execute("course_read", { path: f.input }), /linked path/);
  for (const bad of ["../outside.txt", "file:///outside.txt", "/outside.txt", "shared/case/a.json:1-2", "shared/case/CON", "shared\\case\\inventory.json"]) {
    assert.throws(() => resolveCoursePath(bad, f.work));
  }
  assert.equal(f.records().some(row => JSON.stringify(row).includes("outside secret")), false);
});

test("native cwd aliases resolve to the same approved role rather than blocking children", async t => {
  const f = await fixture(t, { child: true, cwdAlias: true });
  const result = await f.execute("course_read", { path: f.input });
  assert.equal(result.details.sha256, f.policy.reads.inventory[f.input].sha256);
  assert.equal(f.aborted(), false);
});

test("task object key order is immaterial but changed assignments and duplicate spawns are blocked", async t => {
  const f = await fixture(t);
  const item = f.policy.task_call.tasks[0];
  const reordered = { tasks: [{ solutionSpace: item.solutionSpace, task: item.task, agent: item.agent, name: item.name }], context: f.policy.task_call.context };
  const changed = structuredClone(reordered);
  changed.tasks[0].task = "read an unassigned file";
  assert.equal(f.call("task", changed, "changed").block, true);
  assert.equal(f.call("task", reordered, "approved"), undefined);
  const spawn = { agent: "inventory", spawnKey: "Inventory", invocationKind: "task" };
  assert.equal(f.hooks.get("before_subagent_spawn")(spawn, f.ctx), undefined);
  assert.equal(f.hooks.get("before_subagent_spawn")(spawn, f.ctx).block, true);
  assert.equal(f.aborted(), true);
});

test("coordinator writes only after reads, exactly once, without overwriting a concurrent candidate", async t => {
  const f = await fixture(t, { stage: "integrate" });
  const args = { path: "out/status-brief.json", content: '{"decision":"HOLD"}\n' };
  assert.equal(f.call("course_write", args, "premature").block, true);
  await f.execute("course_read", { path: f.input }, "read");
  assert.equal(f.call("course_write", { ...args, path: "out/other.json" }, "other").block, true);
  assert.equal(f.call("course_write", args, "write"), undefined);
  const output = await f.execute("course_write", args, "write");
  assert.equal(fs.readFileSync(path.join(f.work, args.path), "utf8"), args.content);
  assert.equal(output.details.sha256, digest(Buffer.from(args.content)));
  assert.equal(f.call("course_write", { ...args, content: "changed" }, "second").block, true);
  await assert.rejects(f.execute("course_write", args, "second"), /only once/);
  assert.equal(fs.readFileSync(path.join(f.work, args.path), "utf8"), args.content);
});

test("an output appearing after freeze is preserved instead of overwritten", async t => {
  const f = await fixture(t, { stage: "integrate" });
  await f.execute("course_read", { path: f.input }, "read");
  const args = { path: "out/status-brief.json", content: "replacement" };
  fs.mkdirSync(path.join(f.work, "out"));
  fs.writeFileSync(path.join(f.work, args.path), "concurrent work");
  f.call("course_write", args, "write");
  await assert.rejects(f.execute("course_write", args, "write"), /candidate changed/);
  assert.equal(fs.readFileSync(path.join(f.work, args.path), "utf8"), "concurrent work");
});
