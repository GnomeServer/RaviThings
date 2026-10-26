<script module lang="ts">
  export type PaletteItem = {
    id: string;
    group: "Actions" | "Entities";
    label: string;
    detail: string;
  };
</script>

<script lang="ts">
  import AtlasIcon from "./AtlasIcon.svelte";

  let { open, query, loading, error, items, onquery, onchoose, onclose }: {
    open: boolean;
    query: string;
    loading: boolean;
    error: string;
    items: PaletteItem[];
    onquery: (value: string) => void;
    onchoose: (id: string) => void;
    onclose: () => void;
  } = $props();

  let dialogEl: HTMLDialogElement;
  let inputEl: HTMLInputElement;
  let highlighted = $state(-1);
  let opener: HTMLElement | null = null;
  let choosing = false;
  let backdropDown = false;

  $effect(() => {
    if (!dialogEl) return;
    if (open && !dialogEl.open) {
      const active = document.activeElement;
      opener = active instanceof HTMLElement && active !== document.body ? active : null;
      dialogEl.showModal();
      inputEl?.focus();
    } else if (!open && dialogEl.open) {
      dialogEl.close();
    }
  });

  $effect(() => {
    query;
    highlighted = open && items.length ? 0 : -1;
  });

  $effect(() => {
    if (open && highlighted >= 0) {
      dialogEl?.querySelector(`#atlas-palette-option-${highlighted}`)?.scrollIntoView({ block: "nearest" });
    }
  });

  const activeDescendant = $derived(open && highlighted >= 0 && highlighted < items.length
    ? `atlas-palette-option-${highlighted}` : undefined);

  function choose(id: string) {
    if (!dialogEl?.open) return;
    // The native close event is queued; keep this flag until that event arrives.
    choosing = true;
    dialogEl.close();
    onchoose(id);
  }

  function closed() {
    if (choosing) {
      choosing = false;
      return;
    }
    onclose();
    queueMicrotask(() => {
      const target = opener?.isConnected ? opener : document.getElementById("atlas-search-trigger");
      target?.focus();
    });
  }

  function dismiss() {
    if (dialogEl?.open) dialogEl.close();
  }

  function outside(event: PointerEvent): boolean {
    if (event.target !== dialogEl) return false;
    const bounds = dialogEl.getBoundingClientRect();
    return event.clientX < bounds.left || event.clientX > bounds.right
      || event.clientY < bounds.top || event.clientY > bounds.bottom;
  }

  function keydown(event: KeyboardEvent) {
    if (!open) return;
    const count = items.length;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (count) highlighted = (highlighted + (event.key === "ArrowDown" ? 1 : -1) + count) % count;
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      highlighted = count ? (event.key === "Home" ? 0 : count - 1) : -1;
    } else if (event.key === "Enter") {
      event.preventDefault();
      const item = items[highlighted];
      if (item) choose(item.id);
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      dismiss();
    }
  }
</script>

<dialog bind:this={dialogEl} class="sc-palette atlas-palette" aria-label="Find entity or command"
  onclose={closed} oncancel={(event) => { event.preventDefault(); dismiss(); }}
  onpointerdown={(event) => { backdropDown = outside(event); }}
  onpointerup={(event) => { if (backdropDown && outside(event)) dismiss(); backdropDown = false; }}>
  <div class="sc-palette__input-row">
    <AtlasIcon name="search" />
    <label for="atlas-palette-query" class="sc-visually-hidden">Find entity or command</label>
    <input bind:this={inputEl} id="atlas-palette-query" class="sc-palette__input" type="text"
      role="combobox" aria-autocomplete="list" aria-controls="atlas-palette-list"
      aria-expanded={open} aria-activedescendant={activeDescendant}
      placeholder="Name, UEI, CAGE, or command" autocomplete="off" spellcheck="false" value={query}
      oninput={(event) => onquery(event.currentTarget.value)} onkeydown={keydown} />
    <button class="sc-icon-btn" type="button" aria-label="Close search" onclick={dismiss}><AtlasIcon name="close" /></button>
  </div>
  <div id="atlas-palette-list" class="sc-palette__list" role="listbox" aria-label="Actions and entities" aria-busy={loading}>
    {#each items as item, index (item.id)}
      {#if index === 0 || items[index - 1].group !== item.group}
        <div class="sc-label atlas-palette-group" role="presentation">{item.group}</div>
      {/if}
      <button type="button" class="sc-palette__item" role="option" tabindex="-1"
        id={`atlas-palette-option-${index}`} aria-selected={highlighted === index}
        onpointerdown={(event) => event.preventDefault()} onclick={() => choose(item.id)}>
        <span class="sc-palette__text"><strong>{item.label}</strong><span class="sc-palette__meta">{item.detail}</span></span>
      </button>
    {/each}
  </div>
  {#if loading}<p class="atlas-palette-state" role="status">Searching</p>
  {:else if error}<p class="atlas-palette-state" role="alert">{error}</p>
  {:else if items.length === 0}<p class="atlas-palette-state" role="status">No matches</p>{/if}
  <div class="sc-palette__footer"><span>↑ ↓ Navigate · Enter Open</span><span>Esc Close</span></div>
</dialog>

<style>
  .atlas-palette {
    position: fixed;
    inset: 16px 0 auto;
    width: min(640px, calc(100% - 24px));
    max-height: calc(100dvh - 32px);
    background: var(--sc-deck-2);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    overflow: hidden;
  }
  .sc-palette__input-row { height: auto; min-height: 60px; padding: 8px 12px; gap: 8px; }
  .sc-palette__input { min-height: 34px; font-size: 13px; }
  .sc-icon-btn { min-width: 34px; min-height: 34px; }
  .sc-palette__list { min-height: 0; max-height: none; flex: 1 1 auto; padding: 6px; }
  .atlas-palette-group { padding: 10px 10px 6px; }
  .sc-palette__item { height: auto; min-height: 52px; padding: 10px; white-space: normal; }
  .sc-palette__text { overflow: visible; overflow-wrap: anywhere; }
  .sc-palette__text strong { display: block; line-height: 1.5; }
  .sc-palette__meta { display: block; color: var(--sc-ink-2); font: 12px/1.5 var(--sc-font-ui); white-space: normal; }
  .atlas-palette-state { padding: 12px 16px; margin: 0; }
  .sc-palette__footer { min-height: 36px; height: auto; white-space: normal; flex-wrap: wrap; padding: 8px 12px; }
  @media (pointer: coarse) {
    .sc-icon-btn, .sc-palette__input { min-height: 44px; }
    .sc-icon-btn { min-width: 44px; }
  }
  @media (forced-colors: active) {
    .atlas-palette { background: Canvas; color: CanvasText; border-color: CanvasText; }
    .sc-palette__item[aria-selected="true"] { background: Highlight; color: HighlightText; }
    .sc-palette__item[aria-selected="true"] * { color: inherit; }
  }
</style>
