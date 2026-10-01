export type AtlasPalette = {
  void: string;
  head: string;
  ink: string;
  ink2: string;
  ink3: string;
  gold: string;
  steel: string;
  olive: string;
  signal: string;
  spice: string;
};

const TOKEN_NAMES: Record<keyof AtlasPalette, string> = {
  void: "--sc-void",
  head: "--sc-head",
  ink: "--sc-ink",
  ink2: "--sc-ink-2",
  ink3: "--sc-ink-3",
  gold: "--sc-gold",
  steel: "--sc-steel",
  olive: "--sc-olive",
  signal: "--sc-signal",
  spice: "--sc-spice",
};

/** Resolve Sirocco tokens, including forced-colors system colors, to concrete CSS colors. */
export function readAtlasPalette(root: HTMLElement): AtlasPalette {
  const span = document.createElement("span");
  span.setAttribute("aria-hidden", "true");
  span.style.position = "absolute";
  span.style.pointerEvents = "none";
  root.appendChild(span);
  const style = getComputedStyle(span);
  const palette = {} as AtlasPalette;
  for (const key of Object.keys(TOKEN_NAMES) as (keyof AtlasPalette)[]) {
    span.style.color = `var(${TOKEN_NAMES[key]})`;
    palette[key] = style.color;
  }
  span.remove();
  return palette;
}
