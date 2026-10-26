import type * as CesiumNS from "cesium";
import type { Cartesian2, Cartesian3 } from "cesium";
import type { AtlasPalette } from "./atlas-theme";
import type { BuildingPolygon } from "./building-footprint";

declare global {
  interface Window {
    Cesium: typeof CesiumNS;
  }
}

const Cesium = new Proxy({} as typeof CesiumNS, {
  get(_target, prop) {
    const runtime = window.Cesium;
    if (!runtime) throw new Error("Cesium failed to load");
    const value = runtime[prop as keyof typeof runtime];
    return value;
  },
});

export type ContractorPoint = {
  id: number;
  name: string;
  category: string;
  lat: number;
  lon: number;
  city: string;
  state: string;
  uei: string;
  cage: string;
  riskScore: number;
  riskSeverity: string;
};

export type Flight = {
  id: string;
  callsign: string;
  lat: number;
  lon: number;
  altM: number;
  heading: number;
  military: boolean;
};

export type SelectPayload = { kind: "contractor" | "facility"; id: string; lat: number; lon: number; name: string };
export type MapHover = {
  name: string;
  x: number;
  y: number;
  severity: string;
  kind: string;
  detail: string;
  score: number | null;
};


type Lens = "all" | "energy" | "digital" | "defense";
type Hit = {
  atlasKind: string;
  atlasId?: string | number;
  lon: number;
  lat: number;
  name?: string;
  kind?: string;
  distanceKm?: number;
  label?: string;
  matched?: number;
  clusterBounds?: CesiumNS.BoundingSphere;
  clusterLabelHalfWidth?: number;
};
type ContractorRec = {
  id: number;
  name: string;
  category: string;
  lat: number;
  lon: number;
  severity: string;
  city: string;
  state: string;
  score: number;
  position: Cartesian3;
  point: CesiumNS.PointPrimitive;
  glyph: Glyph;
};
type Glyph = {
  diameter: number;
  ring: boolean;
  css: string;
  color: CesiumNS.Color;
  dim: CesiumNS.Color;
};
type LiveRow = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  alt: number;
  image?: string;
  color?: string;
  scale?: number;
  heading?: number;
  opacity?: number;
};

const ENERGY = "Energy & Utilities";
const DIGITAL = "IT & Cyber";
const DEFENSE = new Set(["Security & Defense", "Research & Labs", "Manufacturing"]);
const CLUSTER_M = 800_000;
const SURFACE_PICK_BATCH_SIZE = 4;

