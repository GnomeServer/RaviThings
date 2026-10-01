mod catalog;
mod feeds;
mod orgfeed;
mod key;

use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use catalog::{CatalogStatus, Counts};
use rusqlite::Connection;
use serde_json::Value;
use tauri::State;

struct Atlas {
    db: Mutex<Option<Connection>>,
    status: Mutex<CatalogStatus>,
    feeds: std::sync::Arc<feeds::Hub>,
    repo: PathBuf,
    data_dir: PathBuf,
    sidecar: Mutex<Option<Child>>,
}

fn empty_status(gev_missing: Option<String>, error: Option<String>) -> CatalogStatus {
    CatalogStatus {
        contractors: 0,
        dams: 0,
        datacenters: 0,
        skipped: 0,
        gev_missing,
        error,
    }
}

fn load_catalog(data_dir: &std::path::Path, repo: &std::path::Path) -> (Connection, CatalogStatus) {
    let db_path = data_dir.join("catalog.sqlite");
    let gev = key::gev_root();
    if !gev.is_dir() {
        let missing = format!("GodsEyeView data not found at {}", gev.display());
        let sources = catalog::Sources {
            contractors: repo.join("frontend/static/contractors.json"),
            dams: PathBuf::from("/missing/dams.geojsonl"),
            datacenters: PathBuf::from("/missing/datacenters.geojsonl"),
        };
        return match catalog::import_contractors_only(&db_path, &sources.contractors) {
            Ok(conn_counts) => {
                let conn = Connection::open(&db_path).expect("catalog");
                (conn, status_from(conn_counts, Some(missing), None))
            }
            Err(error) => {
                let conn = Connection::open_in_memory().expect("memory");
                (conn, empty_status(Some(missing), Some(error)))
            }
        };
    }
    let sources = catalog::default_sources(repo, &gev);
    match catalog::open_or_rebuild(&db_path, &sources) {
        Ok(counts) => {
            let conn = Connection::open(&db_path).expect("catalog");
            (conn, status_from(counts, None, None))
        }
        Err(error) => {
            let conn = Connection::open_in_memory().expect("memory");
            (conn, empty_status(None, Some(error)))
        }
    }
}

fn status_from(counts: Counts, gev_missing: Option<String>, error: Option<String>) -> CatalogStatus {
    CatalogStatus {
        contractors: counts.contractors,
        dams: counts.dams,
        datacenters: counts.datacenters,
        skipped: counts.skipped,
        gev_missing,
        error,
    }
}

#[tauri::command]
fn google_maps_key(state: State<Atlas>) -> String {
    key::google_maps_key(&state.repo, &state.data_dir, key::no_keychain_flag())
}

#[tauri::command]
fn app_data_dir(state: State<Atlas>) -> String {
    state.data_dir.display().to_string()
}

#[tauri::command]
fn ensure_catalog(state: State<Atlas>) -> CatalogStatus {
    state.status.lock().expect("status").clone()
}

#[tauri::command]
fn catalog_counts(state: State<Atlas>) -> CatalogStatus {
    state.status.lock().expect("status").clone()
}

#[tauri::command]
fn catalog_contractors(state: State<Atlas>) -> Result<Vec<catalog::ContractorPoint>, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::contractors(conn)
}

#[tauri::command]
fn catalog_facilities(state: State<Atlas>) -> Result<Vec<catalog::FacilityPoint>, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::facilities(conn)
}

#[tauri::command]
fn contractor_payload(state: State<Atlas>, id: i64) -> Result<Option<Value>, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::payload(conn, "contractor", &id.to_string())
}

#[tauri::command]
fn facility_payload(state: State<Atlas>, id: String) -> Result<Option<Value>, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::payload(conn, "facility", &id)
}

#[tauri::command]
fn nearby(state: State<Atlas>, target_kind: String, id: String, radius_km: f64) -> Result<catalog::Nearby, String> {
    let radius = if [25.0, 50.0, 100.0].contains(&radius_km) { radius_km } else { 50.0 };
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::nearby(conn, &target_kind, &id, radius)
}

