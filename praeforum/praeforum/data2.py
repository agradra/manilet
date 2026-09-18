#!/usr/bin/env python3
"""
바이낸스 / 바이비트 / 하이퍼리퀴드 통합 선물 심볼 검색기.

특정 티커(BTC, SOL, XYZ100, AAPL, GOLD ...)를 세 거래소에서 한 번에 찾아
  - 어느 마켓(USDⓈ-M / COIN-M / linear / inverse / HL perp / HIP-3 dex)에 있는지
  - 봉 데이터가 가장 과거 언제까지 있는지 (first_candle_time)
  - 지금 실제로 거래 중인지 (status + 최신 봉 신선도)
를 dict로 반환한다.

의존성: requests
사용법:
    from futures_scanner import search_futures
    info = search_futures("BTC")

    $ python futures_scanner.py XYZ100
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

# ----------------------------------------------------------------------------
# 상수
# ----------------------------------------------------------------------------

BINANCE_USDM = ("https://fapi.binance.com", "/fapi/v1")   # USDT/USDC 마진 선물
BINANCE_COINM = ("https://dapi.binance.com", "/dapi/v1")  # 코인(인버스) 마진 선물
BYBIT = "https://api.bybit.com"                           # 막히면 https://api.bytick.com
HYPERLIQUID = "https://api.hyperliquid.xyz/info"          # info는 POST 전용

TIMEOUT = 15
MAX_RETRY = 3
STALE_MINUTES = 30          # 최신 봉이 이보다 오래되면 "거래 정지/휴장"으로 간주
DEFAULT_MAX_SYMBOLS = 12    # 광범위 검색 시 상세 조회할 심볼 상한

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "futures-scanner/1.0"})

# 메타데이터 캐시 (프로세스 수명 동안 유지)
_CACHE: Dict[str, Any] = {}


# ----------------------------------------------------------------------------
# 공통 유틸
# ----------------------------------------------------------------------------

def _request(method: str, url: str, **kw) -> Any:
    """429/5xx에 대해 지수 백오프 재시도."""
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRY):
        try:
            r = _SESSION.request(method, url, timeout=TIMEOUT, **kw)
            if r.status_code in (418, 429) or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} {r.text[:200]}")
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < MAX_RETRY - 1:
                time.sleep(0.6 * (2 ** attempt))
    raise RuntimeError(f"{method} {url} 실패: {last_exc}") from last_exc


def _get(url: str, params: Optional[dict] = None) -> Any:
    return _request("GET", url, params=params)


def _post(url: str, payload: dict) -> Any:
    return _request("POST", url, json=payload)


def _iso(ms: Optional[int]) -> Optional[str]:
    if not ms:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _norm(s: str) -> str:
    return (s or "").upper().replace("-", "").replace("_", "").replace("/", "").replace(":", "")


def _match_rank(query: str, symbol: str, base: str) -> Optional[int]:
    """0 = 베이스 코인 완전 일치, 1 = 심볼 접두 일치, 2 = 부분 일치, None = 불일치."""
    q, sym, b = _norm(query), _norm(symbol), _norm(base)
    if not q:
        return None
    if q == b or q == sym:
        return 0
    if sym.startswith(q):
        return 1
    if q in sym or q in b:
        return 2
    return None


def _is_stale(last_candle_ms: Optional[int]) -> Optional[bool]:
    if not last_candle_ms:
        return None
    return (_now_ms() - last_candle_ms) > STALE_MINUTES * 60_000


# ----------------------------------------------------------------------------
# 바이낸스
# ----------------------------------------------------------------------------

def _binance_catalog(market: str) -> List[dict]:
    """market: 'usdm' | 'coinm'"""
    key = f"binance:{market}"
    if key in _CACHE:
        return _CACHE[key]
    host, prefix = BINANCE_USDM if market == "usdm" else BINANCE_COINM
    data = _get(f"{host}{prefix}/exchangeInfo")
    _CACHE[key] = data.get("symbols", [])
    return _CACHE[key]


def _binance_first_candle(market: str, symbol: str) -> Optional[int]:
    host, prefix = BINANCE_USDM if market == "usdm" else BINANCE_COINM
    # startTime=0 을 주면 상장 이후 첫 일봉부터 반환된다.
    kl = _get(f"{host}{prefix}/klines",
              {"symbol": symbol, "interval": "1d", "startTime": 0, "limit": 1})
    return int(kl[0][0]) if kl else None


def _binance_last_candle(market: str, symbol: str) -> Optional[int]:
    host, prefix = BINANCE_USDM if market == "usdm" else BINANCE_COINM
    kl = _get(f"{host}{prefix}/klines", {"symbol": symbol, "interval": "1m", "limit": 1})
    return int(kl[0][0]) if kl else None


def _binance_search(query: str, max_symbols: int) -> List[dict]:
    out: List[dict] = []
    for market in ("usdm", "coinm"):
        try:
            catalog = _binance_catalog(market)
        except Exception as exc:  # noqa: BLE001
            out.append({"exchange": "binance", "market": market, "error": str(exc)})
            continue

        hits: List[Tuple[int, dict]] = []
        for s in catalog:
            rank = _match_rank(query, s.get("symbol", ""), s.get("baseAsset", ""))
            if rank is not None:
                hits.append((rank, s))
        hits.sort(key=lambda x: (x[0], x[1].get("symbol", "")))

        for _, s in hits[:max_symbols]:
            sym = s["symbol"]
            entry = {
                "exchange": "binance",
                "market": "USDⓈ-M" if market == "usdm" else "COIN-M",
                "symbol": sym,
                "base": s.get("baseAsset"),
                "quote": s.get("quoteAsset"),
                "contract_type": s.get("contractType"),      # PERPETUAL / CURRENT_QUARTER ...
                "status_raw": s.get("status") or s.get("contractStatus"),
                "listed_at": _iso(s.get("onboardDate")),
                "delivery_at": _iso(s.get("deliveryDate")),
            }
            try:
                first = _binance_first_candle(market, sym)
                last = _binance_last_candle(market, sym)
                entry["first_candle_time"] = _iso(first) or entry["listed_at"]
                entry["first_candle_source"] = "klines" if first else "onboardDate"
                entry["last_candle_time"] = _iso(last)
                entry["history_days"] = round((_now_ms() - first) / 86_400_000, 1) if first else None
                entry["stale"] = _is_stale(last)
            except Exception as exc:  # noqa: BLE001
                entry["candle_error"] = str(exc)

            entry["is_trading"] = entry["status_raw"] == "TRADING"
            entry["recently_active"] = (entry.get("stale") is False)
            out.append(entry)
    return out


# ----------------------------------------------------------------------------
# 바이비트
# ----------------------------------------------------------------------------

def _bybit_catalog(category: str) -> List[dict]:
    """category: 'linear' | 'inverse'"""
    key = f"bybit:{category}"
    if key in _CACHE:
        return _CACHE[key]
    items: List[dict] = []
    cursor = None
    while True:
        params = {"category": category, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        data = _get(f"{BYBIT}/v5/market/instruments-info", params)
        if data.get("retCode") != 0:
            raise RuntimeError(f"bybit retCode={data.get('retCode')} {data.get('retMsg')}")
        result = data.get("result", {})
        items.extend(result.get("list", []))
        cursor = result.get("nextPageCursor")
        if not cursor:
            break
    _CACHE[key] = items
    return items


def _bybit_kline(category: str, symbol: str, interval: str,
                 start: Optional[int] = None, end: Optional[int] = None,
                 limit: int = 1) -> List[list]:
    params = {"category": category, "symbol": symbol, "interval": interval, "limit": limit}
    if start is not None:
        params["start"] = int(start)
    if end is not None:
        params["end"] = int(end)
    data = _get(f"{BYBIT}/v5/market/kline", params)
    if data.get("retCode") != 0:
        raise RuntimeError(f"bybit retCode={data.get('retCode')} {data.get('retMsg')}")
    # 응답은 최신 → 과거 순(내림차순)
    return data.get("result", {}).get("list", [])


def _bybit_first_candle(category: str, symbol: str, launch_ms: Optional[int]) -> Optional[int]:
    """
    바이비트는 내림차순 반환이라 '가장 오래된 봉'을 직접 못 준다.
    launchTime 부터 200일 창을 잡고 리스트의 마지막(=가장 과거) 원소를 취한다.
    launchTime이 없으면 2018년부터 훑는다.
    """
    start = int(launch_ms) if launch_ms else 1_514_764_800_000  # 2018-01-01
    rows = _bybit_kline(category, symbol, "D", start=start,
                        end=start + 200 * 86_400_000, limit=200)
    if not rows:
        # 창을 넓혀 한 번 더 시도
        rows = _bybit_kline(category, symbol, "D", start=start,
                            end=_now_ms(), limit=1000)
    return int(rows[-1][0]) if rows else None


def _bybit_search(query: str, max_symbols: int) -> List[dict]:
    out: List[dict] = []
    for category in ("linear", "inverse"):
        try:
            catalog = _bybit_catalog(category)
        except Exception as exc:  # noqa: BLE001
            out.append({"exchange": "bybit", "market": category, "error": str(exc)})
            continue

        hits: List[Tuple[int, dict]] = []
        for s in catalog:
            rank = _match_rank(query, s.get("symbol", ""), s.get("baseCoin", ""))
            if rank is not None:
                hits.append((rank, s))
        hits.sort(key=lambda x: (x[0], x[1].get("symbol", "")))

        for _, s in hits[:max_symbols]:
            sym = s["symbol"]
            launch = s.get("launchTime")
            launch_ms = int(launch) if launch and str(launch).isdigit() else None
            entry = {
                "exchange": "bybit",
                "market": category,
                "symbol": sym,
                "base": s.get("baseCoin"),
                "quote": s.get("quoteCoin"),
                "contract_type": s.get("contractType"),   # LinearPerpetual / InverseFutures ...
                "status_raw": s.get("status"),            # Trading / PreLaunch / Delivering / Closed
                "listed_at": _iso(launch_ms),
                "delivery_at": _iso(int(s["deliveryTime"])) if s.get("deliveryTime") not in (None, "", "0") else None,
            }
            try:
                first = _bybit_first_candle(category, sym, launch_ms)
                last_rows = _bybit_kline(category, sym, "1", limit=1)
                last = int(last_rows[0][0]) if last_rows else None
                entry["first_candle_time"] = _iso(first) or entry["listed_at"]
                entry["first_candle_source"] = "kline" if first else "launchTime"
                entry["last_candle_time"] = _iso(last)
                entry["history_days"] = round((_now_ms() - first) / 86_400_000, 1) if first else None
                entry["stale"] = _is_stale(last)
            except Exception as exc:  # noqa: BLE001
                entry["candle_error"] = str(exc)

            entry["is_trading"] = entry["status_raw"] == "Trading"
            entry["recently_active"] = (entry.get("stale") is False)
            out.append(entry)
    return out


# ----------------------------------------------------------------------------
# 하이퍼리퀴드 (네이티브 perp + HIP-3 dex: xyz 등 주식/지수/원자재)
# ----------------------------------------------------------------------------

def _hl_dex_names() -> List[str]:
    """네이티브('')와 모든 HIP-3 빌더 dex 이름."""
    if "hl:dexs" in _CACHE:
        return _CACHE["hl:dexs"]
    names = [""]
    try:
        dexs = _post(HYPERLIQUID, {"type": "perpDexs"})
        for d in dexs or []:
            if isinstance(d, dict) and isinstance(d.get("name"), str) and d["name"]:
                names.append(d["name"])
    except Exception:  # noqa: BLE001
        pass  # perpDexs 실패 시 네이티브만
    _CACHE["hl:dexs"] = names
    return names


def _hl_universe(dex: str) -> Tuple[List[dict], List[dict]]:
    """(universe, assetCtxs) — metaAndAssetCtxs 한 번으로 메타 + 실시간 컨텍스트."""
    key = f"hl:meta:{dex}"
    if key in _CACHE:
        return _CACHE[key]
    payload = {"type": "metaAndAssetCtxs"}
    if dex:
        payload["dex"] = dex
    data = _post(HYPERLIQUID, payload)
    universe = (data[0] or {}).get("universe", []) if isinstance(data, list) else []
    ctxs = data[1] if isinstance(data, list) and len(data) > 1 else []
    _CACHE[key] = (universe, ctxs)
    return _CACHE[key]


def _hl_candles(coin: str, interval: str, start_ms: int, end_ms: int) -> List[dict]:
    payload = {"type": "candleSnapshot",
               "req": {"coin": coin, "interval": interval,
                       "startTime": int(start_ms), "endTime": int(end_ms)}}
    return _post(HYPERLIQUID, payload) or []


def _hl_coin_id(dex: str, name: str) -> str:
    """
    HIP-3 자산의 캔들/주문용 코인 식별자.
    meta universe의 name이 이미 'xyz:SKHY'처럼 dex 접두사를 포함하는 경우가 있어
    중복 접두사를 방지한다.
    """
    if not dex:
        return name
    if ":" in name:
        return name
    return f"{dex}:{name}"


def _hl_first_candle(coin: str) -> Tuple[Optional[int], Optional[str], int]:
    """
    가장 과거 봉을 여러 전략으로 탐색한다.
    Returns: (first_ms, source, daily_count)

    하이퍼리퀴드 캔들은 체결 기반이라 무체결 자산은 진짜로 봉이 없다.
    따라서 빈 응답 = 조회 실패가 아니라 '체결 이력 없음'일 수 있다.
    """
    now = _now_ms()
    attempts = [
        ("1d", 0, now),                              # 일봉 5000개 ≈ 13.7년
        ("1d", now - 5000 * 86_400_000, now),        # startTime=0 거부 대비
        ("1w", 0, now),
        ("1M", 0, now),
        ("1h", now - 365 * 86_400_000, now),         # 초신규 상장 대비
        ("1m", now - 7 * 86_400_000, now),
    ]
    daily_count = 0
    for interval, start, end in attempts:
        try:
            rows = _hl_candles(coin, interval, start, end)
        except Exception:  # noqa: BLE001
            continue
        if not rows:
            continue
        if interval == "1d":
            daily_count = len(rows)
        first = min(int(r["t"]) for r in rows)
        return first, f"candleSnapshot({interval})", daily_count
    return None, None, 0


def _hl_last_candle(coin: str) -> Optional[int]:
    """최신 봉. 유동성이 낮으면 최근 구간이 비므로 창을 점점 넓힌다."""
    now = _now_ms()
    for hours in (6, 48, 24 * 30, 24 * 365):
        try:
            interval = "1m" if hours <= 48 else "1d"
            rows = _hl_candles(coin, interval, now - hours * 3_600_000, now)
        except Exception:  # noqa: BLE001
            return None
        if rows:
            return max(int(r["t"]) for r in rows)
    return None


def _hl_search(query: str, max_symbols: int) -> List[dict]:
    out: List[dict] = []
    hits: List[Tuple[int, str, str, dict, dict]] = []  # rank, dex, name, meta, ctx

    for dex in _hl_dex_names():
        try:
            universe, ctxs = _hl_universe(dex)
        except Exception as exc:  # noqa: BLE001
            out.append({"exchange": "hyperliquid", "market": dex or "perp", "error": str(exc)})
            continue
        for idx, asset in enumerate(universe):
            name = asset.get("name", "")
            rank = _match_rank(query, name, name)
            if rank is not None:
                ctx = ctxs[idx] if idx < len(ctxs) else {}
                hits.append((rank, dex, name, asset, ctx))

    hits.sort(key=lambda x: (x[0], x[1], x[2]))

    for rank, dex, name, asset, ctx in hits[:max_symbols]:
        coin = _hl_coin_id(dex, name)
        delisted = bool(asset.get("isDelisted"))
        mark_px = ctx.get("markPx")
        notes: List[str] = []

        entry = {
            "exchange": "hyperliquid",
            "market": f"HIP-3:{dex}" if dex else "perp",
            "symbol": coin,
            "base": name.split(":")[-1],
            "quote": "USDC",
            "contract_type": "PERPETUAL",
            "status_raw": "delisted" if delisted else "listed",
            "max_leverage": asset.get("maxLeverage"),
            "mark_px": mark_px,
            "open_interest": ctx.get("openInterest"),
            "funding": ctx.get("funding"),
            "day_volume": ctx.get("dayNtlVlm"),
            "listed_at": None,  # HL은 상장 시각 메타를 주지 않음 → 첫 봉으로 추정
        }

        try:
            first, source, daily_count = _hl_first_candle(coin)
            last = _hl_last_candle(coin)
            entry["first_candle_time"] = _iso(first)
            entry["first_candle_source"] = source
            entry["last_candle_time"] = _iso(last)
            entry["history_days"] = round((_now_ms() - first) / 86_400_000, 1) if first else None
            entry["daily_candle_count"] = daily_count or None
            entry["stale"] = _is_stale(last)
            if daily_count >= 5000:
                notes.append("candleSnapshot 5000개 상한에 도달 → 실제 상장은 더 이전일 수 있음")
            if first is None:
                # 하이퍼리퀴드 캔들은 체결 기반이므로 무체결 자산은 봉 자체가 없다.
                if mark_px is not None:
                    entry["no_candle_reason"] = "listed_but_no_trades"
                    notes.append("상장 상태이나 체결 이력이 없어 봉이 생성되지 않음 "
                                 "(마크가격은 오라클로 갱신 중)")
                else:
                    entry["no_candle_reason"] = "unknown"
                    notes.append("봉·마크가격 모두 없음 → 심볼명 또는 dex 확인 필요")
        except Exception as exc:  # noqa: BLE001
            entry["candle_error"] = str(exc)

        # 거래 가능 여부는 캔들이 아니라 상장 상태 + 마크가격으로 판단한다.
        # 캔들 신선도는 '최근 체결 활동'이라는 별도 지표로 분리.
        entry["is_trading"] = (not delisted) and (mark_px is not None)
        entry["recently_active"] = (entry.get("stale") is False)

        if dex and entry.get("stale"):
            notes.append("주식/tradfi 마켓은 정규장 외 시간에 체결이 멈출 수 있음")
        if notes:
            entry["note"] = " / ".join(notes)
        out.append(entry)
    return out


# ----------------------------------------------------------------------------
# 통합 진입점
# ----------------------------------------------------------------------------

def search_futures(query: str,
                   exchanges: Optional[List[str]] = None,
                   max_symbols: int = DEFAULT_MAX_SYMBOLS) -> Dict[str, Any]:
    """
    세 거래소에서 query에 해당하는 선물 심볼을 찾아 dict로 반환한다.

    Args:
        query:       티커 또는 부분 문자열. "BTC", "SOLUSDT", "XYZ100", "AAPL", "GOLD" 등
        exchanges:   ["binance", "bybit", "hyperliquid"] 중 일부. None이면 전체.
        max_symbols: 거래소·마켓별로 상세 조회할 심볼 상한 (봉 조회 호출 수 제어)

    Returns:
        {
          "query": str,
          "fetched_at": ISO8601,
          "results": {"binance": [...], "bybit": [...], "hyperliquid": [...]},
          "summary": {"total": int, "trading": int, "earliest_candle": ISO8601 | None}
        }
    """
    targets = exchanges or ["binance", "bybit", "hyperliquid"]
    runners = {
        "binance": _binance_search,
        "bybit": _bybit_search,
        "hyperliquid": _hl_search,
    }

    results: Dict[str, List[dict]] = {}
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(runners[ex], query, max_symbols): ex
                   for ex in targets if ex in runners}
        for fut in cf.as_completed(futures):
            ex = futures[fut]
            try:
                results[ex] = fut.result()
            except Exception as exc:  # noqa: BLE001
                results[ex] = [{"exchange": ex, "error": str(exc)}]

    flat = [e for lst in results.values() for e in lst if "error" not in e]
    firsts = [e["first_candle_time"] for e in flat if e.get("first_candle_time")]

    return {
        "query": query,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "results": {ex: results.get(ex, []) for ex in targets},
        "summary": {
            "total": len(flat),
            "trading": sum(1 for e in flat if e.get("is_trading")),
            "earliest_candle": min(firsts) if firsts else None,
        },
    }


def _print_table(info: Dict[str, Any]) -> None:
    rows = [e for lst in info["results"].values() for e in lst]
    if not rows:
        print("결과 없음")
        return
    hdr = (f"{'EXCHANGE':<12}{'MARKET':<14}{'SYMBOL':<20}{'TRADING':<9}"
           f"{'ACTIVE':<8}{'FIRST CANDLE':<28}{'DAYS':>8}")
    print(hdr)
    print("-" * len(hdr))
    for e in rows:
        if "error" in e:
            print(f"{e.get('exchange','?'):<12}{e.get('market',''):<14}ERROR: {e['error'][:60]}")
            continue
        days = e.get("history_days")
        first = e.get("first_candle_time") or f"none ({e.get('no_candle_reason', '-')})"
        print(f"{e['exchange']:<12}{e['market']:<14}{e['symbol']:<20}"
              f"{str(e.get('is_trading')):<9}{str(e.get('recently_active')):<8}"
              f"{first[:26]:<28}{days if days is not None else '-':>8}")
        if e.get("note"):
            print(f"{'':<12}└ {e['note']}")
    s = info["summary"]
    print(f"\n총 {s['total']}건 / 거래중 {s['trading']}건 / 최초 봉 {s['earliest_candle']}")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    result = search_futures(q)
    _print_table(result)
    if "--json" in sys.argv:
        print()
        print(json.dumps(result, indent=2, ensure_ascii=False))