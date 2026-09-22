mod models;
mod binance;
mod bybit;
mod hyperliquid;
mod scanner;

use tauri::Manager;
use window_vibrancy::{apply_vibrancy, apply_blur, NSVisualEffectMaterial};

#[tauri::command]
fn close_window(app_handle: tauri::AppHandle) {
    app_handle.exit(0);
}

#[tauri::command]
fn minimize_window(window: tauri::Window) {
    window.minimize().unwrap();
}

#[tauri::command]
fn toggle_maximize_window(window: tauri::Window) {
    if window.is_maximized().unwrap() {
        window.unmaximize().unwrap();
    } else {
        window.maximize().unwrap();
    }
}

#[tauri::command]
async fn search_futures(query: String, max_symbols: usize) -> Result<models::SearchResult, String> {
    Ok(scanner::search_futures(&query, max_symbols).await)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      let _window = app.get_webview_window("main").unwrap();

      #[cfg(target_os = "macos")]
      apply_vibrancy(&_window, NSVisualEffectMaterial::HudWindow, None, None)
        .expect("Unsupported platform! 'apply_vibrancy' is only supported on macOS");

      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![close_window, minimize_window, toggle_maximize_window, search_futures])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