#[tauri::command]
fn search_catalog(state: State<Atlas>, query: String) -> Result<Vec<catalog::SearchHit>, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::search(conn, &query)
}

#[tauri::command]
fn ask_catalog(
    state: State<Atlas>,
    question: String,
    value: String,
    lat: Option<f64>,
    lon: Option<f64>,
    radius_km: Option<f64>,
) -> Result<catalog::AskResult, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::ask(conn, &question, &value, lat, lon, radius_km)
}

#[tauri::command]
fn shared_exposure(state: State<Atlas>) -> Result<catalog::SharedExposure, String> {
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::shared_exposure(conn)
}

#[tauri::command]
fn onprem_near_dams(state: State<Atlas>, radius_km: f64) -> Result<Vec<catalog::DamAtRisk>, String> {
    let radius = if [25.0, 50.0, 100.0].contains(&radius_km) { radius_km } else { 50.0 };
    let guard = state.db.lock().expect("db");
    let conn = guard.as_ref().ok_or("catalog not ready")?;
    catalog::onprem_near_dams(conn, radius)
}

#[tauri::command]
fn openrouter_configured(state: State<Atlas>) -> bool {
    !key::openrouter_key(&state.repo, &state.data_dir).is_empty()
}

fn firms_feed_key(repo: &std::path::Path, data_dir: &std::path::Path) -> String {
    let primary = key::optional_key(repo, data_dir, "FIRMS_API_KEY", "firms_api_key");
    if primary.is_empty() {
        key::optional_key(repo, data_dir, "FIRMS_MAP_KEY", "firms_map_key")
    } else {
        primary
    }
}

fn key_flags(state: &Atlas) -> Value {
    serde_json::json!({
        "google": !key::google_maps_key(&state.repo, &state.data_dir, key::no_keychain_flag()).is_empty(),
        "openrouter": !key::openrouter_key(&state.repo, &state.data_dir).is_empty(),
        "ais": !key::optional_key(&state.repo, &state.data_dir, "AIS_API_KEY", "ais_api_key").is_empty(),
        "firms": !key::optional_key(&state.repo, &state.data_dir, "FIRMS_API_KEY", "firms_api_key").is_empty(),
        "jev": !key::optional_key(&state.repo, &state.data_dir, "JEV_API_KEY", "jev_api_key").is_empty(),
    })
}

#[tauri::command]
fn api_key_status(state: State<Atlas>) -> Value {
    key_flags(&state)
}

#[tauri::command]
fn save_api_keys(state: State<Atlas>, keys: Value) -> Result<(), String> {
    key::save_config_keys(&state.data_dir, &keys)?;
    state.feeds.set_keys(
        key::optional_key(&state.repo, &state.data_dir, "AIS_API_KEY", "ais_api_key"),
        firms_feed_key(&state.repo, &state.data_dir),
    );
    Ok(())
}

#[tauri::command]
fn start_feeds(state: State<Atlas>) {
    state.feeds.start();
}

#[tauri::command]
fn set_camera(
    state: State<Atlas>,
    lat: f64,
    lon: f64,
    height_m: f64,
    west: f64,
    south: f64,
    east: f64,
    north: f64,
) {
    state.feeds.set_camera(feeds::Camera {
        lat,
        lon,
        height_m,
        west,
        south,
        east,
        north,
        set: true,
    });
}

#[tauri::command]
fn set_feed_enabled(state: State<Atlas>, feed: String, enabled: bool) {
    state.feeds.set_enabled(&feed, enabled);
}

#[tauri::command]
fn set_feed_focus(state: State<Atlas>, contractor_id: Option<i64>) {
    state.feeds.set_focus(contractor_id);
}

#[tauri::command]
fn feed_snapshot(state: State<Atlas>) -> feeds::Snapshot {
    state.feeds.snapshot()
}

