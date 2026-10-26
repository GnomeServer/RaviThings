export type BuildingPolygon = { outer: [number, number][]; holes: [number, number][][] };
export type BuildingFootprint = { placeId: string; address: string; polygons: BuildingPolygon[] };
export type BuildingLookup =
  | { status: "ready"; footprint: BuildingFootprint }
  | { status: "unavailable"; message: string };

type Point = [number, number];
type Query = { address: string | null; lat: number; lon: number };

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function longitudeDelta(lon: number, origin: number): number {
  return ((lon - origin + 540) % 360) - 180;
}

function ring(value: unknown): Point[] {
  if (!Array.isArray(value) || value.length < 4) throw new Error("Google returned invalid building geometry.");
  const points: Point[] = value.map((point: unknown) => {
    if (!Array.isArray(point) || typeof point[0] !== "number" || typeof point[1] !== "number"
      || !Number.isFinite(point[0]) || !Number.isFinite(point[1])
      || Math.abs(point[0]) > 180 || Math.abs(point[1]) > 90) {
      throw new Error("Google returned invalid building geometry.");
    }
    return [point[0], point[1]];
  });
  const first = points[0];
  const last = points[points.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) throw new Error("Google returned an open building boundary.");
  let area = 0;
  for (let i = 1; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    area += longitudeDelta(a[0], first[0]) * (b[1] - first[1])
      - longitudeDelta(b[0], first[0]) * (a[1] - first[1]);
  }
  if (area === 0) throw new Error("Google returned a degenerate building boundary.");
  return points;
}

function polygon(value: unknown): BuildingPolygon {
  if (!Array.isArray(value) || value.length === 0) throw new Error("Google returned invalid building geometry.");
  return { outer: ring(value[0]), holes: value.slice(1).map(ring) };
}

function polygons(value: unknown): BuildingPolygon[] {
  const geometry = record(value);
  if (geometry?.type === "Polygon") return [polygon(geometry.coordinates)];
  if (geometry?.type === "MultiPolygon" && Array.isArray(geometry.coordinates) && geometry.coordinates.length > 0) {
    return geometry.coordinates.map(polygon);
  }
  throw new Error("Google returned unsupported building geometry.");
}

// Boundary is 0, interior is 1, exterior is -1. Unwrap about a ring vertex,
// not the query point, so a building at the date line cannot contain Greenwich.
function inRing(point: Point, boundary: Point[]): -1 | 0 | 1 {
  const origin = boundary[0][0];
  const x = longitudeDelta(point[0], origin);
  const y = point[1];
  let inside = false;
  for (let i = 0; i < boundary.length - 1; i++) {
    const a = boundary[i];
    const b = boundary[i + 1];
    const ax = longitudeDelta(a[0], origin);
    const bx = longitudeDelta(b[0], origin);
    const cross = (x - ax) * (b[1] - a[1]) - (y - a[1]) * (bx - ax);
    if (Math.abs(cross) < 1e-12 && x >= Math.min(ax, bx) && x <= Math.max(ax, bx)
      && y >= Math.min(a[1], b[1]) && y <= Math.max(a[1], b[1])) return 0;
    if ((a[1] > y) !== (b[1] > y) && x < (bx - ax) * (y - a[1]) / (b[1] - a[1]) + ax) inside = !inside;
  }
  return inside ? 1 : -1;
}

export async function lookupBuildingFootprint(key: string, query: Query, signal: AbortSignal): Promise<BuildingLookup> {
  if (!key) throw new Error("A Google Maps key is required for building footprints.");
  const address = query.address?.trim();
  if (!address && (!Number.isFinite(query.lat) || !Number.isFinite(query.lon)
    || Math.abs(query.lat) > 90 || Math.abs(query.lon) > 180)) {
    return { status: "unavailable", message: "No street address or valid mapped location is available." };
  }
  const body = address
    ? { addressQuery: { addressQuery: address } }
    : { locationQuery: { location: { latitude: query.lat, longitude: query.lon }, placeFilter: { structureType: "BUILDING" } } };
  let response: Response;
  try {
    response = await fetch("https://geocode.googleapis.com/v4/geocode/destinations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "destinations.primary,destinations.containingPlaces",
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error("Building lookup could not reach Google.");
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch (error) {
    if (signal.aborted) throw error;
    if (response.ok) throw new Error("Google returned invalid building data.");
  }
  if (!response.ok) {
    const failure = record(record(data)?.error);
    const message = typeof failure?.message === "string" ? failure.message : "";
    if (response.status === 403 && /not been used|disabled/i.test(message)) {
      throw new Error("Google Geocoding API is disabled. Enable it for your Maps project, then retry.");
    }
    if (response.status === 401 || response.status === 403) {
      throw new Error("Google Geocoding access denied. Check the Maps key, API restrictions, and billing.");
    }
    if (response.status === 429) throw new Error("Google Geocoding quota exceeded. Try again after quota is available.");
    throw new Error(`Building lookup failed (Google HTTP ${response.status}).`);
  }
  const result = record(data);
  // Protobuf JSON omits empty repeated fields.
  const destinations = result?.destinations === undefined ? [] : result.destinations;
  if (!result || !Array.isArray(destinations)) throw new Error("Google returned invalid building data.");
  if (destinations.length === 0) return { status: "unavailable", message: "Google has no building match for this address or mapped location." };
  if (destinations.length !== 1) return { status: "unavailable", message: "Google returned multiple destinations; no building was chosen." };
  const destination = record(destinations[0]);
  if (!destination) throw new Error("Google returned invalid building data.");
  const primary = record(destination.primary);
  const parents = Array.isArray(destination.containingPlaces) ? destination.containingPlaces : [];
  const buildings = primary?.structureType === "BUILDING"
    ? [primary]
    : parents.map(record).filter((place): place is Record<string, unknown> => place?.structureType === "BUILDING");
  if (buildings.length !== 1) {
    return { status: "unavailable", message: "The destination does not identify one building. Grounds and nearby landmarks are not building footprints." };
  }
  const building = buildings[0];
  if (!building.displayPolygon) return { status: "unavailable", message: "Google identifies the building but has no outline for it." };
  const shapes = polygons(building.displayPolygon);
  const point: Point = [query.lon, query.lat];
  if (!address && !shapes.some((shape) => inRing(point, shape.outer) >= 0
    && shape.holes.every((hole) => inRing(point, hole) <= 0))) {
    return { status: "unavailable", message: "The returned building does not contain the mapped point; it was not highlighted." };
  }
  return {
    status: "ready",
    footprint: {
      placeId: typeof building.placeId === "string" ? building.placeId : "",
      address: typeof building.formattedAddress === "string" ? building.formattedAddress : "",
      polygons: shapes,
    },
  };
}
