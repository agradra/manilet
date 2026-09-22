use crate::models::SymbolInfo;
use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};

const HYPERLIQUID: &str = "https://api.hyperliquid.xyz/info";
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

async fn hl_dex_names(client: &reqwest::Client) -> Vec<String> {
    let mut names = vec!["".to_string()];
    if let Ok(res) = client.post(HYPERLIQUID).json(&json!({"type": "perpDexs"})).send().await {
        if let Ok(json) = res.json::<Value>().await {
            if let Some(arr) = json.as_array() {
                for d in arr {
                    if let Some(n) = d.get("name").and_then(|v| v.as_str()) {
                        if !n.is_empty() { names.push(n.to_string()); }
                    }
                }
            }
        }
    }
    names
}

async fn hl_universe(client: &reqwest::Client, dex: &str) -> Result<(Vec<Value>, Vec<Value>), reqwest::Error> {
    let mut payload = json!({"type": "metaAndAssetCtxs"});
    if !dex.is_empty() {
        payload.as_object_mut().unwrap().insert("dex".to_string(), json!(dex));
    }
    let res = client.post(HYPERLIQUID).json(&payload).send().await?.error_for_status()?;
    let json: Value = res.json().await?;
    
    let mut universe = Vec::new();
    let mut ctxs = Vec::new();
    
    if let Some(arr) = json.as_array() {
        if let Some(meta) = arr.get(0) {
            if let Some(univ) = meta.get("universe").and_then(|v| v.as_array()) {
                universe = univ.clone();
            }
        }
        if arr.len() > 1 {
            if let Some(c) = arr.get(1).and_then(|v| v.as_array()) {
                ctxs = c.clone();
            }
        }
    }
    Ok((universe, ctxs))
}

async fn hl_candles(client: &reqwest::Client, coin: &str, interval: &str, start_ms: u64, end_ms: u64) -> Vec<Value> {
    let payload = json!({
        "type": "candleSnapshot",
        "req": {
            "coin": coin, "interval": interval, "startTime": start_ms, "endTime": end_ms
        }
    });
    if let Ok(res) = client.post(HYPERLIQUID).json(&payload).send().await {
        if let Ok(json) = res.json::<Value>().await {
            if let Some(arr) = json.as_array() {
                return arr.clone();
            }
        }
    }
    Vec::new()
}

fn hl_coin_id(dex: &str, name: &str) -> String {
    if dex.is_empty() || name.contains(':') {
        name.to_string()
    } else {
        format!("{}:{}", dex, name)
    }
}

async fn hl_first_candle(client: &reqwest::Client, coin: &str) -> (Option<u64>, Option<String>, u64) {
    let now = now_ms();
    let attempts = [
        ("1d", 0, now),
        ("1d", now.saturating_sub(5000 * 86_400_000), now),
        ("1w", 0, now),
        ("1M", 0, now),
        ("1h", now.saturating_sub(365 * 86_400_000), now),
        ("1m", now.saturating_sub(7 * 86_400_000), now),
    ];
    
    let mut daily_count = 0;
    for (interval, start, end) in attempts {
        let rows = hl_candles(client, coin, interval, start, end).await;
        if rows.is_empty() { continue; }
        if interval == "1d" { daily_count = rows.len() as u64; }
        
        let mut min_t = u64::MAX;
        for r in &rows {
            if let Some(t) = r.get("t").and_then(|v| v.as_u64()) {
                if t < min_t { min_t = t; }
            }
        }
        if min_t != u64::MAX {
            return (Some(min_t), Some(format!("candleSnapshot({})", interval)), daily_count);
        }
    }
    (None, None, 0)
}

async fn hl_last_candle(client: &reqwest::Client, coin: &str) -> Option<u64> {
    let now = now_ms();
    for hours in [6, 48, 24 * 30, 24 * 365] {
        let interval = if hours <= 48 { "1m" } else { "1d" };
        let rows = hl_candles(client, coin, interval, now.saturating_sub(hours * 3_600_000), now).await;
        if rows.is_empty() { continue; }
        let mut max_t = 0;
        for r in &rows {
            if let Some(t) = r.get("t").and_then(|v| v.as_u64()) {
                if t > max_t { max_t = t; }
            }
        }
        if max_t > 0 { return Some(max_t); }
    }
    None
}

