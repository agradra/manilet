from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from platformdirs import user_data_dir, user_downloads_dir

TITLE: str = "NEXUS"  # 사용자 ui용
APP_NAME: str = "nexus_app"  # 시스템 사용용
PACKAGE_NAME: str = "manilet-nexus-app"  # 패키지 이름 (배포용)

try:
    VERSION: str = version(PACKAGE_NAME)
except PackageNotFoundError:
    VERSION: str = "D.E.V"

# 절대 불변
DATA_DIR: Path = Path(user_data_dir(APP_NAME, appauthor=False))
DB_PATH: Path = DATA_DIR / f"{APP_NAME}_db.json"

# 초기값
DEFAULT_LOG_PATH: Path = Path(user_downloads_dir())