export async function mountGlobe(
  container: HTMLElement,
  credits: HTMLElement,
  apiKey: string,
  hooks: {
    onSelect: (hit: SelectPayload) => void;
    onCamera: (cam: { lat: number; lon: number; heightM: number; west: number; south: number; east: number; north: number }) => void;
    onHover: (hit: MapHover | null) => void;
    onThread: (hit: { id: string; kind: string; name: string; lat: number; lon: number; distanceKm: number }) => void;
    onOrbitChange: (active: boolean) => void;
    onUserInteraction: () => void;
  },
  palette: AtlasPalette,
) {
  // No ion assets or geocoder: remove renderer branding, not provider attribution.
  Cesium.CreditDisplay.cesiumCredit = new Cesium.Credit("");
  Cesium.RequestScheduler.requestsByServer["tile.googleapis.com:443"] = 36;
  Cesium.RequestScheduler.maximumRequests = 64;
  const viewer = new Cesium.Viewer(container, {
    timeline: false,
    animation: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    selectionIndicator: false,
    infoBox: false,
    baseLayer: false,
    creditContainer: credits,
    // The credits popup must remain usable above an expanded dossier's tiny map.
    creditViewport: container.ownerDocument.body,
  });
  viewer.targetFrameRate = 60;
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);
  viewer.scene.requestRenderMode = false;
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(-98.5, 39.5, 8_000_000),
  });

  // Input can arrive while the real tileset factory is still pending. Initialize
  // everything stopOrbit reads before installing the capture listeners.
  type Motion = {
    generation: number;
    geometry: CesiumNS.BoundingSphere | null;
    cancelled: Promise<void>;
    cancel: () => void;
  };
  let disposed = false;
  let motionGeneration = 0;
  let motion: Motion | null = null;
  let orbitFrame = 0;
  let orbiting = false;
  let orbitAnnounced = false;
  function stopOrbit() {
    motionGeneration += 1;
    const previous = motion;
    motion = null;
    previous?.cancel();
    if (orbitFrame) cancelAnimationFrame(orbitFrame);
    orbitFrame = 0;
    // Cancel before Cesium receives the initiating gesture: flight cancellation
    // restores screenSpaceCameraController.enableInputs synchronously.
    if (!viewer.isDestroyed()) {
      viewer.camera.cancelFlight();
      // No offset means _setTransform preserves position/direction/up in world space.
      viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    }
    orbiting = false;
    if (orbitAnnounced) {
      orbitAnnounced = false;
      hooks.onOrbitChange(false);
    }
  }
  const onUserInteraction = () => {
    if (disposed) return;
    stopOrbit();
    hooks.onUserInteraction();
  };
  const removeInteractionListeners = () => {
    container.removeEventListener("pointerdown", onUserInteraction, true);
    container.removeEventListener("wheel", onUserInteraction, true);
  };
  container.addEventListener("pointerdown", onUserInteraction, { capture: true, passive: true });
  container.addEventListener("wheel", onUserInteraction, { capture: true, passive: true });

  try {
  let tilesetError = "";
  let photoreal: CesiumNS.Cesium3DTileset | undefined;
  try {
    const resource = new Cesium.Resource({
      url: "https://tile.googleapis.com/v1/3dtiles/root.json",
      queryParameters: { key: apiKey },
    });
    photoreal = await Cesium.Cesium3DTileset.fromUrl(resource, {
      cacheBytes: 1536 * 1024 * 1024,
      maximumCacheOverflowBytes: 1024 * 1024 * 1024,
      enableCollision: true,
      cullRequestsWhileMoving: false,
      preloadFlightDestinations: true,
      skipLevelOfDetail: true,
      skipLevels: 2,
      immediatelyLoadDesiredLevelOfDetail: false,
      loadSiblings: false,
      progressiveResolutionHeightFraction: 0,
      dynamicScreenSpaceError: false,
      foveatedScreenSpaceError: true,
      foveatedTimeDelay: 0,
      preferLeaves: true,
    });
    viewer.scene.primitives.add(photoreal);
    // Text attribution keeps the compact map-and-credits strip readable.
    viewer.creditDisplay.addStaticCredit(new Cesium.Credit('<span class="atlas-google-attribution">Google Maps</span>', true));
    viewer.scene.globe.show = false;
    viewer.scene.requestRenderMode = false;
  } catch (error) {
    tilesetError = error instanceof Error ? error.message : String(error);
    viewer.scene.globe.show = false;
  }

  const contractorPoints = new Cesium.PointPrimitiveCollection();
  const threadPoints = new Cesium.PointPrimitiveCollection();
  const clusterPoints = new Cesium.PointPrimitiveCollection();
  const live = new Cesium.BillboardCollection();
  viewer.scene.primitives.add(contractorPoints);
  viewer.scene.primitives.add(threadPoints);
  viewer.scene.primitives.add(clusterPoints);
  viewer.scene.primitives.add(live);
  // Canvas owns marker rendering and eligibility; suppress only the GPU collections.
  contractorPoints.show = false;
  clusterPoints.show = false;

  const overlay = document.createElement("canvas");
  overlay.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:2";
  container.appendChild(overlay);

  // cached palette colors, once
  const gold = Cesium.Color.fromCssColorString(palette.gold);
  const voidC = Cesium.Color.fromCssColorString(palette.void);
  const headC = Cesium.Color.fromCssColorString(palette.head);
  const ink2C = Cesium.Color.fromCssColorString(palette.ink2);
  const steelC = Cesium.Color.fromCssColorString(palette.steel);
  const signalC = Cesium.Color.fromCssColorString(palette.signal);
  const tintWhite = Cesium.Color.WHITE.clone();
  const buildingFill = Cesium.ColorGeometryInstanceAttribute.fromColor(gold.withAlpha(0.18));
  const buildingStroke = Cesium.ColorGeometryInstanceAttribute.fromColor(gold);
  const tintCivilian = Cesium.Color.WHITE.withAlpha(0.4);

  function makeGlyph(css: string, diameter: number, ring: boolean): Glyph {
    const color = Cesium.Color.fromCssColorString(css);
    const dim = color.withAlpha(0.25);
    return { diameter, ring, css, color, dim };
  }
  const glyphs: Record<string, Glyph> = {
    critical: makeGlyph(palette.signal, 10, false),
    high: makeGlyph(palette.gold, 8, false),
    medium: makeGlyph(palette.gold, 8, true),
    low: makeGlyph(palette.ink3, 6, false),
    "": makeGlyph(palette.ink3, 6, true),
  };
  function getGlyph(severity: string): Glyph {
    return glyphs[severity] || glyphs[""];
  }

  // hollow pin with void outer halo (no cesium param)
  function pin(color: string, outline: string): string {
    const canvas = document.createElement("canvas");
    canvas.width = 24;
    canvas.height = 24;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.strokeStyle = outline;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(12, 12, 9, 0, Math.PI * 2);
      ctx.stroke();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(12, 12, 6, 0, Math.PI * 2);
      ctx.stroke();
    }
    return canvas.toDataURL();
  }

  const flightIcon = pin(palette.ink2, palette.void);
  const milIcon = pin(palette.gold, palette.void);
  const installIcon = pin(palette.gold, palette.void);
  const satIcon = pin(palette.steel, palette.void);
  const aisIcon = pin(palette.steel, palette.void);
  const firmsIcon = pin(palette.signal, palette.void);

  let lens: Lens = "all";
  let selectedId = "";
  let selectedPosition: Cartesian3 | null = null;
  let selectedContractor: ContractorRec | null = null;
  let selectedAnnotation: { line1: string; line2: string; width: number } | null = null;
  let cveIds: Set<number> | null = null;
  const shownLayers = new Set<string>();
  let clusterQueued = false;
  let hoverPoint: Cartesian2 | null = null;
  let hoverQueued = false;
  let ellipse: { remove: () => void; refine: (gen: number, exclude: object[]) => Promise<void> } | null = null;
  let ellipseEntity: CesiumNS.Entity | null = null;
  let ellipseGen = 0;
  let threadEntities: CesiumNS.Entity[] = [];
  const buildingPrimitives: (CesiumNS.GroundPrimitive | CesiumNS.GroundPolylinePrimitive)[] = [];
  let buildingSphere: CesiumNS.BoundingSphere | null = null;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let contractors: ContractorRec[] = [];
  let cameraMoving = false;
  let clampGen = 0;
  let clampTimer = 0;
  const liveByKey = new Map<string, CesiumNS.Billboard>();

  function contractorVisible(category: string) {
    if (lens === "all") return true;
    if (lens === "energy") return category === ENERGY;
    if (lens === "digital") return category === DIGITAL;
    if (lens === "defense") return DEFENSE.has(category);
    return true;
  }

  function liveShown(layer: string) {
    return shownLayers.has(layer);
  }

  function clusteredNow() {
    if (viewer.isDestroyed?.() === true) return false;
    // Beyond a 2:1 viewport, fitting the short axis requires a higher camera.
    // Keep a fitted regional group unclustered in shallow or narrow map layouts.
    const { width, height } = viewer.canvas;
    const aspect = Math.max(width, height) / Math.max(1, Math.min(width, height));
    return viewer.camera.positionCartographic.height > CLUSTER_M * Math.max(1, aspect / 2);
  }

  function asHit(value: unknown): Hit | null {
    if (!value || typeof value !== "object") return null;
    const rec = value as Hit;
    if (typeof rec.atlasKind !== "string" || typeof rec.lon !== "number" || typeof rec.lat !== "number") return null;
    return rec;
  }

  function rebuildClusters() {
    clusterPoints.removeAll();
    const bins = new Map<string, { lon: number; lat: number; height: number; n: number; matched: number; positions: Cartesian3[] }>();
    for (const rec of contractors) {
      if (!contractorVisible(rec.category)) continue;
      const key = `${Math.floor(rec.lat / 2)}:${Math.floor(rec.lon / 2)}`;
      const bin = bins.get(key) ?? { lon: 0, lat: 0, height: 0, n: 0, matched: 0, positions: [] };
      const carto = Cesium.Cartographic.fromCartesian(rec.position);
      bin.lon += rec.lon;
      bin.lat += rec.lat;
      bin.height += carto.height;
      bin.n += 1;
      // CVE filtering dims members; it does not remove them from the group.
      bin.positions.push(rec.position);
      if (cveIds === null || cveIds.has(rec.id)) bin.matched += 1;
      bins.set(key, bin);
    }
    for (const bin of bins.values()) {
      const lon = bin.lon / bin.n;
      const lat = bin.lat / bin.n;
      const position = Cesium.Cartesian3.fromDegrees(lon, lat, bin.height / bin.n);
      const label = cveIds ? `${bin.matched}/${bin.n}` : String(bin.n);
      const id: Hit = {
        atlasKind: "cluster",
        lon,
        lat,
        name: label,
        label,
        matched: bin.matched,
        // Snapshot the actual member extent, independent of the display centroid.
        clusterBounds: Cesium.BoundingSphere.fromPoints(bin.positions),
        // Digits and slash occupy 12px monospace cells (~7.2px). Pad to 8px
        // per cell plus the text outline; no font measurement during rendering.
        clusterLabelHalfWidth: label.length * 4 + 3,
      };
      const point = clusterPoints.add({
        position,
        pixelSize: 14,
        color: voidC.withAlpha(0),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      });
      point.id = id;
    }
    invalidateOverlay();
  }

  function surfaceExclusions(): object[] {
    // Picking excludes individual points/billboards, not their collections.
    const exclude: object[] = [...buildingPrimitives, ...threadEntities];
    if (ellipseEntity) exclude.push(ellipseEntity);
    for (const collection of [contractorPoints, clusterPoints, threadPoints, live]) {
      for (let i = 0; i < collection.length; i += 1) exclude.push(collection.get(i));
    }
    return exclude;
  }

  function inView(lon: number, lat: number, rect: CesiumNS.Rectangle | undefined) {
    if (!rect) return true;
    const pad = Cesium.Math.toRadians(0.5);
    const west = rect.west - pad;
    const east = rect.east + pad;
    const south = rect.south - pad;
    const north = rect.north + pad;
    const lonRad = Cesium.Math.toRadians(lon);
    const latRad = Cesium.Math.toRadians(lat);
    const lonOk = west <= east ? lonRad >= west && lonRad <= east : lonRad >= west || lonRad <= east;
    return lonOk && latRad >= south && latRad <= north;
  }

  function scheduleClamp() {
    window.clearTimeout(clampTimer);
    clampTimer = window.setTimeout(() => {
      if (disposed || cameraMoving) return;
      void clampSurfaces();
    }, 180);
  }

  async function clampSurfaces() {
    if (!viewer.scene.clampToHeightSupported || viewer.camera.positionCartographic.height > 2_000_000) return;
    const gen = ++clampGen;
    const rect = viewer.camera.computeViewRectangle();
    const currentEllipse = ellipse;
    const exclude = surfaceExclusions();
    const sampled = new Cesium.Cartesian3();
    let picked = 0;
    let wrote = false;
    try {
      if (selectedPosition && !selectedContractor) {
        const next = viewer.scene.clampToHeight(selectedPosition, exclude, 10, sampled);
        if (next && !Cesium.Cartesian3.equals(next, selectedPosition)) {
          Cesium.Cartesian3.clone(next, selectedPosition);
          invalidateOverlay();
        }
      }
      for (const rec of contractors) {
        if (gen !== clampGen || cameraMoving || disposed) return;
        if (!contractorVisible(rec.category) || !inView(rec.lon, rec.lat, rect)) continue;
        // Decoration follows rendered tiles; it must not download distant leaf tiles.
        const next = viewer.scene.clampToHeight(rec.position, exclude, 10, sampled);
        if (next && !Cesium.Cartesian3.equals(next, rec.position)) {
          Cesium.Cartesian3.clone(next, rec.position);
          rec.point.position = rec.position;
          wrote = true;
          invalidateOverlay();
        }
        if (++picked % SURFACE_PICK_BATCH_SIZE === 0) {
          await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        }
      }
    } finally {
      if (wrote && !disposed) rebuildClusters();
    }
    if (gen === clampGen && !cameraMoving && !disposed && ellipse === currentEllipse) {
      await currentEllipse?.refine(gen, exclude);
    }
  }

  const toCameraScratch = new Cesium.Cartesian3();
  const normalScratch = new Cesium.Cartesian3();

  function onVisibleSide(position: Cartesian3) {
    Cesium.Cartesian3.subtract(viewer.camera.positionWC, position, toCameraScratch);
    Cesium.Ellipsoid.WGS84.geodeticSurfaceNormal(position, normalScratch);
    return Cesium.Cartesian3.dot(normalScratch, toCameraScratch) > 0;
  }

  const projectScratch = new Cesium.Cartesian2();
  function project(position: Cartesian3) {
    if (!onVisibleSide(position)) return undefined;
    return viewer.scene.cartesianToCanvasCoordinates(position, projectScratch);
  }

  let overlayDirty = true;
  let lastW = 0;
  let lastH = 0;
  let lastDpr = 0;

  function invalidateOverlay() {
    overlayDirty = true;
  }

  function drawOverlay() {
    if (disposed || viewer.isDestroyed?.() === true) return;
    const dpr = window.devicePixelRatio || 1;
    const width = container.clientWidth;
    const height = container.clientHeight;
    const pxW = Math.max(1, Math.floor(width * dpr));
    const pxH = Math.max(1, Math.floor(height * dpr));
    if (overlay.width !== pxW || overlay.height !== pxH) {
      overlay.width = pxW;
      overlay.height = pxH;
    }
    const ctx = overlay.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    for (const [key, bill] of liveByKey) {
      bill.show = liveShown(key.slice(0, key.indexOf(":"))) && onVisibleSide(bill.position);
    }

    const clustered = clusteredNow();
    if (clustered) {
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      ctx.font = `12px "Space Mono", ui-monospace, monospace`;
      const filtered = cveIds !== null;
      for (let i = 0; i < clusterPoints.length; i += 1) {
        const point = clusterPoints.get(i);
        const screen = project(point.position);
        if (!screen) continue;
        const hit = asHit(point.id);
        const matched = hit?.matched ?? 0;
        ctx.globalAlpha = filtered && matched === 0 ? 0.25 : 1;
        ctx.fillStyle = palette.void;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = palette.head;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        const label = hit?.label ?? hit?.name ?? "";
        ctx.strokeStyle = palette.void;
        ctx.lineWidth = 3;
        ctx.strokeText(label, screen.x, screen.y - 10);
        ctx.fillStyle = palette.head;
        ctx.fillText(label, screen.x, screen.y - 10);
      }
      ctx.globalAlpha = 1;
    } else {
      for (const rec of contractors) {
        if (!contractorVisible(rec.category)) continue;
        const screen = project(rec.position);
        if (!screen) continue;
        const glyph = rec.glyph;
        const r = glyph.diameter / 2 + 2;
        ctx.globalAlpha = cveIds && !cveIds.has(rec.id) ? 0.25 : 1;
        ctx.fillStyle = glyph.css;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, r, 0, Math.PI * 2);
        ctx.fill();
        if (glyph.ring) {
          ctx.strokeStyle = glyph.css;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(screen.x, screen.y, r - 1, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }
    // Selection paints last so nearby glyphs never overwrite the annotation.
    if (!clustered && selectedPosition && selectedAnnotation && (!selectedContractor || contractorVisible(selectedContractor.category))) {
      const screen = project(selectedPosition);
      if (!screen) return;
      const radius = selectedContractor ? selectedContractor.glyph.diameter / 2 + 5 : 9;
      ctx.globalAlpha = 1;
      ctx.strokeStyle = palette.head;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(screen.x, screen.y, radius, 0, Math.PI * 2);
      ctx.stroke();
      const boxWidth = Math.min(selectedAnnotation.width, width - 16);
      const left = Math.max(8, Math.min(width - boxWidth - 8, screen.x + radius + 12));
      const bottom = Math.max(52, screen.y - radius - 12);
      ctx.strokeStyle = palette.gold;
      ctx.beginPath();
      ctx.moveTo(screen.x, screen.y - radius);
      ctx.lineTo(left, bottom - 10);
      ctx.stroke();
      ctx.fillStyle = palette.void;
      ctx.globalAlpha = 0.94;
      ctx.fillRect(left, bottom - 42, boxWidth, 42);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = palette.gold;
      ctx.lineWidth = 1;
      ctx.strokeRect(left, bottom - 42, boxWidth, 42);
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";
      ctx.font = `11px "Space Mono", ui-monospace, monospace`;
      ctx.fillStyle = palette.head;
      ctx.fillText(selectedAnnotation.line1, left + 10, bottom - 25, boxWidth - 20);
      ctx.font = `10px "Space Mono", ui-monospace, monospace`;
      ctx.fillStyle = palette.gold;
      ctx.fillText(selectedAnnotation.line2, left + 10, bottom - 10, boxWidth - 20);
    }
  }

  function overlayHit(position: Cartesian2): Hit | null {
    let bestHit: Hit | null = null;
    let bestDistance = Infinity;
    const consider = (cartesian: Cartesian3, hit: Hit | null, radius: number) => {
      if (!hit) return;
      const screen = project(cartesian);
      if (!screen) return;
      const distance = Math.hypot(screen.x - position.x, screen.y - position.y);
      if (distance <= radius && distance < bestDistance) {
        bestDistance = distance;
        bestHit = hit;
      }
    };
    if (clusteredNow()) {
      for (let i = 0; i < clusterPoints.length; i += 1) {
        const point = clusterPoints.get(i);
        const hit = asHit(point.id);
        if (!hit) continue;
        const screen = project(point.position);
        if (!screen) continue;
        const dx = position.x - screen.x;
        const dy = position.y - screen.y;
        const distance = Math.hypot(dx, dy);
        // Include the outlined count above the circle in the same pick target.
        const onLabel = Math.abs(dx) <= (hit.clusterLabelHalfWidth ?? 0) && dy >= -25 && dy <= -6;
        // Rank a label hit from the label, not a neighboring circle's padded halo.
        const hitDistance = onLabel ? Math.min(distance, Math.hypot(dx, dy + 16)) : distance;
        if ((distance <= 14 || onLabel) && hitDistance < bestDistance) {
          bestDistance = hitDistance;
          bestHit = hit;
        }
      }
    } else {
      for (const rec of contractors) {
        if (!contractorVisible(rec.category)) continue;
        const glyph = rec.glyph;
        const r = glyph.diameter / 2 + 2 + (selectedId === `contractor:${rec.id}` ? 3 : 0);
        consider(rec.position, asHit(rec.point.id), r);
      }
    }
    for (let i = 0; i < threadPoints.length; i += 1) {
      const point = threadPoints.get(i);
      if (!point.show) continue;
      const hit = asHit(point.id);
      if (!hit || hit.atlasKind === "thread-origin") continue;
      consider(point.position, hit, 10);
    }
    return bestHit;
  }

  // one preRender guard; no recursive raf paint
  const preRem = viewer.scene.preRender.addEventListener(() => {
    if (disposed) return;
    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth;
    const h = container.clientHeight;
    const sizeCh = w !== lastW || h !== lastH || dpr !== lastDpr;
    const moving = cameraMoving || orbiting;
    if (!overlayDirty && !moving && !sizeCh) return;
    drawOverlay();
    overlayDirty = false;
    lastW = w;
    lastH = h;
    lastDpr = dpr;
  });

  const camRem = viewer.camera.changed.addEventListener(() => {
    if (disposed) return;
    invalidateOverlay();
  });

  // load font once, invalidate on success
  document.fonts.load('12px "Space Mono"').then(() => {
    if (!disposed) invalidateOverlay();
  }).catch(() => {});

  let initialRem: (() => void) | undefined;
  let allRem: (() => void) | undefined;
  if (photoreal) {
    initialRem = photoreal.initialTilesLoaded.addEventListener(scheduleClamp);
    allRem = photoreal.allTilesLoaded.addEventListener(scheduleClamp);
  }

  const moveStartRem = viewer.camera.moveStart.addEventListener(() => {
    cameraMoving = true;
    clampGen += 1;
    window.clearTimeout(clampTimer);
    invalidateOverlay();
  });

  const moveEndRem = viewer.camera.moveEnd.addEventListener(() => {
    cameraMoving = false;
    if (!clusterQueued) {
      clusterQueued = true;
      requestAnimationFrame(() => {
        clusterQueued = false;
        if (disposed || viewer.isDestroyed?.() === true) return;
        rebuildClusters();
        applyVisibility();
      });
    }
    scheduleClamp();
    const carto = viewer.camera.positionCartographic;
    const rect = viewer.camera.computeViewRectangle();
    if (!rect) return;
    hooks.onCamera({
      lat: Cesium.Math.toDegrees(carto.latitude),
      lon: Cesium.Math.toDegrees(carto.longitude),
      heightM: carto.height,
      west: Cesium.Math.toDegrees(rect.west),
      south: Cesium.Math.toDegrees(rect.south),
      east: Cesium.Math.toDegrees(rect.east),
      north: Cesium.Math.toDegrees(rect.north),
    });
  });

  const removers: Array<() => void> = [
    () => preRem(),
    () => camRem(),
    () => moveStartRem(),
    () => moveEndRem(),
  ];

  function applyVisibility() {
    for (const [key, bill] of liveByKey) {
      bill.show = liveShown(key.slice(0, key.indexOf(":")));
    }
    invalidateOverlay();
  }

  function syncLive(layer: string, rows: LiveRow[]) {
    const next = new Set<string>();
    for (const row of rows) {
      const key = `${layer}:${row.id}`;
      next.add(key);
      const position = Cesium.Cartesian3.fromDegrees(row.lon, row.lat, row.alt);
      const isImage = !!row.image;
      const alpha = row.opacity ?? 1;
      const tint = isImage ? (alpha < 0.99 ? tintCivilian : tintWhite) : Cesium.Color.fromCssColorString(row.color ?? palette.ink2);
      const rotation = -Cesium.Math.toRadians(row.heading ?? 0);
      const scale = row.scale ?? 0.7;
      const show = liveShown(layer);
      const existing = liveByKey.get(key);
      if (existing) {
        existing.position = position;
        if (row.image) existing.image = row.image;
        existing.color = tint;
        existing.rotation = rotation;
        existing.scale = scale;
        existing.show = show;
        continue;
      }
      const bill = live.add({
        position,
        image: row.image,
        color: tint,
        rotation,
        alignedAxis: Cesium.Cartesian3.ZERO,
        scale,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        show,
      });
      bill.id = { atlasKind: layer, atlasId: row.id, lon: row.lon, lat: row.lat, name: row.name };
      liveByKey.set(key, bill);
    }
    for (const [key, bill] of liveByKey) {
      if (!key.startsWith(`${layer}:`) || next.has(key)) continue;
      live.remove(bill);
      liveByKey.delete(key);
    }
    invalidateOverlay();
  }

  function flyDuration() {
    return reducedMotion.matches ? 0 : 1.2;
  }

  function currentMotion(request: Motion) {
    return !disposed && request.generation === motionGeneration && motion === request;
  }

  function beginMotion(geometry: CesiumNS.BoundingSphere | null, autoOrbit: boolean): Motion | null {
    stopOrbit();
    if (disposed) return null;
    let cancel!: () => void;
    const cancelled = new Promise<void>((resolve) => { cancel = resolve; });
    const request = { generation: motionGeneration, geometry, cancelled, cancel };
    motion = request;
    if (autoOrbit && !reducedMotion.matches) {
      orbitAnnounced = true;
      hooks.onOrbitChange(true);
    }
    return request;
  }

  async function surfaceCenter(request: Motion, point: Cartesian3): Promise<Cartesian3 | null> {
    if (!currentMotion(request)) return null;
    if (!photoreal || !viewer.scene.clampToHeightSupported) {
      throw new Error("Surface height is unavailable. Try again after the 3D tiles load.");
    }
    const exclude = surfaceExclusions();
    let timer: number | undefined;
    let timedOut = false;
    try {
      let center: Cartesian3 | undefined = viewer.scene.clampToHeight(Cesium.Cartesian3.clone(point), exclude, 10);
      if (!center) {
        // Clone the input: the detailed query mutates its positions array.
        // Cancellation and the deadline settle even if Cesium keeps loading tiles.
        const deadline = new Promise<never>((_resolve, reject) => {
          timer = window.setTimeout(() => {
            timedOut = true;
            reject(new Error("Surface preparation timed out."));
          }, 10_000);
        });
        const clamped = await Promise.race([
          viewer.scene.clampToHeightMostDetailed([Cesium.Cartesian3.clone(point)], exclude, 10),
          request.cancelled.then(() => null),
          deadline,
        ]);
        if (!currentMotion(request)) return null;
        center = clamped?.[0];
      }
      if (!currentMotion(request)) return null;
      if (!center || !Number.isFinite(center.x) || !Number.isFinite(center.y) || !Number.isFinite(center.z)) {
        throw new Error("Surface height is unavailable.");
      }
      return center;
    } catch {
      if (!currentMotion(request)) return null;
      // focus stops this motion and forwards the failure to the page.
      throw new Error(timedOut
        ? "Surface preparation timed out after 10 seconds. Wait for the 3D tiles to load, then try again."
        : "Surface height is unavailable. Try again after the 3D tiles load.");
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function focusFlight(
    request: Motion,
    sphere: CesiumNS.BoundingSphere,
    offset: CesiumNS.HeadingPitchRange,
    duration: number,
  ): Promise<boolean> {
    if (!currentMotion(request)) return false;
    const completed = await Promise.race([
      new Promise<boolean>((resolve) => {
        viewer.camera.flyToBoundingSphere(sphere, {
          offset,
          duration,
          complete: () => resolve(currentMotion(request)),
          cancel: () => resolve(false),
        });
      }),
      request.cancelled.then(() => false),
    ]);
    return completed && currentMotion(request);
  }

  function startOrbit(request: Motion, center: Cartesian3, offset: CesiumNS.HeadingPitchRange) {
    if (!currentMotion(request)) return;
    if (reducedMotion.matches) {
      stopOrbit();
      return;
    }
    orbiting = true;
    const heading0 = viewer.camera.heading;
    const started = performance.now();
    const step = (now: number) => {
      if (!currentMotion(request)) return;
      const u = Math.min(1, (now - started) / 40_000);
      offset.heading = heading0 + u * Math.PI * 2;
      viewer.camera.lookAt(center, offset);
      if (u < 1) orbitFrame = requestAnimationFrame(step);
      else stopOrbit();
    };
    orbitFrame = requestAnimationFrame(step);
  }

  async function focus(
    mode: "region" | "site" | "inspect",
    lon: number,
    lat: number,
    geometry: CesiumNS.BoundingSphere | null,
  ): Promise<void> {
    const closeUp = mode === "inspect";
    const request = beginMotion(geometry, closeUp);
    if (!request) return;
    try {
      const target = geometry?.center ?? Cesium.Cartesian3.fromDegrees(lon, lat);
      const center = mode === "region" ? target : await surfaceCenter(request, target);
      if (!currentMotion(request) || !center) return;
      const radius = geometry?.radius ?? 1;
      const range = geometry ? Math.max(radius * 4, 140) : mode === "region" ? 80_000 : mode === "site" ? 2_500 : 450;
      const pitch = geometry ? -45 : mode === "region" ? -90 : mode === "site" ? -45 : -35;
      const offset = new Cesium.HeadingPitchRange(closeUp ? viewer.camera.heading : 0, Cesium.Math.toRadians(pitch), range);
      const duration = reducedMotion.matches ? 0 : geometry ? flyDuration() : mode === "region" ? 0.7 : mode === "site" ? 0.45 : 0.35;
      const completed = await focusFlight(request, new Cesium.BoundingSphere(center, radius), offset, duration);
      if (!currentMotion(request)) return;
      if (completed && closeUp && !reducedMotion.matches) startOrbit(request, center, offset);
      else stopOrbit();
    } catch (error) {
      if (!currentMotion(request)) return;
      stopOrbit();
      throw error;
    }
  }

  function frame(mode: "region" | "site" | "inspect", lon: number, lat: number): Promise<void> {
    // Capture geometry now. A later footprint must not retarget a coordinate focus.
    return focus(mode, lon, lat, mode === "inspect" ? buildingSphere : null);
  }

  const onReducedMotion = () => {
    if (reducedMotion.matches) stopOrbit();
  };
  reducedMotion.addEventListener("change", onReducedMotion);

  async function focusCluster(hit: Hit): Promise<void> {
    const bounds = hit.clusterBounds;
    if (!bounds) return;
    // Member bounds are already in world coordinates. No surface query is needed
    // for a regional view, and a centroid-sized site flight can miss every member.
    const sphere = new Cesium.BoundingSphere(bounds.center, Math.max(bounds.radius * 1.2, 20_000));
    const request = beginMotion(sphere, false);
    if (!request) return;
    try {
      await focusFlight(request, sphere, new Cesium.HeadingPitchRange(0, -Math.PI / 2, 0), reducedMotion.matches ? 0 : 0.7);
      if (currentMotion(request)) stopOrbit();
    } catch (error) {
      if (!currentMotion(request)) return;
      stopOrbit();
      throw error;
    }
  }

  viewer.screenSpaceEventHandler.setInputAction((click: { position: Cartesian2 }) => {
    const hit = overlayHit(click.position) ?? asHit((viewer.scene.pick(click.position) as { id?: unknown } | undefined)?.id);
    if (!hit) return;
    if (hit.atlasKind === "cluster") {
      const pending = focusCluster(hit);
      const generation = motionGeneration;
      const { x, y } = click.position;
      void pending.catch(() => {
        // A current failure stops its own generation; newer input must not show stale feedback.
        if (!disposed && motionGeneration === generation + 1) {
          hooks.onHover({ name: "Cluster view unavailable. Try selecting the cluster again.", x, y, severity: "", kind: "cluster", detail: "", score: null });
        }
      });
      return;
    }
    if (hit.atlasKind === "thread") {
      hooks.onThread({
        id: String(hit.atlasId ?? ""),
        kind: String(hit.kind ?? ""),
        name: String(hit.name ?? ""),
        lat: hit.lat,
        lon: hit.lon,
        distanceKm: hit.distanceKm ?? 0,
      });
      return;
    }
    if (hit.atlasKind !== "contractor" && hit.atlasKind !== "facility") return;
    hooks.onSelect({
      kind: hit.atlasKind as "contractor" | "facility",
      id: String(hit.atlasId ?? ""),
      lat: hit.lat,
      lon: hit.lon,
      name: String(hit.name ?? ""),
    });
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  const onLeave = () => {
    hoverPoint = null;
    hooks.onHover(null);
  };
  container.addEventListener("pointerleave", onLeave);

  let hoverRaf = 0;
  viewer.screenSpaceEventHandler.setInputAction((movement: { endPosition: Cartesian2 }) => {
    hoverPoint = movement.endPosition;
    if (hoverQueued) return;
    hoverQueued = true;
    hoverRaf = requestAnimationFrame(() => {
      hoverQueued = false;
      if (disposed || viewer.isDestroyed?.() === true) return;
      const position = hoverPoint;
      if (!position) {
        hooks.onHover(null);
        return;
      }
      const picked = viewer.scene.pick(position) as { id?: unknown } | undefined;
      const hit = overlayHit(position) ?? asHit(picked?.id);
      if (!hit?.name) {
        hooks.onHover(null);
        return;
      }
      let severity = "";
      let kind = hit.atlasKind;
      let detail = "";
      let score: number | null = null;
      if (kind === "contractor") {
        const rec = contractors.find((r) => r.id === Number(hit.atlasId));
        severity = rec?.severity ?? "";
        if (rec) {
          const loc = rec.city && rec.state ? `${rec.city}, ${rec.state}` : rec.city || rec.state || "";
          detail = rec.category + (loc ? ` · ${loc}` : "");
          score = rec.score;
        }
        kind = "contractor";
      } else if (kind === "cluster") {
        kind = "cluster";
        detail = cveIds !== null ? `${hit.label} matched contractors` : `${hit.label} contractors · click to expand`;
        score = null;
      } else if (kind === "thread") {
        kind = "thread";
        const sub = hit.kind || "proximity";
        const d = typeof hit.distanceKm === "number" ? `${hit.distanceKm} km` : "";
        detail = `${sub} · ${d} · geographic proximity`.replace(/ ·  · /g, " · ");
        score = null;
      } else if (kind === "install" || kind === "facility") {
        kind = "facility";
        detail = "";
        score = null;
      } else {
        kind = hit.atlasKind;
        detail = "";
        score = null;
      }
      hooks.onHover({ name: String(hit.name), x: position.x, y: position.y, severity, kind, detail, score });
    });
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  let clusterRaf = 0;

  function applyLensOrFilter() {
    rebuildClusters();
    applyVisibility();
  }

  function clearBuildingFootprint() {
    if (buildingSphere && motion?.geometry === buildingSphere) stopOrbit();
    buildingSphere = null;
    if (buildingPrimitives.length === 0) return;
    for (const primitive of buildingPrimitives) viewer.scene.groundPrimitives.remove(primitive);
    buildingPrimitives.length = 0;
    invalidateOverlay();
  }

  function setBuildingFootprint(polygons: BuildingPolygon[] | null) {
    if (disposed) return;
    clearBuildingFootprint();
    if (!polygons?.length) return;
    const fills: CesiumNS.GeometryInstance[] = [];
    const outlines: CesiumNS.GeometryInstance[] = [];
    const bounds: Cartesian3[] = [];
    for (let i = 0; i < polygons.length; i++) {
      const polygon = polygons[i];
      const rings = [polygon.outer, ...polygon.holes].map((ring) =>
        ring.map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(lon, lat)));
      for (const position of rings[0]) bounds.push(position);
      fills.push(new Cesium.GeometryInstance({
        id: `atlas-building-fill-${i}`,
        geometry: new Cesium.PolygonGeometry({
          polygonHierarchy: new Cesium.PolygonHierarchy(rings[0], rings.slice(1).map((hole) => new Cesium.PolygonHierarchy(hole))),
          vertexFormat: Cesium.PerInstanceColorAppearance.FLAT_VERTEX_FORMAT,
        }),
        attributes: { color: buildingFill },
      }));
      for (let j = 0; j < rings.length; j++) {
        outlines.push(new Cesium.GeometryInstance({
          id: `atlas-building-ring-${i}-${j}`,
          geometry: new Cesium.GroundPolylineGeometry({ positions: rings[j], width: 2 }),
          attributes: { color: buildingStroke },
        }));
      }
    }
    buildingSphere = Cesium.BoundingSphere.fromPoints(bounds);
    buildingPrimitives.push(viewer.scene.groundPrimitives.add(new Cesium.GroundPrimitive({
      geometryInstances: fills,
      appearance: new Cesium.PerInstanceColorAppearance({ flat: true, translucent: true }),
      classificationType: Cesium.ClassificationType.BOTH,
      allowPicking: false,
    })));
    buildingPrimitives.push(viewer.scene.groundPrimitives.add(new Cesium.GroundPolylinePrimitive({
      geometryInstances: outlines,
      appearance: new Cesium.PolylineColorAppearance({ translucent: false }),
      classificationType: Cesium.ClassificationType.BOTH,
      allowPicking: false,
    })));
    invalidateOverlay();
  }

  async function frameBuildingFootprint(): Promise<void> {
    if (disposed) return;
    if (!buildingSphere) {
      stopOrbit();
      throw new Error("No matched building footprint is available.");
    }
    return focus("inspect", 0, 0, buildingSphere);
  }

  return {
    tilesetError,
    stopOrbit,
    setBuildingFootprint,
    frameBuildingFootprint,
    frame,
    setLens(next: Lens) {
      lens = next;
      applyLensOrFilter();
    },
    setLayer(layer: "ais" | "firms" | "flights" | "quakes" | "sats" | "install", on: boolean) {
      const key = layer === "flights" ? "flight" : layer === "quakes" ? "quake" : layer === "sats" ? "sat" : layer;
      if (on) shownLayers.add(key);
      else shownLayers.delete(key);
      applyVisibility();
    },
    clearSelect() {
      stopOrbit();
      clearBuildingFootprint();
      selectedId = "";
      selectedPosition = null;
      selectedContractor = null;
      selectedAnnotation = null;
      applyVisibility();
      if (ellipse) ellipse.remove();
      ellipse = null;
    },
    setContractors(points: ContractorPoint[]) {
      contractorPoints.removeAll();
      contractors = points.map((point) => {
        const position = Cesium.Cartesian3.fromDegrees(point.lon, point.lat, 0);
        const glyph = getGlyph(point.riskSeverity);
        const primitive = contractorPoints.add({
          position,
          pixelSize: 0,
          color: voidC.withAlpha(0),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });
        primitive.id = {
          atlasKind: "contractor",
          atlasId: point.id,
          lon: point.lon,
          lat: point.lat,
          name: point.name,
        };
        return {
          id: point.id,
          name: point.name,
          category: point.category,
          lat: point.lat,
          lon: point.lon,
          severity: point.riskSeverity,
          city: point.city,
          state: point.state,
          score: point.riskScore,
          position,
          point: primitive,
          glyph,
        };
      });
      if (selectedId.startsWith("contractor:")) {
        selectedContractor = contractors.find((row) => row.id === Number(selectedId.slice(11))) ?? null;
        selectedPosition = selectedContractor?.position ?? null;
      }
      rebuildClusters();
      applyVisibility();
      scheduleClamp();
      invalidateOverlay();
    },
    select(kind: string, id: string, target: { name: string; lat: number; lon: number }) {
      const nextId = `${kind}:${id}`;
      if (selectedId !== nextId) {
        stopOrbit();
        clearBuildingFootprint();
      }
      selectedId = nextId;
      selectedContractor = kind === "contractor" ? contractors.find((row) => row.id === Number(id)) ?? null : null;
      if (selectedContractor) {
        selectedPosition = selectedContractor.position;
      } else {
        const sampled = viewer.scene.sampleHeight(Cesium.Cartographic.fromDegrees(target.lon, target.lat), surfaceExclusions());
        selectedPosition = Cesium.Cartesian3.fromDegrees(target.lon, target.lat, typeof sampled === "number" && Number.isFinite(sampled) ? sampled : 0);
      }
      const name = target.name.trim();
      const line1 = name.length > 38 ? `${name.slice(0, 37)}…` : name;
      const context = selectedContractor
        ? [selectedContractor.category, [selectedContractor.city, selectedContractor.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")
        : kind === "contractor" ? "Contractor" : "Geographic facility";
      const line2 = context.length > 42 ? `${context.slice(0, 41)}…` : context;
      selectedAnnotation = { line1, line2, width: Math.max(line1.length * 7, line2.length * 6.5, 100) + 20 };
      scheduleClamp();
      applyVisibility();
    },
    setEllipse(lon: number, lat: number, radiusKm: number) {
      if (ellipse) ellipse.remove();
      const meters = radiusKm * 1000;
      const steps = 96;
      const sampledCenter = viewer.scene.sampleHeight(Cesium.Cartographic.fromDegrees(lon, lat), surfaceExclusions());
      const centerH = typeof sampledCenter === "number" && Number.isFinite(sampledCenter) ? sampledCenter : 0;
      // Refine against rendered tiles in small batches after the camera settles.
      let positions: Cartesian3[] = [];
      for (let i = 0; i <= steps; i += 1) {
        const heading = (i / steps) * Math.PI * 2;
        const delta = meters / 6378137;
        const lat1 = Cesium.Math.toRadians(lat);
        const lon1 = Cesium.Math.toRadians(lon);
        const lat2 = Math.asin(Math.sin(lat1) * Math.cos(delta) + Math.cos(lat1) * Math.sin(delta) * Math.cos(heading));
        const lon2 = lon1 + Math.atan2(
          Math.sin(heading) * Math.sin(delta) * Math.cos(lat1),
          Math.cos(delta) - Math.sin(lat1) * Math.sin(lat2),
        );
        positions.push(Cesium.Cartesian3.fromRadians(lon2, lat2, centerH + 40));
      }
      const ink = gold.withAlpha(0.9);
      const entity = viewer.entities.add({
        polyline: {
          positions,
          arcType: Cesium.ArcType.NONE,
          width: 2.5,
          clampToGround: false,
          material: new Cesium.ColorMaterialProperty(ink),
          depthFailMaterial: new Cesium.ColorMaterialProperty(ink),
        },
      });
      ellipseEntity = entity;
      const generation = ++ellipseGen;
      ellipse = {
        remove: () => {
          ellipseGen += 1;
          viewer.entities.remove(entity);
          if (ellipseEntity === entity) ellipseEntity = null;
        },
        refine: async (gen, exclude) => {
          const raised = positions.slice();
          const sampled = new Cesium.Cartesian3();
          const carto = new Cesium.Cartographic();
          let wrote = false;
          for (let i = 0; i < positions.length; i += 1) {
            if (disposed || cameraMoving || gen !== clampGen || generation !== ellipseGen) return;
            const next = viewer.scene.clampToHeight(positions[i], exclude, 10, sampled);
            if (next) {
              Cesium.Cartographic.fromCartesian(next, Cesium.Ellipsoid.WGS84, carto);
              Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, carto.height + 40, Cesium.Ellipsoid.WGS84, sampled);
              if (!Cesium.Cartesian3.equals(sampled, positions[i])) {
                raised[i] = Cesium.Cartesian3.clone(sampled);
                wrote = true;
              }
            }
            if ((i + 1) % SURFACE_PICK_BATCH_SIZE === 0) {
              await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
            }
          }
          if (wrote && entity.polyline) {
            positions = raised;
            entity.polyline.positions = new Cesium.ConstantProperty(positions);
          }
        },
      };
      scheduleClamp();
      invalidateOverlay();
    },
    clearThreads() {
      for (const entity of threadEntities) viewer.entities.remove(entity);
      threadEntities = [];
      threadPoints.removeAll();
      invalidateOverlay();
    },
    setThreads(
      origin: { lat: number; lon: number; kind: string },
      links: { id: string; kind: string; name: string; lat: number; lon: number; distanceKm: number }[],
    ) {
      for (const entity of threadEntities) viewer.entities.remove(entity);
      threadEntities = [];
      threadPoints.removeAll();
      const surfaceMeters = (lon: number, lat: number) => {
        const sampled = viewer.scene.sampleHeight(Cesium.Cartographic.fromDegrees(lon, lat), buildingPrimitives);
        return typeof sampled === "number" && Number.isFinite(sampled) ? sampled : 0;
      };
      const originSurface = surfaceMeters(origin.lon, origin.lat);
      const start = Cesium.Cartographic.fromDegrees(origin.lon, origin.lat);
      for (const link of links) {
        const endSurface = surfaceMeters(link.lon, link.lat);
        const point = threadPoints.add({
          position: Cesium.Cartesian3.fromDegrees(link.lon, link.lat, endSurface),
          pixelSize: 8,
          color: gold,
          outlineColor: voidC,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });
        point.id = {
          atlasKind: "thread",
          atlasId: link.id,
          kind: link.kind,
          name: link.name,
          lat: link.lat,
          lon: link.lon,
          distanceKm: link.distanceKm,
        };
        const geodesic = new Cesium.EllipsoidGeodesic(start, Cesium.Cartographic.fromDegrees(link.lon, link.lat));
        const positions: Cartesian3[] = [];
        for (let i = 0; i <= 24; i += 1) {
          const carto = geodesic.interpolateUsingFraction(i / 24);
          const lift = Math.sin((i / 24) * Math.PI) * Math.min(link.distanceKm * 40, 12_000);
          const surface = originSurface + (endSurface - originSurface) * (i / 24);
          positions.push(Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, surface + lift));
        }
        const ink = gold.withAlpha(0.72);
        const material = new Cesium.ColorMaterialProperty(ink);
        const depthFail = new Cesium.ColorMaterialProperty(ink);
        threadEntities.push(viewer.entities.add({
          polyline: {
            positions,
            arcType: Cesium.ArcType.NONE,
            width: 1.25,
            clampToGround: false,
            material,
            depthFailMaterial: depthFail,
          },
        }));
      }
      if (origin.kind !== "contractor") {
        const originPoint = threadPoints.add({
          position: Cesium.Cartesian3.fromDegrees(origin.lon, origin.lat, originSurface),
          pixelSize: 10,
          color: gold,
          outlineColor: voidC,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });
        originPoint.id = { atlasKind: "thread-origin", lon: origin.lon, lat: origin.lat };
      }
      invalidateOverlay();
    },
    clearEllipse() {
      if (ellipse) ellipse.remove();
      ellipse = null;
      invalidateOverlay();
    },
    setCveFilter(ids: number[] | null) {
      cveIds = ids ? new Set(ids) : null;
      rebuildClusters();
      applyVisibility();
    },
    flyToIds(ids: number[]) {
      stopOrbit();
      if (disposed) return;
      const want = new Set(ids);
      const positions = contractors.filter((rec) => want.has(rec.id)).map((rec) => rec.position);
      if (positions.length === 0) return;
      viewer.camera.flyToBoundingSphere(Cesium.BoundingSphere.fromPoints(positions), { duration: flyDuration() });
    },
    flyToPositions(points: { lon: number; lat: number }[]) {
      stopOrbit();
      if (disposed) return;
      if (points.length === 0) return;
      const positions = points.map((point) => Cesium.Cartesian3.fromDegrees(point.lon, point.lat));
      viewer.camera.flyToBoundingSphere(Cesium.BoundingSphere.fromPoints(positions), { duration: flyDuration() });
    },
    orbit(lon: number, lat: number): Promise<void> {
      return frame("inspect", lon, lat);
    },
    setFlights(rows: Flight[]) {
      syncLive("flight", rows.map((row) => ({
        id: row.id,
        name: row.callsign || row.id,
        lat: row.lat,
        lon: row.lon,
        alt: row.altM,
        image: row.military ? milIcon : flightIcon,
        opacity: row.military ? 1 : 0.4,
        heading: row.heading,
        scale: 0.7,
      })));
    },
    setQuakes(rows: { id: string; mag: number; lat: number; lon: number }[]) {
      syncLive("quake", rows.map((row) => ({
        id: row.id,
        name: row.id,
        lat: row.lat,
        lon: row.lon,
        alt: 0,
        color: palette.gold,
        scale: Math.max(8, row.mag * 4) / 16,
      })));
    },
    setSats(rows: { name: string; lat: number; lon: number; altM: number }[]) {
      syncLive("sat", rows.map((row, i) => ({
        id: `${row.name}-${i}`,
        name: row.name,
        lat: row.lat,
        lon: row.lon,
        alt: row.altM,
        color: palette.steel,
        scale: 0.45,
      })));
    },
    setInstalls(rows: { id: string; name: string; lat: number; lon: number }[]) {
      syncLive("install", rows.map((row) => ({
        id: row.id,
        name: row.name,
        lat: row.lat,
        lon: row.lon,
        alt: 0,
        image: installIcon,
        scale: 0.7,
      })));
    },
    setVessels(rows: { id: string; name: string; lat: number; lon: number; heading: number }[]) {
      syncLive("ais", rows.map((row) => ({
        id: row.id,
        name: row.name,
        lat: row.lat,
        lon: row.lon,
        alt: 0,
        color: palette.steel,
        heading: row.heading,
        scale: 0.55,
      })));
    },
    setFires(rows: { id: string; name?: string; lat: number; lon: number }[]) {
      syncLive("firms", rows.map((row) => ({
        id: row.id,
        name: row.name || row.id,
        lat: row.lat,
        lon: row.lon,
        alt: 0,
        color: palette.signal,
        scale: 0.45,
      })));
    },
    destroy() {
      if (disposed) return;
      disposed = true;
      clearBuildingFootprint();
      clampGen += 1;
      ellipseGen += 1;
      stopOrbit();
      if (hoverRaf) cancelAnimationFrame(hoverRaf);
      if (clusterRaf) cancelAnimationFrame(clusterRaf);
      window.clearTimeout(clampTimer);
      container.removeEventListener("pointerleave", onLeave);
      removeInteractionListeners();
      reducedMotion.removeEventListener("change", onReducedMotion);
      viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
      viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.MOUSE_MOVE);
      for (const r of removers) {
        try { r(); } catch {}
      }
      removers.length = 0;
      initialRem?.();
      allRem?.();
      selectedPosition = null;
      selectedContractor = null;
      selectedAnnotation = null;
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      viewer.destroy();
    },
  };
  } catch (error) {
    disposed = true;
    removeInteractionListeners();
    if (!viewer.isDestroyed()) viewer.destroy();
    throw error;
  }
}