pub async fn search(client: &reqwest::Client, query: &str, max_symbols: usize) -> Vec<SymbolInfo> {
    let mut out = Vec::new();
    let dexs = hl_dex_names(client).await;
    
    let mut hits = Vec::new();
    for dex in dexs {
        let (universe, ctxs) = match hl_universe(client, &dex).await {
            Ok((u, c)) => (u, c),
            Err(e) => {
                out.push(SymbolInfo {
                    exchange: "hyperliquid".to_string(), market: if dex.is_empty() { "perp".to_string() } else { dex },
                    symbol: "".to_string(), error: Some(e.to_string()),
                    base: None, quote: None, contract_type: None, status_raw: None,
                    listed_at: None, delivery_at: None, first_candle_time: None, first_candle_source: None,
                    last_candle_time: None, history_days: None, stale: None, candle_error: None, is_trading: false,
                    recently_active: false, note: None, max_leverage: None, mark_px: None, open_interest: None,
                    funding: None, day_volume: None, daily_candle_count: None, no_candle_reason: None,
                });
                continue;
            }
        };
        
        for (idx, asset) in universe.into_iter().enumerate() {
            let name = asset.get("name").and_then(|v| v.as_str()).unwrap_or("");
            if let Some(rank) = match_rank(query, name, name) {
                let ctx = ctxs.get(idx).cloned().unwrap_or_else(|| json!({}));
                hits.push((rank, dex.clone(), name.to_string(), asset, ctx));
            }
        }
    }
    
    hits.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)).then(a.2.cmp(&b.2)));

    for (_, dex, name, asset, ctx) in hits.into_iter().take(max_symbols) {
        let coin = hl_coin_id(&dex, &name);
        let delisted = asset.get("isDelisted").and_then(|v| v.as_bool()).unwrap_or(false);
        // Sometimes string, sometimes float
        let mark_px = ctx.get("markPx").and_then(|v| v.as_f64().or_else(|| v.as_str().and_then(|s| s.parse::<f64>().ok())));
        let oi = ctx.get("openInterest").and_then(|v| v.as_f64().or_else(|| v.as_str().and_then(|s| s.parse::<f64>().ok())));
        let fund = ctx.get("funding").and_then(|v| v.as_f64().or_else(|| v.as_str().and_then(|s| s.parse::<f64>().ok())));
        let dv = ctx.get("dayNtlVlm").and_then(|v| v.as_f64().or_else(|| v.as_str().and_then(|s| s.parse::<f64>().ok())));
        
        let mut notes = Vec::new();
        let base_name = name.split(':').last().unwrap_or(&name);

        let mut entry = SymbolInfo {
            exchange: "hyperliquid".to_string(),
            market: if dex.is_empty() { "perp".to_string() } else { format!("HIP-3:{}", dex) },
            symbol: coin.clone(),
            base: Some(base_name.to_string()),
            quote: Some("USDC".to_string()),
            contract_type: Some("PERPETUAL".to_string()),
            status_raw: Some(if delisted { "delisted".to_string() } else { "listed".to_string() }),
            max_leverage: asset.get("maxLeverage").and_then(|v| v.as_f64()),
            mark_px,
            open_interest: oi,
            funding: fund,
            day_volume: dv,
            listed_at: None, delivery_at: None, first_candle_time: None, first_candle_source: None,
            last_candle_time: None, history_days: None, daily_candle_count: None, stale: None, candle_error: None,
            is_trading: !delisted && mark_px.is_some(),
            recently_active: false, error: None, note: None, no_candle_reason: None,
        };

        let (first, source, daily_count) = hl_first_candle(client, &coin).await;
        let last = hl_last_candle(client, &coin).await;

        entry.first_candle_time = iso(first);
        entry.first_candle_source = source;
        entry.last_candle_time = iso(last);
        entry.daily_candle_count = if daily_count > 0 { Some(daily_count) } else { None };

        if let Some(f) = first { entry.history_days = Some(((now_ms() - f) as f64) / 86_400_000.0); }
        if let Some(l) = last {
            let stale = (now_ms() - l) > (STALE_MINUTES * 60_000);
            entry.stale = Some(stale);
            entry.recently_active = !stale;
        }

        if daily_count >= 5000 { notes.push("candleSnapshot 5000개 상한에 도달 → 실제 상장은 더 이전일 수 있음".to_string()); }
        if first.is_none() {
            if mark_px.is_some() {
                entry.no_candle_reason = Some("listed_but_no_trades".to_string());
                notes.push("상장 상태이나 체결 이력이 없어 봉이 생성되지 않음 (마크가격은 오라클로 갱신 중)".to_string());
            } else {
                entry.no_candle_reason = Some("unknown".to_string());
                notes.push("봉·마크가격 모두 없음 → 심볼명 또는 dex 확인 필요".to_string());
            }
        }
        if !dex.is_empty() && entry.stale.unwrap_or(false) {
            notes.push("주식/tradfi 마켓은 정규장 외 시간에 체결이 멈출 수 있음".to_string());
        }
        if !notes.is_empty() {
            entry.note = Some(notes.join(" / "));
        }

        out.push(entry);
    }
    out
}
