<script lang="ts">
  import { tick } from "svelte";
  import type { Operation } from "./operation-progress";

  let { operations, ondismiss }: { operations: Operation[]; ondismiss: (id: number) => void } = $props();
  let now = $state(0);
  let progressRegion: HTMLElement | undefined = $state();
  const activeCount = $derived(operations.filter((operation) => operation.phase === "running").length);
  const running = $derived(activeCount > 0);
  const ordered = $derived([...operations].sort((a, b) =>
    Number(b.phase === "running") - Number(a.phase === "running") || b.id - a.id));
  const newestId = $derived(Math.max(0, ...operations.map((operation) => operation.id)));

  // Registered before the template: move focus while the preview is still attached.
  // The page retains a focused operation when pruning terminal history.
  $effect.pre(() => {
    const previews = operations.map((operation) => ({
      id: operation.id,
      visible: operation.phase === "running" && Boolean(operation.preview),
    }));
    const focused = document.activeElement;
    if (!(focused instanceof HTMLTextAreaElement) || !progressRegion?.contains(focused)) return;
    const article = focused.closest("article");
    const preview = previews.find((item) => item.id === Number(article?.dataset.operationId));
    if (article && preview && !preview.visible) article.focus({ preventScroll: true });
  });

  // Reveal a newly requested operation once, never on stream/clock updates.
  function revealNewRequest(node: HTMLElement, id: number) {
    let latest = id;
    return {
      update(nextId: number) {
        if (nextId <= latest) return;
        latest = nextId;
        void tick().then(() => {
          if (node.isConnected && !node.contains(document.activeElement)) node.scrollTop = 0;
        });
      },
    };
  }

  function followAnswer(node: HTMLTextAreaElement, preview: string) {
    let latest = preview;
    let following = true;
    let focused = document.activeElement === node;
    const atEnd = () => node.scrollHeight - node.clientHeight - node.scrollTop <= 2;
    const showLatest = () => {
      const paused = focused || !following;
      node.classList.toggle("atlas-preview-paused", paused);
      if (paused) return;
      // Own the displayed value: even a readonly value write disrupts selection.
      if (node.value !== latest) node.value = latest;
      node.scrollTop = node.scrollHeight;
    };
    const onScroll = () => {
      following = atEnd();
      showLatest();
    };
    const onWheel = (event: WheelEvent) => {
      if (event.deltaY < 0 && node.scrollTop > 0) {
        following = false;
        showLatest();
      }
    };
    const onFocus = () => {
      focused = true;
      showLatest();
    };
    const onBlur = () => {
      focused = false;
      following = atEnd();
      showLatest();
    };
    node.addEventListener("scroll", onScroll);
    node.addEventListener("wheel", onWheel, { passive: true });
    node.addEventListener("focus", onFocus);
    node.addEventListener("blur", onBlur);
    showLatest();
    return {
      update(preview: string) {
        latest = preview;
        showLatest();
      },
      destroy() {
        node.removeEventListener("scroll", onScroll);
        node.removeEventListener("wheel", onWheel);
        node.removeEventListener("focus", onFocus);
        node.removeEventListener("blur", onBlur);
      },
    };
  }
  $effect(() => {
    if (!running) return;
    now = performance.now();
    const timer = window.setInterval(() => { now = performance.now(); }, 250);
    return () => window.clearInterval(timer);
  });
  function duration(milliseconds: number) {
    const seconds = Math.max(0, Math.floor(milliseconds / 1000));
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
</script>

<section bind:this={progressRegion} class="atlas-operations" aria-label="Operation progress" use:revealNewRequest={newestId}>
  <p class="atlas-operation-status"><strong>{activeCount} active {activeCount === 1 ? "operation" : "operations"}</strong> · newest running request first</p>
  {#each ordered as operation (operation.id)}
    <article class="atlas-operation" data-operation-id={operation.id} tabindex="-1" data-phase={operation.phase} aria-label={`${operation.kind}: ${operation.subject}`}>
      <div class="atlas-operation-heading">
        <strong>{operation.kind} · {operation.subject}</strong>
        {#if operation.phase !== "running"}
          <button type="button" class="sc-btn sc-btn--ghost" aria-label={`Dismiss ${operation.kind} for ${operation.subject}`} onclick={() => ondismiss(operation.id)}>Dismiss</button>
        {/if}
      </div>
      <!-- Identity accompanies stage/terminal announcements; clock and stream stay outside. -->
      <p role="status" aria-live="polite" aria-atomic="true" class="atlas-operation-status">
        <span class="sc-visually-hidden">{operation.kind}: {operation.subject}. </span>
        {operation.phase === "running" ? `${operation.stage} · ${operation.message}` : operation.phase === "failed" ? `Failed · ${operation.error}` : `Complete · ${operation.message}`}
      </p>
      <div aria-busy={operation.phase === "running"} class="atlas-operation-work">
        <p class="atlas-operation-metrics">
          <span>{duration((operation.finishedAt ?? now) - operation.startedAt)} elapsed</span>
          {#if operation.analysis}
            <span>{operation.model || "Model not reported yet"}</span>
            <span>{operation.characters.toLocaleString()} output characters</span>
            <span>{operation.activityAt === undefined ? "No model data received yet" : operation.phase === "running" ? `Last model data ${duration(now - operation.activityAt)} ago` : `Last model data at ${duration(operation.activityAt - operation.startedAt)}`}</span>
          {/if}
        </p>
        {#if operation.phase === "running" && operation.preview}
          <div class="atlas-operation-output">
            <p>Provisional streamed answer · last 1,200 characters · not the final result</p>
            <textarea readonly rows="3" aria-label={`Provisional answer for ${operation.kind}: ${operation.subject}`} aria-describedby={`preview-reading-${operation.id}`} use:followAnswer={operation.preview}></textarea>
            <p id={`preview-reading-${operation.id}`} class="atlas-preview-reading">Preview paused for reading · generation continues</p>
          </div>
        {/if}
      </div>
    </article>
  {/each}
</section>
