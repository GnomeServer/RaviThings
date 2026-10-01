<script lang="ts">
  import { onMount, tick } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { computeRiskScore, RISKY_PORTS } from "../../ui/src/risk";
  import DossierExposure from "../lib/DossierExposure.svelte";
  import AtlasIcon from "../lib/AtlasIcon.svelte";
  import CommandPalette from "../lib/CommandPalette.svelte";
  type PaletteItem = { id: string; group: "Actions" | "Entities"; label: string; detail: string };

  import { mountGlobe, type ContractorPoint, type Flight } from "../lib/globe";
  import { readAtlasPalette } from "../lib/atlas-theme";
  import { lookupBuildingFootprint, type BuildingFootprint } from "../lib/building-footprint";
  import "../app.css";

  type Status = {
    contractors: number;
    dams: number;
    datacenters: number;
    skipped: number;
    gevMissing: string | null;
    error: string | null;
  };
  type Hit = { kind: string; id: string; name: string; subtitle: string; lat: number; lon: number };
  type Nearby = {
    facilities: { id: string; kind: string; name: string; distanceKm: number; lat: number; lon: number }[];
    contractors: { id: number; name: string; lat: number | null; lon: number | null; riskScore: number; riskSeverity: string; distanceKm: number }[];
  };
  type Cve = { id: string; contractorCount: number; maxScore: number | null; severity: string; contractorIds: number[] };
  type DamRisk = {
    damId: string;
    damName: string;
    lat: number;
    lon: number;
    contractors: { id: number; name: string; riskScore: number; distanceKm: number }[];
  };
  type FeedLayer = { ageSec: number | null; keySet: boolean; enabled: boolean; items: unknown[] };
  type Feeds = {
    flights: FeedLayer & { items: Flight[] };
    quakes: FeedLayer & { items: { id: string; mag: number; lat: number; lon: number }[] };
    satellites: FeedLayer & { items: { name: string; lat: number; lon: number; altM: number }[] };
    installations: FeedLayer & { items: { id: string; name: string; lat: number; lon: number }[] };
    ais: FeedLayer & { items: { id: string; name: string; lat: number; lon: number; heading: number }[] };
    firms: FeedLayer & { items: { id: string; name: string; lat: number; lon: number }[] };
  };
  type LensName = "all" | "energy" | "digital" | "defense";
  type LayerName = "ais" | "firms" | "flights" | "quakes" | "sats" | "install";
  type PanelName = "explore" | "cve" | "dams" | "keys" | "ask" | "sites" | "case" | "layers";
  type Surface = PanelName | "dossier";
  type ActiveFilter = { source: "cve" | "ask" | "sites"; label: string; total: number; contractorIds: number[] | null };
  type AskHit = {
    kind: string;
    id: string;
    name: string;
    subtitle: string;
    lat: number;
    lon: number;
    riskScore: number;
    riskSeverity: string;
    distanceKm: number | null;
    count: number;
  };
  type AskResult = { total: number; hits: AskHit[] };
  type Pin = { kind: "contractor" | "facility"; id: string; name: string; lat: number; lon: number; note: string };
  type ThreadLink = {
    id: string;
    kind: "contractor" | "dam" | "datacenter";
    name: string;
    lat: number;
    lon: number;
    distanceKm: number;
  };
  type Command = { id: string; label: string; run: () => void };
  type KeyField = "google_maps_api_key" | "openrouter_api_key" | "ais_api_key" | "firms_api_key" | "jev_api_key";

  const SETUP = "Set GOOGLE_MAPS_API_KEY, or add Keychain item service=google-maps-api account=api-key. Map Tiles API must be enabled.";
  const LENSES: LensName[] = ["all", "energy", "digital", "defense"];
  const LENS_LABEL: Record<LensName, string> = {
    all: "All sectors",
    energy: "Energy",
    digital: "Digital",
    defense: "Defense",
  };
  const KEY_FIELDS: { field: KeyField; label: string }[] = [
    { field: "google_maps_api_key", label: "Google Maps" },
    { field: "openrouter_api_key", label: "OpenRouter" },
    { field: "ais_api_key", label: "AIS" },
    { field: "firms_api_key", label: "FIRMS" },
    { field: "jev_api_key", label: "Jev" },
  ];
  const RADII = [25, 50, 100];

  let status = $state<Status | null>(null);
  let catalogState = $state<"loading" | "ready" | "error">("loading");
  let catalogError = $state("");
  let mapState = $state<"loading" | "ready" | "missing-key" | "error">("loading");
  let mapError = $state("");
  let disposed = false;
  let bootGeneration = 0;
  let catalogToken = 0;
  let feedInFlight = false;
  let feedError = $state("");
  let cameraError = $state("");
  let feedStartError = $state("");
  let layerError = $state<Partial<Record<LayerName, string>>>({});
  let layerBusy = $state<Partial<Record<LayerName, boolean>>>({});
  let lens = $state<LensName>("all");
  let activeSurface = $state<Surface | null>(null);
  let returnSurface = $state<PanelName | null>(null);
  let sheetExpanded = $state(false);
  let sheetLayout = $state(false);
  let reducedMotion = $state(false);
  let orbitActive = $state(false);
  let activeFilter = $state<ActiveFilter | null>(null);
  let askLabel = $state("");
  let returnFocusId = "rail-map";
  let focusWorkspaceOnOpen = false;
  let cves = $state<Cve[]>([]);
  let dams = $state<DamRisk[]>([]);
  let searchQuery = $state("");
  let searchHits = $state<Hit[]>([]);
  let tab = $state<"exposure" | "nearby" | "kill">("exposure");
  let selected = $state<{ kind: string; id: string; name: string; lat: number; lon: number } | null>(null);
  let payload = $state<Record<string, unknown> | null>(null);
  let payloadBusy = $state(false);
  let buildingState = $state<"idle" | "loading" | "ready" | "unavailable" | "error">("idle");
  let building = $state<BuildingFootprint | null>(null);
  let buildingMessage = $state("");
  let buildingAttempt = $state(0);
  let buildingFrameBusy = $state(false);
  let buildingFrameError = $state("");
  let buildingController: AbortController | null = null;
  let googleMapsKey = "";
  let nearby = $state<Nearby | null>(null);
  let nearbyToken = 0;
  let nearbyBusy = $state(false);
  let nearbyError = $state("");
  let nearbySource = $state<"query" | "dam-summary">("query");
  let feedFocusError = $state("");
  let radius = $state(50);
  let threadKind = $state<null | "kin" | "dam" | "datacenter">(null);
  let threadCard = $state<ThreadLink | null>(null);
  let orbitReady = $state(false);
  let killChain = $state<any | null>(null);
  let killError = $state<string>("");
  let killBusy = $state(false);
  let openrouter = $state<boolean | null>(null);
  let openStep = $state<number | null>(null);
  let stepDetail = $state<any | null>(null);
  let stepDetailError = $state<string>("");
  let stepDetailBusy = $state(false);
  let stepToken = 0;
  let selectionToken = 0;
  let searchToken = 0;
  let searchTimer = 0;
  let feeds = $state<Feeds | null>(null);
  let aisOn = $state(false);
  let firmsOn = $state(false);
  let flightsOn = $state(false);
  let quakesOn = $state(false);
  let satsOn = $state(false);
  let installsOn = $state(false);
  let keyStatus = $state<{ google: boolean; openrouter: boolean; ais: boolean; firms: boolean; jev: boolean } | null>(null);
  let keyDrafts = $state({ google_maps_api_key: "", openrouter_api_key: "", ais_api_key: "", firms_api_key: "", jev_api_key: "" });
  let keyNote = $state("");
  let keyBusy = $state(false);
  let keyError = $state("");
  let keyStatusError = $state("");
  let mapsChanged = $state(false);
  let hover = $state<{ name: string; x: number; y: number; severity: string } | null>(null);
  let hoverEl = $state<HTMLDivElement | undefined>(undefined);
  let askResult = $state<AskResult | null>(null);
  let askNote = $state("");
  let askError = $state("");
  let askToken = 0;
  let points = $state<ContractorPoint[]>([]);
  let pins = $state<Pin[]>([]);
  let caseError = $state("");
  let caseNote = $state("");
  let confirmClearCase = $state(false);
  let selectionError = $state("");
  let searchError = $state("");
  let utc = $state(new Date().toISOString().slice(11, 19));
  let workspaceTitleEl = $state<HTMLElement | undefined>(undefined);
  let workspaceBodyEl = $state<HTMLDivElement | undefined>(undefined);

  let paletteOpen = $state(false);
  let searchBusy = $state(false);
  let cvesBusy = $state(false);
  let cvesError = $state("");
  let cvesToken = 0;
  let damsBusy = $state(false);
  let damsError = $state("");
  let damsToken = 0;
  const creditLine = $derived(dataCredit(feeds, aisOn, firmsOn));

  const risk = $derived(payload && !payloadBusy && !selectionError && selected?.kind === "contractor" ? computeRiskScore(payload) : null);
  const briefStep = $derived.by(() => {
    const steps = Array.isArray(killChain?.steps) ? killChain.steps : [];
    if (openStep !== null) {
      const open = steps.find((step: { step?: number }) => step.step === openStep);
      if (open) return open;
    }
    return steps[0] ?? null;
  });
  const shownHits = $derived(searchHits.slice(0, 8));
  const showSheetThread = $derived(threadCard !== null && sheetLayout && activeSurface === "dossier" && tab === "nearby");
  const showMapThread = $derived(threadCard !== null && !(sheetLayout && activeSurface !== null));
  const showMapChrome = $derived(!(sheetExpanded && activeSurface !== null));
  const workspaceTitle = $derived.by(() => {
    if (activeSurface === "dossier") return selected?.name ?? "Dossier";
    if (activeSurface === "explore") return "Explore";
    if (activeSurface === "cve") return "Shared CVEs";
    if (activeSurface === "dams") return "Dams at risk";
    if (activeSurface === "keys") return "Settings";
    if (activeSurface === "ask") return askLabel || "Ask";
    if (activeSurface === "sites") return "Critical sites";
    if (activeSurface === "case") return "Case";
    if (activeSurface === "layers") return "Layers";
    return "";
  });
  const mapReady = $derived(mapState === "ready");
  const mapStateLabel = $derived(mapState === "missing-key" ? "Map key missing" : `Map ${mapState}`);
  const bootStatus = $derived(`Catalog ${catalogState} · ${mapStateLabel}`);
  const activeLayerCount = $derived([flightsOn, quakesOn, satsOn, installsOn, aisOn, firmsOn].filter(Boolean).length);
  const LAYERS: { id: LayerName; feed: keyof Feeds; label: string; provider: string }[] = [
    { id: "flights", feed: "flights", label: "ADS-B flights", provider: "adsb.lol" },
    { id: "quakes", feed: "quakes", label: "Earthquakes", provider: "USGS" },
    { id: "sats", feed: "satellites", label: "Satellites", provider: "CelesTrak" },
    { id: "install", feed: "installations", label: "Installations", provider: "OpenStreetMap / Open Infrastructure Map" },
    { id: "ais", feed: "ais", label: "AIS vessels", provider: "Datalastic" },
    { id: "firms", feed: "firms", label: "FIRMS fires", provider: "NASA FIRMS" },
  ];
  const commands = $derived.by(() => {
    const raw = searchQuery.trim();
    const q = raw.toLowerCase();
    if (!q) return [] as Command[];
    const direct = directAsk(raw);
    if (direct) return [direct];
    const all: Command[] = [
      { id: "lens-all", label: "All sectors", run: () => setLens("all") },
      { id: "lens-energy", label: "Energy", run: () => setLens("energy") },
      { id: "lens-digital", label: "Digital", run: () => setLens("digital") },
      { id: "lens-defense", label: "Defense", run: () => setLens("defense") },
      { id: "show-mobility", label: "Show mobility overlays", run: () => showMobilityContext() },
      { id: "layer-ais", label: "AIS", run: () => toggleLayer("ais") },
      { id: "layer-firms", label: "FIRMS", run: () => toggleLayer("firms") },
      { id: "layer-flights", label: "ADS-B", run: () => toggleLayer("flights") },
      { id: "layer-quakes", label: "Quakes", run: () => toggleLayer("quakes") },
      { id: "layer-sats", label: "Satellites", run: () => toggleLayer("sats") },
      { id: "layer-installs", label: "Installations", run: () => toggleLayer("install") },
      { id: "panel-cve", label: "Shared CVEs", run: () => { void loadCves(); } },
      { id: "panel-dams", label: "Dams at risk", run: () => { void loadDams(); } },
      { id: "panel-keys", label: "Settings", run: () => setPanel("keys") },
      { id: "panel-sites", label: "Critical sites", run: openCriticalSites },
      { id: "panel-case", label: "Open case", run: () => setPanel("case") },
      { id: "ask-risk-critical", label: "risk critical", run: () => { void runAsk("risk", "critical"); } },
      { id: "ask-risk-high", label: "risk high", run: () => { void runAsk("risk", "high"); } },
      { id: "ask-risk-medium", label: "risk medium", run: () => { void runAsk("risk", "medium"); } },
      { id: "ask-risk-low", label: "risk low", run: () => { void runAsk("risk", "low"); } },
      { id: "ask-onprem", label: "on-prem", run: () => { void runAsk("onprem", ""); } },
      { id: "ask-dmarc-missing", label: "dmarc missing", run: () => { void runAsk("dmarc", "not_set"); } },
      { id: "ask-dmarc-none", label: "dmarc none", run: () => { void runAsk("dmarc", "none"); } },
      { id: "ask-dmarc-quarantine", label: "dmarc quarantine", run: () => { void runAsk("dmarc", "quarantine"); } },
      { id: "ask-dmarc-reject", label: "dmarc reject", run: () => { void runAsk("dmarc", "reject"); } },
      { id: "ask-near-25", label: "near 25", run: () => askNear(25) },
      { id: "ask-near-50", label: "near 50", run: () => askNear(50) },
      { id: "ask-near-100", label: "near 100", run: () => askNear(100) },
    ];
    return all.filter((cmd) => cmd.label.toLowerCase().includes(q)).slice(0, 6);
  });
  let globe: Awaited<ReturnType<typeof mountGlobe>> | null = null;
  let root = $state<HTMLDivElement | undefined>(undefined);
  let creditEl = $state<HTMLDivElement | undefined>(undefined);

  function dataCredit(snapshot: Feeds | null, ais: boolean, firms: boolean) {
    let line = "© OpenStreetMap contributors · Open Infrastructure Map · adsb.lol · USGS · CelesTrak";
    if (ais && snapshot?.ais.keySet) line += " · Datalastic";
    if (firms && snapshot?.firms.keySet) line += " · FIRMS";
    return line;
  }

  function railCurrent(item: "map" | "explore" | "case" | "layers" | "keys") {
    if (item === "map") return activeSurface === null || activeSurface === "dossier";
    if (item === "explore") return activeSurface === "explore" || activeSurface === "cve" || activeSurface === "dams" || activeSurface === "ask" || activeSurface === "sites";
    if (item === "case") return activeSurface === "case";
    if (item === "layers") return activeSurface === "layers";
    return activeSurface === "keys";
  }

  function ageLevel(layer: FeedLayer | undefined) {
    if (!layer || layer.ageSec == null) return "";
    if (layer.ageSec > 1800) return "bad";
    if (layer.ageSec >= 300) return "warn";
    return "";
  }

  async function focusHeading() {
    await tick();
    workspaceTitleEl?.focus();
  }

  function consumeWorkspaceFocus() {
    if (!focusWorkspaceOnOpen) return;
    focusWorkspaceOnOpen = false;
    void focusHeading();
  }

  function setPanel(next: PanelName | null): void {
    hover = null;
    if (next !== activeSurface) sheetExpanded = false;
    const opening = next !== null && next !== activeSurface;
    activeSurface = next;
    if (opening) consumeWorkspaceFocus();
  }

  function showDossier(): void {
    hover = null;
    if (!selected) return;
    if (activeSurface !== "dossier") {
      sheetExpanded = false;
    }
    activeSurface = "dossier";
    consumeWorkspaceFocus();
  }

  function hideWorkspace(): void {
    const focusId = returnFocusId;
    setPanel(null);
    void tick().then(() => {
      const origin = document.getElementById(focusId);
      (origin?.getClientRects().length ? origin : document.getElementById("rail-map"))?.focus();
    });
  }

  function backWorkspace(): void {
    const next = returnSurface;
    sheetExpanded = false;
    activeSurface = next;
    void tick().then(() => {
      if (next) workspaceTitleEl?.focus();
      else document.getElementById("rail-map")?.focus();
    });
  }

  function rememberReturn() {
    if (activeSurface !== "dossier") returnSurface = activeSurface;
  }

  function onOrbitChange(active: boolean) {
    orbitActive = active;
  }

  function clearBuildingFootprint() {
    buildingController?.abort();
    buildingController = null;
    globe?.setBuildingFootprint(null);
    building = null;
    buildingState = "idle";
    buildingMessage = "";
    buildingFrameBusy = false;
    buildingFrameError = "";
  }

  async function frameBuilding() {
    if (!globe || buildingState !== "ready") return;
    const epoch = selectionToken;
    const mounted = globe;
    buildingFrameBusy = true;
    buildingFrameError = "";
    orbitReady = false;
    sheetExpanded = false;
    try {
      await tick();
      if (disposed || epoch !== selectionToken) return;
      await mounted.frameBuildingFootprint();
    } catch (error) {
      if (!disposed && epoch === selectionToken) buildingFrameError = errorText(error);
    } finally {
      if (!disposed && epoch === selectionToken) buildingFrameBusy = false;
    }
  }

  $effect(() => {
    const target = selected;
    const state = mapState;
    const waitingForAddress = payloadBusy;
    const address = typeof payload?.address === "string" ? payload.address.trim() : null;
    buildingAttempt;
    building = null;
    if (!target) {
      buildingState = "idle";
      buildingMessage = "";
      return;
    }
    if (state !== "ready" || !globe) {
      buildingState = state === "loading" ? "loading" : "unavailable";
      buildingMessage = state === "loading" ? "Waiting for the map." : "The map must be available to display a building footprint.";
      return;
    }
    buildingState = "loading";
    if (waitingForAddress) {
      buildingMessage = "Waiting for the selected address.";
      return;
    }
    buildingMessage = "Looking up the building with Google Geocoding.";
    const controller = new AbortController();
    buildingController = controller;
    const mounted = globe;
    const epoch = selectionToken;
    void (async () => {
      try {
        const result = await lookupBuildingFootprint(googleMapsKey, { address, lat: target.lat, lon: target.lon }, controller.signal);
        if (disposed || controller.signal.aborted || epoch !== selectionToken) return;
        if (result.status === "ready") {
          mounted.setBuildingFootprint(result.footprint.polygons);
          building = result.footprint;
          buildingState = "ready";
          buildingMessage = address ? "Outline matched to the selected address." : "The building contains the mapped point.";
        } else {
          buildingState = "unavailable";
          buildingMessage = result.message;
        }
      } catch (error) {
        if (disposed || controller.signal.aborted || epoch !== selectionToken) return;
        mounted.setBuildingFootprint(null);
        buildingState = "error";
        buildingMessage = errorText(error);
      }
    })();
    return () => {
      controller.abort();
      if (buildingController === controller) buildingController = null;
      mounted.setBuildingFootprint(null);
    };
  });

  $effect(() => {
    if (activeSurface === "dossier") {
      selected;
      tab;
    } else if (activeSurface === "ask" || activeSurface === "sites") {
      askResult;
      askLabel;
    }
    if (workspaceBodyEl) workspaceBodyEl.scrollTop = 0;
  });

  $effect(() => {
    const hit = hover;
    if (!hit || !hoverEl || !root) return;
    hoverEl.style.left = `${Math.max(8, Math.min(hit.x + 12, root.clientWidth - hoverEl.offsetWidth - 8))}px`;
    hoverEl.style.top = `${Math.max(8, Math.min(hit.y + 12, root.clientHeight - hoverEl.offsetHeight - 8))}px`;
  });

  async function refreshKeyStatus() {
    const epoch = bootGeneration;
    try {
      const value = await invoke<typeof keyStatus>("api_key_status");
      if (disposed || epoch !== bootGeneration) return;
      keyStatus = value;
      keyStatusError = "";
    } catch (error) {
      if (disposed || epoch !== bootGeneration) return;
      keyStatus = null;
      keyStatusError = `Key status unavailable: ${errorText(error)}`;
    }
  }

  async function refreshOpenRouter() {
    const epoch = bootGeneration;
    try {
      const value = await invoke<boolean>("openrouter_configured");
      if (!disposed && epoch === bootGeneration) openrouter = value;
    } catch {
      if (!disposed && epoch === bootGeneration) openrouter = null;
    }
  }

  function keyReady(field: KeyField) {
    if (!keyStatus) return null;
    if (field === "google_maps_api_key") return keyStatus.google;
    if (field === "openrouter_api_key") return keyStatus.openrouter;
    if (field === "ais_api_key") return keyStatus.ais;
    if (field === "firms_api_key") return keyStatus.firms;
    return keyStatus.jev;
  }

  async function saveKeys() {
    if (keyBusy) return;
    keyBusy = true;
    keyNote = "";
    keyError = "";
    const next: Record<string, string> = {};
    for (const { field } of KEY_FIELDS) {
      if (keyDrafts[field].trim()) next[field] = keyDrafts[field].trim();
    }
    const epoch = bootGeneration;
    try {
      await invoke("save_api_keys", { keys: next });
      if (disposed || epoch !== bootGeneration) return;
      keyDrafts = { google_maps_api_key: "", openrouter_api_key: "", ais_api_key: "", firms_api_key: "", jev_api_key: "" };
      mapsChanged = mapsChanged || !!next.google_maps_api_key;
      keyNote = "Saved";
      void refreshKeyStatus();
      void refreshOpenRouter();
      void refreshFeeds();
    } catch {
      if (!disposed && epoch === bootGeneration) keyError = "Keys could not be saved. Drafts have been kept.";
    } finally {
      if (!disposed && epoch === bootGeneration) keyBusy = false;
    }
  }

  function ageLabel(layer: FeedLayer | undefined) {
    if (!layer || layer.ageSec == null) return "No data";
    const sec = layer.ageSec;
    const text = sec < 90 ? `${sec}s` : sec < 3600 ? `${Math.round(sec / 60)}m` : `${Math.round(sec / 3600)}h`;
    return text;
  }

  function setLens(next: LensName) {
    lens = next;
    globe?.setLens(next);
  }

  async function toggleLayer(layer: LayerName) {
    if (!mapReady) {
      setPanel("layers");
      return;
    }
    layerError[layer] = "";
    if (layer === "ais" || layer === "firms") {
      if (layerBusy[layer]) return;
      const prior = layer === "ais" ? aisOn : firmsOn;
      const next = !prior;
      if (next && layerKey(layer) !== true) {
        setPanel("layers");
        return;
      }
      if (layer === "ais") aisOn = next;
      else firmsOn = next;
      globe?.setLayer(layer, next);
      layerBusy[layer] = true;
      const epoch = bootGeneration;
      try {
        await invoke("set_feed_enabled", { feed: layer, enabled: next });
        if (disposed || epoch !== bootGeneration) return;
        if (next && feeds) {
          if (layer === "ais") globe?.setVessels(feeds.ais.items);
          else globe?.setFires(feeds.firms.items);
        }
      } catch (error) {
        if (disposed || epoch !== bootGeneration) return;
        if (layer === "ais") aisOn = prior;
        else firmsOn = prior;
        globe?.setLayer(layer, prior);
        layerError[layer] = `Change failed: ${errorText(error)}`;
      } finally {
        if (!disposed && epoch === bootGeneration) layerBusy[layer] = false;
      }
      return;
    }
    if (layer === "flights") {
      flightsOn = !flightsOn;
      globe?.setLayer("flights", flightsOn);
      if (flightsOn && feeds) globe?.setFlights(feeds.flights.items);
      return;
    }
    if (layer === "quakes") {
      quakesOn = !quakesOn;
      globe?.setLayer("quakes", quakesOn);
      if (quakesOn && feeds) globe?.setQuakes(feeds.quakes.items);
      return;
    }
    if (layer === "sats") {
      satsOn = !satsOn;
      globe?.setLayer("sats", satsOn);
      if (satsOn && feeds) globe?.setSats(feeds.satellites.items);
      return;
    }
    installsOn = !installsOn;
    globe?.setLayer("install", installsOn);
    if (installsOn && feeds) globe?.setInstalls(feeds.installations.items);
  }

  function showMobilityContext(): void {
    if (!mapReady) {
      setPanel("layers");
      return;
    }
    setLens("all");
    if (!flightsOn) toggleLayer("flights");
    if (!quakesOn) toggleLayer("quakes");
    if (!satsOn) toggleLayer("sats");
  }

  function layerEnabled(layer: LayerName) {
    return layer === "ais" ? aisOn : layer === "firms" ? firmsOn : layer === "flights" ? flightsOn : layer === "quakes" ? quakesOn : layer === "sats" ? satsOn : installsOn;
  }

  function layerKey(layer: "ais" | "firms"): boolean | null {
    return keyStatus?.[layer] ?? feeds?.[layer].keySet ?? null;
  }

  async function refreshFeeds() {
    if (feedInFlight || disposed) return;
    feedInFlight = true;
    const epoch = bootGeneration;
    try {
      const snapshot = await invoke<Feeds>("feed_snapshot");
      if (disposed || epoch !== bootGeneration) return;
      feeds = snapshot;
      feedError = "";
      if (!mapReady) return;
      if (flightsOn) globe?.setFlights(snapshot.flights.items);
      if (quakesOn) globe?.setQuakes(snapshot.quakes.items);
      if (satsOn) globe?.setSats(snapshot.satellites.items);
      if (installsOn) globe?.setInstalls(snapshot.installations.items);
      if (aisOn) globe?.setVessels(snapshot.ais.items);
      if (firmsOn) globe?.setFires(snapshot.firms.items);
    } catch (error) {
      if (!disposed && epoch === bootGeneration) feedError = `Refresh failed: ${errorText(error)}`;
    } finally {
      if (!disposed && epoch === bootGeneration) feedInFlight = false;
    }
  }

  function clearFilter(): void {
    askToken += 1;
    activeFilter = null;
    globe?.setCveFilter(null);
  }

  function selectCve(cve: Cve) {
    clearFilter();
    activeFilter = {
      source: "cve",
      label: cve.id,
      total: cve.contractorCount,
      contractorIds: cve.contractorIds,
    };
    setLens("all");
    globe?.setCveFilter(cve.contractorIds);
    if (mapReady) globe?.flyToIds(cve.contractorIds);
  }

  function queryLabel(question: string, value: string, radiusKm?: number) {
    if (question === "risk") return `risk ${value}`;
    if (question === "port") return `port ${value}`;
    if (question === "cve") return value.toUpperCase().startsWith("CVE-") ? value.toUpperCase() : value;
    if (question === "near") return `within ${radiusKm ?? ""} km of ${selected?.name ?? "selection"}`;
    if (question === "sites") return "Critical sites";
    if (question === "onprem") return "on-prem";
    if (question === "dmarc") return `dmarc ${value}`;
    if (question === "obligation") return `obligation ${value}`;
    return `${question} ${value}`.trim();
  }

  function noteAsk(note: string) {
    clearFilter();
    askResult = null;
    askError = "";
    askNote = note;
    askLabel = "";
    setPanel("ask");
  }

  async function loadCves() {
    const token = ++cvesToken;
    cvesBusy = true;
    cvesError = "";
    cves = [];
    setPanel("cve");
    try {
      const res = await invoke<{ cves: Cve[] }>("shared_exposure");
      if (token !== cvesToken) return;
      cves = res.cves;
    } catch (e) {
      if (token !== cvesToken) return;
      cvesError = errorText(e);
    } finally {
      if (token === cvesToken) cvesBusy = false;
    }
  }

  async function loadDams() {
    const token = ++damsToken;
    damsBusy = true;
    damsError = "";
    dams = [];
    setPanel("dams");
    try {
      const res = await invoke<DamRisk[]>("onprem_near_dams", { radiusKm: 50 });
      if (token !== damsToken) return;
      dams = res;
    } catch (e) {
      if (token !== damsToken) return;
      damsError = errorText(e);
    } finally {
      if (token === damsToken) damsBusy = false;
    }
  }

  function clearFind() {
    searchToken += 1;
    window.clearTimeout(searchTimer);
    searchQuery = "";
    searchHits = [];
    searchBusy = false;
    searchError = "";
  }

  function runSearch(query = searchQuery) {
    searchQuery = query;
    searchError = "";
    window.clearTimeout(searchTimer);
    if (!query.trim() || directAsk(query)) {
      searchToken += 1;
      searchHits = [];
      searchBusy = false;
      return;
    }
    searchToken += 1;
    const token = searchToken;
    searchHits = [];
    searchBusy = true;
    searchTimer = window.setTimeout(() => {
      void invoke<Hit[]>("search_catalog", { query }).then((hits) => {
        if (token !== searchToken) return;
        searchHits = hits;
        searchBusy = false;
      }).catch(() => {
        if (token !== searchToken) return;
        searchHits = [];
        searchError = "Search failed";
        searchBusy = false;
      });
    }, 120);
  }

  async function openFind() {
    returnFocusId = "atlas-search-trigger";
    paletteOpen = true;
  }

  function getPaletteItems(): PaletteItem[] {
    const q = searchQuery.trim();
    if (!q) {
      return [
        { id: "command:ask-risk-critical", group: "Actions", label: "Critical risk", detail: "" },
        { id: "command:panel-cve", group: "Actions", label: "Shared CVEs", detail: "" },
        { id: "command:panel-sites", group: "Actions", label: "Critical sites", detail: "" },
        { id: "command:panel-case", group: "Actions", label: "Open case", detail: "" },
      ];
    }
    const cmds = commands;
    const ents = shownHits;
    const items: PaletteItem[] = [];
    for (const c of cmds) items.push({ id: `command:${c.id}`, group: "Actions", label: c.label, detail: "" });
    for (const h of ents) items.push({ id: `entity:${h.kind}:${h.id}`, group: "Entities", label: h.name, detail: h.subtitle });
    return items;
  }

  function onPaletteQuery(value: string) {
    runSearch(value);
  }

  function onPaletteChoose(id: string) {
    let runner: (() => void) | null = null;
    let hit: Hit | null = null;
    if (id.startsWith("command:")) {
      const cmdId = id.slice(8);
      if (cmdId === "ask-risk-critical") {
        runner = () => { void runAsk("risk", "critical"); };
      } else if (cmdId === "panel-cve") {
        runner = () => { void loadCves(); };
      } else if (cmdId === "panel-sites") {
        runner = openCriticalSites;
      } else if (cmdId === "panel-case") {
        runner = () => setPanel("case");
      } else {
        const found = commands.find((c) => c.id === cmdId);
        if (found) runner = found.run;
      }
    } else if (id.startsWith("entity:")) {
      const key = id.slice(7);
      const found = searchHits.find((h) => `${h.kind}:${h.id}` === key);
      if (found) hit = found;
    }
    paletteOpen = false;
    clearFind();
    void tick().then(async () => {
      returnFocusId = "atlas-search-trigger";
      if (runner) runner();
      else if (hit) void openSelection(hit.kind, hit.id, hit.name, hit.lat, hit.lon, true);
      await tick();
      if (activeSurface) workspaceTitleEl?.focus();
      else document.getElementById("rail-map")?.focus();
    });
  }

  function onPaletteClose() {
    paletteOpen = false;
    clearFind();
  }
  async function loadCatalog() {
    const token = ++catalogToken;
    catalogState = "loading";
    catalogError = "";
    try {
      const nextStatus = await invoke<Status>("ensure_catalog");
      if (disposed || token !== catalogToken) return;
      status = nextStatus;
      const loaded = await invoke<ContractorPoint[]>("catalog_contractors");
      if (disposed || token !== catalogToken) return;
      points = loaded;
      catalogError = nextStatus.error ?? "";
      catalogState = catalogError ? "error" : "ready";
      if (mapReady) {
        globe?.setContractors(loaded);
        globe?.setLens(lens);
        globe?.setCveFilter(activeFilter?.contractorIds ?? null);
        if (selected) globe?.select(selected.kind, selected.id);
      }
    } catch (error) {
      if (disposed || token !== catalogToken) return;
      catalogError = errorText(error);
      catalogState = "error";
    }
  }

  function plotName(name: string) {
    const trimmed = name.trim().toLowerCase();
    return trimmed !== "" && trimmed !== "unnamed" && trimmed !== "data not collected" && trimmed !== "not collected";
  }

  function threadLinks(): ThreadLink[] {
    if (!nearby || !threadKind) return [];
    const chip = threadKind;
    const rows: ThreadLink[] = chip === "kin"
      ? nearby.contractors.flatMap((hit) => {
          if (hit.lat == null || hit.lon == null || !Number.isFinite(hit.lat) || !Number.isFinite(hit.lon) || !plotName(hit.name)) return [];
          const link: ThreadLink = { id: String(hit.id), kind: "contractor", name: hit.name, lat: hit.lat, lon: hit.lon, distanceKm: hit.distanceKm };
          return [link];
        })
      : nearby.facilities.flatMap((hit) => {
          if (hit.kind !== chip || !Number.isFinite(hit.lat) || !Number.isFinite(hit.lon) || !plotName(hit.name)) return [];
          const link: ThreadLink = { id: hit.id, kind: chip, name: hit.name, lat: hit.lat, lon: hit.lon, distanceKm: hit.distanceKm };
          return [link];
        });
    rows.sort((a, b) => a.distanceKm - b.distanceKm);
    const links = rows.slice(0, 8);
    const extra = threadCard;
    const preview = extra && rows.find((row) => row.id === extra.id && row.kind === extra.kind);
    if (preview && !links.some((link) => link.id === preview.id && link.kind === preview.kind)) links.push(preview);
    return links;
  }

  function drawThreads() {
    if (!selected || !threadKind || !nearby || !globe || !mapReady) return;
    globe.setThreads(
      { lat: selected.lat, lon: selected.lon, kind: selected.kind },
      threadLinks(),
    );
  }

  function clearThreads() {
    if (document.activeElement?.closest(".atlas-thread-card")) restorePreviewFocus();
    threadKind = null;
    threadCard = null;
    globe?.clearThreads();
  }

  function setThreadChip(next: "kin" | "dam" | "datacenter") {
    if (threadKind === next) {
      clearThreads();
      return;
    }
    if (threadCard && (threadCard.kind === "contractor" ? "kin" : threadCard.kind) !== next) threadCard = null;
    threadKind = next;
    drawThreads();
  }

  function trace(link: ThreadLink) {
    if (!plotName(link.name) || !Number.isFinite(link.lat) || !Number.isFinite(link.lon)) return;
    const focusPreview = focusWorkspaceOnOpen;
    const epoch = selectionToken;
    threadCard = link;
    threadKind = link.kind === "contractor" ? "kin" : link.kind;
    drawThreads();
    sheetExpanded = false;
    frameEndpoint(link);
    void tick().then(() => {
      if (disposed || epoch !== selectionToken || threadCard?.id !== link.id || threadCard.kind !== link.kind) return;
      if (focusPreview) document.getElementById("atlas-thread-open")?.focus();
      else if (showSheetThread) document.querySelector(".atlas-sheet-thread")?.scrollIntoView({ block: "start" });
    });
  }

  function openThreadCard() {
    const card = threadCard;
    if (!card) return;
    if (card.kind === "contractor") void openSelection("contractor", card.id, card.name, card.lat, card.lon, true);
    else void openSelection("facility", card.id, card.name, card.lat, card.lon, true);
  }

  function dismissThreadCard() {
    if (document.activeElement?.closest(".atlas-thread-card")) restorePreviewFocus();
    threadCard = null;
    drawThreads();
  }

  function restorePreviewFocus() {
    const epoch = selectionToken;
    void tick().then(() => {
      if (disposed || epoch !== selectionToken) return;
      (activeSurface === "dossier" ? document.getElementById(`atlas-tab-${tab}`) : document.getElementById("atlas-selection-chip"))?.focus();
    });
  }

  function frameEndpoint(point: { lat: number; lon: number }) {
    sheetExpanded = false;
    const epoch = selectionToken;
    void tick().then(() => requestAnimationFrame(() => {
      if (!disposed && epoch === selectionToken && mapReady) globe?.frame("site", point.lon, point.lat);
    }));
  }

  function fitConnections() {
    if (!selected) return;
    sheetExpanded = false;
    const origin = { lat: selected.lat, lon: selected.lon };
    const links = threadLinks();
    const epoch = selectionToken;
    void tick().then(() => requestAnimationFrame(() => {
      if (!disposed && epoch === selectionToken && mapReady) globe?.flyToPositions([origin, ...links]);
    }));
  }

  type NearbyRow = Omit<ThreadLink, "lat" | "lon"> & { lat: number | null; lon: number | null; riskScore: number | null; riskSeverity: string };
  const nearbyGroups = $derived.by(() => {
    const contractors: NearbyRow[] = (nearby?.contractors ?? []).map((row) => ({ ...row, id: String(row.id), kind: "contractor" }));
    const facilities: NearbyRow[] = (nearby?.facilities ?? []).flatMap((row) => {
      if (row.kind !== "dam" && row.kind !== "datacenter") return [];
      return [{ ...row, kind: row.kind, riskScore: null, riskSeverity: "" }];
    });
    return [
      { label: "Contractors", rows: contractors },
      { label: "Dams", rows: facilities.filter((row) => row.kind === "dam") },
      { label: "Data centers", rows: facilities.filter((row) => row.kind === "datacenter") },
    ].map((group) => ({ ...group, rows: group.rows.sort((a, b) => a.distanceKm - b.distanceKm) }));
  });
  const connectionCount = $derived(threadLinks().length);

  function plotIssue(row: NearbyRow) {
    if (!plotName(row.name)) return "Unnamed — cannot plot";
    if (row.lat === null || row.lon === null || !Number.isFinite(row.lat) || !Number.isFinite(row.lon)) return "No coordinates";
    return "";
  }

  function previewNearby(row: NearbyRow) {
    if (plotIssue(row) || row.lat === null || row.lon === null) return;
    trace({ ...row, lat: row.lat, lon: row.lon });
  }

  function focusFeed(contractorId: number | null) {
    const epoch = selectionToken;
    feedFocusError = "";
    void invoke("set_feed_focus", { contractorId }).catch((error) => {
      if (epoch === selectionToken) feedFocusError = `Feed focus failed: ${errorText(error)}`;
    });
  }

  async function loadPayload(kind: string, id: string, epoch: number) {
    try {
      const value = kind === "contractor"
        ? await invoke<Record<string, unknown> | null>("contractor_payload", { id: Number(id) })
        : await invoke<Record<string, unknown> | null>("facility_payload", { id });
      if (epoch === selectionToken) payload = value;
    } catch (error) {
      if (epoch === selectionToken) selectionError = errorText(error);
    } finally {
      if (epoch === selectionToken) payloadBusy = false;
    }
  }

  function clearKill() {
    killChain = null;
    killError = "";
    killBusy = false;
    openStep = null;
    stepDetail = null;
    stepDetailError = "";
    stepDetailBusy = false;
    stepToken += 1;
  }

  function openSelection(kind: string, id: string, name: string, lat: number, lon: number, site = true) {
    clearThreads();
    clearBuildingFootprint();
    const epoch = ++selectionToken;
    nearbyToken += 1;
    rememberReturn();
    selected = { kind, id, name, lat, lon };
    selectionError = "";
    payload = null;
    payloadBusy = true;
    nearby = null;
    nearbyError = "";
    nearbySource = "query";
    tab = "exposure";
    orbitReady = false;
    clearKill();
    sheetExpanded = false;
    activeSurface = "dossier";
    consumeWorkspaceFocus();
    if (mapReady) globe?.select(kind, id);
    focusFeed(kind === "contractor" ? Number(id) : null);
    void loadPayload(kind, id, epoch);
    void setRadius(50);
    if (site) frameEndpoint({ lat, lon });
  }

  function closeSelection() {
    const dossierVisible = activeSurface === "dossier";
    const restoreClearFocus = document.activeElement?.id === "atlas-selection-clear";
    clearThreads();
    clearBuildingFootprint();
    selectionToken += 1;
    nearbyToken += 1;
    selected = null;
    payload = null;
    payloadBusy = false;
    selectionError = "";
    nearby = null;
    nearbyBusy = false;
    nearbyError = "";
    orbitReady = false;
    clearKill();
    globe?.stopOrbit();
    globe?.clearSelect();
    globe?.clearEllipse();
    focusFeed(null);
    if (dossierVisible) {
      activeSurface = returnSurface;
      sheetExpanded = false;
      void tick().then(() => {
        if (activeSurface) workspaceTitleEl?.focus();
        else document.getElementById("rail-map")?.focus();
      });
    } else if (restoreClearFocus) {
      void tick().then(() => (document.getElementById("atlas-filter-chip") ?? document.getElementById("rail-map"))?.focus());
    }
  }

  async function setRadius(next: number) {
    radius = next;
    if (!selected) return;
    const target = selected;
    const epoch = selectionToken;
    const token = ++nearbyToken;
    nearby = null;
    nearbySource = "query";
    nearbyError = "";
    nearbyBusy = true;
    threadCard = null;
    globe?.clearThreads();
    if (mapReady) globe?.setEllipse(target.lon, target.lat, next);
    try {
      const rows = await invoke<Nearby>("nearby", { targetKind: target.kind, id: target.id, radiusKm: next });
      if (epoch !== selectionToken || token !== nearbyToken) return;
      nearby = rows;
      drawThreads();
    } catch (error) {
      if (epoch === selectionToken && token === nearbyToken) nearbyError = errorText(error);
    } finally {
      if (epoch === selectionToken && token === nearbyToken) nearbyBusy = false;
    }
  }

  function openDam(dam: DamRisk) {
    clearThreads();
    clearBuildingFootprint();
    const epoch = ++selectionToken;
    nearbyToken += 1;
    rememberReturn();
    selected = { kind: "facility", id: dam.damId, name: dam.damName, lat: dam.lat, lon: dam.lon };
    selectionError = "";
    payload = null;
    payloadBusy = true;
    nearbyBusy = false;
    nearbyError = "";
    nearbySource = "dam-summary";
    tab = "nearby";
    orbitReady = false;
    radius = 50;
    clearKill();
    sheetExpanded = false;
    activeSurface = "dossier";
    consumeWorkspaceFocus();
    focusFeed(null);
    nearby = {
      facilities: [],
      contractors: dam.contractors.map((contractor) => {
        const point = points.find((item) => item.id === contractor.id);
        return {
          id: contractor.id,
          name: contractor.name,
          riskScore: contractor.riskScore,
          riskSeverity: point?.riskSeverity ?? "",
          distanceKm: contractor.distanceKm,
          lat: point ? point.lat : null,
          lon: point ? point.lon : null,
        };
      }),
    };
    if (mapReady) {
      globe?.select("facility", dam.damId);
      globe?.setEllipse(dam.lon, dam.lat, 50);
    }
    frameEndpoint({ lat: dam.lat, lon: dam.lon });
    void loadPayload("facility", dam.damId, epoch);
  }

  function fly(mode: "region" | "site" | "inspect" | "orbit") {
    if (!mapReady) { setPanel("layers"); return; }
    if (!selected) return;
    sheetExpanded = false;
    const target = selected;
    const epoch = selectionToken;
    if (mode !== "orbit") orbitReady = mode === "inspect";
    void tick().then(() => requestAnimationFrame(() => {
      if (disposed || epoch !== selectionToken) return;
      if (mode === "orbit") globe?.orbit(target.lon, target.lat);
      else globe?.frame(mode, target.lon, target.lat);
    }));
  }

  function resetView() {
    sheetExpanded = false;
    if (!mapReady) { setPanel("layers"); return; }
    void tick().then(() => requestAnimationFrame(() => {
      if (!disposed) globe?.flyToIds(points.map((point) => point.id));
    }));
  }

  async function generateKill() {
    if (!selected || selected.kind !== "contractor" || !openrouter) return;
    const token = selectionToken;
    const id = Number(selected.id);
    killBusy = true;
    killChain = null;
    killError = "";
    openStep = null;
    stepDetail = null;
    stepDetailError = "";
    stepDetailBusy = false;
    stepToken += 1;
    try {
      let result: any = await invoke("kill_chain", { contractorIndex: id });
      if (token !== selectionToken) return;
      if (typeof result === "string") {
        try { result = JSON.parse(result); } catch {}
      }
      if (result && typeof result.steps === "string") {
        try { result.steps = JSON.parse(result.steps); } catch {}
      }
      if (token !== selectionToken) return;
      if (result && result.error) {
        killError = String(result.error);
      } else if (result && (Array.isArray(result.steps) || result.summary)) {
        killChain = result;
      } else {
        killError = "No kill chain data";
      }
    } catch (error) {
      if (token !== selectionToken) return;
      killError = error instanceof Error ? error.message : String(error);
    } finally {
      if (token === selectionToken) killBusy = false;
    }
  }

  async function toggleStep(stepNum: number, step: any) {
    if (openStep === stepNum) {
      stepToken += 1;
      openStep = null;
      stepDetail = null;
      stepDetailError = "";
      stepDetailBusy = false;
      return;
    }
    openStep = stepNum;
    stepDetail = null;
    stepDetailError = "";
    stepDetailBusy = true;
    const token = ++stepToken;
    try {
      const detail = await invoke("step_detail", { contractorIndex: Number(selected!.id), step });
      if (token !== stepToken) return;
      stepDetail = detail;
    } catch (error) {
      if (token !== stepToken) return;
      stepDetailError = error instanceof Error ? error.message : String(error);
    } finally {
      if (token === stepToken) stepDetailBusy = false;
    }
  }

  function errorText(error: unknown) {
    if (typeof error === "string") return error;
    if (error instanceof Error) return error.message;
    return String(error);
  }

  function isPin(value: unknown): value is Pin {
    if (!value || typeof value !== "object") return false;
    const row = value as Pin;
    return (row.kind === "contractor" || row.kind === "facility")
      && typeof row.id === "string"
      && typeof row.name === "string"
      && typeof row.lat === "number"
      && Number.isFinite(row.lat)
      && typeof row.lon === "number"
      && Number.isFinite(row.lon)
      && typeof row.note === "string";
  }

  function readCase(): Pin[] {
    try {
      const raw = localStorage.getItem("osint-atlas-case");
      if (!raw) return [];
      const parsed: unknown = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(isPin).slice(-12);
    } catch {
      return [];
    }
  }

  function writeCase(next: Pin[]): boolean {
    caseError = "";
    caseNote = "";
    try {
      localStorage.setItem("osint-atlas-case", JSON.stringify(next));
      pins = next;
      caseNote = "Case saved";
      return true;
    } catch {
      caseError = "Case could not be saved";
      return false;
    }
  }

  function pinSelected(note: string) {
    if (!selected) return;
    if (selected.kind !== "contractor" && selected.kind !== "facility") return;
    const pin: Pin = {
      kind: selected.kind,
      id: selected.id,
      name: selected.name,
      lat: selected.lat,
      lon: selected.lon,
      note,
    };
    const next = [...pins.filter((item) => item.kind !== pin.kind || item.id !== pin.id), pin];
    writeCase(next.length > 12 ? next.slice(next.length - 12) : next);
  }

  function removePin(pin: Pin) {
    writeCase(pins.filter((item) => item.kind !== pin.kind || item.id !== pin.id));
  }

  function clearCase() {
    if (writeCase([])) confirmClearCase = false;
  }

  async function runAsk(question: string, value: string, lat?: number, lon?: number, radiusKm?: number, surface: "ask" | "sites" = "ask") {
    clearFilter();
    const token = ++askToken;
    askNote = "";
    askError = "";
    askResult = null;
    askLabel = queryLabel(question, value, radiusKm);
    setPanel(surface);
    try {
      const result = await invoke<AskResult>("ask_catalog", {
        question,
        value,
        lat: lat ?? null,
        lon: lon ?? null,
        radiusKm: radiusKm ?? null,
      });
      if (token !== askToken) return;
      askResult = result;
      const contractors = result.hits.filter((hit) => hit.kind === "contractor");
      const facilities = result.hits.filter((hit) => hit.kind === "facility");
      const facilityQuery = question === "sites" || (contractors.length === 0 && facilities.length > 0);
      setLens("all");
      if (facilityQuery) {
        activeFilter = { source: surface === "sites" ? "sites" : "ask", label: askLabel, total: result.total, contractorIds: null };
        globe?.setCveFilter(null);
        if (mapReady && facilities.length > 0) globe?.flyToPositions(facilities.map((hit) => ({ lon: hit.lon, lat: hit.lat })));
      } else {
        const ids = contractors.map((hit) => Number(hit.id)).filter((id) => Number.isFinite(id));
        activeFilter = { source: "ask", label: askLabel, total: result.total, contractorIds: ids };
        globe?.setCveFilter(ids);
        if (mapReady && ids.length > 0) globe?.flyToIds(ids);
      }
    } catch (error) {
      if (token !== askToken) return;
      askError = errorText(error);
      activeFilter = null;
      globe?.setCveFilter(null);
    }
  }

  function askNear(radiusKm: number) {
    if (!selected) {
      noteAsk("Select a target first");
      return;
    }
    void runAsk("near", selected.kind === "contractor" ? selected.id : "", selected.lat, selected.lon, radiusKm);
  }

  function openCriticalSites() {
    void runAsk("sites", "datacenter", undefined, undefined, undefined, "sites");
  }

  function directAsk(raw: string): Command | null {
    const port = raw.match(/^port\s+(\d+)$/i);
    if (port) {
      const number = port[1];
      return {
        id: "ask-port",
        label: `port ${number}`,
        run: () => {
          if (!RISKY_PORTS.has(Number(number))) {
            noteAsk("Port not in the risk set");
            return;
          }
          void runAsk("port", number);
        },
      };
    }
    const obligation = raw.match(/^obligation\s+(\d+)$/i);
    if (obligation) {
      return {
        id: "ask-obligation",
        label: `obligation ${obligation[1]}`,
        run: () => { void runAsk("obligation", obligation[1]); },
      };
    }
    const cve = raw.match(/^cve\s+(CVE-\d{4}-\d+)$/i);
    if (cve) {
      const id = cve[1].toUpperCase();
      return {
        id: "ask-cve",
        label: `cve ${id}`,
        run: () => { void runAsk("cve", id); },
      };
    }
    return null;
  }


  onMount(() => {
    disposed = false;
    const generation = ++bootGeneration;
    const current = () => !disposed && generation === bootGeneration;
    pins = readCase();
    const sheetQuery = window.matchMedia("(max-width: 1099px)");
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    sheetLayout = sheetQuery.matches;
    reducedMotion = motionQuery.matches;
    const onSheet = () => {
      hover = null;
      sheetLayout = sheetQuery.matches;
      if (!sheetQuery.matches) sheetExpanded = false;
    };
    const onMotion = () => {
      reducedMotion = motionQuery.matches;
      if (motionQuery.matches) globe?.stopOrbit();
      drawThreads();
    };
    sheetQuery.addEventListener("change", onSheet);
    motionQuery.addEventListener("change", onMotion);
    const onResize = () => { hover = null; };
    const beforeClick = (event: MouseEvent) => {
      focusWorkspaceOnOpen = event.detail === 0 && event.target instanceof Element && !!event.target.closest("button");
    };
    const afterClick = () => { focusWorkspaceOnOpen = false; };
    window.addEventListener("resize", onResize);
    window.addEventListener("click", beforeClick, true);
    window.addEventListener("click", afterClick);
    const clock = window.setInterval(() => {
      utc = new Date().toISOString().slice(11, 19);
    }, 1000);
    let timer = 0;
    void loadCatalog();
    void refreshKeyStatus();
    void refreshOpenRouter();
    void refreshFeeds();
    void (async () => {
      try {
        const key = await invoke<string>("google_maps_key");
        if (!current()) return;
        if (!key) {
          mapState = "missing-key";
          return;
        }
        googleMapsKey = key;
        if (!root || !creditEl) throw new Error("Map container unavailable");
        let cameraReady = false;
        const mounted = await mountGlobe(root, creditEl, key, {
          onSelect: (hit) => {
            if (current()) openSelection(hit.kind, hit.id, hit.name, hit.lat, hit.lon, true);
          },
          onCamera: (cam) => {
            if (!current() || !cameraReady) return;
            void invoke("set_camera", cam).catch((error) => {
              if (current()) cameraError = `Camera focus failed: ${errorText(error)}`;
            });
          },
          onHover: (hit) => { if (current()) hover = hit; },
          onThread: (hit) => {
            if (!current()) return;
            const kind = hit.kind === "dam" || hit.kind === "datacenter" ? hit.kind : "contractor";
            trace({ ...hit, kind });
          },
          onOrbitChange: (active) => { if (current()) onOrbitChange(active); },
        }, readAtlasPalette(root));
        if (!current()) {
          mounted.destroy();
          return;
        }
        globe = mounted;
        if (mounted.tilesetError) {
          mapState = "error";
          mapError = `Google Photorealistic 3D Tiles failed: ${mounted.tilesetError}`;
          return;
        }
        mapState = "ready";
        mounted.setContractors(points);
        mounted.setLens(lens);
        mounted.setCveFilter(activeFilter?.contractorIds ?? null);
        try {
          await invoke("set_camera", { lat: 39.5, lon: -98.5, heightM: 8_000_000, west: -125, south: 24, east: -66, north: 50 });
          if (!current()) return;
          await invoke("start_feeds");
          if (!current()) return;
          timer = window.setInterval(() => { void refreshFeeds(); }, 2000);
        } catch (error) {
          if (current()) feedStartError = `Feed startup failed: ${errorText(error)}`;
        }
        if (!current()) return;
        cameraReady = true;
        if (selected) {
          mounted.select(selected.kind, selected.id);
          mounted.setEllipse(selected.lon, selected.lat, radius);
          drawThreads();
          frameEndpoint(selected);
        }
      } catch (error) {
        if (current()) {
          mapState = "error";
          mapError = errorText(error);
        }
      }
    })();
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        void openFind();
        return;
      }
      if (paletteOpen) return;
      if (event.key === "Escape") {
        if (activeSurface === "dossier" && tab === "kill" && openStep !== null) {
          stepToken += 1;
          openStep = null;
          stepDetail = null;
          stepDetailError = "";
          stepDetailBusy = false;
          return;
        }
        if (threadKind || threadCard) {
          clearThreads();
          return;
        }
        if (activeSurface) {
          hideWorkspace();
          return;
        }
        if (selected) {
          void closeSelection();
          return;
        }
        globe?.stopOrbit();
        return;
      }
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return;
      if (target instanceof HTMLElement && target.isContentEditable) return;
      if (activeSurface === "dossier" && target instanceof HTMLElement && target.closest('[role="tablist"]') && (event.key === "ArrowLeft" || event.key === "ArrowRight" || event.key === "Home" || event.key === "End")) {
        event.preventDefault();
        const order: ("exposure" | "nearby" | "kill")[] = ["exposure", "nearby", "kill"];
        let i = order.indexOf(tab);
        if (event.key === "ArrowRight") i = (i + 1) % 3;
        else if (event.key === "ArrowLeft") i = (i - 1 + 3) % 3;
        else if (event.key === "Home") i = 0;
        else if (event.key === "End") i = 2;
        tab = order[i];
        void tick().then(() => document.getElementById(`atlas-tab-${tab}`)?.focus());
        return;
      }
      if (activeSurface !== "dossier") return;
      if (event.key === "1" || event.key === "2" || event.key === "3") {
        event.preventDefault();
        tab = event.key === "1" ? "exposure" : event.key === "2" ? "nearby" : "kill";
        void tick().then(() => document.getElementById(`atlas-tab-${tab}`)?.focus());
      } else if (event.key === "p") pinSelected("");
      else if (event.key === "f") fly("site");
      else if (event.key === "[" || event.key === "]") {
        const at = RADII.indexOf(radius);
        const dir = event.key === "]" ? 1 : -1;
        void setRadius(RADII[(at + dir + RADII.length) % RADII.length]);
      } else if (tab === "kill" && (event.key === "j" || event.key === "k") && Array.isArray(killChain?.steps) && killChain.steps.length) {
        const steps = killChain.steps as { step: number }[];
        let idx = steps.findIndex((step) => step.step === openStep);
        if (idx < 0) idx = event.key === "j" ? -1 : 0;
        const next = event.key === "j" ? (idx + 1) % steps.length : (idx - 1 + steps.length) % steps.length;
        void toggleStep(steps[next].step, steps[next]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      disposed = true;
      bootGeneration += 1;
      catalogToken += 1;
      selectionToken += 1;
      nearbyToken += 1;
      stepToken += 1;
      searchToken += 1;
      askToken += 1;
      cvesToken += 1;
      damsToken += 1;
      window.removeEventListener("keydown", onKey);
      sheetQuery.removeEventListener("change", onSheet);
      motionQuery.removeEventListener("change", onMotion);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("click", beforeClick, true);
      window.removeEventListener("click", afterClick);
      window.clearInterval(clock);
      window.clearInterval(timer);
      window.clearTimeout(searchTimer);
      buildingController?.abort();
      googleMapsKey = "";
      globe?.destroy();
      globe = null;
    };
  });
