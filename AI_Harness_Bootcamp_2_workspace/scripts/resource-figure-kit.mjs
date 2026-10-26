import path from "node:path";

const WIDTH = 1120;
const HEIGHT = 280;
const ALLOWED_HEIGHTS = new Set([280, 420, 560]);

const PALETTE = {
  paper: "#FFFFFF",
  warm: "#FAFAF8",
  panel: "#F4F4F2",
  ink: "#0A0A0A",
  muted: "#4A4A4A",
  faint: "#6B6B6B",
  rule: "#D0D0D0",
  mark: "#E31C23",
  gold: "#A58650"
};

function xml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function slug(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function wrap(value, limit = 26, maxLines = 3) {
  const words = String(value ?? "").trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length <= limit || !line) {
      line = candidate;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  if (lines.length <= maxLines) return lines;
  const kept = lines.slice(0, maxLines);
  kept[maxLines - 1] = kept[maxLines - 1].replace(/[.,;:]?$/, "") + "…";
  return kept;
}

function textLines({ x, y, value, cls = "body", anchor = "start", limit = 28, maxLines = 3, lineHeight = 19 }) {
  const lines = wrap(value, limit, maxLines);
  return `<text class="${cls}" x="${x}" y="${y}" text-anchor="${anchor}">${lines.map((line, index) =>
    `<tspan x="${x}" dy="${index === 0 ? 0 : lineHeight}">${xml(line)}</tspan>`
  ).join("")}</text>`;
}

function header(figure) {
  return [
    `<text class="eyebrow" x="36" y="35">${xml(figure.eyebrow || figure.role || "FIELD FIGURE")}</text>`,
    textLines({ x: 36, y: 62, value: figure.title, cls: "figure-title", limit: 72, maxLines: 1 })
  ].join("\n  ");
}

function itemLabel(item) {
  return typeof item === "string" ? item : item.label || item.title || "";
}

function itemDetail(item) {
  return typeof item === "string" ? "" : item.detail || item.note || item.description || "";
}

function arrowDefs(id) {
  return `<defs><marker id="${id}-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="${PALETTE.mark}" /></marker></defs>`;
}

function panel(x, y, width, height, accent = false) {
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="2" fill="${accent ? PALETTE.warm : PALETTE.paper}" stroke="${accent ? PALETTE.gold : PALETTE.rule}" />`;
}

function figureHeight(figure) {
  const height = Number(figure.height) || HEIGHT;
  if (!ALLOWED_HEIGHTS.has(height)) {
    throw new Error(`unsupported figure height ${figure.height}`);
  }
  return height;
}

function takeItems(figure, cap, compactCap = 5) {
  const items = figure.items || [];
  if (items.length > compactCap && figureHeight(figure) === 280) {
    throw new Error("height 420 or 560 required for more than 5 items");
  }
  return items.slice(0, cap);
}

function renderFlow(figure, id) {
  const height = figureHeight(figure);
  const items = takeItems(figure, 8);
  const count = Math.max(items.length, 1);
  const gap = 34;
  const x0 = 36;
  const y = 102;
  const h = height === 280 ? 132 : height - y - 32;
  const w = (WIDTH - 72 - gap * (count - 1)) / count;
  const body = [];
  body.push(arrowDefs(id));
  items.forEach((item, index) => {
    const x = x0 + index * (w + gap);
    if (index > 0) {
      body.push(`<path d="M ${x - gap + 5} ${y + h / 2} H ${x - 8}" fill="none" stroke="${PALETTE.mark}" stroke-width="2" marker-end="url(#${id}-arrow)" />`);
    }
    body.push(panel(x, y, w, h, index === items.length - 1));
    body.push(`<text class="step" x="${x + 16}" y="${y + 24}">${String(index + 1).padStart(2, "0")}</text>`);
    body.push(textLines({ x: x + 16, y: y + 53, value: itemLabel(item), cls: "label", limit: Math.max(12, Math.floor(w / 8.5)), maxLines: 2 }));
    body.push(textLines({ x: x + 16, y: y + 94, value: itemDetail(item), cls: "body", limit: Math.max(15, Math.floor(w / 7.4)), maxLines: 2 }));
  });
  return body.join("\n  ");
}

function renderComparison(figure) {
  const items = takeItems(figure, 5);
  const count = Math.max(items.length, 2);
  const gap = 18;
  const x0 = 36;
  const y = 101;
  const h = 142;
  const w = (WIDTH - 72 - gap * (count - 1)) / count;
  const body = [];
  items.forEach((item, index) => {
    const x = x0 + index * (w + gap);
    body.push(panel(x, y, w, h, index === items.length - 1));
    body.push(`<rect x="${x}" y="${y}" width="5" height="${h}" fill="${index === items.length - 1 ? PALETTE.mark : PALETTE.gold}" />`);
    body.push(textLines({ x: x + 20, y: y + 36, value: itemLabel(item), cls: "label", limit: Math.floor(w / 8), maxLines: 2 }));
    body.push(textLines({ x: x + 20, y: y + 85, value: itemDetail(item), cls: "body", limit: Math.floor(w / 7.2), maxLines: 3 }));
  });
  return body.join("\n  ");
}

function renderStack(figure) {
  const height = figureHeight(figure);
  const items = takeItems(figure, 9);
  const x = 205;
  const w = 880;
  const y0 = 94;
  const gap = 8;
  const area = height === 280 ? 154 : height - y0 - 32;
  const h = Math.min(42, (area - gap * Math.max(items.length - 1, 0)) / Math.max(items.length, 1));
  const body = [];
  items.forEach((item, index) => {
    const y = y0 + index * (h + gap);
    body.push(`<text class="step" x="36" y="${y + h / 2 + 5}">${String(index + 1).padStart(2, "0")}</text>`);
    body.push(panel(x, y, w, h, index === 0));
    body.push(`<text class="label" x="${x + 18}" y="${y + h / 2 + 5}">${xml(itemLabel(item))}</text>`);
    body.push(`<text class="body" x="${x + w - 18}" y="${y + h / 2 + 5}" text-anchor="end">${xml(itemDetail(item))}</text>`);
  });
  return body.join("\n  ");
}

function renderFork(figure, id) {
  const height = figureHeight(figure);
  const items = takeItems(figure, 8, 6);
  const source = figure.source || figure.root || { label: figure.question || "OBSERVED SIGNAL", detail: figure.prompt || "Choose the next discriminating branch" };
  const body = [arrowDefs(id)];
  const sx = 36, sy = height === 280 ? 119 : 110, sw = 250, sh = height === 280 ? 104 : Math.min(140, height - 160);
  body.push(panel(sx, sy, sw, sh, true));
  body.push(textLines({ x: sx + 18, y: sy + 38, value: itemLabel(source), cls: "label", limit: 24, maxLines: 2 }));
  body.push(textLines({ x: sx + 18, y: sy + 79, value: itemDetail(source), cls: "body", limit: 28, maxLines: 2 }));
  const tx = 410, tw = 674;
  const gap = 9;
  const area = height === 280 ? 144 : height - 96 - 32;
  const th = (area - gap * Math.max(items.length - 1, 0)) / Math.max(items.length, 1);
  items.forEach((item, index) => {
    const ty = 96 + index * (th + gap);
    const targetY = ty + th / 2;
    body.push(`<path d="M ${sx + sw} ${sy + sh / 2} C 345 ${sy + sh / 2}, 345 ${targetY}, ${tx - 10} ${targetY}" fill="none" stroke="${PALETTE.mark}" stroke-width="1.8" marker-end="url(#${id}-arrow)" />`);
    body.push(panel(tx, ty, tw, th));
    body.push(`<text class="label" x="${tx + 16}" y="${targetY + 5}">${xml(itemLabel(item))}</text>`);
    body.push(`<text class="body" x="${tx + tw - 16}" y="${targetY + 5}" text-anchor="end">${xml(itemDetail(item))}</text>`);
  });
  return body.join("\n  ");
}

function renderTimeline(figure, id) {
  const height = figureHeight(figure);
  const items = takeItems(figure, 8, 6);
  const count = Math.max(items.length, 1);
  const left = 58, right = 1062, y = height === 280 ? 155 : 94 + Math.round((height - 110) / 2);
  const step = count === 1 ? 0 : (right - left) / (count - 1);
  const body = [arrowDefs(id), `<path d="M ${left} ${y} H ${right}" stroke="${PALETTE.rule}" stroke-width="3" marker-end="url(#${id}-arrow)" />`];
  items.forEach((item, index) => {
    const x = left + index * step;
    const above = index % 2 === 0;
    body.push(`<circle cx="${x}" cy="${y}" r="8" fill="${index === items.length - 1 ? PALETTE.mark : PALETTE.gold}" stroke="${PALETTE.paper}" stroke-width="3" />`);
    body.push(textLines({ x, y: above ? y - 36 : y + 37, value: itemLabel(item), cls: "label", anchor: "middle", limit: 18, maxLines: 2, lineHeight: 17 }));
    body.push(textLines({ x, y: above ? y - 73 : y + 75, value: itemDetail(item), cls: "body", anchor: "middle", limit: 21, maxLines: 2, lineHeight: 17 }));
  });
  return body.join("\n  ");
}

function renderMatrix(figure) {
  const columns = (figure.columns || []).slice(0, 5);
  const rows = (figure.rows || []).slice(0, 5);
  const x = 36, y = 94, w = 1048, h = 154;
  const colCount = Math.max(columns.length, rows.reduce((n, row) => Math.max(n, Array.isArray(row) ? row.length : 0), 0), 1);
  const rowCount = Math.max(rows.length + (columns.length ? 1 : 0), 1);
  const cw = w / colCount, rh = h / rowCount;
  const body = [`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${PALETTE.paper}" stroke="${PALETTE.rule}" />`];
  for (let c = 1; c < colCount; c++) body.push(`<path d="M ${x + c * cw} ${y} V ${y + h}" stroke="${PALETTE.rule}" />`);
  for (let r = 1; r < rowCount; r++) body.push(`<path d="M ${x} ${y + r * rh} H ${x + w}" stroke="${PALETTE.rule}" />`);
  if (columns.length) {
    body.push(`<rect x="${x}" y="${y}" width="${w}" height="${rh}" fill="${PALETTE.warm}" />`);
    columns.forEach((value, c) => body.push(textLines({ x: x + c * cw + 12, y: y + rh / 2 + 5, value, cls: "micro", limit: Math.floor(cw / 8), maxLines: 1 })));
  }
  rows.forEach((row, r) => {
    const values = Array.isArray(row) ? row : row.cells || [];
    const yy = y + (r + (columns.length ? 1 : 0)) * rh;
    values.slice(0, colCount).forEach((value, c) => body.push(textLines({ x: x + c * cw + 12, y: yy + rh / 2 + 5, value, cls: c === 0 ? "label" : "body", limit: Math.floor(cw / 8), maxLines: 1 })));
  });
  return body.join("\n  ");
}

function renderThread(figure, id) {
  const height = figureHeight(figure);
  const items = figure.items || [];
  if (items.length < 2 || items.length > 8) {
    throw new Error("thread requires 2–8 items");
  }
  if (items.length > 5 && height === 280) {
    throw new Error("height 420 or 560 required for more than 5 items");
  }
  const n = items.length;
  const y0 = 94;
  const rowH = (height - 110) / n;
  const gap = 8;
  const panelH = rowH - gap;
  const body = [arrowDefs(id)];
  items.forEach((item, index) => {
    const y = y0 + index * rowH;
    const midY = y + panelH / 2 + 5;
    body.push(`<text class="step" x="36" y="${midY}">${String(index + 1).padStart(2, "0")}</text>`);
    body.push(panel(88, y, 996, panelH, index === n - 1));
    body.push(`<text class="label" x="108" y="${midY}">${xml(itemLabel(item))}</text>`);
    body.push(`<text class="body" x="1064" y="${midY}" text-anchor="end">${xml(itemDetail(item))}</text>`);
    if (index < n - 1) {
      body.push(`<path d="M 52 ${y + panelH} V ${y + rowH}" fill="none" stroke="${PALETTE.mark}" stroke-width="2" marker-end="url(#${id}-arrow)" />`);
    }
  });
  return body.join("\n  ");
}

function renderCycle(figure, id) {
  const height = figureHeight(figure);
  if (height !== 420 && height !== 560) {
    throw new Error("cycle requires height 420 or 560");
  }
  const items = figure.items || [];
  if (items.length !== 4 && items.length !== 5) {
    throw new Error("cycle requires 4 or 5 items");
  }
  const n = items.length;
  const bw = 236;
  const bh = 78;
  const cx = WIDTH / 2;
  const cy = 94 + (height - 110) / 2;
  const rx = 360;
  const ry = height === 420 ? 118 : 176;
  const body = [arrowDefs(id)];
  const boxes = items.map((item, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI / n);
    return {
      item,
      index,
      angle,
      x: Math.round(cx + rx * Math.cos(angle) - bw / 2),
      y: Math.round(cy + ry * Math.sin(angle) - bh / 2)
    };
  });
  boxes.forEach((box, index) => {
    const next = boxes[(index + 1) % n];
    const midAngle = box.angle + Math.PI / n;
    const qx = Math.round(cx + (rx + 48) * Math.cos(midAngle));
    const qy = Math.round(cy + (ry + 36) * Math.sin(midAngle));
    const startAngle = box.angle + 0.42;
    const endAngle = next.angle - 0.42;
    const sx = Math.round(cx + rx * Math.cos(startAngle));
    const sy = Math.round(cy + ry * Math.sin(startAngle));
    const ex = Math.round(cx + rx * Math.cos(endAngle));
    const ey = Math.round(cy + ry * Math.sin(endAngle));
    body.push(`<path d="M ${sx} ${sy} Q ${qx} ${qy} ${ex} ${ey}" fill="none" stroke="${PALETTE.mark}" stroke-width="2" marker-end="url(#${id}-arrow)" />`);
    body.push(panel(box.x, box.y, bw, bh, index === n - 1));
    body.push(textLines({ x: box.x + 16, y: box.y + 28, value: itemLabel(box.item), cls: "label", limit: 22, maxLines: 2 }));
    body.push(textLines({ x: box.x + 16, y: box.y + 56, value: itemDetail(box.item), cls: "body", limit: 26, maxLines: 1 }));
  });
  return body.join("\n  ");
}