#[tauri::command]
fn kill_chain(state: State<Atlas>, contractor_index: i64) -> Result<Value, String> {
    let key = key::openrouter_key(&state.repo, &state.data_dir);
    if key.is_empty() {
        return Err("Kill chain needs OPENROUTER_API_KEY".into());
    }
    let port = ensure_sidecar(&state, &key)?;
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(180))
        .build()
        .map_err(|e| e.to_string())?;
    let resp = client
        .post(format!("http://127.0.0.1:{port}/kill-chain"))
        .json(&serde_json::json!({ "contractor_index": contractor_index }))
        .send()
        .map_err(|e| e.to_string())?;
    let value: Value = resp.json().map_err(|e| e.to_string())?;
    Ok(scrub_kill_chain(value))
}

#[tauri::command]
fn step_detail(state: State<Atlas>, contractor_index: i64, step: Value) -> Result<Value, String> {
    let key = key::openrouter_key(&state.repo, &state.data_dir);
    if key.is_empty() {
        return Err("Kill chain needs OPENROUTER_API_KEY".into());
    }
    let port = ensure_sidecar(&state, &key)?;
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(180))
        .build()
        .map_err(|e| e.to_string())?;
    let resp = client
        .post(format!("http://127.0.0.1:{port}/step-detail"))
        .json(&serde_json::json!({ "contractor_index": contractor_index, "step": step }))
        .send()
        .map_err(|e| e.to_string())?;
    let value: Value = resp.json().map_err(|e| e.to_string())?;
    Ok(value)
}

fn scrub_kill_chain(mut value: Value) -> Value {
    let blob = value.to_string();
    if blob.contains("NoneType") && blob.contains("not iterable") {
        value = serde_json::json!({
            "summary": "Kill chain generation failed: model returned an empty response.",
            "risk_level": "unknown",
            "steps": [],
            "remediation": [],
            "error": "model returned an empty response"
        });
    }
    value
}

