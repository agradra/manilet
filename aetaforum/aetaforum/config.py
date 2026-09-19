from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from platformdirs import user_data_dir, user_downloads_dir

TITLE: str = "Aetaforum"  # 사용자 ui용
PROG_NAME: str = "aetaforum"  # 시스템 사용
PACKAGE_NAME: str = "manilet-aetaforum"  # 패키지 이름 (배포용)

try:
    VERSION: str = version(PACKAGE_NAME)
except PackageNotFoundError:
    VERSION: str = "D.E.V"

# 경로
DATA_DIR: Path = Path(user_data_dir(PROG_NAME, appauthor=False))
DB_PATH: Path = DATA_DIR / f"{PROG_NAME}_db.json"
COIN_DIR: Path = DATA_DIR / "coins"

# 지원 코인 거래소
class EXCHANGE(StrEnum):
    Binance = "bnc"
    Bybit = "bbt"
    HyperLiquid = "hpl"

