use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use rusqlite::{params, Connection};
use serde::Serialize;
use serde_json::Value;

const RISKY_PORTS: &[i64] = &[
    21, 23, 25, 110, 143, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200, 11211, 27017,
];

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Counts {
    pub contractors: i64,
    pub dams: i64,
    pub datacenters: i64,
    pub skipped: i64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CatalogStatus {
    pub contractors: i64,
    pub dams: i64,
    pub datacenters: i64,
    pub skipped: i64,
    pub gev_missing: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ContractorPoint {
    pub id: i64,
    pub name: String,
    pub category: String,
    pub lat: f64,
    pub lon: f64,
    pub city: String,
    pub state: String,
    pub uei: String,
    pub cage: String,
    pub risk_score: i64,
    pub risk_severity: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FacilityPoint {
    pub id: String,
    pub kind: String,
    pub name: String,
    pub operator: String,
    pub lat: f64,
    pub lon: f64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ContractorHit {
    pub id: i64,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub risk_score: i64,
    pub risk_severity: String,
    pub distance_km: f64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FacilityHit {
    pub id: String,
    pub kind: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub distance_km: f64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Nearby {
    pub facilities: Vec<FacilityHit>,
    pub contractors: Vec<ContractorHit>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SearchHit {
    pub kind: String,
    pub id: String,
    pub name: String,
    pub subtitle: String,
    pub lat: f64,
    pub lon: f64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AskHit {
    pub kind: String,
    pub id: String,
    pub name: String,
    pub subtitle: String,
    pub lat: f64,
    pub lon: f64,
    pub risk_score: i64,
    pub risk_severity: String,
    pub distance_km: Option<f64>,
    pub count: i64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AskResult {
    pub total: i64,
    pub hits: Vec<AskHit>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SharedCve {
    pub id: String,
    pub contractor_count: i64,
    pub max_score: Option<f64>,
    pub severity: String,
    pub contractor_ids: Vec<i64>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SharedExposure {
    pub cves: Vec<SharedCve>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DamContractor {
    pub id: i64,
    pub name: String,
    pub risk_score: i64,
    pub distance_km: f64,
}
pub fn import_contractors_only(db_path: &Path, contractors: &Path) -> Result<Counts, String> {
    require_file(contractors)?;
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let _ = std::fs::remove_file(db_path);
    let conn = Connection::open(db_path).map_err(|e| e.to_string())?;
    conn.execute_batch(
        "
        CREATE TABLE contractors (
          id INTEGER PRIMARY KEY, name TEXT, category TEXT, lat REAL, lon REAL,
          city TEXT, state TEXT, uei TEXT, cage TEXT, risk_score INTEGER,
          risk_severity TEXT, on_prem_count INTEGER NOT NULL DEFAULT 0, payload_json TEXT
        );
        CREATE TABLE facilities (
          row_id INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, kind TEXT, name TEXT,
          operator TEXT, lat REAL, lon REAL, source TEXT, license TEXT, payload_json TEXT
        );
        CREATE VIRTUAL TABLE contractor_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE VIRTUAL TABLE facility_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE cve_hits (cve TEXT, contractor_id INTEGER, base_score REAL, severity TEXT, scored INTEGER);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        ",
    )
    .map_err(|e| e.to_string())?;
    let loaded = load_contractors(contractors)?;
    let tx = conn.unchecked_transaction().map_err(|e| e.to_string())?;
    let mut skipped = 0_i64;
    {
        let mut insert = tx
            .prepare(
                "INSERT INTO contractors (id, name, category, lat, lon, city, state, uei, cage, risk_score, risk_severity, on_prem_count, payload_json)
                 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)",
            )
            .map_err(|e| e.to_string())?;
        let mut rtree = tx
            .prepare("INSERT INTO contractor_rtree (id, min_lon, max_lon, min_lat, max_lat) VALUES (?1,?2,?3,?4,?5)")
            .map_err(|e| e.to_string())?;
        for contractor in &loaded {
            let Some((lat, lon)) = coord(contractor.get("lat"), contractor.get("lon")) else {
                skipped += 1;
                continue;
            };
            let id = contractor.get("id").and_then(|v| v.as_i64()).unwrap_or(-1);
            if id < 0 {
                skipped += 1;
                continue;
            }
            let (score, severity) = risk_score(contractor);
            insert
                .execute(params![
                    id,
                    text(contractor, "name"),
                    text(contractor, "category"),
                    lat,
                    lon,
                    text(contractor, "city"),
                    text(contractor, "state"),
                    text(contractor, "uei"),
                    text(contractor, "cage"),
                    score,
                    severity,
                    on_prem_count(contractor),
                    contractor.to_string(),
                ])
                .map_err(|e| e.to_string())?;
            rtree
                .execute(params![id, lon - 0.01, lon + 0.01, lat - 0.01, lat + 0.01])
                .map_err(|e| e.to_string())?;
        }
    }
    let counts = count_tables(&tx, skipped)?;
    tx.commit().map_err(|e| e.to_string())?;
    Ok(counts)
}


#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DamAtRisk {
    pub dam_id: String,
    pub dam_name: String,
    pub lat: f64,
    pub lon: f64,
    pub contractors: Vec<DamContractor>,
}

pub struct Sources {
    pub contractors: PathBuf,
    pub dams: PathBuf,
    pub datacenters: PathBuf,
}

pub fn default_sources(repo: &Path, gev: &Path) -> Sources {
    Sources {
        contractors: repo.join("frontend/static/contractors.json"),
        dams: gev.join("src/data/local_data/dams/dams.geojsonl"),
        datacenters: gev.join("src/data/local_data/datacenters/datacenters.geojsonl"),
    }
}

pub fn open_or_rebuild(db_path: &Path, sources: &Sources) -> Result<Counts, String> {
    if let Ok(conn) = Connection::open(db_path) {
        if fresh(&conn, sources) {
            return counts_of(&conn);
        }
    }
    import_catalog(db_path, sources)
}

pub fn import_catalog(db_path: &Path, sources: &Sources) -> Result<Counts, String> {
    require_file(&sources.contractors)?;
    require_file(&sources.dams)?;
    require_file(&sources.datacenters)?;
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let _ = std::fs::remove_file(db_path);
    let conn = Connection::open(db_path).map_err(|e| e.to_string())?;
    conn.execute_batch(
        "
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE contractors (
          id INTEGER PRIMARY KEY,
          name TEXT,
          category TEXT,
          lat REAL,
          lon REAL,
          city TEXT,
          state TEXT,
          uei TEXT,
          cage TEXT,
          risk_score INTEGER,
          risk_severity TEXT,
          on_prem_count INTEGER NOT NULL DEFAULT 0,
          payload_json TEXT
        );
        CREATE TABLE facilities (
          row_id INTEGER PRIMARY KEY,
          id TEXT UNIQUE NOT NULL,
          kind TEXT,
          name TEXT,
          operator TEXT,
          lat REAL,
          lon REAL,
          source TEXT,
          license TEXT,
          payload_json TEXT
        );
        CREATE VIRTUAL TABLE contractor_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE VIRTUAL TABLE facility_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE cve_hits (
          cve TEXT NOT NULL,
          contractor_id INTEGER NOT NULL,
          base_score REAL,
          severity TEXT,
          scored INTEGER NOT NULL
        );
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        ",
    )
    .map_err(|e| e.to_string())?;

    let mut skipped = 0_i64;
    let contractors = load_contractors(&sources.contractors)?;
    let tx = conn.unchecked_transaction().map_err(|e| e.to_string())?;
    {
        let mut insert = tx
            .prepare(
                "INSERT INTO contractors (id, name, category, lat, lon, city, state, uei, cage, risk_score, risk_severity, on_prem_count, payload_json)
                 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)",
            )
            .map_err(|e| e.to_string())?;
        let mut rtree = tx
            .prepare("INSERT INTO contractor_rtree (id, min_lon, max_lon, min_lat, max_lat) VALUES (?1,?2,?3,?4,?5)")
            .map_err(|e| e.to_string())?;
        let mut cve = tx
            .prepare("INSERT INTO cve_hits (cve, contractor_id, base_score, severity, scored) VALUES (?1,?2,?3,?4,?5)")
            .map_err(|e| e.to_string())?;
        for contractor in &contractors {
            let Some((lat, lon)) = coord(contractor.get("lat"), contractor.get("lon")) else {
                skipped += 1;
                continue;
            };
            let id = contractor.get("id").and_then(|v| v.as_i64()).unwrap_or(-1);
            if id < 0 {
                skipped += 1;
                continue;
            }
            let (score, severity) = risk_score(contractor);
            let on_prem = on_prem_count(contractor);
            insert
                .execute(params![
                    id,
                    text(contractor, "name"),
                    text(contractor, "category"),
                    lat,
                    lon,
                    text(contractor, "city"),
                    text(contractor, "state"),
                    text(contractor, "uei"),
                    text(contractor, "cage"),
                    score,
                    severity,
                    on_prem,
                    contractor.to_string(),
                ])
                .map_err(|e| e.to_string())?;
            rtree
                .execute(params![id, lon - 0.01, lon + 0.01, lat - 0.01, lat + 0.01])
                .map_err(|e| e.to_string())?;
            for hit in cve_rows(contractor) {
                cve.execute(params![hit.0, id, hit.1, hit.2, hit.3])
                    .map_err(|e| e.to_string())?;
            }
        }
    }
    skipped += import_facilities(&tx, &sources.dams, "dam")?;
    skipped += import_facilities(&tx, &sources.datacenters, "datacenter")?;
    let counts = count_tables(&tx, skipped)?;
    write_meta(&tx, sources)?;
    tx.commit().map_err(|e| e.to_string())?;
    Ok(counts)
}

fn import_facilities(conn: &Connection, path: &Path, kind: &str) -> Result<i64, String> {
    let file = File::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut skipped = 0_i64;
    let mut insert = conn
        .prepare(
            "INSERT INTO facilities (id, kind, name, operator, lat, lon, source, license, payload_json)
             VALUES (?1,?2,?3,?4,?5,?6,'OpenStreetMap','ODbL',?7)",
        )
        .map_err(|e| e.to_string())?;
    let mut rtree = conn
        .prepare("INSERT INTO facility_rtree (id, min_lon, max_lon, min_lat, max_lat) VALUES (?1,?2,?3,?4,?5)")
        .map_err(|e| e.to_string())?;
    for (lineno, line) in BufReader::new(file).lines().enumerate() {
        let line = line.map_err(|e| e.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        let feature: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => return Err(format!("{}:{}: {e}", path.display(), lineno + 1)),
        };
        let Some(point) = feature_point(&feature) else {
            skipped += 1;
            continue;
        };
        let raw_id = feature
            .get("id")
            .map(|v| match v {
                Value::String(s) => s.clone(),
                other => other.to_string(),
            })
            .unwrap_or_else(|| format!("line{}", lineno + 1));
        let id = format!("{kind}:{raw_id}:{lineno}");
        let props = feature.get("properties").cloned().unwrap_or(Value::Null);
        let tags = props.get("tags").cloned().unwrap_or(Value::Null);
        let name = first_text(&[&props, &tags], "name").unwrap_or_else(|| "unnamed".into());
        let operator = first_text(&[&props, &tags], "operator").unwrap_or_default();
        insert
            .execute(params![id, kind, name, operator, point.lat, point.lon, feature.to_string()])
            .map_err(|e| e.to_string())?;
        let row_id = conn.last_insert_rowid();
        rtree
            .execute(params![row_id, point.min_lon, point.max_lon, point.min_lat, point.max_lat])
            .map_err(|e| e.to_string())?;
    }
    Ok(skipped)
}

struct Place {
    lat: f64,
    lon: f64,
    min_lon: f64,
    max_lon: f64,
    min_lat: f64,
    max_lat: f64,
}

fn feature_point(feature: &Value) -> Option<Place> {
    let geom = feature.get("geometry")?;
    let kind = geom.get("type").and_then(|v| v.as_str()).unwrap_or("");
    let coords = geom.get("coordinates")?;
    let mut pts = Vec::new();
    match kind {
        "Point" => push_pos(coords, &mut pts),
        "LineString" | "MultiPoint" => push_line(coords, &mut pts),
        "Polygon" => {
            if let Some(ring) = coords.as_array().and_then(|a| a.first()) {
                push_line(ring, &mut pts);
            }
        }
        "MultiLineString" => {
            if let Some(lines) = coords.as_array() {
                for line in lines {
                    push_line(line, &mut pts);
                }
            }
        }
        "MultiPolygon" => {
            if let Some(poly) = coords.as_array().and_then(|a| a.first()).and_then(|p| p.as_array()) {
                if let Some(ring) = poly.first() {
                    push_line(ring, &mut pts);
                }
            }
        }
        _ => {}
    }
    if pts.is_empty() {
        return None;
    }
    let (sum_lon, sum_lat) = pts.iter().fold((0.0, 0.0), |acc, (lon, lat)| (acc.0 + lon, acc.1 + lat));
    let n = pts.len() as f64;
    let lon = sum_lon / n;
    let lat = sum_lat / n;
    if !lon.is_finite() || !lat.is_finite() {
        return None;
    }
    let mut min_lon = pts.iter().map(|p| p.0).fold(f64::INFINITY, f64::min);
    let mut max_lon = pts.iter().map(|p| p.0).fold(f64::NEG_INFINITY, f64::max);
    let mut min_lat = pts.iter().map(|p| p.1).fold(f64::INFINITY, f64::min);
    let mut max_lat = pts.iter().map(|p| p.1).fold(f64::NEG_INFINITY, f64::max);
    if kind == "Point" || (max_lon - min_lon) < 0.02 {
        min_lon = lon - 0.01;
        max_lon = lon + 0.01;
        min_lat = lat - 0.01;
        max_lat = lat + 0.01;
    }
    Some(Place { lat, lon, min_lon, max_lon, min_lat, max_lat })
}

fn push_pos(value: &Value, out: &mut Vec<(f64, f64)>) {
    let Some(arr) = value.as_array() else { return };
    if arr.len() < 2 {
        return;
    }
    if let (Some(lon), Some(lat)) = (arr[0].as_f64(), arr[1].as_f64()) {
        if lon.is_finite() && lat.is_finite() {
            out.push((lon, lat));
        }
    }
}

fn push_line(value: &Value, out: &mut Vec<(f64, f64)>) {
    let Some(arr) = value.as_array() else { return };
    for item in arr {
        push_pos(item, out);
    }
}

fn load_contractors(path: &Path) -> Result<Vec<Value>, String> {
    let file = File::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let root: Value = serde_json::from_reader(file).map_err(|e| format!("{}: {e}", path.display()))?;
    let list = root
        .get("contractors")
        .and_then(|v| v.as_array())
        .ok_or_else(|| format!("{}: missing contractors array", path.display()))?;
    Ok(list.clone())
}

fn require_file(path: &Path) -> Result<(), String> {
    if path.is_file() {
        Ok(())
    } else {
        Err(path.display().to_string())
    }
}

fn text(value: &Value, key: &str) -> String {
    match value.get(key) {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Number(n)) => n.to_string(),
        _ => String::new(),
    }
}

fn first_text(nodes: &[&Value], key: &str) -> Option<String> {
    for node in nodes {
        let value = text(node, key);
        if !value.is_empty() {
            return Some(value);
        }
    }
    None
}

fn coord(lat: Option<&Value>, lon: Option<&Value>) -> Option<(f64, f64)> {
    let lat = lat?.as_f64()?;
    let lon = lon?.as_f64()?;
    if lat.is_finite() && lon.is_finite() { Some((lat, lon)) } else { None }
}

fn on_prem_count(contractor: &Value) -> i64 {
    contractor
        .get("osint")
        .and_then(|o| o.get("onprem_network"))
        .and_then(|n| n.get("on_prem_count"))
        .and_then(|v| v.as_i64().or_else(|| v.as_f64().map(|n| n as i64)))
        .unwrap_or(0)
}

fn cve_rows(contractor: &Value) -> Vec<(String, Option<f64>, String, i64)> {
    let mut rows: HashMap<String, (Option<f64>, String, i64)> = HashMap::new();
    if let Some(scores) = contractor
        .pointer("/osint/nvd_cvss/scores")
        .and_then(|v| v.as_object())
    {
        for (key, rec) in scores {
            let Some(id) = normalize_cve(key) else { continue };
            let score = rec.get("base_score").and_then(|v| v.as_f64());
            let severity = rec.get("severity").and_then(|v| v.as_str()).unwrap_or("").to_string();
            rows.insert(id, (score, severity, 1));
        }
    }
    if let Some(vulns) = contractor.pointer("/shodan/vulns").and_then(|v| v.as_array()) {
        for vuln in vulns {
            let raw = vuln.get("cve").and_then(|v| v.as_str()).unwrap_or("");
            let Some(id) = normalize_cve(raw) else { continue };
            rows.entry(id).or_insert((None, String::new(), 0));
        }
    }
    rows.into_iter().map(|(id, (score, sev, scored))| (id, score, sev, scored)).collect()
}

pub fn normalize_cve(raw: &str) -> Option<String> {
    let upper = raw.trim().to_uppercase();
    if upper.is_empty() {
        return None;
    }
    let body = upper.trim_start_matches("CVE").trim_start_matches('-');
    let mut parts = body.split('-').filter(|p| !p.is_empty());
    let year = parts.next()?;
    let num = parts.next()?;
    if year.len() != 4 || !year.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    if !num.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    Some(format!("CVE-{year}-{num}"))
}

fn risk_score(c: &Value) -> (i64, String) {
    let s = c.get("shodan").cloned().unwrap_or(Value::Null);
    let o = c.get("osint").cloned().unwrap_or(Value::Null);
    let dns = o.get("dns").cloned().unwrap_or(Value::Null);
    let web = o.get("web").cloned().unwrap_or(Value::Null);
    let ct = o.get("ct").cloned().unwrap_or(Value::Null);
    let sip = o.get("shodan_ip").cloned().unwrap_or(Value::Null);
    let sip_agg = sip.get("aggregate").cloned().unwrap_or(Value::Null);
    let mut score = 0.0;

    let exposed = if js_truthy(sip.get("ips_enriched")) {
        num(sip.get("ips_enriched"))
    } else if js_truthy(s.get("total_hosts")) {
        num(s.get("total_hosts"))
    } else {
        0.0
    };
    if exposed > 0.0 {
        score += (exposed / 20.0).min(1.0) * 20.0;
    }
    let crit = sip_agg.get("critical_findings").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0);
    if crit > 0 {
        score += ((crit * 5) as f64).min(15.0);
    }
    let vuln_count = s.get("vulns").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0);
    let nvd = o.get("nvd_cvss").cloned().unwrap_or(Value::Null);
    let summary = nvd.get("summary").cloned().unwrap_or(Value::Null);
    let scored = num(nvd.get("scored_cves"));
    if vuln_count > 0 {
        if scored > 0.0 {
            let weighted = (num(summary.get("critical")) * 4.0
                + num(summary.get("high")) * 3.0
                + num(summary.get("medium")) * 2.0
                + num(summary.get("low")))
                / (scored * 4.0);
            score += weighted * 30.0;
        } else {
            score += (vuln_count as f64 / 15.0).min(1.0) * 30.0;
        }
    }
    let danger = o
        .pointer("/service_risk/danger_summary")
        .cloned()
        .unwrap_or(Value::Null);
    let critical_svcs = num(danger.get("critical"));
    let high_svcs = num(danger.get("high"));
    if critical_svcs > 0.0 || high_svcs > 0.0 {
        score += ((critical_svcs * 3.0 + high_svcs * 1.5) / 8.0).min(1.0) * 15.0;
    } else if let Some(ports) = s.get("top_ports").and_then(|v| v.as_array()) {
        let risky = ports
            .iter()
            .filter(|p| RISKY_PORTS.contains(&p.get("port").and_then(|v| v.as_i64()).unwrap_or(-1)))
            .count();
        if risky > 0 {
            score += (risky as f64 / 5.0).min(1.0) * 15.0;
        }
    }
    let dmarc = dns.get("dmarc_policy").and_then(|v| v.as_str()).unwrap_or("");
    if dmarc.is_empty() || dmarc == "not_set" || dmarc == "none" {
        score += 10.0;
    } else if dmarc == "quarantine" {
        score += 3.0;
    }
    if let Some(web_sec) = web.get("security_score").and_then(|v| v.as_f64()) {
        score += ((100.0 - web_sec) / 100.0).max(0.0) * 10.0;
    } else if js_truthy(dns.get("queried")) {
        score += 5.0;
    }
    let subs = ct.get("subdomains").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0);
    if subs > 10 {
        score += ((subs as f64 - 10.0) / 40.0).min(1.0) * 10.0;
    }
    if s
        .get("sample_hosts")
        .and_then(|v| v.as_array())
        .into_iter()
        .flatten()
        .any(|host| host.get("ssl_expires").and_then(|v| v.as_str()).is_some_and(ssl_expired))
    {
        score += 5.0;
    }
    let score = score.round().min(100.0) as i64;
    let severity = if score >= 70 {
        "critical"
    } else if score >= 40 {
        "high"
    } else if score >= 15 {
        "medium"
    } else {
        "low"
    };
    (score, severity.into())
}

fn js_or(primary: Option<&Value>, fallback: Option<&Value>) -> f64 {
    if js_truthy(primary) {
        return num(primary);
    }
    if js_truthy(fallback) {
        return num(fallback);
    }
    0.0
}

fn js_truthy(value: Option<&Value>) -> bool {
    match value {
        None | Some(Value::Null) => false,
        Some(Value::Bool(v)) => *v,
        Some(Value::Number(n)) => n.as_f64().unwrap_or(0.0) != 0.0,
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

fn num(value: Option<&Value>) -> f64 {
    value.and_then(|v| v.as_f64().or_else(|| v.as_i64().map(|n| n as f64))).unwrap_or(0.0)
}

fn ssl_expired(raw: &str) -> bool {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(raw) {
        return dt < chrono::Utc::now();
    }
    let head = raw.get(..10).unwrap_or(raw);
    if let Ok(date) = chrono::NaiveDate::parse_from_str(head, "%Y-%m-%d") {
        return date < chrono::Utc::now().date_naive();
    }
    false
}

fn write_meta(conn: &Connection, sources: &Sources) -> Result<(), String> {
    let mut stmt = conn
        .prepare("INSERT INTO meta (key, value) VALUES (?1, ?2)")
        .map_err(|e| e.to_string())?;
    for (key, path) in [
        ("contractors", &sources.contractors),
        ("dams", &sources.dams),
        ("datacenters", &sources.datacenters),
    ] {
        stmt.execute(params![key, mtime(path)])
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn mtime(path: &Path) -> String {
    std::fs::metadata(path)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
        .map(|d| d.as_secs().to_string())
        .unwrap_or_default()
}

fn fresh(conn: &Connection, sources: &Sources) -> bool {
    for (key, path) in [
        ("contractors", &sources.contractors),
        ("dams", &sources.dams),
        ("datacenters", &sources.datacenters),
    ] {
        let stored: Result<String, _> = conn.query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0));
        if stored.ok().as_deref() != Some(mtime(path).as_str()) {
            return false;
        }
    }
    true
}

fn counts_of(conn: &Connection) -> Result<Counts, String> {
    count_tables(conn, skipped_of(conn))
}

fn skipped_of(conn: &Connection) -> i64 {
    conn.query_row("SELECT value FROM meta WHERE key = 'skipped'", [], |r| r.get::<_, String>(0))
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0)
}

fn count_tables(conn: &Connection, skipped: i64) -> Result<Counts, String> {
    let contractors = scalar(conn, "SELECT COUNT(*) FROM contractors")?;
    let dams = scalar(conn, "SELECT COUNT(*) FROM facilities WHERE kind = 'dam'")?;
    let datacenters = scalar(conn, "SELECT COUNT(*) FROM facilities WHERE kind = 'datacenter'")?;
    let _ = conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('skipped', ?1)", [skipped.to_string()]);
    Ok(Counts { contractors, dams, datacenters, skipped })
}

fn scalar(conn: &Connection, sql: &str) -> Result<i64, String> {
    conn.query_row(sql, [], |r| r.get(0)).map_err(|e| e.to_string())
}

pub fn counts(conn: &Connection) -> Result<Counts, String> {
    counts_of(conn)
}

const PLOT_NAME_SQL: &str = "name IS NOT NULL AND trim(name) != '' AND lower(trim(name)) NOT IN ('unnamed', 'data not collected', 'not collected')";

pub fn contractors(conn: &Connection) -> Result<Vec<ContractorPoint>, String> {
    let mut stmt = conn
        .prepare(&format!(
            "SELECT id, name, category, lat, lon, city, state, uei, cage, risk_score, risk_severity FROM contractors WHERE {PLOT_NAME_SQL}"
        ))
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map([], |r| {
            Ok(ContractorPoint {
                id: r.get(0)?,
                name: r.get(1)?,
                category: r.get(2)?,
                lat: r.get(3)?,
                lon: r.get(4)?,
                city: r.get(5)?,
                state: r.get(6)?,
                uei: r.get(7)?,
                cage: r.get(8)?,
                risk_score: r.get(9)?,
                risk_severity: r.get(10)?,
            })
        })
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

pub fn facilities(conn: &Connection) -> Result<Vec<FacilityPoint>, String> {
    let mut stmt = conn
        .prepare(&format!(
            "SELECT id, kind, name, operator, lat, lon FROM facilities WHERE {PLOT_NAME_SQL}"
        ))
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map([], |r| {
            Ok(FacilityPoint {
                id: r.get(0)?,
                kind: r.get(1)?,
                name: r.get(2)?,
                operator: r.get(3)?,
                lat: r.get(4)?,
                lon: r.get(5)?,
            })
        })
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

pub fn payload(conn: &Connection, kind: &str, id: &str) -> Result<Option<Value>, String> {
    let sql = if kind == "contractor" {
        "SELECT payload_json FROM contractors WHERE id = ?1"
    } else {
        "SELECT payload_json FROM facilities WHERE id = ?1"
    };
    let raw: Result<String, _> = conn.query_row(sql, [id], |r| r.get(0));
    match raw {
        Ok(text) => serde_json::from_str(&text).map(Some).map_err(|e| e.to_string()),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

pub fn nearby(conn: &Connection, target_kind: &str, id: &str, radius_km: f64) -> Result<Nearby, String> {
    let (lat, lon, self_contractor, self_facility) = if target_kind == "contractor" {
        let id_num: i64 = id.parse().map_err(|_| format!("bad contractor id {id}"))?;
        let (lat, lon): (f64, f64) = conn
            .query_row("SELECT lat, lon FROM contractors WHERE id = ?1", [id_num], |r| Ok((r.get(0)?, r.get(1)?)))
            .map_err(|_| format!("contractor {id} not found"))?;
        (lat, lon, Some(id_num), None)
    } else {
        let (lat, lon): (f64, f64) = conn
            .query_row("SELECT lat, lon FROM facilities WHERE id = ?1", [id], |r| Ok((r.get(0)?, r.get(1)?)))
            .map_err(|_| format!("facility {id} not found"))?;
        (lat, lon, None, Some(id.to_string()))
    };
    let mut hits: Vec<(f64, bool, i64, String)> = Vec::new();
    for (cid, clat, clon) in contractor_window(conn, lat, lon, radius_km)? {
        if self_contractor == Some(cid) {
            continue;
        }
        let dist = haversine_km(lat, lon, clat, clon);
        if dist <= radius_km {
            hits.push((dist, true, cid, String::new()));
        }
    }
    for (fid, row_id, flat, flon) in facility_window(conn, lat, lon, radius_km)? {
        if self_facility.as_deref() == Some(fid.as_str()) {
            continue;
        }
        let dist = haversine_km(lat, lon, flat, flon);
        if dist <= radius_km {
            hits.push((dist, false, row_id, fid));
        }
    }
    hits.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    hits.truncate(40);
    let mut facilities = Vec::new();
    let mut contractors = Vec::new();
    for (dist, is_contractor, num, fid) in hits {
        let distance_km = (dist * 10.0).round() / 10.0;
        if is_contractor {
            if let Ok(hit) = contractor_hit(conn, num, distance_km) {
                contractors.push(hit);
            }
        } else if let Ok(hit) = facility_hit(conn, &fid, distance_km) {
            facilities.push(hit);
        }
    }
    Ok(Nearby { facilities, contractors })
}

fn contractor_window(conn: &Connection, lat: f64, lon: f64, radius_km: f64) -> Result<Vec<(i64, f64, f64)>, String> {
    let (min_lon, max_lon, min_lat, max_lat) = window(lat, lon, radius_km);
    let mut stmt = conn
        .prepare(
            "SELECT c.id, c.lat, c.lon FROM contractor_rtree r
             JOIN contractors c ON c.id = r.id
             WHERE r.min_lon <= ?1 AND r.max_lon >= ?2 AND r.min_lat <= ?3 AND r.max_lat >= ?4",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![max_lon, min_lon, max_lat, min_lat], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

fn facility_window(conn: &Connection, lat: f64, lon: f64, radius_km: f64) -> Result<Vec<(String, i64, f64, f64)>, String> {
    let (min_lon, max_lon, min_lat, max_lat) = window(lat, lon, radius_km);
    let mut stmt = conn
        .prepare(
            "SELECT f.id, f.row_id, f.lat, f.lon FROM facility_rtree r
             JOIN facilities f ON f.row_id = r.id
             WHERE r.min_lon <= ?1 AND r.max_lon >= ?2 AND r.min_lat <= ?3 AND r.max_lat >= ?4",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![max_lon, min_lon, max_lat, min_lat], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)))
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

fn window(lat: f64, lon: f64, radius_km: f64) -> (f64, f64, f64, f64) {
    let lat_deg = radius_km / 111.0 + 0.02;
    let lon_deg = lat_deg / lat.to_radians().cos().abs().max(0.2);
    (lon - lon_deg, lon + lon_deg, lat - lat_deg, lat + lat_deg)
}

fn contractor_hit(conn: &Connection, id: i64, distance_km: f64) -> Result<ContractorHit, String> {
    conn.query_row(
        "SELECT id, name, lat, lon, risk_score, risk_severity FROM contractors WHERE id = ?1",
        [id],
        |r| {
            Ok(ContractorHit {
                id: r.get(0)?,
                name: r.get(1)?,
                lat: r.get(2)?,
                lon: r.get(3)?,
                risk_score: r.get(4)?,
                risk_severity: r.get(5)?,
                distance_km,
            })
        },
    )
    .map_err(|e| e.to_string())
}

fn facility_hit(conn: &Connection, id: &str, distance_km: f64) -> Result<FacilityHit, String> {
    conn.query_row(
        "SELECT id, kind, name, lat, lon FROM facilities WHERE id = ?1",
        [id],
        |r| {
            Ok(FacilityHit {
                id: r.get(0)?,
                kind: r.get(1)?,
                name: r.get(2)?,
                lat: r.get(3)?,
                lon: r.get(4)?,
                distance_km,
            })
        },
    )
    .map_err(|e| e.to_string())
}

pub fn haversine_km(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6371.0;
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let a = (dlat / 2.0).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon / 2.0).sin().powi(2);
    2.0 * r * a.sqrt().asin()
}

pub fn search(conn: &Connection, query: &str) -> Result<Vec<SearchHit>, String> {
    let q = query.trim();
    if q.is_empty() {
        return Ok(Vec::new());
    }
    let like = format!("%{}%", q.replace('%', ""));
    let mut out = Vec::new();
    let mut stmt = conn
        .prepare(
            "SELECT id, name, city, uei, lat, lon FROM contractors
             WHERE name LIKE ?1 COLLATE NOCASE OR uei LIKE ?1 COLLATE NOCASE
                OR cage LIKE ?1 COLLATE NOCASE OR city LIKE ?1 COLLATE NOCASE
             LIMIT 20",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![like], |r| {
            Ok(SearchHit {
                kind: "contractor".into(),
                id: r.get::<_, i64>(0)?.to_string(),
                name: r.get(1)?,
                subtitle: format!("{} · {}", r.get::<_, String>(2)?, r.get::<_, String>(3)?),
                lat: r.get(4)?,
                lon: r.get(5)?,
            })
        })
        .map_err(|e| e.to_string())?;
    for row in rows {
        out.push(row.map_err(|e| e.to_string())?);
    }
    let mut stmt = conn
        .prepare(
            "SELECT id, name, kind, lat, lon FROM facilities
             WHERE name LIKE ?1 COLLATE NOCASE LIMIT 20",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![like], |r| {
            Ok(SearchHit {
                kind: "facility".into(),
                id: r.get(0)?,
                name: r.get(1)?,
                subtitle: r.get(2)?,
                lat: r.get(3)?,
                lon: r.get(4)?,
            })
        })
        .map_err(|e| e.to_string())?;
    for row in rows {
        out.push(row.map_err(|e| e.to_string())?);
    }
    Ok(out)
}

pub fn shared_exposure(conn: &Connection) -> Result<SharedExposure, String> {
    let mut stmt = conn
        .prepare("SELECT cve, contractor_id, base_score, severity, scored FROM cve_hits")
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, Option<f64>>(2)?,
                r.get::<_, String>(3)?,
                r.get::<_, i64>(4)?,
            ))
        })
        .map_err(|e| e.to_string())?;
    struct Acc {
        ids: HashSet<i64>,
        max_score: Option<f64>,
        severity: String,
        scored: bool,
        high: bool,
    }
    let mut map: HashMap<String, Acc> = HashMap::new();
    for row in rows {
        let (cve, id, score, severity, scored) = row.map_err(|e| e.to_string())?;
        let acc = map.entry(cve).or_insert(Acc {
            ids: HashSet::new(),
            max_score: None,
            severity: String::new(),
            scored: false,
            high: false,
        });
        acc.ids.insert(id);
        if scored == 1 {
            acc.scored = true;
            if severity.eq_ignore_ascii_case("CRITICAL") || severity.eq_ignore_ascii_case("HIGH") {
                acc.high = true;
            }
            if let Some(score) = score {
                if acc.max_score.map(|cur| score > cur).unwrap_or(true) {
                    acc.max_score = Some(score);
                    acc.severity = severity.to_uppercase();
                }
            } else if acc.severity.is_empty() && acc.high {
                acc.severity = severity.to_uppercase();
            }
        }
    }
    let mut cves: Vec<SharedCve> = map
        .into_iter()
        .filter_map(|(id, acc)| {
            if acc.ids.len() < 2 {
                return None;
            }
            if acc.scored && !acc.high {
                return None;
            }
            let mut contractor_ids: Vec<i64> = acc.ids.into_iter().collect();
            contractor_ids.sort_unstable();
            Some(SharedCve {
                id,
                contractor_count: contractor_ids.len() as i64,
                max_score: if acc.scored { acc.max_score } else { None },
                severity: if acc.scored {
                    if acc.severity.is_empty() { "HIGH".into() } else { acc.severity }
                } else {
                    "unscored".into()
                },
                contractor_ids,
            })
        })
        .collect();
    cves.sort_by(|a, b| {
        b.contractor_count
            .cmp(&a.contractor_count)
            .then(b.max_score.unwrap_or(-1.0).partial_cmp(&a.max_score.unwrap_or(-1.0)).unwrap_or(std::cmp::Ordering::Equal))
    });
    cves.truncate(30);
    Ok(SharedExposure { cves })
}

pub fn onprem_near_dams(conn: &Connection, radius_km: f64) -> Result<Vec<DamAtRisk>, String> {
    let mut stmt = conn
        .prepare(
            "SELECT id, name, lat, lon, risk_score FROM contractors
             WHERE on_prem_count > 0 AND risk_severity IN ('critical', 'high')",
        )
        .map_err(|e| e.to_string())?;
    let contractors = stmt
        .query_map([], |r| Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?, r.get::<_, f64>(2)?, r.get::<_, f64>(3)?, r.get::<_, i64>(4)?)))
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    let mut grouped: HashMap<String, (String, f64, f64, Vec<DamContractor>)> = HashMap::new();
    for (id, name, lat, lon, risk_score) in contractors {
        for (fid, flat, flon, fname) in dams_near(conn, lat, lon, radius_km)? {
            let dist = haversine_km(lat, lon, flat, flon);
            if dist > radius_km {
                continue;
            }
            let entry = grouped.entry(fid.clone()).or_insert((fname, flat, flon, Vec::new()));
            entry.3.push(DamContractor {
                id,
                name: name.clone(),
                risk_score,
                distance_km: (dist * 10.0).round() / 10.0,
            });
        }
    }
    let mut dams: Vec<DamAtRisk> = grouped
        .into_iter()
        .map(|(dam_id, (dam_name, lat, lon, mut contractors))| {
            contractors.sort_by(|a, b| a.distance_km.partial_cmp(&b.distance_km).unwrap_or(std::cmp::Ordering::Equal));
            contractors.truncate(8);
            DamAtRisk { dam_id, dam_name, lat, lon, contractors }
        })
        .filter(|d| !d.contractors.is_empty())
        .collect();
    dams.sort_by(|a, b| {
        b.contractors
            .len()
            .cmp(&a.contractors.len())
            .then_with(|| {
                let an = a.contractors.first().map(|c| c.distance_km).unwrap_or(f64::MAX);
                let bn = b.contractors.first().map(|c| c.distance_km).unwrap_or(f64::MAX);
                an.partial_cmp(&bn).unwrap_or(std::cmp::Ordering::Equal)
            })
    });
    dams.truncate(20);
    Ok(dams)
}

fn dams_near(conn: &Connection, lat: f64, lon: f64, radius_km: f64) -> Result<Vec<(String, f64, f64, String)>, String> {
    let (min_lon, max_lon, min_lat, max_lat) = window(lat, lon, radius_km);
    let mut stmt = conn
        .prepare(
            "SELECT f.id, f.lat, f.lon, f.name FROM facility_rtree r
             JOIN facilities f ON f.row_id = r.id
             WHERE f.kind = 'dam' AND r.min_lon <= ?1 AND r.max_lon >= ?2 AND r.min_lat <= ?3 AND r.max_lat >= ?4",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![max_lon, min_lon, max_lat, min_lat], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)))
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

pub fn contractor_id_by_name(conn: &Connection, name: &str) -> Result<(i64, f64, f64), String> {
    conn.query_row(
        "SELECT id, lat, lon FROM contractors WHERE name = ?1",
        [name],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
    )
    .map_err(|e| e.to_string())
}

pub fn first_facility(conn: &Connection, kind: &str) -> Result<String, String> {
    conn.query_row("SELECT id FROM facilities WHERE kind = ?1 ORDER BY row_id LIMIT 1", [kind], |r| r.get(0))
        .map_err(|e| e.to_string())
}

struct ContractorRow {
    id: i64,
    name: String,
    lat: f64,
    lon: f64,
    risk_score: i64,
    risk_severity: String,
    on_prem_count: i64,
}

fn map_contractor(row: &rusqlite::Row) -> rusqlite::Result<ContractorRow> {
    Ok(ContractorRow {
        id: row.get(0)?,
        name: row.get(1)?,
        lat: row.get(2)?,
        lon: row.get(3)?,
        risk_score: row.get(4)?,
        risk_severity: row.get(5)?,
        on_prem_count: row.get(6)?,
    })
}

fn query_contractors(conn: &Connection, sql: &str, params: impl rusqlite::Params) -> Result<Vec<ContractorRow>, String> {
    let mut stmt = conn.prepare(sql).map_err(|e| e.to_string())?;
    let rows = stmt.query_map(params, map_contractor).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

fn empty_ask() -> AskResult {
    AskResult { total: 0, hits: Vec::new() }
}

fn contractor_hits(rows: Vec<ContractorRow>) -> AskResult {
    let total = rows.len() as i64;
    let hits = rows
        .into_iter()
        .take(200)
        .map(|row| AskHit {
            kind: "contractor".into(),
            id: row.id.to_string(),
            name: row.name,
            subtitle: format!("{} · {} on-prem", row.risk_severity, row.on_prem_count),
            lat: row.lat,
            lon: row.lon,
            risk_score: row.risk_score,
            risk_severity: row.risk_severity,
            distance_km: None,
            count: 0,
        })
        .collect();
    AskResult { total, hits }
}

fn json1_missing(err: &str) -> bool {
    let lower = err.to_ascii_lowercase();
    lower.contains("no such function") && (lower.contains("json_extract") || lower.contains("json_each"))
}

fn sort_contractors(rows: &mut [ContractorRow]) {
    rows.sort_by(|a, b| {
        b.risk_score
            .cmp(&a.risk_score)
            .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });
}

fn payload_rows(conn: &Connection) -> Result<Vec<(ContractorRow, String)>, String> {
    let mut stmt = conn
        .prepare(
            "SELECT id, name, lat, lon, risk_score, risk_severity, on_prem_count, COALESCE(payload_json, '')
             FROM contractors",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map([], |row| Ok((map_contractor(row)?, row.get::<_, String>(7)?)))
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

fn scan_dmarc(conn: &Connection, policy: &str) -> Result<Vec<ContractorRow>, String> {
    let mut rows = Vec::new();
    for (row, payload) in payload_rows(conn)? {
        let Ok(value) = serde_json::from_str::<Value>(&payload) else {
            continue;
        };
        let found = value
            .get("osint")
            .and_then(|node| node.get("dns"))
            .and_then(|node| node.get("dmarc_policy"))
            .and_then(|node| node.as_str());
        if found == Some(policy) {
            rows.push(row);
        }
    }
    sort_contractors(&mut rows);
    Ok(rows)
}

fn port_in_payload(payload: &str, port: i64) -> bool {
    let Ok(value) = serde_json::from_str::<Value>(payload) else {
        return false;
    };
    let Some(services) = value
        .get("osint")
        .and_then(|node| node.get("service_risk"))
        .and_then(|node| node.get("dangerous_services"))
        .and_then(|node| node.as_array())
    else {
        return false;
    };
    services.iter().any(|item| match item.get("port") {
        Some(found) => {
            found.as_i64() == Some(port) || found.as_str().and_then(|text| text.parse::<i64>().ok()) == Some(port)
        }
        None => false,
    })
}

fn scan_port(conn: &Connection, port: i64) -> Result<Vec<ContractorRow>, String> {
    let mut rows = Vec::new();
    for (row, payload) in payload_rows(conn)? {
        if port_in_payload(&payload, port) {
            rows.push(row);
        }
    }
    sort_contractors(&mut rows);
    Ok(rows)
}

fn ask_window(lat: f64, lon: f64, radius_km: f64) -> (f64, f64, f64, f64) {
    let lat_pad = radius_km / 111.0;
    let lon_pad = radius_km / (111.0 * lat.to_radians().cos().max(0.2));
    (lon - lon_pad, lon + lon_pad, lat - lat_pad, lat + lat_pad)
}

const CONTRACTOR_SQL: &str =
    "SELECT id, name, lat, lon, risk_score, risk_severity, on_prem_count FROM contractors";

fn ask_column(conn: &Connection, where_sql: &str, params: impl rusqlite::Params) -> Result<AskResult, String> {
    let sql = format!(
        "{CONTRACTOR_SQL} WHERE {where_sql} ORDER BY risk_score DESC, name COLLATE NOCASE"
    );
    Ok(contractor_hits(query_contractors(conn, &sql, params)?))
}

pub fn ask(
    conn: &Connection,
    question: &str,
    value: &str,
    lat: Option<f64>,
    lon: Option<f64>,
    radius_km: Option<f64>,
) -> Result<AskResult, String> {
    match question {
        "risk" => {
            if !matches!(value, "critical" | "high" | "medium" | "low") {
                return Err("unknown severity".into());
            }
            ask_column(conn, "risk_severity = ?1", params![value])
        }
        "onprem" => ask_column(conn, "on_prem_count > 0", []),
        "dmarc" => {
            if !matches!(value, "not_set" | "none" | "quarantine" | "reject") {
                return Err("unknown dmarc".into());
            }
            let sql = format!(
                "{CONTRACTOR_SQL} WHERE json_extract(payload_json, '$.osint.dns.dmarc_policy') = ?1 ORDER BY risk_score DESC, name COLLATE NOCASE"
            );
            match query_contractors(conn, &sql, params![value]) {
                Ok(rows) => Ok(contractor_hits(rows)),
                Err(err) if json1_missing(&err) => Ok(contractor_hits(scan_dmarc(conn, value)?)),
                Err(err) => Err(err),
            }
        }
        "port" => {
            let Ok(port) = value.parse::<i64>() else {
                return Ok(empty_ask());
            };
            if !RISKY_PORTS.contains(&port) {
                return Ok(empty_ask());
            }
            let sql = "SELECT DISTINCT c.id, c.name, c.lat, c.lon, c.risk_score, c.risk_severity, c.on_prem_count
                       FROM contractors c, json_each(json_extract(c.payload_json, '$.osint.service_risk.dangerous_services')) je
                       WHERE json_extract(je.value, '$.port') = ?1
                       ORDER BY c.risk_score DESC, c.name COLLATE NOCASE";
            match query_contractors(conn, sql, params![port]) {
                Ok(rows) => Ok(contractor_hits(rows)),
                Err(err) if json1_missing(&err) => Ok(contractor_hits(scan_port(conn, port)?)),
                Err(err) => Err(err),
            }
        }
        "obligation" => {
            let Ok(min) = value.parse::<f64>() else {
                return Ok(empty_ask());
            };
            ask_column(
                conn,
                "CAST(json_extract(payload_json, '$.obligation') AS REAL) >= ?1",
                params![min],
            )
        }
        "cve" => {
            let Some(cve) = normalize_cve(value) else {
                return Ok(empty_ask());
            };
            let sql = "SELECT DISTINCT c.id, c.name, c.lat, c.lon, c.risk_score, c.risk_severity, c.on_prem_count
                       FROM contractors c
                       JOIN cve_hits h ON h.contractor_id = c.id
                       WHERE h.cve = ?1
                       ORDER BY c.risk_score DESC, c.name COLLATE NOCASE";
            Ok(contractor_hits(query_contractors(conn, sql, params![cve])?))
        }
        "near" => ask_near(conn, value, lat, lon, radius_km),
        "sites" => ask_sites(conn, value),
        _ => Err("unknown question".into()),
    }
}

fn ask_near(
    conn: &Connection,
    value: &str,
    lat: Option<f64>,
    lon: Option<f64>,
    radius_km: Option<f64>,
) -> Result<AskResult, String> {
    let (Some(lat), Some(lon)) = (lat, lon) else {
        return Err("no target".into());
    };
    let radius = match radius_km {
        Some(km) if km == 25.0 || km == 50.0 || km == 100.0 => km,
        _ => 50.0,
    };
    let exclude = value.parse::<i64>().ok();
    let (min_lon, max_lon, min_lat, max_lat) = ask_window(lat, lon, radius);
    let mut stmt = conn
        .prepare(
            "SELECT c.id, c.name, c.lat, c.lon, c.risk_score, c.risk_severity, c.on_prem_count
             FROM contractor_rtree r
             JOIN contractors c ON c.id = r.id
             WHERE r.min_lon <= ?1 AND r.max_lon >= ?2 AND r.min_lat <= ?3 AND r.max_lat >= ?4",
        )
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![max_lon, min_lon, max_lat, min_lat], map_contractor)
        .map_err(|e| e.to_string())?;
    let mut kept = Vec::new();
    for row in rows {
        let row = row.map_err(|e| e.to_string())?;
        if exclude == Some(row.id) {
            continue;
        }
        let dist = haversine_km(lat, lon, row.lat, row.lon);
        if dist <= radius {
            kept.push((dist, row));
        }
    }
    kept.sort_by(|a, b| {
        a.0.partial_cmp(&b.0)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(b.1.risk_score.cmp(&a.1.risk_score))
    });
    let total = kept.len() as i64;
    let hits = kept
        .into_iter()
        .take(200)
        .map(|(dist, row)| AskHit {
            kind: "contractor".into(),
            id: row.id.to_string(),
            name: row.name,
            subtitle: format!("{} · {} on-prem", row.risk_severity, row.on_prem_count),
            lat: row.lat,
            lon: row.lon,
            risk_score: row.risk_score,
            risk_severity: row.risk_severity,
            distance_km: Some(dist),
            count: 0,
        })
        .collect();
    Ok(AskResult { total, hits })
}

fn ask_sites(conn: &Connection, value: &str) -> Result<AskResult, String> {
    if value != "datacenter" {
        return Err("unknown site kind".into());
    }
    let radius = 25.0;
    let mut facilities = conn
        .prepare(&format!("SELECT id, name, lat, lon FROM facilities WHERE kind = ?1 AND {PLOT_NAME_SQL}"))
        .map_err(|e| e.to_string())?;
    let places = facilities
        .query_map(params![value], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, f64>(2)?,
                row.get::<_, f64>(3)?,
            ))
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    let mut window = conn
        .prepare(
            "SELECT c.lat, c.lon FROM contractor_rtree r
             JOIN contractors c ON c.id = r.id
             WHERE c.on_prem_count > 0 AND c.risk_severity IN ('critical', 'high')
               AND r.min_lon <= ?1 AND r.max_lon >= ?2 AND r.min_lat <= ?3 AND r.max_lat >= ?4",
        )
        .map_err(|e| e.to_string())?;
    let mut hits = Vec::new();
    for (id, name, lat, lon) in places {
        let (min_lon, max_lon, min_lat, max_lat) = ask_window(lat, lon, radius);
        let rows = window
            .query_map(params![max_lon, min_lon, max_lat, min_lat], |row| {
                Ok((row.get::<_, f64>(0)?, row.get::<_, f64>(1)?))
            })
            .map_err(|e| e.to_string())?;
        let mut count = 0_i64;
        for row in rows {
            let (clat, clon) = row.map_err(|e| e.to_string())?;
            if haversine_km(lat, lon, clat, clon) <= radius {
                count += 1;
            }
        }
        if count > 0 {
            hits.push(AskHit {
                kind: "facility".into(),
                id,
                name,
                subtitle: format!("{count} critical on-prem"),
                lat,
                lon,
                risk_score: 0,
                risk_severity: String::new(),
                distance_km: None,
                count,
            });
        }
    }
    hits.sort_by(|a, b| b.count.cmp(&a.count).then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase())));
    let total = hits.len() as i64;
    hits.truncate(20);
    Ok(AskResult { total, hits })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::LazyLock;

    fn shared() -> PathBuf {
        static DB: LazyLock<PathBuf> = LazyLock::new(|| {
            let path = std::env::temp_dir().join(format!("osint-atlas-catalog-{}.sqlite", std::process::id()));
            let _ = std::fs::remove_file(&path);
            let repo = crate::key::repo_root();
            let gev = crate::key::gev_root();
            let sources = default_sources(&repo, &gev);
            import_catalog(&path, &sources).expect("import real catalog");
            path
        });
        DB.clone()
    }

    #[test]
    fn imports_real_counts() {
        let conn = Connection::open(shared()).unwrap();
        let counts = counts(&conn).unwrap();
        assert_eq!(counts.contractors, 2214);
        assert_eq!(counts.dams, 704);
        assert_eq!(counts.datacenters, 4351);
    }

    #[test]
    fn shared_cves_and_dams_at_risk_obey_bounds() {
        let conn = Connection::open(shared()).unwrap();
        let shared = shared_exposure(&conn).unwrap();
        assert!(!shared.cves.is_empty(), "expected shared CVEs");
        for cve in &shared.cves {
            assert!(cve.contractor_count >= 2, "{}", cve.id);
        }
        let dams = onprem_near_dams(&conn, 50.0).unwrap();
        for dam in &dams {
            assert!(!dam.contractors.is_empty());
            for contractor in &dam.contractors {
                assert!(contractor.distance_km <= 50.0, "{} {}", dam.dam_name, contractor.distance_km);
            }
        }
    }

    #[test]
    fn nearby_sandia_and_first_dam_stay_inside_radius() {
        let conn = Connection::open(shared()).unwrap();
        let (id, lat, lon) = contractor_id_by_name(
            &conn,
            "NATIONAL TECHNOLOGY & ENGINEERING SOLUTIONS OF SANDIA, LLC",
        )
        .unwrap();
        assert!((lat - 35.064623).abs() < 0.0001);
        assert!((lon - -106.532597).abs() < 0.0001);
        let near = nearby(&conn, "contractor", &id.to_string(), 100.0).unwrap();
        for hit in &near.contractors {
            assert!(hit.distance_km <= 100.0);
        }
        for hit in &near.facilities {
            assert!(hit.distance_km <= 100.0);
        }
        let dam = first_facility(&conn, "dam").unwrap();
        let near = nearby(&conn, "facility", &dam, 50.0).unwrap();
        for hit in &near.contractors {
            assert!(hit.distance_km <= 50.0);
        }
        for hit in &near.facilities {
            assert!(hit.distance_km <= 50.0);
        }
    }

    #[test]
    fn missing_source_reports_path() {
        let path = std::env::temp_dir().join(format!("osint-atlas-missing-{}.sqlite", std::process::id()));
        let missing = PathBuf::from("/tmp/osint-atlas-does-not-exist.json");
        let sources = Sources {
            contractors: missing.clone(),
            dams: missing.clone(),
            datacenters: missing.clone(),
        };
        let err = import_catalog(&path, &sources).unwrap_err();
        assert!(err.contains(&missing.display().to_string()), "{err}");
    }

    #[test]
    fn plotted_points_skip_placeholders() {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "
            CREATE TABLE contractors (
              id INTEGER PRIMARY KEY, name TEXT, category TEXT, lat REAL, lon REAL,
              city TEXT, state TEXT, uei TEXT, cage TEXT, risk_score INTEGER,
              risk_severity TEXT, on_prem_count INTEGER NOT NULL DEFAULT 0, payload_json TEXT
            );
            CREATE TABLE facilities (
              row_id INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, kind TEXT, name TEXT,
              operator TEXT, lat REAL, lon REAL, source TEXT, license TEXT, payload_json TEXT
            );
            ",
        )
        .unwrap();
        for (id, name) in [(1, "Fixture Power"), (2, "unnamed"), (3, "Data Not Collected"), (4, "not collected"), (5, "  ")] {
            conn.execute(
                "INSERT INTO contractors (id, name, category, lat, lon, city, state, uei, cage, risk_score, risk_severity, on_prem_count) VALUES (?1, ?2, '', 35, -106, '', '', '', '', 1, 'low', 0)",
                params![id, name],
            )
            .unwrap();
        }
        for (id, name) in [("dam-named", "Abiquiu Dam"), ("dam-blank", "unnamed"), ("dc-missing", "data not collected")] {
            conn.execute(
                "INSERT INTO facilities (id, kind, name, operator, lat, lon) VALUES (?1, 'dam', ?2, '', 35, -106)",
                params![id, name],
            )
            .unwrap();
        }
        let plotted = contractors(&conn).unwrap();
        assert_eq!(plotted.len(), 1);
        assert_eq!(plotted[0].name, "Fixture Power");
        let places = facilities(&conn).unwrap();
        assert_eq!(places.len(), 1);
        assert_eq!(places[0].name, "Abiquiu Dam");
    }
}