const RENDERERS = {
  flow: renderFlow,
  comparison: renderComparison,
  stack: renderStack,
  fork: renderFork,
  timeline: renderTimeline,
  matrix: renderMatrix,
  thread: renderThread,
  cycle: renderCycle
};

export const FIGURE_TEMPLATES = Object.freeze(Object.keys(RENDERERS));

export function renderResourceFigure(figure, resourceId) {
  const id = slug(figure.id || `${resourceId}-${figure.role}`);
  const renderer = RENDERERS[figure.template];
  if (!renderer) throw new Error(`${resourceId}: unsupported figure template ${figure.template}`);
  const height = figureHeight(figure);
  const body = renderer(figure, id);
  return `<!-- GENERATED from resources/figures; edit the JSON spec, not this plate. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${WIDTH} ${height}" width="${WIDTH}" height="${height}" role="img" aria-labelledby="${id}-title ${id}-desc">
  <title id="${id}-title">${xml(figure.title)}</title>
  <desc id="${id}-desc">${xml(figure.desc)}</desc>
  <style>
    text { font-family: Inter, "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif; fill: ${PALETTE.ink}; }
    .eyebrow, .step, .micro { font-size: 14px; font-weight: 650; letter-spacing: 1.7px; }
    .eyebrow { fill: ${PALETTE.mark}; }
    .step, .micro { fill: ${PALETTE.faint}; }
    .figure-title { font-size: 22px; font-weight: 600; letter-spacing: -0.2px; }
    .label { font-size: 15px; font-weight: 650; }
    .body { font-size: 14px; font-weight: 430; fill: ${PALETTE.muted}; }
  </style>
  <rect width="${WIDTH}" height="${height}" fill="${PALETTE.paper}" />
  <path d="M 0 0 H ${WIDTH}" stroke="${PALETTE.ink}" stroke-width="4" />
  ${header(figure)}
  ${body}
</svg>
`;
}

export function figureOutputName(figure) {
  return `${path.basename(figure.id)}.svg`;
}
