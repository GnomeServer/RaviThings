<script lang="ts">
  import AtlasIcon from "./AtlasIcon.svelte";
  import type { EntitySummary } from "./entity-insights";
  import type { RiskResult } from "../../ui/src/risk";

  let { entity, summary, risk, busy, error, pinned, mapReady, footprint, onopen, onclear, oninspect, onnearby, onpin, onfootprint }: {
    entity: { kind: string; id: string; name: string; lat: number; lon: number };
    summary: EntitySummary;
    risk: RiskResult | null;
    busy: boolean;
    error: string;
    pinned: boolean;
    mapReady: boolean;
    footprint: string;
    onopen: () => void;
    onclear: () => void;
    oninspect: () => void;
    onnearby: () => void;
    onpin: () => void;
    onfootprint: () => void;
  } = $props();
  const contractor = $derived(entity.kind === "contractor");
  const sourceErrors = $derived(summary.sources.filter((source) => source.state === "error").length);
</script>

<section class="entity-card" aria-label="Selected entity on map" aria-busy={busy}>
  <div class="entity-card__eyebrow">
    <span><span class="entity-card__locator" aria-hidden="true"></span>Selected {contractor ? "contractor" : "facility"}</span>
    <button id="atlas-selection-clear" class="sc-icon-btn" type="button" aria-label="Clear selection" onclick={onclear}><AtlasIcon name="close" /></button>
  </div>
  <button id="atlas-selection-chip" class="entity-card__title" type="button" onclick={onopen} aria-label={`Open dossier for ${entity.name}`}>{entity.name}<AtlasIcon name="arrow-right" /></button>
  <p class="entity-card__location">{summary.location || `${entity.lat.toFixed(4)}, ${entity.lon.toFixed(4)}`}</p>
  <div class="entity-card__details">
    {#if busy}
      <p class="entity-card__note" role="status">Loading catalog evidence…</p>
    {:else if error}
      <p class="entity-card__warning">Evidence unavailable. Open the dossier to retry.</p>
    {:else}
      {#if summary.category}<p class="entity-card__category">{summary.category}</p>{/if}
      {#if contractor}
        <div class="entity-card__exposure">
          <span class="entity-card__note">Catalog exposure</span>
          {#if risk}<span class="entity-card__score" data-severity={risk.severity}><strong>{risk.score}</strong><span>/100 · {risk.severity}</span></span>{:else}<span class="entity-card__note">Not assessed</span>{/if}
        </div>
        {#if risk}<div class="entity-card__meter" aria-hidden="true"><span data-severity={risk.severity} style:width={`${risk.score}%`}></span></div>{/if}
        <dl class="entity-card__metrics">
          <div><dt>Federal obligation</dt><dd>{summary.obligation}</dd></div>
          <div><dt>Hosts observed</dt><dd>{summary.hosts}</dd></div>
          <div><dt>Recorded CVEs</dt><dd>{summary.cves}</dd></div>
        </dl>
        <p class="entity-card__note entity-card__provenance">{summary.collectedCount}/{summary.sourceCount} sources collected{#if summary.latestEvidence} · Latest {summary.latestEvidence}{/if}</p>
        {#if summary.domainMismatch}<p class="entity-card__warning"><AtlasIcon name="alert" />Domain mismatch · review source evidence</p>
        {:else if sourceErrors}<p class="entity-card__warning">{sourceErrors} source {sourceErrors === 1 ? "error" : "errors"} · evidence is incomplete</p>{/if}
        <p class="entity-card__caveat">Recorded indicators, not a live security assessment.</p>
      {:else}
        {#if summary.operator}<p class="entity-card__note">Operated by {summary.operator}</p>{/if}
        {#if summary.address}<p class="entity-card__note">{summary.address}</p>{/if}
      {/if}
    {/if}
    <button id="atlas-building-chip" class="entity-card__footprint" type="button" onclick={onfootprint}><AtlasIcon name="mission" /><span>Building footprint</span><span>{footprint}</span><AtlasIcon name="chevron-right" /></button>
  </div>
  <div class="entity-card__actions">
    <button class="sc-btn entity-card__inspect" type="button" disabled={!mapReady} onclick={oninspect}><AtlasIcon name="eye" />Inspect</button>
    <button class="sc-btn sc-btn--ghost" type="button" onclick={onnearby}>Nearby</button>
    <button class="sc-btn sc-btn--ghost" type="button" onclick={onpin} aria-label={pinned ? "Update pin in Case" : "Pin entity to Case"}><AtlasIcon name={pinned ? "check" : "archive"} />{pinned ? "Pinned" : "Pin"}</button>
  </div>
</section>

<style>
  .entity-card { width: 336px; max-width: 100%; border: 1px solid var(--sc-line-2); border-top: 2px solid var(--sc-gold); border-radius: 6px; background: var(--sc-deck); box-shadow: 0 8px 28px var(--sc-scrim); color: var(--sc-ink); overflow: hidden; }
  .entity-card__eyebrow { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 8px 0 16px; }
  .entity-card__eyebrow > span { display: flex; align-items: center; gap: 8px; color: var(--sc-gold); font: 10px var(--sc-font-mono); letter-spacing: .09em; text-transform: uppercase; }
  .entity-card__eyebrow :global(.sc-icon-btn) { min-width: 34px; min-height: 34px; }
  .entity-card__locator { width: 7px; height: 7px; border: 1px solid currentColor; box-shadow: 0 0 0 3px var(--sc-gold-2); border-radius: 50%; }
  .entity-card__title { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; width: 100%; min-height: 34px; padding: 0 16px; border: 0; background: transparent; color: var(--sc-head); font: 500 17px/1.35 var(--sc-font-display); text-align: left; overflow-wrap: anywhere; }
  .entity-card__title :global(svg) { width: 16px; height: 16px; flex: 0 0 auto; margin-top: 4px; color: var(--sc-gold); }
  .entity-card__location { padding: 4px 16px 10px; margin: 0; font-size: 11px; color: var(--sc-ink-2); }
  .entity-card__details { padding: 0 16px; }
  .entity-card__category { margin: 0 0 12px; font: 10px var(--sc-font-mono); color: var(--sc-ink-2); }
  .entity-card__exposure { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .entity-card__score { display: flex; align-items: baseline; gap: 5px; color: var(--sc-gold); }
  .entity-card__score strong { font: 500 26px/1 var(--sc-font-display); }
  .entity-card__score > span { font-size: 10px; text-transform: capitalize; }
  .entity-card__score[data-severity="critical"] { color: var(--sc-signal-ink); }
  .entity-card__meter { height: 3px; margin: 8px 0 14px; background: var(--sc-deck-3); }
  .entity-card__meter > span { display: block; height: 100%; background: var(--sc-gold); }
  .entity-card__meter > span[data-severity="critical"] { background: var(--sc-signal); }
  .entity-card__metrics { display: grid; grid-template-columns: 1.25fr 1fr 1fr; gap: 10px; margin: 0 0 12px; }
  .entity-card__metrics > div { min-width: 0; }
  .entity-card__metrics dt { font-size: 10px; line-height: 1.5; color: var(--sc-ink-2); }
  .entity-card__metrics dd { margin: 4px 0 0; font: 500 19px var(--sc-font-display); font-variant-numeric: tabular-nums; }
  .entity-card__note { color: var(--sc-ink-2); font-size: 11px; line-height: 1.5; margin: 0; overflow-wrap: anywhere; }
  .entity-card__provenance { font-size: 10px; }
  .entity-card__warning { display: flex; align-items: flex-start; gap: 6px; margin: 8px 0; color: var(--sc-gold); font-size: 11px; line-height: 1.5; }
  .entity-card__warning :global(svg) { width: 14px; height: 14px; flex: 0 0 auto; margin-top: 1px; }
  .entity-card__caveat { font-size: 10px; color: var(--sc-ink-2); margin: 5px 0 10px; line-height: 1.5; }
  .entity-card__footprint { width: 100%; display: flex; gap: 7px; align-items: center; min-height: 34px; padding: 8px 0; border: 0; border-top: 1px solid var(--sc-line); background: transparent; font: 10px var(--sc-font-ui); color: var(--sc-ink-2); text-align: left; }
  .entity-card__footprint > span:nth-of-type(2) { margin-left: auto; color: var(--sc-gold); }
  .entity-card__footprint :global(svg) { width: 13px; height: 13px; flex: 0 0 auto; }
  .entity-card__actions { display: flex; align-items: center; gap: 4px; padding: 9px 12px; border-top: 1px solid var(--sc-line); background: var(--sc-deck-2); }
  .entity-card__actions :global(.sc-btn) { min-height: 34px; font-size: 11px; flex: 1; padding-inline: 9px; }
  .entity-card__inspect { background: var(--sc-gold); color: var(--sc-void); border-color: var(--sc-gold); }
  button:focus-visible { outline: 2px solid var(--sc-gold); outline-offset: -2px; }
  @container (max-width: 660px) { .entity-card { width: 290px; } .entity-card__details { display: none; } .entity-card__title { font-size: 14px; } }
  @container (max-height: 500px) { .entity-card__details { display: none; } .entity-card__title { font-size: 14px; } }
  @container (max-height: 300px) { .entity-card { width: clamp(180px, calc(100cqw - 188px), 320px); } .entity-card__eyebrow { padding-top: 0; } .entity-card__eyebrow > span { font-size: 9px; } .entity-card__title { font-size: 12px; display: block; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; min-height: 24px; } .entity-card__title :global(svg), .entity-card__location, .entity-card__actions { display: none; } }
  @media (pointer: coarse) { .entity-card__actions :global(.sc-btn), .entity-card__eyebrow :global(.sc-icon-btn), .entity-card__footprint, .entity-card__title { min-height: 44px; } }
  @media (forced-colors: active) { .entity-card { box-shadow: none; border-color: CanvasText; background: Canvas; } .entity-card__inspect { background: ButtonFace; color: ButtonText; border: 1px solid ButtonText; } .entity-card__meter > span { background: Highlight; } }
</style>
