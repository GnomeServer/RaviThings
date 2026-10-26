// Run one frozen judgment batch inside the OMP eval kernel and save the raw answers.
// The launcher writes the plan; the guard allows only the one-line cell that calls run().
import fs from "node:fs";
import path from "node:path";

const read = location => JSON.parse(fs.readFileSync(location, "utf8"));

export async function run({ judgeBatch, plan }) {
  const spec = read(new URL(plan));
  const questions = read(spec.questions).questions;
  const states = {};
  for (const [id, file] of Object.entries(spec.states)) {
    const item = read(file);
    if (item.id !== id) throw new Error(`state file ${file} does not carry id ${id}`);
    states[id] = item.state;
  }
  const ids = Object.keys(states);
  fs.mkdirSync(spec.output_dir);
  const batch = await judgeBatch(states, questions, { intent: spec.intent, concurrency: spec.concurrency, retries: spec.retries });
  const rows = new Map();
  const deadline = Date.now() + spec.deadline_seconds * 1000;
  try {
    while (rows.size < ids.length && Date.now() < deadline) {
      for (const [key, item] of await batch.drain({ timeout: 10 })) {
        rows.set(String(key), { key: String(key), answers: item.answers ?? null, error: item.error ?? null, model: item.model ?? null });
      }
    }
    if (rows.size < ids.length) await batch.cancel();
    const status = await batch.status();
    const ordered = ids.map(id => rows.get(id) ?? { key: id, answers: null, error: "no judgment before the deadline", model: null });
    fs.writeFileSync(path.join(spec.output_dir, "judgments.jsonl"), ordered.map(row => JSON.stringify(row)).join("\n") + "\n", { flag: "wx" });
    fs.writeFileSync(path.join(spec.output_dir, "batch-status.json"), JSON.stringify(status, null, 2) + "\n", { flag: "wx" });
    const failed = ordered.filter(row => row.error !== null).length;
    return `judged ${ids.length - failed}/${ids.length}; failed ${failed}; model ${status.model ?? "none"}; cost ${status.cost}`;
  } finally {
    await batch.close();
  }
}
