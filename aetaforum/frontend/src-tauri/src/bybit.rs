use crate::models::SymbolInfo;
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};

const BYBIT: &str = "https://api.bybit.com";
const STALE_MINUTES: u64 = 30;

fn now_ms() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64
}

fn iso(ms: Option<u64>) -> Option<String> {
    ms.map(|m| {
        let d = std::time::UNIX_EPOCH + std::time::Duration::from_millis(m);
        let dt = chrono::DateTime::<chrono::Utc>::from(d);
        dt.to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
    })
}

fn norm(s: &str) -> String {
    s.to_uppercase().replace("-", "").replace("_", "").replace("/", "").replace(":", "")
}

fn match_rank(query: &str, symbol: &str, base: &str) -> Option<usize> {
    let q = norm(query);
    let sym = norm(symbol);
    let b = norm(base);
    if q.is_empty() { return None; }
    if q == b || q == sym { return Some(0); }
    if sym.starts_with(&q) { return Some(1); }
    if sym.contains(&q) || b.contains(&q) { return Some(2); }
    None
}

async fn get_catalog(client: &reqwest::Client, category: &str) -> Result<Vec<Value>, reqwest::Error> {
    let mut items = Vec::new();
    let mut cursor: Option<String> = None;
    loop {
        let mut req = client.get(format!("{}/v5/market/instruments-info", BYBIT))
            .query(&[("category", category), ("limit", "1000")]);
        if let Some(c) = &cursor {
            req = req.query(&[("cursor", c)]);
        }
        let res = req.send().await?.error_for_status()?;
        let json: Value = res.json().await?;
        
        let result = json.get("result").and_then(|v| v.as_object());
        if let Some(res_obj) = result {
            if let Some(list) = res_obj.get("list").and_then(|v| v.as_array()) {
                items.extend(list.clone());
            }
            if let Some(c) = res_obj.get("nextPageCursor").and_then(|v| v.as_str()) {
                if !c.is_empty() {
                    cursor = Some(c.to_string());
                    continue;
                }
            }
        }
        break;
    }
    Ok(items)
}

async fn get_kline(client: &reqwest::Client, category: &str, symbol: &str, interval: &str, start: Option<u64>, end: Option<u64>, limit: u64) -> Vec<Value> {
    let mut req = client.get(format!("{}/v5/market/kline", BYBIT))
        .query(&[("category", category), ("symbol", symbol), ("interval", interval), ("limit", &limit.to_string())]);
    if let Some(s) = start { req = req.query(&[("start", &s.to_string())]); }
    if let Some(e) = end { req = req.query(&[("end", &e.to_string())]); }
    
    if let Ok(res) = req.send().await {
        if let Ok(json) = res.json::<Value>().await {
            if let Some(list) = json.get("result").and_then(|v| v.get("list")).and_then(|v| v.as_array()) {
                return list.clone();
            }
        }
    }
    Vec::new()
}

async fn get_first_candle(client: &reqwest::Client, category: &str, symbol: &str, launch_ms: Option<u64>) -> Option<u64> {
    let start = launch_ms.unwrap_or(1_514_764_800_000);
    let mut rows = get_kline(client, category, symbol, "D", Some(start), Some(start + 200 * 86_400_000), 200).await;
    if rows.is_empty() {
        rows = get_kline(client, category, symbol, "D", Some(start), Some(now_ms()), 1000).await;
    }
    if let Some(last_row) = rows.last() {
        if let Some(timestamp_str) = last_row.as_array().and_then(|arr| arr.get(0)).and_then(|v| v.as_str()) {
            return timestamp_str.parse::<u64>().ok();
        }
    }
    None
}

pub async fn search(client: &reqwest::Client, query: &str, max_symbols: usize) -> Vec<SymbolInfo> {
    let mut out = Vec::new();
    for category in ["linear", "inverse"] {
        let catalog = match get_catalog(client, category).await {
            Ok(c) => c,
            Err(e) => {
                out.push(SymbolInfo {
                    exchange: "bybit".to_string(), market: category.to_string(), symbol: "".to_string(),
                    error: Some(e.to_string()),
                    base: None, quote: None, contract_type: None, status_raw: None,
                    listed_at: None, delivery_at: None, first_candle_time: None,
                    first_candle_source: None, last_candle_time: None, history_days: None,
                    stale: None, candle_error: None, is_trading: false, recently_active: false,
                    note: None, max_leverage: None, mark_px: None, open_interest: None,
                    funding: None, day_volume: None, daily_candle_count: None, no_candle_reason: None,
                });
                continue;
            }
        };

        let mut hits = Vec::new();
        for s in catalog {
            let symbol = s.get("symbol").and_then(|v| v.as_str()).unwrap_or("");
            let base = s.get("baseCoin").and_then(|v| v.as_str()).unwrap_or("");
            if let Some(rank) = match_rank(query, symbol, base) {
                hits.push((rank, symbol.to_string(), s.clone()));
            }
        }
        hits.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));

        for (_, sym, s) in hits.into_iter().take(max_symbols) {
            let status_raw = s.get("status").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let launch = s.get("launchTime").and_then(|v| v.as_str()).and_then(|v| v.parse::<u64>().ok());
            let delivery = s.get("deliveryTime").and_then(|v| v.as_str()).and_then(|v| v.parse::<u64>().ok()).filter(|&v| v > 0);

            let mut entry = SymbolInfo {
                exchange: "bybit".to_string(),
                market: category.to_string(),
                symbol: sym.clone(),
                base: s.get("baseCoin").and_then(|v| v.as_str()).map(|s| s.to_string()),
                quote: s.get("quoteCoin").and_then(|v| v.as_str()).map(|s| s.to_string()),
                contract_type: s.get("contractType").and_then(|v| v.as_str()).map(|s| s.to_string()),
                status_raw: Some(status_raw.clone()),
                listed_at: iso(launch),
                delivery_at: iso(delivery),
                
                first_candle_time: None, first_candle_source: None, last_candle_time: None,
                history_days: None, stale: None, candle_error: None,
                is_trading: status_raw == "Trading",
                recently_active: false, error: None, note: None,
                max_leverage: None, mark_px: None, open_interest: None, funding: None,
                day_volume: None, daily_candle_count: None, no_candle_reason: None,
            };

            let first = get_first_candle(client, category, &sym, launch).await;
            let last_rows = get_kline(client, category, &sym, "1", None, None, 1).await;
            let last = last_rows.first().and_then(|r| r.as_array()).and_then(|arr| arr.get(0)).and_then(|v| v.as_str()).and_then(|v| v.parse::<u64>().ok());

            entry.first_candle_time = iso(first).or(entry.listed_at.clone());
            entry.first_candle_source = if first.is_some() { Some("kline".to_string()) } else { Some("launchTime".to_string()) };
            entry.last_candle_time = iso(last);
            
            if let Some(f) = first { entry.history_days = Some(((now_ms() - f) as f64) / 86_400_000.0); }
            if let Some(l) = last {
                let stale = (now_ms() - l) > (STALE_MINUTES * 60_000);
                entry.stale = Some(stale);
                entry.recently_active = !stale;
            } else { entry.recently_active = false; }

            out.push(entry);
        }
    }
    out
}
