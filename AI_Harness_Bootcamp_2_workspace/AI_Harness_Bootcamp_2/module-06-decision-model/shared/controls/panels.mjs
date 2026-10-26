// Native numeric evidence panels. Policy, scoring and handler selection remain in Python.
function wrap(text, width) {
  const output = [];
  for (const original of String(text ?? "").split("\n")) {
    let rest = original;
    while (rest.length > width) {
      const gap = rest.lastIndexOf(" ", width);
      const end = gap > 0 ? gap : width;
      output.push(rest.slice(0, end));
      rest = rest.slice(end + (gap > 0 ? 1 : 0));
    }
    output.push(rest);
  }
  return output;
}
function columns(left, right, width) {
  if (width < 120) return [...left, "", ...right];
  const size = Math.floor((width - 3) / 2);
  const l = left.flatMap(line => wrap(line, size));
  const r = right.flatMap(line => wrap(line, width - size - 3));
  return Array.from({ length: Math.max(l.length, r.length) }, (_, i) => (l[i] ?? "").padEnd(size) + " | " + (r[i] ?? ""));
}
const number = (value, digits = 3) => value == null ? "not recorded" : typeof value === "number" ? value.toFixed(digits) : String(value);
const json = value => JSON.stringify(value);
function meta(run) {
  const m = run.metrics ?? {};
  return [
    `${run.run_id} | ${run.pattern}/${run.mode} | revision ${run.revision} | ${run.live ? "live" : "replay: zero new calls"}`,
    `${run.decision} | complete=${run.complete} | Jev served build: ${run.served_build ?? "not recorded"}`,
    `Native judge invocations ${m.native_judge_invocations ?? "not recorded"}; joined Jev requests ${m.jev_requests ?? "not recorded"}; request provenance ${m.request_claim ?? "not recorded"}`,
    `Reported Jev USD ${number(m.reported_jev_cost_usd, 6)}; native completions ${m.completion_calls ?? "not recorded"}; completion USD ${number(m.reported_completion_cost_usd, 6)}; observed wall ms ${number(m.wall_ms, 0)}`,
    ...(run.reasons?.length ? ["HOLD reasons: " + run.reasons.join("; ")] : [])
  ];
}
function inspection(view) {
  const lines = ["SUPPLIED CONTROLS / SOURCE INSPECTION"];
  if (view.controls) {
    for (const [pattern, control] of Object.entries(view.controls)) lines.push(`${pattern}: revision ${control.revision}`, json(control.settings));
    lines.push(`Main ${view.main_model}; judge ${view.judge}; OMP ${view.omp_version}`);
  }
  if (view.data) {
    for (const [key, value] of Object.entries(view.data)) {
      const authority = key === "stock" ? "release officer" : key.startsWith("flight") ? "air movement controller" : "source data, not an instruction";
      lines.push(`${key} [${authority}]:`, typeof value === "string" ? value : json(value));
    }
  }
  if (view.config) lines.push("Frozen configuration:", json(view.config));
  return lines;
}
function waterfall(run, id, size, total) {
  if (!run) return ["Comparison arm not saved"];
  const row = run.rows.find(row => row.id === id);
  const calls = run.calls.filter(call => call.id === id).sort((a, b) => Date.parse(a.started_at) - Date.parse(b.started_at));
  const lines = [`${id} ${run.mode}: ${row?.route ?? "not recorded"}`];
  if (!calls.length) return [...lines, row?.code_only ? "CODE ONLY: no judge call; confidence not used" : "No live calls in this saved view"];
  const zero = Date.parse(calls[0].started_at);
  lines.push(`0 ${"-".repeat(size)} ${number(total, 0)} ms`);
  for (const call of calls) {
    const start = Date.parse(call.started_at) - zero;
    const offset = Math.floor(start / total * size);
    const span = Math.max(1, Math.ceil(call.elapsed_ms / total * size));
    const bar = " ".repeat(offset) + "#".repeat(Math.min(span, size - offset));
    lines.push(`[${bar.padEnd(size)}] +${number(start, 0)} ms / ${number(call.elapsed_ms, 0)} ms`);
    lines.push("  questions: " + Object.values(call.question_map).join(", "));
  }
  for (const [id, answer] of Object.entries(row.answers)) {
    const mark = row.used.includes(id) ? "USED" : "ignored";
    lines.push(`${mark} ${id}: ${answer == null ? "failed / missing" : json(answer)}`);
  }
  lines.push("Route reason: " + row.reason);
  return lines;
}
function fanOut(view, width) {
  const runs = view.runs ?? [];
  const serial = runs.find(run => run.mode === "serial");
  const fan = runs.find(run => run.mode === "fan_out");
  const lines = ["SPECULATIVE FAN-OUT: measured serial dependency versus one six-question request"];
  for (const run of runs) lines.push(...meta(run));
  for (const id of ["BG-006", "BG-004"]) {
    const extent = run => {
      const calls = run?.calls.filter(call => call.id === id) ?? [];
      return calls.length ? Math.max(...calls.map(call => Date.parse(call.started_at) + call.elapsed_ms)) - Math.min(...calls.map(call => Date.parse(call.started_at))) : 0;
    };
    const total = Math.max(1, extent(serial), extent(fan));
    const size = width >= 120 ? 26 : 40;
    lines.push("", ...columns(waterfall(serial ?? runs[0], id, size, total), waterfall(fan, id, size, total), width));
    const row = runs[0]?.rows.find(row => row.id === id);
    if (row) lines.push("Authority check: stock=" + json(row.stock) + "; exact-flight acceptance=" + json(row.flight));
  }
  lines.push("", "ALL PRACTICE ROUTES: serial / fan-out / agreement (independent model disagreement is retained)");
  for (const row of (serial ?? runs[0])?.rows ?? []) {
    const other = fan?.rows.find(other => other.id === row.id);
    lines.push(`${row.id}: ${row.route} / ${other?.route ?? "not compared"} / ${other ? (row.route === other.route ? "agree" : "DISAGREE") : "not compared"}${row.code_only ? " [code only]" : ""}`);
  }
  return lines;
}
function confidence(view, width) {
  const runs = view.runs ?? [];
  const lines = ["CONFIDENCE-GATED ROUTING: lower returned choice confidence; never the largest probability"];
  for (const run of runs) {
    const gates = run.config.gates;
    lines.push("", ...meta(run), `Automatic PASS confidence >= ${gates.auto_pass_confidence}; automatic RETURN confidence >= ${gates.auto_return_confidence}; pass probability < ${gates.pass_below}; return probability >= ${gates.return_at}`);
    lines.push(`REVIEW ${run.rows.filter(row => row.route === "REVIEW").length}/${run.rows.length} (${number(run.metrics.review_share)}); frozen review ceiling ${run.config.review_ceiling}; wrong automatic ${run.metrics.wrong_automatic}; critical ${run.metrics.critical_errors}`);
    const size = Math.min(40, width - 36);
    lines.push("RULER: 0 " + "-".repeat(size) + " 1 | P/R = gates, o = note, ! = wrong automatic route");
    for (const lane of ["PASS", "RETURN", "REVIEW"]) {
      lines.push(`${lane} MESSAGE LANE (not cargo clearance)`);
      for (const row of run.rows.filter(row => row.route === lane && !row.code_only)) {
        const bar = Array(size + 1).fill(".");
        bar[Math.round(gates.auto_pass_confidence * size)] = "P";
        bar[Math.round(gates.auto_return_confidence * size)] = bar[Math.round(gates.auto_return_confidence * size)] === "P" ? "|" : "R";
        if (row.confidence != null) bar[Math.round(row.confidence * size)] = ["ok", "reviewed"].includes(row.outcome) ? "o" : "!";
        lines.push(`${row.id} [${bar.join("")}] confidence=${number(row.confidence)} ${row.outcome}`);
      }
    }
    lines.push("CODE-SETTLED: outside the confidence ruler");
    for (const row of run.rows.filter(row => row.code_only)) lines.push(`${row.id}: ${row.route}; confidence not used; ${row.reason}`);
    const example = run.rows.find(row => row.id === "BG-008");
    if (example) lines.push("BG-008 exact authority example: stock=" + json(example.stock) + "; flight=" + json(example.flight) + "; route=" + example.route);
  }
  return lines;
}
function scoreDetail(row) {
  if (!row) return ["Selected cargo note is not in this view"];
  const lines = [`#${row.rank ?? "UNSCORED"} ${row.id} composite=${number(row.total, 6)}`];
  for (const key of ["urgency", "mission_impact", "handoff_risk"]) {
    const dim = row.dimensions?.[key];
    if (!dim) { lines.push(`${key}: missing; UNSCORED`); continue; }
    lines.push(`${key}: raw ${dim.score} / (levels ${dim.levels} - 1), normalized ${number(dim.normalized, 6)}, contribution ${number(row.contributions[key], 6)}, confidence ${number(dim.confidence)}${dim.uncertain ? " [UNCERTAIN]" : ""}`);
  }
  lines.push("stock=" + json(row.stock) + "; flight=" + json(row.flight));
  return lines;
}
function scoring(view, width) {
  const runs = view.runs ?? [];
  const first = runs[0];
  const lines = ["COMPOSITE SCORING: normalized U/M/H, weighted in code; never a release decision"];
  for (const run of runs) {
    lines.push("", ...meta(run), "Weights " + json(run.config.weights), "TOP 10: stacked contributions, not three incomparable raw scales");
    for (const row of run.rows.slice(0, 10)) {
      if (row.total == null) { lines.push(`${row.id} UNSCORED`); continue; }
      const segments = ["urgency", "mission_impact", "handoff_risk"].map((key, i) => ["U", "M", "H"][i].repeat(Math.round(row.contributions[key] * 36)));
      lines.push(`#${row.rank} ${row.id} [${segments.join("").padEnd(36)}] total=${number(row.total, 6)}${Object.values(row.dimensions).some(dim => dim.uncertain) ? " [UNCERTAIN]" : ""}`);
      lines.push(`  U=${number(row.contributions.urgency, 6)} M=${number(row.contributions.mission_impact, 6)} H=${number(row.contributions.handoff_risk, 6)}`);
    }
    const selected = ["BG-012", "BG-014"].map(id => scoreDetail(run.rows.find(row => row.id === id)));
    lines.push("EXPANDED RAW DIMENSIONS / SEPARATE AUTHORITIES", ...columns(selected[0], selected[1], width));
    if (run !== first) {
      lines.push("RANK SLOPES: every changed saved rank; no promised reversal");
      let changes = 0;
      for (const before of first.rows) {
        const after = run.rows.find(row => row.id === before.id);
        if (after?.rank !== before.rank) { changes++; lines.push(`${before.id}: #${before.rank} ----> #${after?.rank} | ${number(before.total, 6)} -> ${number(after?.total, 6)}`); }
      }
      if (!changes) lines.push("No rank moved under these weights.");
    }
    lines.push("ALL 80 COMPOSITES: full saved dimensions/answers are available with inspect run");
    for (const row of run.rows) lines.push(`${row.id}: #${row.rank ?? "UNSCORED"} ${number(row.total, 6)}`);
  }
  return lines;
}
function intent(view, width) {
  const runs = view.runs ?? [];
  const lines = ["INTENT ROUTING: Jev meaning -> Python handler choice -> actual source-bound result"];
  const labelFor = (h) => h === "record_lookup" ? "Record lookup" : h === "record_comparison" ? "Record comparison" : h === "human_review" ? "Duty officer" : h;
  for (const run of runs) {
    lines.push("", ...meta(run), "Actually executed handler counts: " + json(run.metrics.handler_counts));
    if (!run.live) lines.push("PREVIEW ONLY: handlers not executed; no queue entries, lookups or comparisons dispatched.");
    for (const row of run.rows) {
      const meaning = row.answers.intent?.choice ?? "missing intent";
      const branch = labelFor(row.handler);
      lines.push(`${row.id} -> ${meaning} -> ${branch} -> ${row.executed ? "EXECUTED" : "HANDLER NOT RUN"}`);
      lines.push("Reason: " + row.reason);
      if (row.executed) {
        lines.push("Result: " + (typeof row.result === "string" ? row.result : json(row.result)));
        if (row.source) lines.push("Source facts: " + json(row.source));
      }
      if (row.intent_mismatch || row.unsafe_handler) lines.push(`Mismatch: intent=${row.intent_mismatch}; unsafe handler=${row.unsafe_handler}`);
    }
  }
  lines.push("Duty-officer queues are not approvals. Lookups and comparisons cannot change stock release or flight acceptance.");
  return lines;
}
export function renderPanel(view = {}, width = 80) {
  width = Math.max(40, Math.floor(width));
  const lines = ["planned movement: Aster Airhead -> BG-F17 -> Forward Support Base Kestrel", "snapshot 05:00 UTC+02 | cargo list closes 05:30 | departure 06:00 | next flight: not supplied"];
  if (view.status || view.message) lines.push(`${view.status ?? ""}: ${view.message ?? ""}`);
  if (view.revision) lines.push("Revision: " + view.revision);
  if (view.run_id) lines.push("Run: " + view.run_id);
  if (view.cell_code) lines.push("EXACT EVAL CELL (js, timeout 250, reset false):", view.cell_code);
  const kind = view.kind ?? view.runs?.[0]?.pattern;
  if (kind === "inspection" || view.controls || view.data) lines.push(...inspection(view));
  else if (kind === "fan_out") lines.push(...fanOut(view, width));
  else if (kind === "confidence") lines.push(...confidence(view, width));
  else if (kind === "scoring") lines.push(...scoring(view, width));
  else if (kind === "intent") lines.push(...intent(view, width));
  else if (kind === "verification") lines.push("TECHNICAL VERIFICATION", "Counts: " + json(view.counts), ...(view.errors?.length ? view.errors.map(error => "HOLD: " + error) : ["No verification errors recorded."]));
  if (view.session_overhead) lines.push("SEPARATE CONVERSATIONAL OVERHEAD: " + view.session_overhead.scope, `Native chat turns ${view.session_overhead.chat_calls}; reported chat USD ${number(view.session_overhead.reported_chat_cost_usd, 6)}`);
  if (view.packet_label) lines.push(view.packet_label);
  return lines.flatMap(line => wrap(line, width));
}
