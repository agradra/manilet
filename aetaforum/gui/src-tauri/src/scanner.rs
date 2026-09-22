use crate::models::{SearchResult, SearchSummary};
use std::collections::HashMap;

pub async fn search_futures(query: &str, max_symbols: usize) -> SearchResult {
    let client = reqwest::Client::builder()
        .user_agent("futures-scanner/2.0 (Tauri Rust)")
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .unwrap();

    let q = query.to_string();
    
    // Spawn tasks for concurrent fetching
    let c1 = client.clone();
    let q1 = q.clone();
    let t1 = tokio::spawn(async move {
        crate::binance::search(&c1, &q1, max_symbols).await
    });

    let c2 = client.clone();
    let q2 = q.clone();
    let t2 = tokio::spawn(async move {
        crate::bybit::search(&c2, &q2, max_symbols).await
    });

    let c3 = client.clone();
    let q3 = q.clone();
    let t3 = tokio::spawn(async move {
        crate::hyperliquid::search(&c3, &q3, max_symbols).await
    });

    let (r1, r2, r3) = tokio::join!(t1, t2, t3);
    
    let binance_res = r1.unwrap_or_default();
    let bybit_res = r2.unwrap_or_default();
    let hl_res = r3.unwrap_or_default();

    let mut results = HashMap::new();
    results.insert("binance".to_string(), binance_res.clone());
    results.insert("bybit".to_string(), bybit_res.clone());
    results.insert("hyperliquid".to_string(), hl_res.clone());

    let mut total = 0;
    let mut trading = 0;
    let mut earliest: Option<String> = None;

    for res_list in [&binance_res, &bybit_res, &hl_res] {
        total += res_list.len();
        for sym in res_list {
            if sym.is_trading { trading += 1; }
            if let Some(ft) = &sym.first_candle_time {
                if earliest.is_none() || ft < earliest.as_ref().unwrap() {
                    earliest = Some(ft.clone());
                }
            }
        }
    }

    SearchResult {
        query: query.to_string(),
        fetched_at: chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        results,
        summary: SearchSummary {
            total,
            trading,
            earliest_candle: earliest,
        }
    }
}