</script>

{#snippet threadPreview(placement: "map" | "sheet")}
  {#if threadCard}
    <div class={placement === "map" ? "atlas-map-thread" : "atlas-sheet-thread"}>
      <div class="atlas-thread-card sc-panel">
        <p class="sc-label">Geographic proximity · {threadCard.kind === "datacenter" ? "Data center" : threadCard.kind}</p>
        <p class="atlas-muted"><span class="sc-mono">{threadCard.distanceKm} km</span> from {selected?.name}</p>
        <p>{threadCard.name}</p>
        <div class="atlas-actions">
          <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady} onclick={() => { if (threadCard) frameEndpoint(threadCard); }}>Frame</button>
          <button id="atlas-thread-open" type="button" class="sc-btn sc-btn--secondary" onclick={openThreadCard}>Open dossier</button>
          <button type="button" class="sc-btn sc-btn--ghost" onclick={dismissThreadCard}>Dismiss</button>
        </div>
      </div>
    </div>
  {/if}
{/snippet}

{#snippet cameraActions()}
  <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady || !points.length} onclick={resetView}>Reset view</button>
  {#if selected}
    <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady} onclick={() => fly("region")}>Region</button>
    <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady} onclick={() => fly("site")}>Site</button>
    <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady} onclick={() => fly("inspect")}>Inspect</button>
    <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady || !orbitReady || reducedMotion || orbitActive} onclick={() => fly("orbit")}>Orbit</button>
    <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady || !orbitActive} onclick={() => globe?.stopOrbit()}>Stop</button>
  {/if}
  {#if !mapReady}
    <p class="atlas-muted">Map unavailable</p>
  {:else if reducedMotion}
    <p class="atlas-muted">Orbit is off because reduced motion is on.</p>
  {:else if selected && !orbitReady}
    <p class="atlas-muted">Inspect before Orbit.</p>
  {/if}
{/snippet}

{#snippet reloadMapActions()}
  <p class="atlas-muted">Reload resets the current view; saved case pins remain.</p>
  <button type="button" class="sc-btn sc-btn--secondary" onclick={() => window.location.reload()}>Reload map</button>
{/snippet}

<div class="sc-app atlas-app">
  <a class="sc-skip-link" href="#atlas-main">Skip to map</a>
  <header class="sc-topbar atlas-topbar">
    <div class="sc-brand" aria-label="Starzl Enterprises | OSINT Atlas">
      <span class="sc-brand__dot" aria-hidden="true"></span>
      <span class="sc-brand__name">Starzl Enterprises</span>
      <span class="sc-brand__divider" aria-hidden="true"></span>
      <span class="sc-brand__product">OSINT Atlas</span>
    </div>
    <span class="sc-topbar__spacer"></span>
    <button id="atlas-search-trigger" class="sc-command" type="button" aria-keyshortcuts="Meta+K Control+K" onclick={() => void openFind()}>
      <AtlasIcon name="search" />
      <span class="sc-command__label">Find entity or command</span>
      <kbd class="sc-kbd">⌘K</kbd>
    </button>
    <span class="sc-topbar__spacer"></span>
    <button id="atlas-engine" class="sc-engine" type="button" aria-label={`${bootStatus}. Open Layers`} onclick={() => { returnFocusId = "atlas-engine"; setPanel("layers"); }}>
      <AtlasIcon name="activity" />
      <span class="sc-engine__label">{bootStatus}</span>
    </button>
  </header>
  <div class="sc-body atlas-body">
    <nav class="sc-rail atlas-rail" aria-label="Atlas">
      <button id="rail-map" class="sc-rail__item" type="button" aria-current={railCurrent("map") ? "page" : undefined} onclick={() => { returnFocusId = "rail-map"; hideWorkspace(); }}>
        <AtlasIcon name="mission" class="sc-rail__icon" />
        <span class="sc-rail__label">Map</span>
      </button>
      <button id="rail-explore" class="sc-rail__item" type="button" aria-current={railCurrent("explore") ? "page" : undefined} onclick={() => { returnFocusId = "rail-explore"; setPanel("explore"); }}>
        <AtlasIcon name="research" class="sc-rail__icon" />
        <span class="sc-rail__label">Explore</span>
      </button>
      <button id="rail-case" class="sc-rail__item" type="button" aria-current={railCurrent("case") ? "page" : undefined} onclick={() => { returnFocusId = "rail-case"; setPanel("case"); }}>
        <AtlasIcon name="archive" class="sc-rail__icon" />
        <span class="sc-rail__label">Case <span class="sc-mono">{pins.length}</span></span>
      </button>
      <button id="rail-layers" class="sc-rail__item" type="button" aria-current={railCurrent("layers") ? "page" : undefined} onclick={() => { returnFocusId = "rail-layers"; setPanel("layers"); }}>
        <AtlasIcon name="activity" class="sc-rail__icon" />
        <span class="sc-rail__label">Layers</span>
      </button>
      <button id="rail-keys" class="sc-rail__item" type="button" aria-current={railCurrent("keys") ? "page" : undefined} onclick={() => { returnFocusId = "rail-keys"; setPanel("keys"); }}>
        <AtlasIcon name="settings" class="sc-rail__icon" />
        <span class="sc-rail__label">Settings</span>
      </button>
    </nav>
    <main id="atlas-main" tabindex="-1" class="atlas-main" class:has-workspace={activeSurface !== null} class:sheet-expanded={sheetExpanded && activeSurface !== null}>
      <section class="atlas-stage" aria-label="Geographic map" aria-describedby="atlas-map-desc">
        <p id="atlas-map-desc" class="sc-visually-hidden">Contractor catalog plotted on a geographic map. Search, results, and nearby rows open the same evidence.</p>
        <div id="cesium-root" bind:this={root}></div>
        {#if showMapChrome}
          {#if mapState === "missing-key" || mapState === "error"}
            <div class="atlas-map-notice sc-notice sc-notice--signal" role="alert">
              <AtlasIcon name="alert" class="sc-notice__icon" />
              <div class="sc-notice__body">
                <p class="sc-notice__title">{mapState === "missing-key" ? "Map key missing" : "Map unavailable"}</p>
                <p>{mapState === "missing-key" ? SETUP : mapError}</p>
                <button type="button" class="sc-btn sc-btn--secondary" onclick={() => { returnFocusId = "rail-keys"; setPanel("keys"); }}>Open settings</button>
                {@render reloadMapActions()}
              </div>
            </div>
          {/if}
          <div class="atlas-context">
            {#if status || points.length > 0}
              <div class="atlas-context-row">
                <span>DOE contractor catalog</span>
              </div>
            {/if}
            {#if selected}
              <div class="atlas-context-row">
                <button id="atlas-selection-chip" class="atlas-context-button" type="button" onclick={() => { returnFocusId = "atlas-selection-chip"; showDossier(); }}>{selected.name}</button>
                <button id="atlas-selection-clear" class="sc-icon-btn" type="button" aria-label="Clear selection" onclick={() => void closeSelection()}>
                  <AtlasIcon name="close" />
                </button>
              </div>
              <div class="atlas-context-row">
                <button id="atlas-building-chip" class="atlas-context-button" type="button" onclick={() => {
                  returnFocusId = "atlas-building-chip";
                  showDossier();
                  void tick().then(() => {
                    const details = document.getElementById("atlas-building-details");
                    if (details instanceof HTMLDetailsElement) details.open = true;
                    document.getElementById("atlas-building-status")?.scrollIntoView({ block: "nearest" });
                  });
                }}>Building footprint: {buildingState === "ready" ? "shown" : buildingState === "loading" ? "loading" : buildingState === "error" ? "lookup failed" : "unavailable"}</button>
              </div>
            {/if}
            {#if activeFilter}
              <div class="atlas-context-row">
                <button id="atlas-filter-chip" class="atlas-context-button" type="button" onclick={() => { returnFocusId = "atlas-filter-chip"; setPanel(activeFilter?.source ?? "ask"); }}>{activeFilter.label}</button>
                <button class="sc-icon-btn" type="button" aria-label="Clear filter" onclick={clearFilter}>
                  <AtlasIcon name="close" />
                </button>
              </div>
            {/if}
          </div>
          <div class="atlas-map-tools">
            <div class="atlas-lens-segments sc-segmented" role="group" aria-label="Sectors">
              {#each LENSES as name (name)}
                <button type="button" aria-pressed={lens === name} onclick={() => setLens(name)}>{LENS_LABEL[name]}</button>
              {/each}
            </div>
            <label class="atlas-lens-select">
              <span class="sc-label">Sector</span>
              <select class="sc-select" aria-label="Sector" value={lens} onchange={(event) => setLens(event.currentTarget.value as LensName)}>
                {#each LENSES as name (name)}
                  <option value={name}>{LENS_LABEL[name]}</option>
                {/each}
              </select>
            </label>
            <div class="atlas-camera-actions">
              {@render cameraActions()}
            </div>
            <details class="atlas-view">
              <summary>View</summary>
              <div class="atlas-view-menu">{@render cameraActions()}</div>
            </details>
            <details class="atlas-legend">
              <summary>Legend</summary>
              <ul>
                {#each ["critical", "high", "medium", "low", "unknown"] as severity (severity)}
                  <li><span class="atlas-glyph" data-severity={severity} aria-hidden="true"></span><span class="atlas-severity" data-severity={severity}>{severity}</span></li>
                {/each}
              </ul>
            </details>
          </div>
          {#if hover}
            <div class="atlas-hover" bind:this={hoverEl}>
              <span>{hover.name}</span>
              {#if hover.severity}<span class="atlas-severity" data-severity={hover.severity.toLowerCase()}>{hover.severity}</span>{/if}
            </div>
          {/if}
          {#if showMapThread}
            {@render threadPreview("map")}
          {/if}
        {/if}
        <div class="atlas-credits">
          <div id="cesium-credits" bind:this={creditEl}></div>
          <div id="data-credits">{creditLine}</div>
        </div>
      </section>
      {#if activeSurface}
        <aside class="sc-drawer atlas-workspace" aria-labelledby="workspace-title">
          <div class="atlas-workspace-head">
            <div class="atlas-dossier-heading">
              <h1 id="workspace-title" tabindex="-1" bind:this={workspaceTitleEl}>{workspaceTitle}</h1>
              {#if activeSurface === "dossier" && selected}
                <p class="atlas-muted">{selected.kind === "contractor" ? "Contractor" : "Facility"} · <span class="sc-mono">ID {selected.id}</span> · {selected.lat.toFixed(4)}, {selected.lon.toFixed(4)}</p>
              {/if}
            </div>
            <div class="atlas-actions">
              {#if activeSurface === "dossier"}
                <button type="button" class="sc-btn sc-btn--ghost" onclick={backWorkspace}>Back</button>
                <button type="button" class="sc-btn sc-btn--secondary" onclick={() => pinSelected("")}>Pin</button>
              {/if}
              <button type="button" class="sc-btn sc-btn--secondary atlas-sheet-toggle" aria-expanded={sheetExpanded} onclick={() => sheetExpanded = !sheetExpanded}>{sheetExpanded ? "Collapse" : "Expand"}</button>
              <button type="button" class="sc-btn sc-btn--ghost" onclick={hideWorkspace}>Hide</button>
            </div>
          </div>
          {#if activeSurface === "dossier"}
            <div class="sc-tabs atlas-dossier-tabs" role="tablist" aria-label="Dossier">
              {#each [{ id: "exposure", label: "Exposure" }, { id: "nearby", label: "Nearby" }, { id: "kill", label: "Kill chain" }] as item, index (item.id)}
                <button id={`atlas-tab-${item.id}`} type="button" class="sc-tab" role="tab" tabindex={tab === item.id ? 0 : -1} aria-selected={tab === item.id} aria-controls="atlas-dossier-panel" onclick={() => { if (item.id === "exposure" || item.id === "nearby" || item.id === "kill") tab = item.id; }}>{item.label} <span class="sc-kbd">{index + 1}</span></button>
              {/each}
            </div>
          {/if}
          <div class="atlas-workspace-body" bind:this={workspaceBodyEl}>
            <div class="atlas-content">
              {#if (activeSurface === "case" || activeSurface === "dossier") && caseError}<p class="sc-notice sc-notice--signal" role="alert">{caseError}</p>{/if}
              {#if activeSurface === "case" || activeSurface === "dossier"}<p class="atlas-muted" role="status">{caseNote}</p>{/if}
              {#if activeSurface === "explore"}
                <div class="atlas-stack">
                  <button type="button" class="sc-btn" onclick={() => { paletteOpen = true; }}>Search</button>
                  <p class="sc-label">Risk</p>
                  <div class="atlas-actions">
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("risk", "critical")}>critical</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("risk", "high")}>high</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("risk", "medium")}>medium</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("risk", "low")}>low</button>
                  </div>
                  <p class="sc-label">Exposure</p>
                  <div class="atlas-actions">
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("onprem", "")}>on-prem</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("dmarc", "not_set")}>dmarc missing</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("dmarc", "none")}>dmarc none</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("dmarc", "quarantine")}>dmarc quarantine</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void runAsk("dmarc", "reject")}>dmarc reject</button>
                  </div>
                  <p class="sc-label">Investigations</p>
                  <div class="atlas-actions">
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void loadCves()}>Shared CVEs</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void loadDams()}>Dams at risk</button>
                    <button type="button" class="sc-btn sc-btn--secondary" onclick={openCriticalSites}>Critical sites</button>
                  </div>
                  <p class="sc-label">Around selection</p>
                  <div class="atlas-actions">
                    {#if selected}
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => askNear(25)}>25 km</button>
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => askNear(50)}>50 km</button>
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => askNear(100)}>100 km</button>
                    {:else}
                      <span class="atlas-muted">Select a target first</span>
                    {/if}
                  </div>
                  <p class="atlas-muted">Syntax: cve CVE-… · port 3389 · obligation N</p>
                </div>
              {:else if activeSurface === "cve"}
                <div class="atlas-stack">
                  <p class="atlas-muted">Shared network CVEs · up to 30 returned</p>
                  {#if cvesBusy}
                    <p role="status">Loading shared CVEs…</p>
                  {:else if cvesError}
                    <p class="atlas-notice sc-notice sc-notice--signal" role="alert">{cvesError}
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void loadCves()}>Try again</button>
                    </p>
                  {:else if cves.length === 0}
                    <p class="atlas-empty sc-empty">No shared CVEs</p>
                  {:else}
                    <p role="status">{cves.length} shared CVEs returned</p>
                    <ul class="atlas-result-list">
                      {#each cves as cve (cve.id)}
                        <li>
                          <button type="button" class="atlas-result" onclick={() => selectCve(cve)}>
                            <span class="atlas-result-title">{cve.id}</span>
                            <span class="atlas-result-meta"><span class="atlas-severity" data-severity={cve.severity.toLowerCase()}>{cve.severity || "Unscored"}</span> · <span class="sc-mono">{cve.contractorCount}</span> contractors{cve.maxScore != null ? ` · Max score ${cve.maxScore}` : ""}</span>
                          </button>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              {:else if activeSurface === "dams"}
                <div class="atlas-stack">
                  <p class="atlas-muted">On-prem contractors within 50 km · up to 20 dams, 8 contractors per dam</p>
                  {#if damsBusy}
                    <p role="status">Loading dams at risk…</p>
                  {:else if damsError}
                    <p class="atlas-notice sc-notice sc-notice--signal" role="alert">{damsError}
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => void loadDams()}>Try again</button>
                    </p>
                  {:else if dams.length === 0}
                    <p class="atlas-empty sc-empty">No dams at risk</p>
                  {:else}
                    <p role="status">{dams.length} dams returned</p>
                    <ul class="atlas-result-list">
                      {#each dams as dam (dam.damId)}
                        <li>
                          <button type="button" class="atlas-result" onclick={() => openDam(dam)}>
                            <span class="atlas-result-title">{dam.damName}</span>
                            <span class="atlas-result-meta">Dam · <span class="sc-mono">{dam.contractors.length}</span> contractors returned</span>
                          </button>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              {:else if activeSurface === "keys"}
                <div class="atlas-stack">
                  <p class="atlas-muted">Blank fields keep saved keys. Saved secrets are never displayed.</p>
                  <p class="atlas-muted">The Google key needs Map Tiles API for the globe and Geocoding API for selected-building footprints.</p>
                  {#if keyStatusError}<p class="sc-notice sc-notice--signal" role="alert">{keyStatusError}</p>{/if}
                  {#each KEY_FIELDS as item (item.field)}
                    <label class="sc-field atlas-key-field">
                      <span class="sc-label">{item.label} <span class="atlas-muted">{keyReady(item.field) === null ? "Unknown" : keyReady(item.field) ? "Set" : "Missing"}</span></span>
                      <input class="sc-input" type="password" disabled={keyBusy} bind:value={keyDrafts[item.field]} placeholder="leave blank to keep the saved key" autocomplete="off" />
                    </label>
                  {/each}
                  <div class="atlas-actions">
                    <button type="button" class="sc-btn sc-btn--primary" disabled={keyBusy} onclick={saveKeys}>{keyBusy ? "Saving" : "Save"}</button>
                  </div>
                  {#if keyNote}<p class="atlas-muted" role="status">{keyNote}</p>{/if}
                  {#if keyError}<p class="sc-notice sc-notice--signal" role="alert">{keyError}</p>{/if}
                  {#if mapsChanged}
                    <p>Maps configuration saved. Reload to apply it.</p>
                    {@render reloadMapActions()}
                  {/if}
                </div>
              {:else if activeSurface === "ask" || activeSurface === "sites"}
                <div class="atlas-stack">
                  {#if askLabel}<p class="sc-label">{askLabel}</p>{/if}
                  {#if askNote || askError}
                    <p class="atlas-notice sc-notice sc-notice--signal" role="alert">{askNote || askError}</p>
                  {/if}
                  {#if askResult === null && !askNote && !askError}
                    <p role="status">Loading matches</p>
                  {:else if askResult}
                    <p role="status"><span class="sc-mono">{askResult.total}</span> matches · Showing {askResult.hits.length} of {askResult.total}</p>
                    {#if askResult.hits.length === 0}
                      <p class="atlas-empty sc-empty">{activeSurface === "sites" ? "No critical sites" : "No matches"}</p>
                    {/if}
                    <ul class="atlas-result-list">
                      {#each askResult.hits as hit (`${hit.kind}:${hit.id}`)}
                        <li>
                          <button type="button" class="atlas-result" onclick={() => openSelection(hit.kind === "facility" ? "facility" : "contractor", hit.id, hit.name, hit.lat, hit.lon, true)}>
                            <span class="atlas-result-title">{hit.name}</span>
                            <span class="atlas-result-meta">{hit.kind === "facility" ? "Facility" : "Contractor"} · {hit.subtitle}</span>
                            <span class="atlas-result-meta">
                              {#if hit.kind === "contractor"}Exposure score <span class="sc-mono">{hit.riskScore}</span> · <span class="atlas-severity" data-severity={hit.riskSeverity}>{hit.riskSeverity || "Unknown"}</span>{/if}
                              {#if hit.distanceKm != null}<span class="sc-mono">{hit.distanceKm} km</span>{/if}
                              {#if hit.kind === "facility"}<span class="sc-mono">{hit.count}</span> nearby contractors{/if}
                            </span>
                          </button>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              {:else if activeSurface === "case"}
                <div class="atlas-stack">
                  <p class="atlas-muted"><span class="sc-mono">{pins.length} / 12</span> pinned · New pins replace the oldest after 12. Re-pinning updates the existing entry.</p>
                  {#if pins.length === 0}
                    <div class="atlas-empty sc-empty">
                      <p>No pinned entities</p>
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => setPanel("explore")}>Explore</button>
                    </div>
                  {:else}
                    <ul class="atlas-result-list">
                      {#each pins as pin (`${pin.kind}:${pin.id}`)}
                        <li>
                          <button type="button" class="atlas-result" onclick={() => openSelection(pin.kind, pin.id, pin.name, pin.lat, pin.lon, true)}>
                            <span class="atlas-result-title">{pin.name}</span>
                            {#if pin.note}<span class="atlas-result-meta">{pin.note}</span>{/if}
                          </button>
                          <button type="button" class="sc-btn sc-btn--ghost" aria-label={`Remove ${pin.name} from Case`} onclick={() => removePin(pin)}>Remove</button>
                        </li>
                      {/each}
                    </ul>
                    {#if confirmClearCase}
                      <div class="sc-notice sc-notice--signal">
                        <p>Clear all {pins.length} pinned entities?</p>
                        <div class="atlas-actions">
                          <button type="button" class="sc-btn sc-btn--danger" onclick={clearCase}>Clear Case</button>
                          <button type="button" class="sc-btn sc-btn--secondary" onclick={() => confirmClearCase = false}>Cancel</button>
                        </div>
                      </div>
                    {:else}
                      <button type="button" class="sc-btn sc-btn--danger" onclick={() => confirmClearCase = true}>Clear case</button>
                    {/if}
                  {/if}
                </div>
              {:else if activeSurface === "layers"}
                <div class="atlas-stack">
                  <p>{bootStatus}</p>
                  {#if catalogError}
                    <div class="sc-notice sc-notice--signal" role="alert">
                      <p>{catalogError}</p>
                      <button type="button" class="sc-btn sc-btn--secondary" disabled={catalogState === "loading"} onclick={loadCatalog}>Retry catalog</button>
                    </div>
                  {/if}
                  {#if status?.gevMissing}<p class="sc-notice sc-notice--signal">{status.gevMissing}</p>{/if}
                  <section class="atlas-section" aria-label="Available context">
                    <h2 class="sc-label">Available context</h2>
                    <p>{points.length} contractor points loaded</p>
                    <p class="atlas-muted">{status?.contractors ?? "Unknown"} contractor records · {status?.dams ?? "Unknown"} dams · {status?.datacenters ?? "Unknown"} data centers</p>
                    <p class="atlas-muted">Dams and data centers are catalog context, not a standing map layer. Open them through search or proximity.</p>
                  </section>
                  {#if !mapReady}
                    <div class="sc-notice sc-notice--signal">
                      <p class="sc-notice__title">Map unavailable</p>
                      <p>{mapState === "loading" ? "Map loading" : mapState === "missing-key" ? SETUP : mapError}</p>
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => setPanel("keys")}>Open settings</button>
                      {#if mapState !== "loading"}{@render reloadMapActions()}{/if}
                    </div>
                  {/if}
                  <div class="sc-segmented" role="group" aria-label="Sector filter">
                    {#each LENSES as name (name)}
                      <button type="button" aria-pressed={lens === name} onclick={() => setLens(name)}>{LENS_LABEL[name]}</button>
                    {/each}
                  </div>
                  <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady} onclick={showMobilityContext}>Show mobility overlays</button>
                  <p class="atlas-muted">Turns on flights, quakes, and satellites that are off. It does not turn an overlay off.</p>
                  {#each [feedError, feedStartError, cameraError, feedFocusError].filter(Boolean) as error (error)}
                    <p class="sc-notice sc-notice--signal" role="alert">{error}</p>
                  {/each}
                  <p class="atlas-muted">Live overlays use hollow symbols. Contractor severity symbols are listed in the map Legend.</p>
                  {#each LAYERS as layer (layer.id)}
                    <section class="atlas-layer sc-panel" aria-label={layer.label}>
                      <button type="button" class="sc-btn" aria-pressed={layerEnabled(layer.id)} disabled={!mapReady || layerBusy[layer.id] || ((layer.id === "ais" || layer.id === "firms") && layerKey(layer.id) !== true)} onclick={() => toggleLayer(layer.id)}>
                        <span class="atlas-live-glyph" data-kind={layer.id} aria-hidden="true"></span>
                        {layer.label}
                      </button>
                      <p>{layerBusy[layer.id] ? "Updating" : layerEnabled(layer.id) ? "On" : "Off"} · {layer.provider}</p>
                      <p class="atlas-muted" data-level={ageLevel(feeds?.[layer.feed])}>{feeds ? `${feeds[layer.feed].items.length} returned` : "Count unknown"} · {ageLabel(feeds?.[layer.feed])}</p>
                      {#if layer.id === "install"}<p class="atlas-muted">Mapped installations are incomplete.</p>{/if}
                      {#if layer.id === "ais" || layer.id === "firms"}
                        <p class="atlas-muted">Key: {layerKey(layer.id) === null ? "Unknown" : layerKey(layer.id) ? "Set" : "Missing"}</p>
                        {#if layerKey(layer.id) === false}<button type="button" class="sc-btn sc-btn--secondary" onclick={() => setPanel("keys")}>Open settings</button>{/if}
                      {/if}
                      {#if layerError[layer.id]}<p class="sc-notice sc-notice--signal" role="alert">{layerError[layer.id]}</p>{/if}
                    </section>
                  {/each}
                  <p class="atlas-muted">AIS plots vessels owned or operated by in-view contractor families (at most eight). FIRMS plots fires within 25 km of those families' sites. Selecting a contractor narrows both feeds to that family; neither feed downloads the camera box.</p>
                </div>
              {:else if activeSurface === "dossier" && selected}
                {#if selectionError}<p class="atlas-notice sc-notice sc-notice--signal" role="alert">{selectionError}</p>{/if}
                <section id="atlas-building-status" class="atlas-section atlas-building-status sc-panel" aria-labelledby="atlas-building-title" aria-busy={buildingState === "loading"}>
                  <div class="atlas-actions">
                    <h3 id="atlas-building-title" class="sc-label">Building footprint</h3>
                    <span role="status">{buildingState === "ready" ? "Shown" : buildingState === "loading" ? "Loading" : buildingState === "error" ? "Lookup failed" : "Unavailable"}</span>
                    {#if buildingState === "ready"}<button type="button" class="sc-btn sc-btn--secondary" disabled={buildingFrameBusy} onclick={() => void frameBuilding()}>{buildingFrameBusy ? "Framing…" : "Frame building"}</button>{/if}
                  </div>
                  {#if buildingFrameError}<p role="alert" class="sc-notice sc-notice--signal">{buildingFrameError}</p>{/if}
                  <details id="atlas-building-details">
                    <summary>Google source and match</summary>
                    <div class="atlas-section">
                      <p>{buildingMessage}</p>
                      {#if building?.address}<p>{building.address}</p>{/if}
                      <p class="atlas-muted">Building outline, not a parcel boundary. Frame building follows the address match; the catalog location stays unchanged.</p>
                      {#if buildingState === "error" || buildingState === "unavailable"}
                        <div class="atlas-actions">
                          <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady || payloadBusy} onclick={() => buildingAttempt += 1}>Retry footprint</button>
                          {#if buildingState === "error"}<button type="button" class="sc-btn sc-btn--ghost" onclick={() => setPanel("keys")}>Settings</button>{/if}
                        </div>
                      {/if}
                    </div>
                  </details>
                </section>
                <div id="atlas-dossier-panel" class="atlas-tab-panel" role="tabpanel" aria-labelledby={`atlas-tab-${tab}`}>
                  {#if tab === "exposure"}
                    {#if payloadBusy}
                      <div class="atlas-stack" role="status">
                        <p class="atlas-muted">Loading evidence</p>
                        <div class="atlas-skeleton"></div>
                        <div class="atlas-skeleton"></div>
                        <div class="atlas-skeleton"></div>
                      </div>
                    {:else if selectionError}
                      <button type="button" class="sc-btn sc-btn--secondary" onclick={() => { if (!selected) return; selectionError = ""; payloadBusy = true; void loadPayload(selected.kind, selected.id, selectionToken); }}>Retry evidence</button>
                    {:else if payload === null}
                      <p class="sc-empty">No evidence in catalog</p>
                    {:else}
                      <DossierExposure payload={payload} risk={risk} onCve={(id) => { void runAsk("cve", id); }} onPort={(port) => { void runAsk("port", String(port)); }} />
                    {/if}
                  {:else if tab === "nearby"}
                    <div class="atlas-stack">
                      <div class="sc-segmented" role="group" aria-label="Nearby kind">
                        <button type="button" aria-pressed={threadKind === "kin"} onclick={() => setThreadChip("kin")}>Contractors</button>
                        <button type="button" aria-pressed={threadKind === "dam"} onclick={() => setThreadChip("dam")}>Dams</button>
                        <button type="button" aria-pressed={threadKind === "datacenter"} onclick={() => setThreadChip("datacenter")}>Data centers</button>
                      </div>
                      <div class="sc-segmented" role="group" aria-label="Radius">
                        {#each RADII as value (value)}
                          <button type="button" aria-pressed={radius === value} onclick={() => setRadius(value)}>{value} km</button>
                        {/each}
                      </div>
                      {#if showSheetThread}{@render threadPreview("sheet")}{/if}
                      {#if nearbyBusy}
                        <p role="status">Loading nearby</p>
                      {:else if nearbyError}
                        <div class="sc-notice sc-notice--signal" role="alert">
                          <p>{nearbyError}</p>
                          <button type="button" class="sc-btn sc-btn--secondary" onclick={() => setRadius(radius)}>Retry nearby</button>
                        </div>
                      {:else if nearby}
                        {#if nearbySource === "dam-summary"}
                          <p class="atlas-muted">Dam risk summary: up to 8 contractors returned. Choose a radius for a fresh proximity query.</p>
                        {/if}
                        <p class="atlas-muted">{nearby.facilities.length + nearby.contractors.length} returned · {mapReady ? connectionCount : 0} connections drawn{#if mapReady && connectionCount === 9} · 8 nearest plus selected preview{/if}</p>
                        {#if !mapReady}<p class="atlas-muted">Map unavailable; proximity evidence remains available.</p>{/if}
                        <div class="atlas-actions">
                          <button type="button" class="sc-btn sc-btn--secondary" disabled={!mapReady || !connectionCount} onclick={fitConnections}>Fit connections</button>
                          <button type="button" class="sc-btn sc-btn--ghost" disabled={!threadKind && !threadCard} onclick={clearThreads}>Clear connections</button>
                        </div>
                        {#each nearbyGroups as group (group.label)}
                          <section class="atlas-section" aria-label={group.label}>
                            <h2 class="sc-label">{group.label} · {group.rows.length} returned</h2>
                            {#if group.rows.length === 0}
                              <p class="atlas-muted">{nearbySource === "dam-summary" ? "Not included in this summary" : group.label !== "Contractors" && status?.gevMissing ? "GodsEyeView context unavailable" : `None in ${radius} km`}</p>
                            {:else}
                              <ul class="atlas-result-list">
                                {#each group.rows as row (`${row.kind}:${row.id}`)}
                                  <li>
                                    <button type="button" class="atlas-result" disabled={!!plotIssue(row)} aria-pressed={threadCard?.id === row.id && threadCard.kind === row.kind} onclick={() => previewNearby(row)}>
                                      <span class="atlas-result-title">{row.name || "Unnamed"}</span>
                                      <span class="atlas-result-meta"><span class="sc-mono">{row.distanceKm} km</span>{#if row.riskScore !== null} · Exposure score {row.riskScore} · <span class="atlas-severity" data-severity={row.riskSeverity.toLowerCase()}>{row.riskSeverity}</span>{/if}</span>
                                      {#if plotIssue(row)}<span class="atlas-result-meta">{plotIssue(row)}</span>{/if}
                                    </button>
                                  </li>
                                {/each}
                              </ul>
                            {/if}
                          </section>
                        {/each}
                      {/if}
                    </div>
                  {:else}
                    <div class="atlas-stack">
                      <p class="sc-label">Generated analysis · OpenRouter</p>
                      <dl class="atlas-definition-list">
                        <dt>Exposure</dt>
                        <dd>{payloadBusy ? "Loading evidence" : risk ? `${risk.score} ${risk.severity}` : "Not collected"}</dd>
                        <dt>Technique</dt>
                        <dd>{briefStep ? `${briefStep.technique_id} ${briefStep.technique_name}` : "no step"}</dd>
                        <dt>Evidence</dt>
                        <dd>{briefStep?.evidence ? briefStep.evidence : "not generated"}</dd>
                        <dt>Control</dt>
                        <dd>{typeof killChain?.remediation?.[0]?.action === "string" && killChain.remediation[0].action ? killChain.remediation[0].action : "not generated"}</dd>
                      </dl>
                      <button type="button" class="sc-btn sc-btn--primary" disabled={!openrouter || killBusy || selected.kind !== "contractor"} onclick={generateKill}>
                        {killBusy ? "Generating kill chain" : selected.kind !== "contractor" ? "Analysis is available for contractors" : openrouter === null ? "Analysis availability unknown" : openrouter ? "Generate kill chain" : "Kill chain needs OPENROUTER_API_KEY"}
                      </button>
                      {#if !openrouter}<button type="button" class="sc-btn sc-btn--secondary" onclick={() => setPanel("keys")}>Open settings</button>{/if}
                      {#if killBusy}<p role="status">Generating analysis</p>{/if}
                      {#if killError}
                        <pre class="atlas-notice sc-notice sc-notice--signal" role="alert">{killError}</pre>
                      {:else if killChain}
                        <div class="atlas-section">
                          <p class="atlas-severity" data-severity={(killChain.risk_level || "").toLowerCase()}>Kill chain — {(killChain.risk_level || "").toUpperCase()}</p>
                          {#if killChain.summary}
                            <div class="sc-dossier atlas-brief" data-sc-theme="sand">
                              <p>{killChain.summary}</p>
                            </div>
                          {/if}
                          {#if killChain.jev_risk_disagreement}
                            <p class="atlas-muted">judged level {killChain.jev_risk_level} differs from {killChain.risk_level}</p>
                          {/if}
                        </div>
                        <ol class="atlas-timeline">
                          {#each (killChain.steps || []) as step (step.step)}
                            <li>
                              <button
                                type="button"
                                class="atlas-step"
                                aria-expanded={openStep === step.step}
                                aria-controls={`atlas-step-${step.step}`}
                                onclick={() => toggleStep(step.step, step)}
                              >
                                <span class="atlas-step-number">{step.step}</span>
                                <span>{step.tactic}</span>
                                <span class="sc-mono">{step.technique_id} {step.technique_name}</span>
                                <span>{step.description}</span>
                                <span>Evidence: {step.evidence}</span>
                                {#if step.ip_unsupported}
                                  <span class="sc-chip">IP not in evidence</span>
                                {/if}
                              </button>
                              {#if openStep === step.step}
                                <div class="atlas-step-detail" id={`atlas-step-${step.step}`}>
                                  <button type="button" class="sc-btn sc-btn--secondary" onclick={() => pinSelected(`${step.technique_id} ${step.evidence}`)}>Pin step</button>
                                  <p>Impact: {step.impact || "—"}</p>
                                  {#if stepDetailBusy}
                                    <p role="status">Generating step detail</p>
                                  {:else if stepDetailError}
                                    <pre class="atlas-notice sc-notice sc-notice--signal" role="alert">{stepDetailError}</pre>
                                  {:else if stepDetail}
                                    {#if stepDetail.vulnerability}
                                      <div class="atlas-section">
                                        <p class="sc-label">Vulnerability</p>
                                        <div>{stepDetail.vulnerability.description || ""}</div>
                                        {#if stepDetail.vulnerability.affected_versions}<div>Affected: {stepDetail.vulnerability.affected_versions}</div>{/if}
                                        {#if stepDetail.vulnerability.cvss}<div>CVSS: {stepDetail.vulnerability.cvss}</div>{/if}
                                        {#if stepDetail.vulnerability.cwe}<div>CWE: {stepDetail.vulnerability.cwe}</div>{/if}
                                      </div>
                                    {/if}
                                    {#if stepDetail.attacker_view}
                                      <div class="atlas-section">
                                        <p class="sc-label">Attacker view</p>
                                        {#if stepDetail.attacker_view.banner}<div class="atlas-code">{stepDetail.attacker_view.banner}</div>{/if}
                                        {#if stepDetail.attacker_view.what_they_see}<div>{stepDetail.attacker_view.what_they_see}</div>{/if}
                                      </div>
                                    {/if}
                                    {#if stepDetail.detection}
                                      <div class="atlas-section">
                                        <p class="sc-label">Detection</p>
                                        {#if stepDetail.detection.monitoring_advice}<div>{stepDetail.detection.monitoring_advice}</div>{/if}
                                        {#each stepDetail.detection.signatures || [] as s}<div class="atlas-code">{s}</div>{/each}
                                        {#each stepDetail.detection.log_indicators || [] as l}<div>Log: {l}</div>{/each}
                                      </div>
                                    {/if}
                                    {#if stepDetail.remediation}
                                      <div class="atlas-section">
                                        <p class="sc-label">Remediation</p>
                                        {#each stepDetail.remediation.immediate || [] as a}<div>Immediate: {a}</div>{/each}
                                        {#each stepDetail.remediation.long_term || [] as a}<div>Long-term: {a}</div>{/each}
                                        {#each stepDetail.remediation.commands || [] as c}<div class="atlas-code">{c}</div>{/each}
                                      </div>
                                    {/if}
                                    {#if stepDetail.references && stepDetail.references.length}
                                      <div class="atlas-section">
                                        <p class="sc-label">References</p>
                                        {#each stepDetail.references as r}
                                          <a href={r.url} target="_blank" rel="noopener">{r.title || r.url}</a>
                                        {/each}
                                      </div>
                                    {/if}
                                    {#if stepDetail.red_team}
                                      <div class="atlas-section">
                                        <p class="sc-label">Red team</p>
                                        {#if stepDetail.red_team.tools}{#each (Array.isArray(stepDetail.red_team.tools) ? stepDetail.red_team.tools : []) as t}<div>{typeof t === "string" ? t : JSON.stringify(t)}</div>{/each}{/if}
                                        {#if stepDetail.red_team.commands}{#each (Array.isArray(stepDetail.red_team.commands) ? stepDetail.red_team.commands : []) as c}<div class="atlas-code">{typeof c === "string" ? c : JSON.stringify(c)}</div>{/each}{/if}
                                        {#if stepDetail.red_team.techniques}{#each (Array.isArray(stepDetail.red_team.techniques) ? stepDetail.red_team.techniques : []) as t}<div>{typeof t === "string" ? t : JSON.stringify(t)}</div>{/each}{/if}
                                      </div>
                                    {/if}
                                  {/if}
                                </div>
                              {/if}
                            </li>
                          {/each}
                        </ol>
                        {#if killChain.remediation && killChain.remediation.length}
                          <div class="atlas-section">
                            <p class="sc-label">Remediation priorities</p>
                            {#each killChain.remediation as r}
                              <p><span class="sc-mono">{r.priority}.</span> {r.action}</p>
                            {/each}
                          </div>
                        {/if}
                      {/if}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        </aside>
      {/if}
    </main>
  </div>
  <footer class="sc-heartbeat atlas-heartbeat">
    <span class="sc-heartbeat__item"><span class="sc-mono">{points.length}</span> contractor points</span>
    <span class="sc-heartbeat__sep" aria-hidden="true"></span>
    <span class="sc-heartbeat__item" role="status">{bootStatus}</span>
    <span class="sc-heartbeat__item">{activeLayerCount} active layers</span>
    <span class="sc-heartbeat__spacer"></span>
    <span class="sc-heartbeat__item" aria-hidden="true">{utc} UTC</span>
  </footer>
<CommandPalette
  open={paletteOpen}
  query={searchQuery}
  loading={searchBusy}
  error={searchError}
  items={getPaletteItems()}
  onquery={onPaletteQuery}
  onchoose={onPaletteChoose}
  onclose={onPaletteClose}
/>

</div>
