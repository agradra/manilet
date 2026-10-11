use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct AppSettings {
    #[serde(default = "default_window_control_style")]
    pub window_control_style: String, // "system" | "mac" | "windows"
}

fn default_window_control_style() -> String {
    "system".to_string()
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            window_control_style: default_window_control_style(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct SettingsResponse {
    pub settings: AppSettings,
    pub os: String,
    pub effective_window_control_style: String, // "mac" | "windows"
}

pub fn get_os_info() -> String {
    #[cfg(target_os = "macos")]
    { "macos".to_string() }
    #[cfg(target_os = "windows")]
    { "windows".to_string() }
    #[cfg(target_os = "linux")]
    { "linux".to_string() }
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    { "unknown".to_string() }
}

pub fn resolve_effective_style(style: &str, os: &str) -> String {
    match style {
        "mac" => "mac".to_string(),
        "windows" => "windows".to_string(),
        _ => {
            if os == "macos" {
                "mac".to_string()
            } else {
                "windows".to_string()
            }
        }
    }
}

pub fn get_settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    let app_data = app.path().data_dir()
        .map_err(|e| e.to_string())
        .or_else(|_| {
            #[cfg(target_os = "windows")]
            {
                std::env::var("APPDATA")
                    .map(PathBuf::from)
                    .map_err(|e| e.to_string())
            }
            #[cfg(not(target_os = "windows"))]
            {
                std::env::var("HOME")
                    .map(|h| PathBuf::from(h).join(".config"))
                    .map_err(|e| e.to_string())
            }
        })?;

    Ok(app_data.join("manilet").join("aetaforum").join("setting.json"))
}

#[tauri::command]
pub async fn load_settings(app: AppHandle) -> Result<SettingsResponse, String> {
    let path = get_settings_path(&app)?;
    let os = get_os_info();
    let settings = if path.exists() {
        let content = fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read settings: {}", e))?;
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        AppSettings::default()
    };
    let effective = resolve_effective_style(&settings.window_control_style, &os);
    Ok(SettingsResponse {
        settings,
        os,
        effective_window_control_style: effective,
    })
}

#[tauri::command]
pub async fn save_settings(app: AppHandle, settings: AppSettings) -> Result<SettingsResponse, String> {
    let path = get_settings_path(&app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("Failed to create settings directory: {}", e))?;
    }
    let json_str = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Failed to serialize settings: {}", e))?;
    fs::write(&path, json_str)
        .map_err(|e| format!("Failed to write settings file: {}", e))?;

    let os = get_os_info();
    let effective = resolve_effective_style(&settings.window_control_style, &os);
    let response = SettingsResponse {
        settings,
        os,
        effective_window_control_style: effective,
    };

    let _ = app.emit("settings-updated", &response);
    Ok(response)
}
