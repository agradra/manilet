use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SymbolInfo {
    pub exchange: String,
    pub market: String,
    pub symbol: String,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub base: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub quote: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub contract_type: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status_raw: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub listed_at: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub delivery_at: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub first_candle_time: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub first_candle_source: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_candle_time: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub history_days: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stale: Option<bool>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub candle_error: Option<String>,
    
    pub is_trading: bool,
    pub recently_active: bool,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
    
    // Hyperliquid specific
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_leverage: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mark_px: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub open_interest: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub funding: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub day_volume: Option<f64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub daily_candle_count: Option<u64>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub no_candle_reason: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchSummary {
    pub total: usize,
    pub trading: usize,
    pub earliest_candle: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchResult {
    pub query: String,
    pub fetched_at: String,
    pub results: std::collections::HashMap<String, Vec<SymbolInfo>>,
    pub summary: SearchSummary,
}
