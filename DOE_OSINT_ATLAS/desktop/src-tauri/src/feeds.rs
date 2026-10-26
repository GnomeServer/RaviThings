use std::io::{Read, Write};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use crate::orgfeed;
use serde::Serialize;
use serde_json::Value;

#[derive(Clone, Debug)]
pub struct Camera {
    pub lat: f64,
    pub lon: f64,
    pub height_m: f64,
    pub west: f64,
    pub south: f64,
    pub east: f64,
    pub north: f64,
    pub set: bool,
}

impl Default for Camera {
    fn default() -> Self {
        Self {
            lat: 39.5,
            lon: -98.5,
            height_m: 8_000_000.0,
            west: -125.0,
            south: 24.0,
            east: -66.0,
            north: 50.0,
            set: false,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Flight {
    pub id: String,
    pub callsign: String,
    pub lat: f64,
    pub lon: f64,
    pub alt_m: f64,
    pub heading: f64,
    pub military: bool,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Quake {
    pub id: String,
    pub mag: f64,
    pub lat: f64,
    pub lon: f64,
    pub place: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SatFix {
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub alt_m: f64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Install {
    pub id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Vessel {
    pub id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub heading: f64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Fire {
    pub id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Layer<T> {
    pub items: Vec<T>,
    pub age_sec: Option<i64>,
    pub key_set: bool,
    pub enabled: bool,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Snapshot {
    pub flights: Layer<Flight>,
    pub quakes: Layer<Quake>,
    pub satellites: Layer<SatFix>,
    pub installations: Layer<Install>,
    pub ais: Layer<Vessel>,
    pub firms: Layer<Fire>,
}

struct Stamp<T> {
    items: Vec<T>,
    at: Option<i64>,
}

impl<T> Default for Stamp<T> {
    fn default() -> Self {
        Self { items: Vec::new(), at: None }
    }
}

struct Store {
    flights: Stamp<Flight>,
    quakes: Stamp<Quake>,
    satellites: Stamp<SatFix>,
    installations: Stamp<Install>,
    ais: Stamp<Vessel>,
    firms: Stamp<Fire>,
    ais_key: bool,
    firms_key: bool,
    ais_on: bool,
    firms_on: bool,
}

struct OrgState {
    index_loaded: bool,
    rows: Vec<orgfeed::ContractorRow>,
    focus_id: Option<i64>,
    fleet: orgfeed::FleetFile,
    fleet_loaded: bool,
    positions: HashMap<String, orgfeed::CachedPos>,
    firms_cache: HashMap<String, (Vec<orgfeed::ParsedFire>, i64)>,
    ownership_unavailable: bool,
    ais_paid_disabled: bool,
    firms_stopped: bool,
    paid_credits: u32,
    ais_retry_after: i64,
    firms_retry_after: i64,
    ais_plot_at: i64,
    ais_plot_sig: String,
    firms_plot_at: i64,
    firms_plot_sig: String,
}

impl Default for OrgState {
    fn default() -> Self {
        Self {
            index_loaded: false,
            rows: Vec::new(),
            focus_id: None,
            fleet: orgfeed::FleetFile::default(),
            fleet_loaded: false,
            positions: HashMap::new(),
            firms_cache: HashMap::new(),
            ownership_unavailable: false,
            ais_paid_disabled: false,
            firms_stopped: false,
            paid_credits: 0,
            ais_retry_after: 0,
            firms_retry_after: 0,
            ais_plot_at: 0,
            ais_plot_sig: String::new(),
            firms_plot_at: 0,
            firms_plot_sig: String::new(),
        }
    }
}

pub struct Hub {
    store: Mutex<Store>,
    camera: Mutex<Camera>,
    org: Mutex<OrgState>,
    started: AtomicBool,
    data_dir: PathBuf,
    ais_key: Mutex<String>,
    firms_key: Mutex<String>,
}

impl Hub {
    pub fn new(data_dir: PathBuf, ais_key: String, firms_key: String) -> Arc<Self> {
        Arc::new(Self {
            store: Mutex::new(Store {
                flights: Stamp::default(),
                quakes: Stamp::default(),
                satellites: Stamp::default(),
                installations: Stamp::default(),
                ais: Stamp::default(),
                firms: Stamp::default(),
                ais_key: !ais_key.is_empty(),
                firms_key: !firms_key.is_empty(),
                ais_on: false,
                firms_on: false,
            }),
            camera: Mutex::new(Camera::default()),
            org: Mutex::new(OrgState::default()),
            started: AtomicBool::new(false),
            data_dir,
            ais_key: Mutex::new(ais_key),
            firms_key: Mutex::new(firms_key),
        })
    }

    pub fn set_keys(&self, ais_key: String, firms_key: String) {
        {
            let mut store = self.store.lock().expect("feeds");
            store.ais_key = !ais_key.is_empty();
            store.firms_key = !firms_key.is_empty();
        }
        *self.ais_key.lock().expect("ais key") = ais_key;
        *self.firms_key.lock().expect("firms key") = firms_key;
    }

    pub fn set_camera(&self, camera: Camera) {
        *self.camera.lock().expect("camera") = camera;
    }

    pub fn set_enabled(&self, feed: &str, enabled: bool) {
        let turning_on = matches!(feed, "ais" | "firms") && enabled;
        if turning_on {
            self.ensure_index();
        }
        {
            let mut store = self.store.lock().expect("feeds");
            match feed {
                "ais" => store.ais_on = enabled && store.ais_key,
                "firms" => store.firms_on = enabled && store.firms_key,
                _ => {}
            }
        }
        if turning_on {
            self.replot_from_cache();
        }
    }

    pub fn set_focus(&self, contractor_id: Option<i64>) {
        {
            let mut org = self.org.lock().expect("org");
            org.focus_id = contractor_id;
        }
        self.replot_from_cache();
    }

    pub fn snapshot(&self) -> Snapshot {
        let org = self.org.lock().expect("org");
        let store = self.store.lock().expect("feeds");
        let now = unix_now();
        let mut ais = layer(&store.ais, now, store.ais_key, store.ais_on);
        if org.ais_paid_disabled && ais.enabled {
            ais.age_sec = Some(ais.age_sec.unwrap_or(0).max(1801));
        }
        Snapshot {
            flights: layer(&store.flights, now, true, true),
            quakes: layer(&store.quakes, now, true, true),
            satellites: layer(&store.satellites, now, true, true),
            installations: layer(&store.installations, now, true, true),
            ais,
            firms: layer(&store.firms, now, store.firms_key, store.firms_on),
        }
    }

    pub fn start(self: &Arc<Self>) {
        if self.started.swap(true, Ordering::SeqCst) {
            return;
        }
        let flights = Arc::clone(self);
        std::thread::spawn(move || loop {
            flights.poll_flights();
            std::thread::sleep(Duration::from_secs(30));
        });
        let quakes = Arc::clone(self);
        std::thread::spawn(move || loop {
            quakes.poll_quakes();
            std::thread::sleep(Duration::from_secs(300));
        });
        let sats = Arc::clone(self);
        std::thread::spawn(move || loop {
            sats.poll_sats();
            std::thread::sleep(Duration::from_secs(15));
        });
        let installs = Arc::clone(self);
        std::thread::spawn(move || loop {
            installs.poll_installations();
            std::thread::sleep(Duration::from_secs(60));
        });
        let org = Arc::clone(self);
        std::thread::spawn(move || loop {
            std::thread::sleep(Duration::from_secs(60));
            org.refresh_org();
        });
    }

    fn poll_flights(&self) {
        let camera = self.camera.lock().expect("camera").clone();
        if !camera.set {
            return;
        }
        let url = format!(
            "https://api.adsb.lol/v2/lat/{:.5}/lon/{:.5}/dist/250",
            camera.lat, camera.lon
        );
        let Ok(body) = get_text(&url) else { return };
        let Ok(value) = serde_json::from_str::<Value>(&body) else { return };
        let Some(list) = value.get("ac").and_then(|v| v.as_array()) else { return };
        let items = list.iter().filter_map(flight_from).collect::<Vec<_>>();
        let mut store = self.store.lock().expect("feeds");
        store.flights.items = items;
        store.flights.at = Some(unix_now());
    }

    fn poll_quakes(&self) {
        let Ok(body) = get_text("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson") else {
            return;
        };
        let Ok(value) = serde_json::from_str::<Value>(&body) else { return };
        let Some(features) = value.get("features").and_then(|v| v.as_array()) else { return };
        let items = features.iter().filter_map(quake_from).collect::<Vec<_>>();
        let mut store = self.store.lock().expect("feeds");
        store.quakes.items = items;
        store.quakes.at = Some(unix_now());
    }

    fn poll_sats(&self) {
        let camera = self.camera.lock().expect("camera").clone();
        if !camera.set {
            return;
        }
        let mut fixes = Vec::new();
        for group in ["stations", "gps-ops", "weather"] {
            let text = match cached_tle(&self.data_dir, group) {
                Some(text) => text,
                None => match get_text(&format!(
                    "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
                )) {
                    Ok(text) if text.lines().any(|l| l.starts_with('1')) => {
                        let _ = store_tle(&self.data_dir, group, &text);
                        text
                    }
                    _ => continue,
                },
            };
            fixes.extend(propagate_group(&text, &camera));
        }
        if fixes.is_empty() && self.store.lock().expect("feeds").satellites.at.is_some() {
            return;
        }
        if fixes.is_empty() {
            return;
        }
        let mut store = self.store.lock().expect("feeds");
        store.satellites.items = fixes;
        store.satellites.at = Some(unix_now());
    }

    fn poll_installations(&self) {
        let camera = self.camera.lock().expect("camera").clone();
        if !camera.set {
            return;
        }
        let key = format!(
            "{:.1}:{:.1}:{:.1}:{:.1}",
            camera.south, camera.west, camera.north, camera.east
        );
        let cache = self.data_dir.join("overpass").join(format!("{key}.json"));
        if let Some(items) = read_install_cache(&cache) {
            let mut store = self.store.lock().expect("feeds");
            if store.installations.at.is_none() {
                store.installations.items = items;
                store.installations.at = Some(unix_now());
            }
            return;
        }
        let query = format!(
            "[out:json][timeout:25];(node[\"military\"]({s},{w},{n},{e});way[\"military\"]({s},{w},{n},{e});node[\"landuse\"=\"military\"]({s},{w},{n},{e});way[\"landuse\"=\"military\"]({s},{w},{n},{e}););out center 80;",
            s = camera.south,
            w = camera.west,
            n = camera.north,
            e = camera.east
        );
        let client = match reqwest::blocking::Client::builder().timeout(Duration::from_secs(30)).build() {
            Ok(c) => c,
            Err(_) => return,
        };
        let Ok(resp) = client
            .post("https://overpass-api.de/api/interpreter")
            .form(&[("data", query)])
            .send()
        else {
            return;
        };
        let Ok(body) = resp.text() else { return };
        let Ok(value) = serde_json::from_str::<Value>(&body) else { return };
        let items = value
            .get("elements")
            .and_then(|v| v.as_array())
            .map(|els| els.iter().filter_map(install_from).collect::<Vec<_>>())
            .unwrap_or_default();
        if let Some(parent) = cache.parent() {
            let _ = std::fs::create_dir_all(parent);
            let _ = std::fs::write(&cache, body);
        }
        let mut store = self.store.lock().expect("feeds");
        store.installations.items = items;
        store.installations.at = Some(unix_now());
    }

    fn refresh_org(&self) {
        self.ensure_index();
        let (ais_on, firms_on) = {
            let store = self.store.lock().expect("feeds");
            (store.ais_on, store.firms_on)
        };
        if ais_on && self.ais_needs_network() {
            self.refresh_ais();
        }
        if firms_on && self.firms_needs_network() {
            self.refresh_firms();
        }
    }

    fn ensure_index(&self) {
        if self.org.lock().expect("org").index_loaded {
            return;
        }
        let Some(rows) = load_contractor_rows(&self.data_dir) else { return };
        let mut org = self.org.lock().expect("org");
        if org.index_loaded {
            return;
        }
        org.rows = rows;
        org.index_loaded = true;
    }

    fn ensure_fleet(&self, org: &mut OrgState) {
        if org.fleet_loaded {
            return;
        }
        let text = std::fs::read_to_string(self.data_dir.join("ais-fleet-cache.json")).unwrap_or_default();
        org.fleet = orgfeed::load_fleet(&text);
        org.fleet_loaded = true;
    }

    fn view(&self) -> orgfeed::ViewBox {
        let camera = self.camera.lock().expect("camera").clone();
        orgfeed::ViewBox {
            set: camera.set,
            lat: camera.lat,
            lon: camera.lon,
            west: camera.west,
            south: camera.south,
            east: camera.east,
            north: camera.north,
        }
    }

    fn current_focus(&self, org: &OrgState) -> (Vec<orgfeed::Family>, Vec<orgfeed::Lookup>, Option<(f64, f64)>) {
        let families = orgfeed::focus_families(&org.rows, &self.view(), org.focus_id);
        let lookups = orgfeed::lookup_names(&families, org.focus_id);
        let site = org.focus_id.and_then(|id| {
            families.iter().flat_map(|family| family.members.iter()).find(|member| member.id == id).map(|member| (member.lat, member.lon))
        });
        (families, lookups, site)
    }

    fn ais_sig(lookups: &[orgfeed::Lookup]) -> String {
        lookups.iter().map(|lookup| lookup.name.clone()).collect::<Vec<_>>().join("|")
    }

    fn firms_sig(boxes: &[orgfeed::DegBox]) -> String {
        boxes.iter().map(orgfeed::firms_cache_key).collect::<Vec<_>>().join("|")
    }

    fn ais_needs_network(&self) -> bool {
        let mut org = self.org.lock().expect("org");
        self.ensure_fleet(&mut org);
        let now = unix_now();
        if org.ais_paid_disabled || now < org.ais_retry_after || self.ais_key.lock().expect("ais key").is_empty() || org.paid_credits >= orgfeed::PAID_BUDGET {
            return false;
        }
        let (_, lookups, _) = self.current_focus(&org);
        if lookups.is_empty() {
            return false;
        }
        let missing = lookups.iter().any(|lookup| match org.fleet.names.get(&lookup.name) {
            Some(entry) => !orgfeed::fleet_fresh(entry, now),
            None => true,
        });
        if missing {
            return true;
        }
        let sig = Self::ais_sig(&lookups);
        org.ais_plot_sig != sig || now.saturating_sub(org.ais_plot_at) >= orgfeed::POSITION_TTL
    }

    fn firms_needs_network(&self) -> bool {
        let org = self.org.lock().expect("org");
        let now = unix_now();
        if org.firms_stopped || now < org.firms_retry_after || self.firms_key.lock().expect("firms key").is_empty() {
            return false;
        }
        let (families, _, site) = self.current_focus(&org);
        let view = self.view();
        let boxes = orgfeed::build_firms_boxes(&families, site, view.lat, view.lon);
        boxes.iter().take(4).any(|box_| {
            org.firms_cache.get(&orgfeed::firms_cache_key(box_)).map(|(_, at)| now.saturating_sub(*at) >= orgfeed::FIRMS_TTL).unwrap_or(true)
        })
    }

    fn refresh_ais(&self) {
        let path = self.data_dir.join("ais-fleet-cache.json");
        let (lookups, previous, mut fleet, mut positions, mut credits, mut unavailable) = {
            let mut org = self.org.lock().expect("org");
            self.ensure_fleet(&mut org);
            let (_, lookups, _) = self.current_focus(&org);
            let previous = self.store.lock().expect("feeds").ais.items.iter().map(plotted_from).collect::<Vec<_>>();
            (lookups, previous, org.fleet.clone(), org.positions.clone(), org.paid_credits, org.ownership_unavailable)
        };
        let mut http = LiveGet;
        let mut save = |fleet: &orgfeed::FleetFile| save_fleet(&path, fleet);
        let ais_key = self.ais_key.lock().expect("ais key").clone();
        let outcome = orgfeed::refresh_ais(&ais_key, &lookups, &previous, &mut fleet, &mut positions, &mut credits, &mut unavailable, unix_now(), &mut http, &mut save);
        let sig = Self::ais_sig(&lookups);
        let now = unix_now();
        {
            let mut org = self.org.lock().expect("org");
            org.fleet = fleet;
            org.positions = positions;
            org.paid_credits = credits;
            org.ownership_unavailable = unavailable;
            if outcome.paid_disabled || outcome.stale {
                org.ais_paid_disabled = true;
            }
            if outcome.retry_after > org.ais_retry_after {
                org.ais_retry_after = outcome.retry_after;
            }
            if outcome.updated {
                org.ais_plot_at = now;
                org.ais_plot_sig = sig;
            }
        }
        if outcome.updated {
            let mut store = self.store.lock().expect("feeds");
            store.ais.items = outcome.vessels.into_iter().map(vessel_from_plotted).collect();
            store.ais.at = Some(now);
        }
    }

    fn refresh_firms(&self) {
        let (boxes, sites, previous, mut cache) = {
            let org = self.org.lock().expect("org");
            let (families, _, site) = self.current_focus(&org);
            let view = self.view();
            let boxes = orgfeed::build_firms_boxes(&families, site, view.lat, view.lon);
            let sites = family_sites(&families);
            let previous = self.store.lock().expect("feeds").firms.items.iter().map(kept_from).collect::<Vec<_>>();
            (boxes, sites, previous, org.firms_cache.clone())
        };
        let mut http = LiveGet;
        let firms_key = self.firms_key.lock().expect("firms key").clone();
        let outcome = orgfeed::refresh_firms(&firms_key, &boxes, &sites, &mut cache, &previous, unix_now(), &mut http);
        let now = unix_now();
        {
            let mut org = self.org.lock().expect("org");
            org.firms_cache = cache;
            if outcome.stopped {
                org.firms_stopped = true;
            }
            if outcome.retry_after > org.firms_retry_after {
                org.firms_retry_after = outcome.retry_after;
            }
            if outcome.updated {
                org.firms_plot_at = now;
                org.firms_plot_sig = Self::firms_sig(&boxes);
            }
        }
        if outcome.updated {
            let mut store = self.store.lock().expect("feeds");
            store.firms.items = outcome.fires.into_iter().map(fire_from_kept).collect();
            store.firms.at = Some(now);
        }
    }

    fn replot_from_cache(&self) {
        self.ensure_index();
        let now = unix_now();
        let mut org = self.org.lock().expect("org");
        self.ensure_fleet(&mut org);
        let (families, lookups, site) = self.current_focus(&org);
        let view = self.view();
        let mut vessels = Vec::new();
        let mut seen = std::collections::HashSet::new();
        for lookup in &lookups {
            let Some(entry) = org.fleet.names.get(&lookup.name) else { continue };
            if !orgfeed::fleet_fresh(entry, now) {
                continue;
            }
            for id in entry.imos.iter().chain(entry.mmsis.iter()) {
                let Some(cached) = org.positions.get(id) else { continue };
                if cached.plotted.name.is_empty() || !cached.plotted.lat.is_finite() || !cached.plotted.lon.is_finite() {
                    continue;
                }
                if !seen.insert(cached.plotted.id.clone()) {
                    continue;
                }
                let ship = cached.plotted.name.split(" · ").next().unwrap_or("vessel");
                vessels.push(Vessel {
                    id: cached.plotted.id.clone(),
                    name: format!("{ship} · {}", lookup.family),
                    lat: cached.plotted.lat,
                    lon: cached.plotted.lon,
                    heading: cached.plotted.heading,
                });
            }
        }
        let boxes = orgfeed::build_firms_boxes(&families, site, view.lat, view.lon);
        let fires = if org.firms_stopped {
            Vec::new()
        } else {
            let mut points = Vec::new();
            for box_ in boxes.iter().take(4) {
                if let Some((parsed, at)) = org.firms_cache.get(&orgfeed::firms_cache_key(box_)) {
                    if now.saturating_sub(*at) < orgfeed::FIRMS_TTL {
                        points.extend(parsed.clone());
                    }
                }
            }
            orgfeed::filter_fires(&points, &family_sites(&families))
        };
        drop(org);
        let mut store = self.store.lock().expect("feeds");
        store.ais.items = vessels;
        store.firms.items = fires.into_iter().map(fire_from_kept).collect();
    }
}

fn layer<T: Clone>(stamp: &Stamp<T>, now: i64, key_set: bool, enabled: bool) -> Layer<T> {
    Layer {
        items: if enabled { stamp.items.clone() } else { Vec::new() },
        age_sec: stamp.at.map(|at| (now - at).max(0)),
        key_set,
        enabled,
    }
}

fn flight_from(ac: &Value) -> Option<Flight> {
    let lat = ac.get("lat")?.as_f64()?;
    let lon = ac.get("lon")?.as_f64()?;
    let id = ac.get("hex")?.as_str()?.trim().to_string();
    if id.is_empty() {
        return None;
    }
    let callsign = ac.get("flight").and_then(|v| v.as_str()).unwrap_or("").trim().to_string();
    let heading = ac.get("track").and_then(|v| v.as_f64()).unwrap_or(0.0);
    let alt_m = match ac.get("alt_baro") {
        Some(Value::String(s)) if s == "ground" => 0.0,
        Some(Value::Number(n)) => n.as_f64().unwrap_or(0.0) * 0.3048,
        Some(Value::String(s)) => s.parse::<f64>().unwrap_or(0.0) * 0.3048,
        _ => 0.0,
    };
    let flags = ac.get("dbFlags").and_then(|v| v.as_i64()).unwrap_or(0);
    let upper = callsign.to_uppercase();
    let military = flags & 1 != 0
        || ["RCH", "EVAC", "NAVY", "USAF", "ARMY", "DUKE", "IRON", "JAKE"]
            .iter()
            .any(|p| upper.starts_with(p));
    Some(Flight { id, callsign, lat, lon, alt_m, heading, military })
}

fn quake_from(feature: &Value) -> Option<Quake> {
    let coords = feature.pointer("/geometry/coordinates")?.as_array()?;
    let lon = coords.first()?.as_f64()?;
    let lat = coords.get(1)?.as_f64()?;
    let mag = feature.pointer("/properties/mag").and_then(|v| v.as_f64()).unwrap_or(2.5);
    let place = feature.pointer("/properties/place").and_then(|v| v.as_str()).unwrap_or("").to_string();
    let id = feature.get("id").and_then(|v| v.as_str()).unwrap_or("quake").to_string();
    Some(Quake { id, mag, lat, lon, place })
}

fn install_from(el: &Value) -> Option<Install> {
    let lat = el.get("lat").and_then(|v| v.as_f64()).or_else(|| el.pointer("/center/lat").and_then(|v| v.as_f64()))?;
    let lon = el.get("lon").and_then(|v| v.as_f64()).or_else(|| el.pointer("/center/lon").and_then(|v| v.as_f64()))?;
    let id = el.get("id").map(|v| v.to_string()).unwrap_or_else(|| format!("{lat:.4},{lon:.4}"));
    let name = el.pointer("/tags/name").and_then(|v| v.as_str()).unwrap_or("installation").to_string();
    Some(Install { id, name, lat, lon })
}


fn propagate_group(text: &str, camera: &Camera) -> Vec<SatFix> {
    let now = chrono::Utc::now().naive_utc();
    let mut out = Vec::new();
    let lines: Vec<&str> = text.lines().map(str::trim_end).filter(|l| !l.is_empty()).collect();
    let mut i = 0;
    while i + 1 < lines.len() {
        let (name, l1, l2, step) = if i + 2 < lines.len() && lines[i + 1].starts_with('1') && lines[i + 2].starts_with('2') {
            (lines[i].trim(), lines[i + 1], lines[i + 2], 3)
        } else if lines[i].starts_with('1') && lines[i + 1].starts_with('2') {
            ("SAT", lines[i], lines[i + 1], 2)
        } else {
            i += 1;
            continue;
        };
        i += step;
        let Ok(elements) = sgp4::Elements::from_tle(Some(name.to_string()), l1.as_bytes(), l2.as_bytes()) else {
            continue;
        };
        let Ok(constants) = sgp4::Constants::from_elements(&elements) else { continue };
        let Ok(minutes) = elements.datetime_to_minutes_since_epoch(&now) else { continue };
        let Ok(prediction) = constants.propagate(minutes) else { continue };
        let Some((lat, lon, alt_m)) = teme_to_lla(prediction.position) else { continue };
        if !in_view(lat, lon, camera) {
            continue;
        }
        out.push(SatFix { name: name.to_string(), lat, lon, alt_m });
    }
    out
}

fn teme_to_lla(position_km: [f64; 3]) -> Option<(f64, f64, f64)> {
    let [x, y, z] = position_km;
    let gmst = gmst_rad();
    let x_e = gmst.cos() * x + gmst.sin() * y;
    let y_e = -gmst.sin() * x + gmst.cos() * y;
    let lon = y_e.atan2(x_e).to_degrees();
    let hyp = (x_e * x_e + y_e * y_e).sqrt();
    let lat = z.atan2(hyp).to_degrees();
    let alt_m = ((x_e * x_e + y_e * y_e + z * z).sqrt() - 6378.137) * 1000.0;
    if lat.is_finite() && lon.is_finite() { Some((lat, lon, alt_m)) } else { None }
}

fn gmst_rad() -> f64 {
    let unix = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
    let jd = unix / 86400.0 + 2440587.5;
    let gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0);
    gmst.to_radians().rem_euclid(std::f64::consts::TAU)
}

fn in_view(lat: f64, lon: f64, camera: &Camera) -> bool {
    if lat < camera.south || lat > camera.north {
        return false;
    }
    if camera.west <= camera.east {
        lon >= camera.west && lon <= camera.east
    } else {
        lon >= camera.west || lon <= camera.east
    }
}

fn cached_tle(dir: &PathBuf, group: &str) -> Option<String> {
    let path = dir.join("tle").join(format!("{group}.tle"));
    let meta = std::fs::metadata(&path).ok()?;
    let age = meta.modified().ok()?.elapsed().ok()?;
    if age > Duration::from_secs(6 * 3600) {
        return None;
    }
    std::fs::read_to_string(path).ok()
}

fn store_tle(dir: &PathBuf, group: &str, text: &str) -> std::io::Result<()> {
    let folder = dir.join("tle");
    std::fs::create_dir_all(&folder)?;
    std::fs::write(folder.join(format!("{group}.tle")), text)
}

fn read_install_cache(path: &std::path::Path) -> Option<Vec<Install>> {
    let meta = std::fs::metadata(path).ok()?;
    if meta.modified().ok()?.elapsed().ok()? > Duration::from_secs(6 * 3600) {
        return None;
    }
    let text = std::fs::read_to_string(path).ok()?;
    let value: Value = serde_json::from_str(&text).ok()?;
    Some(value.get("elements")?.as_array()?.iter().filter_map(install_from).collect())
}

fn get_text(url: &str) -> Result<String, ()> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(25))
        .user_agent("OSINT-Atlas/0.1")
        .build()
        .map_err(|_| ())?;
    let resp = client.get(url).send().map_err(|_| ())?;
    if !resp.status().is_success() {
        return Err(());
    }
    resp.text().map_err(|_| ())
}

struct LiveGet;

impl orgfeed::Get for LiveGet {
    fn get(&mut self, url: &str) -> Result<orgfeed::HttpResponse, ()> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(25))
            .user_agent("OSINT-Atlas/0.1")
            .build()
            .map_err(|_| ())?;
        let resp = client.get(url).send().map_err(|_| ())?;
        let status = resp.status().as_u16();
        let body = resp.text().unwrap_or_default();
        Ok(orgfeed::HttpResponse { status, body })
    }
}

fn load_contractor_rows(data_dir: &Path) -> Option<Vec<orgfeed::ContractorRow>> {
    let conn = rusqlite::Connection::open(data_dir.join("catalog.sqlite")).ok()?;
    let mut stmt = conn.prepare("SELECT id, name, lat, lon, payload_json FROM contractors").ok()?;
    let rows = stmt.query_map([], |row| {
        let payload: String = row.get(4).unwrap_or_default();
        Ok(orgfeed::ContractorRow {
            id: row.get(0)?,
            name: row.get(1)?,
            lat: row.get::<_, Option<f64>>(2).ok().flatten().unwrap_or(f64::NAN),
            lon: row.get::<_, Option<f64>>(3).ok().flatten().unwrap_or(f64::NAN),
            parent: orgfeed::parent_from_payload(&payload),
        })
    }).ok()?;
    Some(rows.filter_map(Result::ok).collect())
}

fn save_fleet(path: &Path, fleet: &orgfeed::FleetFile) {
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(text) = serde_json::to_string(fleet) {
        let _ = std::fs::write(path, text);
    }
}

fn plotted_from(vessel: &Vessel) -> orgfeed::Plotted {
    orgfeed::Plotted { id: vessel.id.clone(), name: vessel.name.clone(), lat: vessel.lat, lon: vessel.lon, heading: vessel.heading }
}

fn vessel_from_plotted(plotted: orgfeed::Plotted) -> Vessel {
    Vessel { id: plotted.id, name: plotted.name, lat: plotted.lat, lon: plotted.lon, heading: plotted.heading }
}

fn kept_from(fire: &Fire) -> orgfeed::KeptFire {
    orgfeed::KeptFire { id: fire.id.clone(), name: fire.name.clone(), lat: fire.lat, lon: fire.lon }
}

fn fire_from_kept(fire: orgfeed::KeptFire) -> Fire {
    Fire { id: fire.id, name: fire.name, lat: fire.lat, lon: fire.lon }
}

fn family_sites(families: &[orgfeed::Family]) -> Vec<orgfeed::SiteRef> {
    families.iter().flat_map(|family| {
        family.members.iter().filter(|member| member.lat.is_finite() && member.lon.is_finite()).map(|member| orgfeed::SiteRef {
            lat: member.lat,
            lon: member.lon,
            family: family.key.clone(),
        })
    }).collect()
}

fn unix_now() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

#[allow(dead_code)]
fn _keep_imports(mut w: impl Write, mut r: impl Read) {
    let _ = (&mut w, &mut r);
}
