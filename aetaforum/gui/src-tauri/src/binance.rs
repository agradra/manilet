use crate::models::SymbolInfo;
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};

const BINANCE_USDM: (&str, &str) = ("https://fapi.binance.com", "/fapi/v1");
const BINANCE_COINM: (&str, &str) = ("https://dapi.binance.com", "/dapi/v1");
const STALE_MINUTES: u64 = 30;

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis() as u64
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

async fn get_catalog(client: &reqwest::Client, market: &str) -> Result<Vec<Value>, reqwest::Error> {
    let (host, prefix) = if market == "usdm" { BINANCE_USDM } else { BINANCE_COINM };
    let url = format!("{}{}/exchangeInfo", host, prefix);
    let res = client.get(&url).send().await?.error_for_status()?;
    let json: Value = res.json().await?;
    let symbols = json.get("symbols").and_then(|v| v.as_array()).cloned().unwrap_or_default();
    Ok(symbols)
}

async fn get_first_candle(client: &reqwest::Client, market: &str, symbol: &str) -> Option<u64> {
    let (host, prefix) = if market == "usdm" { BINANCE_USDM } else { BINANCE_COINM };
    let url = format!("{}{}/klines", host, prefix);
    let res = client.get(&url)
        .query(&[("symbol", symbol), ("interval", "1d"), ("startTime", "0"), ("limit", "1")])
        .send().await.ok()?;
    let json: Value = res.json().await.ok()?;
    let arr = json.as_array()?;
    if arr.is_empty() { return None; }
    arr[0].as_array()?.get(0)?.as_u64()
}

async fn get_last_candle(client: &reqwest::Client, market: &str, symbol: &str) -> Option<u64> {
    let (host, prefix) = if market == "usdm" { BINANCE_USDM } else { BINANCE_COINM };
    let url = format!("{}{}/klines", host, prefix);
    let res = client.get(&url)
        .query(&[("symbol", symbol), ("interval", "1m"), ("limit", "1")])
        .send().await.ok()?;
    let json: Value = res.json().await.ok()?;
    let arr = json.as_array()?;
    if arr.is_empty() { return None; }
    arr[0].as_array()?.get(0)?.as_u64()
}

pub async fn search(client: &reqwest::Client, query: &str, max_symbols: usize) -> Vec<SymbolInfo> {
    let mut out = Vec::new();
    for market in ["usdm", "coinm"] {
        let catalog = match get_catalog(client, market).await {
            Ok(c) => c,
            Err(e) => {
                out.push(SymbolInfo {
                    exchange: "binance".to_string(),
                    market: market.to_string(),
                    symbol: "".to_string(),
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
            let base = s.get("baseAsset").and_then(|v| v.as_str()).unwrap_or("");
            if let Some(rank) = match_rank(query, symbol, base) {
                hits.push((rank, symbol.to_string(), s.clone()));
            }
        }
        hits.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));

        for (_, sym, s) in hits.into_iter().take(max_symbols) {
            let status_raw = s.get("status").or_else(|| s.get("contractStatus")).and_then(|v| v.as_str()).unwrap_or("").to_string();
            let onboard_date = s.get("onboardDate").and_then(|v| v.as_u64());
            let delivery_date = s.get("deliveryDate").and_then(|v| v.as_u64());
            
            let mut entry = SymbolInfo {
                exchange: "binance".to_string(),
                market: if market == "usdm" { "USDⓈ-M".to_string() } else { "COIN-M".to_string() },
                symbol: sym.clone(),
                base: s.get("baseAsset").and_then(|v| v.as_str()).map(|s| s.to_string()),
                quote: s.get("quoteAsset").and_then(|v| v.as_str()).map(|s| s.to_string()),
                contract_type: s.get("contractType").and_then(|v| v.as_str()).map(|s| s.to_string()),
                status_raw: Some(status_raw.clone()),
                listed_at: iso(onboard_date),
                delivery_at: iso(delivery_date),
                
                first_candle_time: None,
                first_candle_source: None,
                last_candle_time: None,
                history_days: None,
                stale: None,
                candle_error: None,
                is_trading: status_raw == "TRADING",
                recently_active: false,
                error: None,
                note: None,
                max_leverage: None, mark_px: None, open_interest: None, funding: None,
                day_volume: None, daily_candle_count: None, no_candle_reason: None,
            };

            let first = get_first_candle(client, market, &sym).await;
            let last = get_last_candle(client, market, &sym).await;

            entry.first_candle_time = iso(first).or(entry.listed_at.clone());
            entry.first_candle_source = if first.is_some() { Some("klines".to_string()) } else { Some("onboardDate".to_string()) };
            entry.last_candle_time = iso(last);
            
            if let Some(f) = first {
                entry.history_days = Some(((now_ms() - f) as f64) / 86_400_000.0);
            }
            if let Some(l) = last {
                let stale = (now_ms() - l) > (STALE_MINUTES * 60_000);
                entry.stale = Some(stale);
                entry.recently_active = !stale;
            } else {
                entry.recently_active = false;
            }

            out.push(entry);
        }
    }
    out
}