fn ensure_sidecar(state: &Atlas, openrouter: &str) -> Result<u16, String> {
    let port_file = state.data_dir.join("sidecar.port");
    if let Some(child) = state.sidecar.lock().expect("sidecar").as_mut() {
        if child.try_wait().map_err(|e| e.to_string())?.is_none() {
            if let Some(port) = read_port(&port_file) {
                return Ok(port);
            }
        }
    }
    let _ = std::fs::remove_file(&port_file);
    let sidecar = state.repo.join("desktop/sidecar.py");
    if !sidecar.is_file() {
        return Err(format!("missing sidecar {}", sidecar.display()));
    }
    let python = venv_python(&state.repo);
    let jev = key::optional_key(&state.repo, &state.data_dir, "JEV_API_KEY", "jev_api_key");
    let mut cmd = Command::new(&python);
    cmd.arg(&sidecar)
        .env("PYTHONPATH", &state.repo)
        .env("ATLAS_REPO_ROOT", &state.repo)
        .env("ATLAS_PORT_FILE", &port_file)
        .env("OPENROUTER_API_KEY", openrouter)
        .env("JEV_API_KEY", jev)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::piped());
    let child = cmd.spawn().map_err(|e| format!("python spawn failed: {e}"))?;
    *state.sidecar.lock().expect("sidecar") = Some(child);
    for _ in 0..50 {
        if let Some(port) = read_port(&port_file) {
            return Ok(port);
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    Err("sidecar did not bind a port".into())
}

fn read_port(path: &std::path::Path) -> Option<u16> {
    std::fs::read_to_string(path).ok()?.trim().parse().ok()
}

fn venv_python(repo: &std::path::Path) -> PathBuf {
    let venv = repo.join(".venv/bin/python");
    if venv.is_file() { venv } else { PathBuf::from("python3") }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let repo = key::repo_root();
    let data_dir = key::app_data_dir();
    let _ = std::fs::create_dir_all(&data_dir);
    let (conn, status) = load_catalog(&data_dir, &repo);
    let feeds = feeds::Hub::new(
        data_dir.clone(),
        key::optional_key(&repo, &data_dir, "AIS_API_KEY", "ais_api_key"),
        firms_feed_key(&repo, &data_dir),
    );
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(Atlas {
            db: Mutex::new(Some(conn)),
            status: Mutex::new(status),
            feeds,
            repo,
            data_dir,
            sidecar: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            google_maps_key,
            app_data_dir,
            ensure_catalog,
            catalog_counts,
            catalog_contractors,
            catalog_facilities,
            contractor_payload,
            facility_payload,
            nearby,
            search_catalog,
            ask_catalog,
            shared_exposure,
            onprem_near_dams,
            openrouter_configured,
            api_key_status,
            save_api_keys,
            start_feeds,
            set_camera,
            set_feed_enabled,
            set_feed_focus,
            feed_snapshot,
            kill_chain,
            step_detail
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[allow(dead_code)]
fn _stdio(mut w: impl Write, mut r: impl Read) {
    let _ = (&mut w, &mut r);
}

#[cfg(test)]
#[test]
fn ask_catalog_filters_fixture() {
    use rusqlite::{params, Connection};
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
        CREATE VIRTUAL TABLE contractor_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE VIRTUAL TABLE facility_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE cve_hits (cve TEXT, contractor_id INTEGER, base_score REAL, severity TEXT, scored INTEGER);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        ",
    )
    .unwrap();
    let payload = serde_json::json!({
        "obligation": 2000000000_i64,
        "osint": {
            "dns": { "dmarc_policy": "not_set" },
            "service_risk": { "dangerous_services": [{ "port": 3389 }] }
        }
    });
    conn.execute(
        "INSERT INTO contractors (id, name, lat, lon, risk_score, risk_severity, on_prem_count, payload_json)
         VALUES (1, 'Fixture Power', 35.0, -106.0, 90, 'critical', 2, ?1)",
        params![payload.to_string()],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO contractor_rtree (id, min_lon, max_lon, min_lat, max_lat) VALUES (1, -106.01, -105.99, 34.99, 35.01)",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO cve_hits (cve, contractor_id, base_score, severity, scored) VALUES ('CVE-2019-0708', 1, 9.8, 'CRITICAL', 1)",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO facilities (id, kind, name, lat, lon) VALUES ('dc-near', 'datacenter', 'dc-near', 35.05, -106.0)",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO facilities (id, kind, name, lat, lon) VALUES ('dc-far', 'datacenter', 'dc-far', 40.0, -106.0)",
        [],
    )
    .unwrap();

    fn fixture(result: &catalog::AskResult) {
        assert_eq!(result.total, 1, "{result:?}");
        assert_eq!(result.hits.len(), 1);
        assert_eq!(result.hits[0].name, "Fixture Power");
        assert_eq!(result.hits[0].kind, "contractor");
    }
    fn empty(result: &catalog::AskResult) {
        assert_eq!(result.total, 0);
        assert!(result.hits.is_empty());
    }

    fixture(&catalog::ask(&conn, "risk", "critical", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "onprem", "", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "dmarc", "not_set", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "port", "3389", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "obligation", "1000000000", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "cve", "CVE-2019-0708", None, None, None).unwrap());
    fixture(&catalog::ask(&conn, "near", "", Some(35.0), Some(-106.0), Some(25.0)).unwrap());
    empty(&catalog::ask(&conn, "risk", "low", None, None, None).unwrap());
    empty(&catalog::ask(&conn, "port", "22", None, None, None).unwrap());
    empty(&catalog::ask(&conn, "obligation", "9000000000", None, None, None).unwrap());
    let sites = catalog::ask(&conn, "sites", "datacenter", None, None, None).unwrap();
    assert!(sites.hits.iter().any(|hit| hit.id == "dc-near" && hit.count == 1), "{sites:?}");
    assert!(sites.hits.iter().all(|hit| hit.id != "dc-far"), "{sites:?}");
    let err = catalog::ask(&conn, "nope", "", None, None, None).unwrap_err();
    assert!(err.contains("unknown question"), "{err}");
}
