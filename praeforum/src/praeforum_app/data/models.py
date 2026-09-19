from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchResult:
    exchange: str         # "binance", "bybit" 등
    symbol: str           # "BTC-USDT"
    market_type: str      # "spot" (현물) 또는 "futures" (선물)
    available_from: str   # "2019-09-01" (데이터가 존재하는 최초 날짜)
    has_funding_rate: bool # 펀딩비 다운로드 지원 여부
    download_type: str    # "zip" (빠른 설치) 또는 "api" (느린 설치)

    #todo: 제미나이 참고해서 여기 이어서 제작