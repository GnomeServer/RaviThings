// Supplied native eval cell. Python owns all routing, arithmetic and handler policy.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const stamp = () => new Date().toISOString();
const read = file => JSON.parse(fs.readFileSync(file, "utf8"));

function invokeAdapter(spec, request) {
  return new Promise((resolve, reject) => {
    const child = spawn(spec.python, [spec.adapter.path, "control", "--policy", spec.policy_path], { stdio: ["pipe", "pipe", "pipe"] });
    let output = "", error = "";
    child.stdout.on("data", bytes => { output += bytes; });
    child.stderr.on("data", bytes => { error += bytes; });
    child.on("error", reject);
    child.on("close", code => {
      if (code !== 0) return reject(new Error(`supplied adapter exited ${code}: ${error}`));
      try { resolve(JSON.parse(output)); } catch { reject(new Error("supplied adapter returned invalid JSON")); }
    });
    child.stdin.end(JSON.stringify(request));
  });
}

export async function run({ judgeBatch, plan }) {
  const spec = read(fileURLToPath(plan));
  const policy = read(spec.policy_path);
  for (const descriptor of [spec.adapter, spec.runner, policy.shared_guard]) {
    if (hash(fs.readFileSync(descriptor.path)) !== descriptor.sha256) throw new Error("HOLD: supplied helper identity changed");
  }
  const { digest, resolveCoursePath } = await import(pathToFileURL(policy.shared_guard.path).href);
  if (spec.schema_version !== 1 || spec.deadline_seconds !== 240 || spec.concurrency !== 2 || spec.live !== true || spec.runner.path !== policy.runner.path) throw new Error("HOLD: invalid frozen native operation");
  const out = resolveCoursePath(spec.output_dir, policy.work_root);
  if (path.dirname(out) !== path.join(policy.evidence_root, "runs")) throw new Error("HOLD: undeclared output directory");
  const rawFile = path.join(out, "raw.jsonl");
  fs.closeSync(fs.openSync(rawFile, "wx"));
  const raw = record => fs.appendFileSync(rawFile, JSON.stringify(record) + "\n");
  const started = stamp(), start = Date.now(), deadline = start + 240_000;
  const batches = new Set();
  let sequence = 0, interrupted = null, adapterTail = Promise.resolve();
  // Serialize local adapter transactions only. Two independent native calls may overlap.
  const adapter = request => {
    const pending = adapterTail.then(() => invokeAdapter(spec, request));
    adapterTail = pending.catch(() => {});
    return pending;
  };
  const remaining = () => Math.max(0, (deadline - Date.now()) / 1000);
  const ensureTime = () => { if (interrupted || !remaining()) throw new Error(interrupted || "240-second operation deadline"); };
  const cancelAll = async () => {
    await Promise.allSettled([...batches].map(handle => handle.cancel()));
  };
  const timer = setTimeout(() => { interrupted = "240-second operation deadline"; void cancelAll(); }, 240_000);
  const adapterStep = async id => {
    ensureTime();
    const result = await adapter({ action: "screen_step", plan_id: spec.run_id, id });
    if (result.status !== "PASS" || !result.view) throw new Error(`HOLD: ${result.message}`);
    return result.view;
  };

  async function ask(id, logicalIds) {
    ensureTime();
    const item = spec.items[id], serial = ++sequence, namespace = `${spec.question_namespace}${serial}_`;
    const questionMap = {}, questions = {};
    for (const logical of logicalIds) {
      const namespaced = namespace + logical;
      questionMap[namespaced] = logical;
      questions[namespaced] = spec.questions[logical];
    }
    const began = stamp(), begin = Date.now();
    const record = { type: "judge", id, sequence: serial, batch_id: null, namespace, question_map: questionMap, questions,
      state_sha256: digest(Buffer.from(JSON.stringify(item.state))), started_at: began, elapsed_ms: null,
      answers: null, error: null, model: null, status: null };
    let batch;
    try {
      batch = await judgeBatch({ [id]: item.state }, questions, { intent: `Blue Gauge ${spec.run_id} ${id}`, concurrency: 1, retries: 0 });
      batches.add(batch);
      record.batch_id = batch.id;
      ensureTime();
      let settled;
      while (!settled) {
        ensureTime();
        const entries = await batch.drain({ timeout: Math.min(5, remaining()) });
        if (entries.length) {
          if (entries.length !== 1 || String(entries[0][0]) !== id) throw new Error("native batch input identity differs");
          settled = entries[0][1];
        } else if (!(await batch.status()).running) throw new Error("native batch completed without its result");
      }
      record.model = settled.model ?? null;
      record.error = settled.error ?? null;
      if (settled.answers) {
        record.answers = {};
        for (const [namespaced, answer] of Object.entries(settled.answers)) {
          const logical = questionMap[namespaced];
          if (!logical) throw new Error("native response used an unrequested question ID");
          record.answers[logical] = answer;
        }
      }
      record.status = await batch.status();
      while (record.status.running) {
        ensureTime();
        await batch.drain({ timeout: Math.min(0.1, remaining()) });
        record.status = await batch.status();
      }
    } catch (error) {
      record.error = String(error.message ?? error);
      if (batch) {
        await batch.cancel().catch(() => {});
        record.status = await batch.status().catch(() => null);
      }
    } finally {
      record.elapsed_ms = Date.now() - begin;
      raw(record);
      if (batch) { await batch.close().catch(() => {}); batches.delete(batch); }
    }
    ensureTime();
    return record;
  }


  async function one(id) {
    const item = spec.items[id];
    if (spec.pattern === "fan_out" || spec.pattern === "confidence") {
      let step = await adapterStep(id);
      if (!step.need.length) return; // Explicit source-settled row: no Jev call.
      if (spec.mode === "fan_out" || spec.mode === "unseen") {
        await ask(id, Object.keys(spec.questions));
      } else {
        while (step.need.length) {
          const result = await ask(id, step.need);
          step = await adapterStep(id);
          if (result.error) break; // A failed response is recorded, never retried.
        }
      }
    } else if (spec.pattern === "scoring") {
      const ids = Object.keys(spec.questions).filter(qid => !Object.hasOwn(spec.seed_answers[id] ?? {}, qid));
      if (ids.length) await ask(id, ids);
    } else if (spec.pattern === "intent") {
      const askRec = await ask(id, Object.keys(spec.questions));
      if (askRec && askRec.error) {
        const began = stamp(), begin = Date.now();
        raw({ type: "handler", id, handler: null, executed: false, result: null, completion_id: null, model: null, started_at: began, elapsed_ms: Date.now() - begin, error: askRec.error });
        return;
      }
      const began = stamp(), begin = Date.now();
      const handlerRec = { type: "handler", id, handler: null, executed: false, result: null, completion_id: null, model: null, started_at: began, elapsed_ms: null, error: null };
      try {
        const selected = await adapterStep(id);
        const registered = ["record_lookup", "record_comparison", "human_review"];
        if (!registered.includes(selected.handler)) {
          throw new Error(`unknown handler ${selected.handler}`);
        }
        handlerRec.handler = selected.handler;
        handlerRec.result = selected.result;
        handlerRec.executed = true;
      } catch (error) {
        handlerRec.error = String(error.message ?? error);
        handlerRec.executed = false;
      } finally {
        handlerRec.elapsed_ms = Date.now() - begin;
        raw(handlerRec);
      }
    } else throw new Error("unregistered pattern");
  }

  const ids = Object.keys(spec.items);
  let cursor = 0, failure = null;
  const worker = async () => {
    while (cursor < ids.length && !interrupted && !failure) {
      const id = ids[cursor++];
      try { await one(id); } catch (error) { failure = String(error.message ?? error); await cancelAll(); }
    }
  };
  try {
    await Promise.all([worker(), worker()]);
    await cancelAll();
    raw({ type: "finish", started_at: started, wall_ms: Date.now() - start, complete: !failure && !interrupted && cursor === ids.length, error: failure || interrupted });
    const result = await adapter({ action: "finalize", plan_id: spec.run_id });
    return { run_id: spec.run_id, status: result.status, message: result.message };
  } finally {
    clearTimeout(timer);
    await cancelAll();
    await Promise.allSettled([...batches].map(batch => batch.close()));
  }
}
