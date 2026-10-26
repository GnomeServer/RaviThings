use std::collections::{BTreeMap, HashMap};
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::Value;

const SUFFIXES: &[&str] = &[
    "L.L.C.", "L.L.C", "LLC", "INCORPORATED", "INC", "CORPORATION", "CORP", "COMPANY", "CO",
    "LIMITED", "LTD", "LLP", "LP", "PLC", "THE",
];

pub const FLEET_TTL: i64 = 7 * 24 * 3600;
pub const POSITION_TTL: i64 = 15 * 60;
pub const FIRMS_TTL: i64 = 30 * 60;
pub const PAID_BUDGET: u32 = 120;
pub const CREDIT_FLOOR: f64 = 30.0;

#[derive(Clone, Debug)]
pub struct ContractorRow {
    pub id: i64,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub parent: String,
}

#[derive(Clone, Debug)]
pub struct Family {
    pub key: String,
    pub members: Vec<ContractorRow>,
}

#[derive(Clone, Debug)]
pub struct ViewBox {
    pub set: bool,
    pub lat: f64,
    pub lon: f64,
    pub west: f64,
    pub south: f64,
    pub east: f64,
    pub north: f64,
}

#[derive(Clone, Debug)]
pub struct Lookup {
    pub name: String,
    pub family: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FleetEntry {
    pub imos: Vec<String>,
    pub mmsis: Vec<String>,
    pub source: String,
    pub at: i64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct FleetFile {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bulk_param: Option<String>,
    #[serde(default)]
    pub names: BTreeMap<String, FleetEntry>,
}

#[derive(Clone, Debug)]
pub struct Plotted {
    pub id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub heading: f64,
}

#[derive(Clone, Debug)]
pub struct CachedPos {
    pub plotted: Plotted,
    pub at: i64,
}

#[derive(Clone, Debug)]
pub struct DegBox {
    pub west: f64,
    pub south: f64,
    pub east: f64,
    pub north: f64,
    pub sites: usize,
}

#[derive(Clone, Debug)]
pub struct ParsedFire {
    pub lat: f64,
    pub lon: f64,
}

#[derive(Clone, Debug)]
pub struct SiteRef {
    pub lat: f64,
    pub lon: f64,
    pub family: String,
}

#[derive(Clone, Debug)]
pub struct KeptFire {
    pub id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
}

pub struct HttpResponse {
    pub status: u16,
    pub body: String,
}

pub trait Get {
    fn get(&mut self, url: &str) -> Result<HttpResponse, ()>;
}

#[derive(Clone, Debug)]
pub struct AisOutcome {
    pub vessels: Vec<Plotted>,
    pub paid_disabled: bool,
    pub stale: bool,
    pub retry_after: i64,
    pub updated: bool,
}

pub fn normalize_lookup(name: &str) -> Option<String> {
    let mut text = collapse_ws(&name.to_uppercase());
    loop {
        let Some(next) = strip_one(&text) else { break };
        text = collapse_ws(&next);
    }
    if text.chars().count() < 4 { None } else { Some(text) }
}

fn collapse_ws(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn strip_one(text: &str) -> Option<String> {
    let text = text.trim();
    for suf in SUFFIXES {
        if let Some(rest) = strip_token(text, suf) {
            return Some(rest);
        }
        let dotted = format!("{suf}.");
        if let Some(rest) = strip_token(text, &dotted) {
            return Some(rest);
        }
    }
    None
}

fn strip_token(text: &str, suf: &str) -> Option<String> {
    if text == suf {
        return Some(String::new());
    }
    let needle = format!(" {suf}");
    text.strip_suffix(&needle).map(|rest| rest.trim().to_string())
}

pub fn parent_from_payload(payload_json: &str) -> String {
    let Ok(value) = serde_json::from_str::<Value>(payload_json) else { return String::new() };
    value.get("parent").and_then(|v| v.as_str()).unwrap_or("").trim().to_string()
}

pub fn family_key(row: &ContractorRow) -> String {
    let parent = row.parent.trim();
    if parent.is_empty() { row.name.clone() } else { parent.to_string() }
}

pub fn group_families(rows: &[ContractorRow]) -> Vec<Family> {
    let mut order: Vec<String> = Vec::new();
    let mut buckets: BTreeMap<String, Vec<ContractorRow>> = BTreeMap::new();
    for row in rows {
        let key = family_key(row);
        if !buckets.contains_key(&key) {
            order.push(key.clone());
        }
        buckets.entry(key).or_default().push(row.clone());
    }
    order.into_iter().filter_map(|key| {
        let members = buckets.remove(&key)?;
        Some(Family { key, members })
    }).collect()
}

pub fn in_camera(lat: f64, lon: f64, camera: &ViewBox) -> bool {
    if !camera.set || !lat.is_finite() || !lon.is_finite() {
        return false;
    }
    if lat < camera.south || lat > camera.north {
        return false;
    }
    if camera.west <= camera.east {
        lon >= camera.west && lon <= camera.east
    } else {
        lon >= camera.west || lon <= camera.east
    }
}

pub fn focus_families(rows: &[ContractorRow], camera: &ViewBox, selected_id: Option<i64>) -> Vec<Family> {
    if let Some(id) = selected_id {
        let Some(row) = rows.iter().find(|r| r.id == id) else { return Vec::new() };
        let key = family_key(row);
        let members = rows.iter().filter(|r| family_key(r) == key).cloned().collect();
        return vec![Family { key, members }];
    }
    if !camera.set {
        return Vec::new();
    }
    let visible: Vec<_> = rows.iter().filter(|r| in_camera(r.lat, r.lon, camera)).cloned().collect();
    let mut families = group_families(&visible);
    families.sort_by(|a, b| b.members.len().cmp(&a.members.len()).then(a.key.cmp(&b.key)));
    families.truncate(8);
    families
}

pub fn lookup_names(families: &[Family], selected_id: Option<i64>) -> Vec<Lookup> {
    if let Some(id) = selected_id {
        let Some(family) = families.first() else { return Vec::new() };
        let Some(member) = family.members.iter().find(|m| m.id == id).or_else(|| family.members.first()) else {
            return Vec::new();
        };
        let mut out: Vec<Lookup> = Vec::new();
        if let Some(name) = normalize_lookup(&member.name) {
            out.push(Lookup { name, family: family.key.clone() });
        }
        if let Some(parent) = normalize_lookup(&member.parent) {
            if out.iter().all(|l| l.name != parent) {
                out.push(Lookup { name: parent, family: family.key.clone() });
            }
        }
        out.truncate(2);
        return out;
    }
    let mut out: Vec<Lookup> = Vec::new();
    for family in families.iter().take(8) {
        if let Some(name) = normalize_lookup(&family.key) {
            if out.iter().all(|l| l.name != name) {
                out.push(Lookup { name, family: family.key.clone() });
            }
        }
    }
    out
}

pub fn clamp_firms_box(west: f64, south: f64, east: f64, north: f64, center_lat: f64, center_lon: f64) -> (f64, f64, f64, f64) {
    let width = east - west;
    let height = north - south;
    if width <= 1.0 && height <= 1.0 {
        (west, south, east, north)
    } else {
        (center_lon - 0.5, center_lat - 0.5, center_lon + 0.5, center_lat + 0.5)
    }
}

pub fn build_firms_boxes(families: &[Family], selected_site: Option<(f64, f64)>, camera_lat: f64, camera_lon: f64) -> Vec<DegBox> {
    let center = selected_site.unwrap_or((camera_lat, camera_lon));
    let mut boxes = Vec::new();
    for family in families {
        let coords: Vec<(f64, f64)> = family.members.iter().filter(|m| m.lat.is_finite() && m.lon.is_finite()).map(|m| (m.lat, m.lon)).collect();
        if coords.is_empty() {
            continue;
        }
        let (mut south, mut north, mut west, mut east) = (coords[0].0, coords[0].0, coords[0].1, coords[0].1);
        for (lat, lon) in &coords {
            south = south.min(*lat);
            north = north.max(*lat);
            west = west.min(*lon);
            east = east.max(*lon);
        }
        let (west, south, east, north) = clamp_firms_box(west - 0.15, south - 0.15, east + 0.15, north + 0.15, center.0, center.1);
        boxes.push(DegBox { west, south, east, north, sites: coords.len() });
    }
    let mut merged = merge_boxes(boxes);
    merged.sort_by(|a, b| b.sites.cmp(&a.sites).then(a.west.partial_cmp(&b.west).unwrap_or(std::cmp::Ordering::Equal)));
    merged.truncate(4);
    for slot in &mut merged {
        let (west, south, east, north) = clamp_firms_box(slot.west, slot.south, slot.east, slot.north, center.0, center.1);
        *slot = DegBox { west, south, east, north, sites: slot.sites };
    }
    merged
}

fn merge_boxes(mut boxes: Vec<DegBox>) -> Vec<DegBox> {
    let mut changed = true;
    while changed {
        changed = false;
        let mut next = Vec::new();
        for slot in boxes.drain(..) {
            if let Some(existing) = next.iter_mut().find(|prev| overlaps(prev, &slot) && union_within_one(prev, &slot)) {
                *existing = union_box(existing, &slot);
                changed = true;
            } else {
                next.push(slot);
            }
        }
        boxes = next;
    }
    boxes
}

fn overlaps(a: &DegBox, b: &DegBox) -> bool {
    !(a.east < b.west || b.east < a.west || a.north < b.south || b.north < a.south)
}

fn union_within_one(a: &DegBox, b: &DegBox) -> bool {
    let west = a.west.min(b.west);
    let east = a.east.max(b.east);
    let south = a.south.min(b.south);
    let north = a.north.max(b.north);
    east - west <= 1.0 && north - south <= 1.0
}

fn union_box(a: &DegBox, b: &DegBox) -> DegBox {
    DegBox {
        west: a.west.min(b.west),
        south: a.south.min(b.south),
        east: a.east.max(b.east),
        north: a.north.max(b.north),
        sites: a.sites + b.sites,
    }
}

pub fn firms_area_path(key: &str, box_: &DegBox) -> String {
    format!(
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{:.4},{:.4},{:.4},{:.4}/1",
        box_.west, box_.south, box_.east, box_.north
    )
}

pub fn firms_cache_key(box_: &DegBox) -> String {
    format!("{:.4},{:.4},{:.4},{:.4}", box_.west, box_.south, box_.east, box_.north)
}

pub fn filter_fires(points: &[ParsedFire], sites: &[SiteRef]) -> Vec<KeptFire> {
    let mut out = Vec::new();
    for point in points {
        let mut best: Option<(f64, &str)> = None;
        for site in sites {
            let dist = crate::catalog::haversine_km(point.lat, point.lon, site.lat, site.lon);
            if dist <= 25.0 && best.map(|(d, _)| dist < d).unwrap_or(true) {
                best = Some((dist, site.family.as_str()));
            }
        }
        if let Some((_, family)) = best {
            out.push(KeptFire {
                id: format!("firms-{:.4}-{:.4}", point.lat, point.lon),
                name: format!("{family} fire"),
                lat: point.lat,
                lon: point.lon,
            });
        }
    }
    out
}

pub fn parse_firms_csv(body: &str) -> Vec<ParsedFire> {
    let mut lat_i = None;
    let mut lon_i = None;
    let mut out = Vec::new();
    for (row_i, line) in body.lines().enumerate() {
        let cols: Vec<&str> = line.split(',').collect();
        if row_i == 0 {
            lat_i = cols.iter().position(|c| c.eq_ignore_ascii_case("latitude"));
            lon_i = cols.iter().position(|c| c.eq_ignore_ascii_case("longitude"));
            continue;
        }
        let (Some(li), Some(oi)) = (lat_i, lon_i) else { continue };
        let lat = cols.get(li).and_then(|s| s.trim().parse().ok());
        let lon = cols.get(oi).and_then(|s| s.trim().parse().ok());
        if let (Some(lat), Some(lon)) = (lat, lon) {
            out.push(ParsedFire { lat, lon });
        }
    }
    out
}

pub fn load_fleet(text: &str) -> FleetFile {
    serde_json::from_str(text).unwrap_or_default()
}

pub fn fleet_fresh(entry: &FleetEntry, now: i64) -> bool {
    now.saturating_sub(entry.at) < FLEET_TTL
}

fn encode_query(value: &str) -> String {
    let mut out = String::new();
    for b in value.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' | b',' => out.push(b as char),
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

fn datalastic(path: &str, key: &str, params: &[(&str, &str)]) -> String {
    let mut url = format!("https://api.datalastic.com{path}?api-key={}", encode_query(key));
    for (k, v) in params {
        url.push('&');
        url.push_str(k);
        url.push('=');
        url.push_str(&encode_query(v));
    }
    url
}

fn find_remaining(value: &Value) -> Option<f64> {
    const KEYS: &[&str] = &["remaining", "credits_remaining", "requests_remaining"];
    fn walk(value: &Value, depth: usize) -> Option<f64> {
        if depth > 4 { return None; }
        let Value::Object(map) = value else { return None };
        for key in KEYS {
            if let Some(num) = map.get(*key).and_then(number) {
                return Some(num);
            }
        }
        for child in map.values() {
            if let Some(num) = walk(child, depth + 1) {
                return Some(num);
            }
        }
        None
    }
    walk(value, 0)
}

fn number(value: &Value) -> Option<f64> {
    value.as_f64().or_else(|| value.as_i64().map(|n| n as f64)).or_else(|| value.as_u64().map(|n| n as f64))
}

fn id_string(value: &Value) -> Option<String> {
    match value {
        Value::String(text) => {
            let trimmed = text.trim().trim_matches('"');
            if trimmed.is_empty() || trimmed == "0" { None } else { Some(trimmed.to_string()) }
        }
        Value::Number(num) => num.as_i64().filter(|n| *n != 0).map(|n| n.to_string()),
        _ => None,
    }
}

fn field_text(obj: &Value, keys: &[&str]) -> Option<String> {
    let Value::Object(map) = obj else { return None };
    for key in keys {
        if let Some(text) = map.get(*key).and_then(id_string) {
            return Some(text);
        }
        if let Some(text) = map.get(*key).and_then(|v| v.as_str()) {
            let trimmed = text.trim();
            if !trimmed.is_empty() {
                return Some(trimmed.to_string());
            }
        }
    }
    None
}

fn contains_ci(obj: &Value, key: &str, needle: &str) -> bool {
    let needle = needle.to_uppercase();
    let Value::Object(map) = obj else { return false };
    if let Some(text) = map.get(key).and_then(|v| v.as_str()) {
        if text.to_uppercase().contains(&needle) {
            return true;
        }
    }
    for child in map.values() {
        if let Value::Object(inner) = child {
            if let Some(text) = inner.get(key).and_then(|v| v.as_str()) {
                if text.to_uppercase().contains(&needle) {
                    return true;
                }
            }
        }
    }
    false
}

fn walk_objects(value: &Value, out: &mut Vec<Value>) {
    match value {
        Value::Array(items) => {
            for item in items {
                walk_objects(item, out);
            }
        }
        Value::Object(map) => {
            out.push(value.clone());
            for child in map.values() {
                if child.is_array() || child.is_object() {
                    walk_objects(child, out);
                }
            }
        }
        _ => {}
    }
}

fn owner_match(obj: &Value, needle: &str) -> bool {
    ["beneficial_owner", "operator", "technical_manager", "commercial_manager"]
        .iter()
        .any(|key| contains_ci(obj, key, needle))
}

struct IdBag {
    imos: Vec<String>,
    mmsis: Vec<String>,
}

fn push_unique(list: &mut Vec<String>, value: String) {
    if !list.iter().any(|item| item == &value) {
        list.push(value);
    }
}

fn ids_from_rows(rows: &[Value], limit: usize) -> IdBag {
    let mut bag = IdBag { imos: Vec::new(), mmsis: Vec::new() };
    for row in rows.iter().take(limit) {
        if let Some(imo) = field_text(row, &["imo", "imo_number"]) {
            push_unique(&mut bag.imos, imo);
        }
        if let Some(mmsi) = field_text(row, &["mmsi", "mmsi_number"]) {
            push_unique(&mut bag.mmsis, mmsi);
        }
    }
    bag
}

fn parse_matching(body: &str, needle: &str, ownership: bool) -> Result<IdBag, ()> {
    let value: Value = serde_json::from_str(body).map_err(|_| ())?;
    let mut objects = Vec::new();
    walk_objects(&value, &mut objects);
    let mut matched = Vec::new();
    for obj in objects {
        let keep = if ownership {
            owner_match(&obj, needle)
        } else {
            contains_ci(&obj, "name", needle)
        };
        if keep {
            matched.push(obj);
            if matched.len() == 20 {
                break;
            }
        }
    }
    Ok(ids_from_rows(&matched, 20))
}

fn pause_between(paid_sent: &mut u32) {
    if *paid_sent > 0 {
        std::thread::sleep(Duration::from_millis(1100));
    }
    *paid_sent += 1;
}

pub fn refresh_ais(
    key: &str,
    lookups: &[Lookup],
    previous: &[Plotted],
    fleet: &mut FleetFile,
    positions: &mut HashMap<String, CachedPos>,
    paid_credits: &mut u32,
    ownership_unavailable: &mut bool,
    now: i64,
    http: &mut impl Get,
    save: &mut dyn FnMut(&FleetFile),
) -> AisOutcome {
    let keep = || AisOutcome {
        vessels: previous.to_vec(),
        paid_disabled: false,
        stale: false,
        retry_after: 0,
        updated: false,
    };
    if lookups.is_empty() {
        return AisOutcome { vessels: Vec::new(), paid_disabled: false, stale: false, retry_after: 0, updated: true };
    }
    let missing = lookups.iter().any(|lookup| match fleet.names.get(&lookup.name) {
        Some(entry) => !fleet_fresh(entry, now),
        None => true,
    });
    let id_family = focus_ids(fleet, lookups, now);
    let positions_fresh = !id_family.is_empty()
        && id_family.keys().all(|id| positions.get(id).map(|pos| now.saturating_sub(pos.at) < POSITION_TTL).unwrap_or(false));
    let empty_fresh = id_family.is_empty()
        && lookups.iter().all(|lookup| fleet.names.get(&lookup.name).map(|entry| fleet_fresh(entry, now)).unwrap_or(false));
    if !missing && (positions_fresh || empty_fresh) {
        return AisOutcome {
            vessels: plot_cached(positions, &id_family),
            paid_disabled: false,
            stale: false,
            retry_after: 0,
            updated: true,
        };
    }
    if *paid_credits >= PAID_BUDGET {
        return keep();
    }
    let stat_url = datalastic("/api/v0/stat", key, &[]);
    let stat = match http.get(&stat_url) {
        Ok(resp) => resp,
        Err(()) => return keep(),
    };
    if stat.status == 401 || (stat.status == 200 && serde_json::from_str::<Value>(&stat.body).is_err()) {
        return AisOutcome {
            vessels: previous.to_vec(),
            paid_disabled: true,
            stale: true,
            retry_after: 0,
            updated: false,
        };
    }
    if stat.status == 429 {
        return AisOutcome {
            vessels: previous.to_vec(),
            paid_disabled: false,
            stale: false,
            retry_after: now + POSITION_TTL,
            updated: false,
        };
    }
    if stat.status != 200 {
        return keep();
    }
    let Ok(stat_json) = serde_json::from_str::<Value>(&stat.body) else {
        return AisOutcome {
            vessels: previous.to_vec(),
            paid_disabled: true,
            stale: true,
            retry_after: 0,
            updated: false,
        };
    };
    if find_remaining(&stat_json).is_some_and(|n| n < CREDIT_FLOOR) {
        return keep();
    }
    let mut paid_sent = 0u32;
    for lookup in lookups {
        if fleet.names.get(&lookup.name).map(|entry| fleet_fresh(entry, now)).unwrap_or(false) {
            continue;
        }
        if *paid_credits >= PAID_BUDGET {
            break;
        }
        let fetched = if !*ownership_unavailable {
            if let Some(bag) = paid_lookup(http, key, &lookup.name, true, paid_credits, &mut paid_sent, now) {
                bag
            } else if *ownership_unavailable {
                match paid_lookup(http, key, &lookup.name, false, paid_credits, &mut paid_sent, now) {
                    Some(bag) => bag,
                    None => return stop_or_keep(previous, now),
                }
            } else {
                return stop_or_keep(previous, now);
            }
        } else {
            match paid_lookup(http, key, &lookup.name, false, paid_credits, &mut paid_sent, now) {
                Some(bag) => bag,
                None => return stop_or_keep(previous, now),
            }
        };
        let Some((bag, source, stop)) = fetched else {
            return stop_or_keep(previous, now);
        };
        if source == "unavailable" {
            *ownership_unavailable = true;
            match paid_lookup(http, key, &lookup.name, false, paid_credits, &mut paid_sent, now) {
                Some(Some((bag, source, stop))) => {
                    store_fleet(fleet, &lookup.name, bag, source, now, save);
                    if stop {
                        return AisOutcome { vessels: previous.to_vec(), paid_disabled: false, stale: false, retry_after: now + POSITION_TTL, updated: false };
                    }
                    continue;
                }
                Some(None) | None => return stop_or_keep(previous, now),
            }
        }
        store_fleet(fleet, &lookup.name, bag, source, now, save);
        if stop {
            return AisOutcome { vessels: previous.to_vec(), paid_disabled: false, stale: false, retry_after: now + POSITION_TTL, updated: false };
        }
    }
    let id_family = focus_ids(fleet, lookups, now);
    let (imos, mmsis) = cap_ids(&id_family);
    if imos.is_empty() && mmsis.is_empty() {
        return AisOutcome { vessels: Vec::new(), paid_disabled: false, stale: false, retry_after: 0, updated: true };
    }
    if *paid_credits >= PAID_BUDGET {
        return AisOutcome {
            vessels: plot_cached(positions, &id_family),
            paid_disabled: false,
            stale: false,
            retry_after: 0,
            updated: true,
        };
    }
    match fetch_bulk(http, key, fleet, &imos, &mmsis, &id_family, paid_credits, &mut paid_sent, now, save) {
        BulkEnd::Vessels(vessels) => {
            for vessel in &vessels {
                positions.insert(vessel.id.clone(), CachedPos { plotted: vessel.clone(), at: now });
                for entry in fleet.names.values() {
                    let hit = entry.imos.iter().chain(entry.mmsis.iter()).any(|id| id == &vessel.id);
                    if !hit {
                        continue;
                    }
                    for id in entry.imos.iter().chain(entry.mmsis.iter()) {
                        let mut alias = vessel.clone();
                        alias.id = id.clone();
                        positions.insert(id.clone(), CachedPos { plotted: alias, at: now });
                    }
                }
            }
            for id in id_family.keys() {
                positions.entry(id.clone()).or_insert_with(|| CachedPos {
                    plotted: Plotted { id: id.clone(), name: String::new(), lat: f64::NAN, lon: f64::NAN, heading: 0.0 },
                    at: now,
                });
            }
            AisOutcome { vessels, paid_disabled: false, stale: false, retry_after: 0, updated: true }
        }
        BulkEnd::Stop => AisOutcome {
            vessels: previous.to_vec(),
            paid_disabled: false,
            stale: false,
            retry_after: now + POSITION_TTL,
            updated: false,
        },
        BulkEnd::Keep => keep(),
    }
}

fn stop_or_keep(previous: &[Plotted], now: i64) -> AisOutcome {
    let _ = now;
    AisOutcome { vessels: previous.to_vec(), paid_disabled: false, stale: false, retry_after: 0, updated: false }
}


fn paid_lookup(
    http: &mut impl Get,
    key: &str,
    name: &str,
    ownership: bool,
    paid_credits: &mut u32,
    paid_sent: &mut u32,
    now: i64,
) -> Option<Option<(IdBag, String, bool)>> {
    let _ = now;
    if *paid_credits >= PAID_BUDGET {
        return Some(None);
    }
    let url = if ownership {
        datalastic("/api/maritime_reports/ownership", key, &[("beneficial_owner", name)])
    } else {
        datalastic("/api/v0/vessel_find", key, &[("name", name), ("fuzzy", "0")])
    };
    pause_between(paid_sent);
    *paid_credits = paid_credits.saturating_add(1);
    let resp = match http.get(&url) {
        Ok(resp) => resp,
        Err(()) => return None,
    };
    if resp.status == 429 {
        return Some(Some((IdBag { imos: Vec::new(), mmsis: Vec::new() }, "stop".into(), true)));
    }
    if ownership && matches!(resp.status, 401 | 403 | 404) {
        return Some(Some((IdBag { imos: Vec::new(), mmsis: Vec::new() }, "unavailable".into(), false)));
    }
    if resp.status != 200 {
        return None;
    }
    let bag = parse_matching(&resp.body, name, ownership).unwrap_or(IdBag { imos: Vec::new(), mmsis: Vec::new() });
    let source = if ownership { "ownership" } else { "find" };
    Some(Some((bag, source.into(), false)))
}

fn store_fleet(fleet: &mut FleetFile, name: &str, bag: IdBag, source: String, now: i64, save: &mut dyn FnMut(&FleetFile)) {
    if source == "stop" || source == "unavailable" {
        return;
    }
    fleet.names.insert(name.to_string(), FleetEntry { imos: bag.imos, mmsis: bag.mmsis, source, at: now });
    save(fleet);
}

fn focus_ids(fleet: &FleetFile, lookups: &[Lookup], now: i64) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let mut count = 0usize;
    for lookup in lookups {
        let Some(entry) = fleet.names.get(&lookup.name) else { continue };
        if !fleet_fresh(entry, now) {
            continue;
        }
        for imo in &entry.imos {
            if count >= 100 { return map; }
            if map.insert(imo.clone(), lookup.family.clone()).is_none() {
                count += 1;
            }
        }
        for mmsi in &entry.mmsis {
            if count >= 100 { return map; }
            if map.insert(mmsi.clone(), lookup.family.clone()).is_none() {
                count += 1;
            }
        }
    }
    map
}

fn cap_ids(id_family: &HashMap<String, String>) -> (Vec<String>, Vec<String>) {
    let mut imos = Vec::new();
    let mut mmsis = Vec::new();
    for id in id_family.keys() {
        if id.len() == 7 && id.chars().all(|c| c.is_ascii_digit()) {
            push_unique(&mut imos, id.clone());
        } else {
            push_unique(&mut mmsis, id.clone());
        }
        if imos.len() + mmsis.len() >= 100 {
            break;
        }
    }
    (imos, mmsis)
}

enum BulkEnd {
    Vessels(Vec<Plotted>),
    Stop,
    Keep,
}

fn fetch_bulk(
    http: &mut impl Get,
    key: &str,
    fleet: &mut FleetFile,
    imos: &[String],
    mmsis: &[String],
    id_family: &HashMap<String, String>,
    paid_credits: &mut u32,
    paid_sent: &mut u32,
    now: i64,
    save: &mut dyn FnMut(&FleetFile),
) -> BulkEnd {
    let _ = now;
    let prefer_mmsi = fleet.bulk_param.as_deref() == Some("mmsi") || imos.is_empty();
    let first_param = if prefer_mmsi { "mmsi" } else { "imo" };
    let first_ids = if first_param == "mmsi" { mmsis } else { imos };
    if first_ids.is_empty() {
        return BulkEnd::Vessels(Vec::new());
    }
    if *paid_credits >= PAID_BUDGET {
        return BulkEnd::Keep;
    }
    match one_bulk(http, key, first_param, first_ids, id_family, paid_credits, paid_sent) {
        BulkCall::Ok(vessels) => {
            fleet.bulk_param = Some(first_param.to_string());
            save(fleet);
            BulkEnd::Vessels(vessels)
        }
        BulkCall::Retry if first_param == "imo" && !mmsis.is_empty() => {
            match one_bulk(http, key, "mmsi", mmsis, id_family, paid_credits, paid_sent) {
                BulkCall::Ok(vessels) => {
                    fleet.bulk_param = Some("mmsi".into());
                    save(fleet);
                    BulkEnd::Vessels(vessels)
                }
                BulkCall::Stop => BulkEnd::Stop,
                _ => BulkEnd::Keep,
            }
        }
        BulkCall::Stop => BulkEnd::Stop,
        _ => BulkEnd::Keep,
    }
}

enum BulkCall {
    Ok(Vec<Plotted>),
    Retry,
    Stop,
    Keep,
}

fn one_bulk(
    http: &mut impl Get,
    key: &str,
    param: &str,
    ids: &[String],
    id_family: &HashMap<String, String>,
    paid_credits: &mut u32,
    paid_sent: &mut u32,
) -> BulkCall {
    if ids.is_empty() || *paid_credits >= PAID_BUDGET {
        return BulkCall::Keep;
    }
    let joined = ids.join(",");
    let url = datalastic("/api/v0/vessel_bulk", key, &[(param, &joined)]);
    pause_between(paid_sent);
    let resp = match http.get(&url) {
        Ok(resp) => resp,
        Err(()) => return BulkCall::Keep,
    };
    if resp.status == 429 {
        return BulkCall::Stop;
    }
    if resp.status == 400 {
        return BulkCall::Retry;
    }
    if resp.status != 200 {
        return BulkCall::Keep;
    }
    let vessels = parse_bulk(&resp.body, id_family);
    *paid_credits = paid_credits.saturating_add(vessels.len() as u32);
    BulkCall::Ok(vessels)
}

fn parse_bulk(body: &str, id_family: &HashMap<String, String>) -> Vec<Plotted> {
    let Ok(value) = serde_json::from_str::<Value>(body) else { return Vec::new() };
    let mut objects = Vec::new();
    walk_objects(&value, &mut objects);
    let mut out = Vec::new();
    for obj in objects {
        let lat = field_number(&obj, &["lat", "latitude"]);
        let lon = field_number(&obj, &["lon", "longitude"]);
        let (Some(lat), Some(lon)) = (lat, lon) else { continue };
        let mmsi = field_text(&obj, &["mmsi", "mmsi_number"]);
        let imo = field_text(&obj, &["imo", "imo_number"]);
        let family = mmsi.as_ref().and_then(|id| id_family.get(id)).or_else(|| imo.as_ref().and_then(|id| id_family.get(id)));
        let Some(family) = family else { continue };
        let id = mmsi.or(imo).unwrap_or_default();
        if id.is_empty() {
            continue;
        }
        let ship = field_text(&obj, &["name", "shipname", "vessel_name", "ship_name"]).unwrap_or_else(|| "vessel".into());
        let heading = field_number(&obj, &["heading", "course"]).unwrap_or(0.0);
        if out.iter().any(|row: &Plotted| row.id == id) {
            continue;
        }
        out.push(Plotted { id, name: format!("{ship} · {family}"), lat, lon, heading });
    }
    out
}

fn field_number(obj: &Value, keys: &[&str]) -> Option<f64> {
    let Value::Object(map) = obj else { return None };
    for key in keys {
        if let Some(num) = map.get(*key).and_then(number) {
            return Some(num);
        }
    }
    None
}

fn plot_cached(positions: &HashMap<String, CachedPos>, id_family: &HashMap<String, String>) -> Vec<Plotted> {
    let mut out = Vec::new();
    for (id, family) in id_family {
        if let Some(cached) = positions.get(id) {
            if cached.plotted.name.is_empty() || !cached.plotted.lat.is_finite() || !cached.plotted.lon.is_finite() {
                continue;
            }
            let mut plotted = cached.plotted.clone();
            let ship = plotted.name.split(" · ").next().unwrap_or("vessel");
            plotted.name = format!("{ship} · {family}");
            plotted.id = id.clone();
            out.push(plotted);
        }
    }
    out
}

pub struct FirmsOutcome {
    pub fires: Vec<KeptFire>,
    pub stopped: bool,
    pub retry_after: i64,
    pub updated: bool,
}

pub fn refresh_firms(
    key: &str,
    boxes: &[DegBox],
    sites: &[SiteRef],
    cache: &mut HashMap<String, (Vec<ParsedFire>, i64)>,
    previous: &[KeptFire],
    now: i64,
    http: &mut impl Get,
) -> FirmsOutcome {
    if boxes.is_empty() {
        return FirmsOutcome { fires: Vec::new(), stopped: false, retry_after: 0, updated: true };
    }
    let mut needed = Vec::new();
    for box_ in boxes.iter().take(4) {
        let cache_key = firms_cache_key(box_);
        let fresh = cache.get(&cache_key).map(|(_, at)| now.saturating_sub(*at) < FIRMS_TTL).unwrap_or(false);
        if !fresh {
            needed.push((cache_key, firms_area_path(key, box_)));
        }
    }
    if needed.is_empty() {
        return FirmsOutcome { fires: fires_from_cache(cache, boxes, sites, now), stopped: false, retry_after: 0, updated: true };
    }
    let mut sent = 0u32;
    for (cache_key, url) in needed {
        if sent > 0 {
            std::thread::sleep(Duration::from_millis(1100));
        }
        sent += 1;
        let resp = match http.get(&url) {
            Ok(resp) => resp,
            Err(()) => {
                return FirmsOutcome { fires: previous.to_vec(), stopped: false, retry_after: now + FIRMS_TTL, updated: false };
            }
        };
        if resp.status == 403 {
            return FirmsOutcome { fires: Vec::new(), stopped: true, retry_after: 0, updated: true };
        }
        if resp.status == 429 || resp.status != 200 {
            return FirmsOutcome { fires: previous.to_vec(), stopped: false, retry_after: now + FIRMS_TTL, updated: false };
        }
        cache.insert(cache_key, (parse_firms_csv(&resp.body), now));
    }
    FirmsOutcome { fires: fires_from_cache(cache, boxes, sites, now), stopped: false, retry_after: 0, updated: true }
}

fn fires_from_cache(cache: &HashMap<String, (Vec<ParsedFire>, i64)>, boxes: &[DegBox], sites: &[SiteRef], now: i64) -> Vec<KeptFire> {
    let mut points = Vec::new();
    for box_ in boxes.iter().take(4) {
        if let Some((parsed, at)) = cache.get(&firms_cache_key(box_)) {
            if now.saturating_sub(*at) < FIRMS_TTL {
                points.extend(parsed.iter().cloned());
            }
        }
    }
    filter_fires(&points, sites)
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_lockheed_martin_corp() {
        assert_eq!(normalize_lookup("LOCKHEED MARTIN CORP").as_deref(), Some("LOCKHEED MARTIN"));
    }

    #[test]
    fn groups_same_parent_into_one_family() {
        let rows = vec![
            ContractorRow { id: 1, name: "LOCKHEED MARTIN CORP".into(), lat: 39.0, lon: -77.0, parent: "LOCKHEED MARTIN CORP".into() },
            ContractorRow { id: 2, name: "LOCKHEED MARTIN SPACE".into(), lat: 40.0, lon: -76.0, parent: "LOCKHEED MARTIN CORP".into() },
            ContractorRow { id: 3, name: "SOLO YARD".into(), lat: 41.0, lon: -75.0, parent: String::new() },
        ];
        let families = group_families(&rows);
        assert_eq!(families.len(), 2);
        let lockheed = families.iter().find(|f| f.key == "LOCKHEED MARTIN CORP").unwrap();
        assert_eq!(lockheed.members.len(), 2);
    }

    #[test]
    fn clamps_continental_camera_box_to_one_degree() {
        let (west, south, east, north) = clamp_firms_box(-125.0, 24.0, -66.0, 50.0, 39.5, -98.5);
        assert!(east - west <= 1.0 + 1e-9);
        assert!(north - south <= 1.0 + 1e-9);
        assert!((east - west - 1.0).abs() < 1e-9);
        assert!((north - south - 1.0).abs() < 1e-9);
        assert!((west - (-99.0)).abs() < 1e-9);
        assert!((south - 39.0).abs() < 1e-9);
    }

    #[test]
    fn skips_paid_ais_when_remaining_credits_are_10() {
        struct Rec(Vec<String>);
        impl Get for Rec {
            fn get(&mut self, url: &str) -> Result<HttpResponse, ()> {
                let path = url.split('?').next().unwrap_or("").to_string();
                assert!(!path.contains("ownership") && !path.contains("vessel_find") && !path.contains("vessel_bulk"));
                self.0.push(path);
                Ok(HttpResponse { status: 200, body: "{\"remaining\":10}".into() })
            }
        }
        let mut http = Rec(Vec::new());
        let mut fleet = FleetFile::default();
        let mut positions = HashMap::new();
        let mut credits = 0u32;
        let mut unavailable = false;
        let lookups = [Lookup { name: "LOCKHEED MARTIN".into(), family: "LOCKHEED MARTIN CORP".into() }];
        let outcome = refresh_ais("test-key", &lookups, &[], &mut fleet, &mut positions, &mut credits, &mut unavailable, 1_700_000_000, &mut http, &mut |_| {});
        assert!(!http.0.is_empty());
        assert!(http.0.iter().all(|path| path.ends_with("/api/v0/stat")));
        assert_eq!(credits, 0);
        assert!(outcome.vessels.is_empty());
        assert!(!outcome.paid_disabled);
    }

    #[test]
    fn drops_fire_30km_and_keeps_10km() {
        let site = SiteRef { lat: 40.0, lon: -105.0, family: "LOCKHEED MARTIN".into() };
        let near = north_of(site.lat, site.lon, 10.0);
        let far = north_of(site.lat, site.lon, 30.0);
        let kept = filter_fires(
            &[ParsedFire { lat: near.0, lon: near.1 }, ParsedFire { lat: far.0, lon: far.1 }],
            &[site],
        );
        assert_eq!(kept.len(), 1);
        assert!((kept[0].lat - near.0).abs() < 1e-6);
        assert_eq!(kept[0].name, "LOCKHEED MARTIN fire");
        assert!(kept[0].id.starts_with("firms-"));
    }

    fn north_of(lat: f64, lon: f64, km: f64) -> (f64, f64) {
        (lat + (km / 6371.0).to_degrees(), lon)
    }
}
