use std::path::{Path, PathBuf};
use std::process::Command;

pub fn no_keychain_flag() -> bool {
    std::env::args().any(|arg| arg == "--no-keychain")
}

pub fn google_maps_key(repo_root: &Path, data_dir: &Path, no_keychain: bool) -> String {
    if !no_keychain {
        for account in ["api-key", "default", "key"] {
            if let Some(value) = keychain("google-maps-api", account) {
                return value;
            }
        }
    }
    optional_key(repo_root, data_dir, "GOOGLE_MAPS_API_KEY", "google_maps_api_key")
}

pub fn openrouter_key(repo_root: &Path, data_dir: &Path) -> String {
    optional_key(repo_root, data_dir, "OPENROUTER_API_KEY", "openrouter_api_key")
}

pub fn optional_key(repo_root: &Path, data_dir: &Path, env_name: &str, config_field: &str) -> String {
    if let Ok(value) = std::env::var(env_name) {
        let value = value.trim().to_string();
        if !value.is_empty() {
            return value;
        }
    }
    if let Some(value) = config_value(&data_dir.join("config.json"), config_field) {
        return value;
    }
    dotenv_value(&repo_root.join(".env"), env_name).unwrap_or_default()
}

pub fn app_data_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join("Library/Application Support/OSINT Atlas")
}

pub fn repo_root() -> PathBuf {
    let start = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut cursor = start.canonicalize().unwrap_or(start);
    for _ in 0..6 {
        if cursor.join("frontend/static/contractors.json").is_file() {
            return cursor;
        }
        if !cursor.pop() {
            break;
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

pub fn gev_root() -> PathBuf {
    std::env::var("GEV_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/Users/ravistarzl/Documents/GitHub/gods-eye-view"))
}

fn keychain(service: &str, account: &str) -> Option<String> {
    let output = Command::new("security")
        .args(["find-generic-password", "-s", service, "-a", account, "-w"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let value = String::from_utf8(output.stdout).ok()?.trim().to_string();
    if value.is_empty() { None } else { Some(value) }
}

pub fn dotenv_value(path: &Path, key: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (name, raw) = line.split_once('=')?;
        if name.trim() != key {
            continue;
        }
        let value = raw.trim().trim_matches('"').trim_matches('\'').to_string();
        if value.is_empty() {
            return None;
        }
        return Some(value);
    }
    None
}

fn config_value(path: &Path, field: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&text).ok()?;
    let raw = value.get(field)?.as_str()?.trim().to_string();
    if raw.is_empty() { None } else { Some(raw) }
}

const CONFIG_KEY_FIELDS: &[&str] = &[
    "google_maps_api_key",
    "openrouter_api_key",
    "ais_api_key",
    "firms_api_key",
    "jev_api_key",
];

pub fn save_config_keys(data_dir: &Path, updates: &serde_json::Value) -> Result<(), String> {
    std::fs::create_dir_all(data_dir).map_err(|e| format!("data dir: {e}"))?;
    let Some(incoming) = updates.as_object() else {
        return Err("keys must be an object".into());
    };
    let mut pending = Vec::new();
    for field in CONFIG_KEY_FIELDS {
        let Some(text) = incoming_key(incoming, field) else { continue };
        pending.push((*field, text));
    }
    if pending.is_empty() {
        return Ok(());
    }
    let path = data_dir.join("config.json");
    let mut root = load_config_object(&path)?;
    for (field, text) in pending {
        root.insert(field.to_string(), serde_json::Value::String(text));
    }
    let mut text = serde_json::to_string_pretty(&root).map_err(|_| "could not write config".to_string())?;
    text.push('\n');
    let tmp = data_dir.join("config.json.tmp");
    if let Err(e) = std::fs::write(&tmp, text) {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!("config write: {e}"));
    }
    if let Err(e) = std::fs::rename(&tmp, &path) {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!("config write: {e}"));
    }
    Ok(())
}

fn incoming_key(incoming: &serde_json::Map<String, serde_json::Value>, field: &str) -> Option<String> {
    let raw = incoming.get(field).or_else(|| incoming.get(&camel_case(field)))?;
    let text = raw.as_str()?.trim();
    if text.is_empty() { None } else { Some(text.to_string()) }
}

fn camel_case(field: &str) -> String {
    let mut out = String::new();
    let mut upper = false;
    for ch in field.chars() {
        if ch == '_' {
            upper = true;
        } else if upper {
            out.push(ch.to_ascii_uppercase());
            upper = false;
        } else {
            out.push(ch);
        }
    }
    out
}

fn load_config_object(path: &Path) -> Result<serde_json::Map<String, serde_json::Value>, String> {
    if !path.exists() {
        return Ok(serde_json::Map::new());
    }
    let text = std::fs::read_to_string(path).map_err(|e| format!("config read: {e}"))?;
    if text.trim().is_empty() {
        return Ok(serde_json::Map::new());
    }
    match serde_json::from_str::<serde_json::Value>(&text) {
        Ok(serde_json::Value::Object(map)) => Ok(map),
        Ok(_) => Err("config.json is not an object".into()),
        Err(_) => Err("config.json is not valid JSON".into()),
    }
}
