import base64
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from tinydb import TinyDB, Query

from nexus_app.config import DB_PATH

__all__ = ["CryptoDB", "is_password_setting"]

_CANARY_TEXT = "__crypto_canary__"
_DEFAULT_TABLE = "_default"
_MISSING = object()

ALLOW_TYPE = (str, int, float, bool, type(None))

class CryptoDB:
    _instances = {}  # 테이블별 객체들 저장용
    _shared_db = None  # TinyDB 파일 연결 객체
    _shared_cipher = None  # 암호화 엔진

    def __new__(cls, table_name: str = _DEFAULT_TABLE):
        # 테이블 별 싱글톤 구조
        if table_name not in cls._instances:
            cls._instances[table_name] = super(CryptoDB, cls).__new__(cls)
        return cls._instances[table_name]

    def __init__(self, table_name: str = _DEFAULT_TABLE):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 비밀번호 세팅, 초기화
        if CryptoDB._shared_db is None or CryptoDB._shared_cipher is None:
            raise RuntimeError("CryptoDB가 초기화되지 않았습니다. 먼저 CryptoDB.initialize(password)를 호출하세요.")

        # 테이블 지정
        self._table_name = table_name
        self._table = CryptoDB._shared_db.table(table_name)
        self._query = Query()

        self._initialized = True

    # private -----------------------

    @classmethod
    def _derive_cipher(cls, password: str, salt: bytes) -> Fernet:
        # PBKDF2 알고리즘으로 AES 암호화 키 생성
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return Fernet(key)

    def _encrypt(self, value: Any) -> str:
        json_str = json.dumps(value)
        return self._shared_cipher.encrypt(json_str.encode('utf-8')).decode('utf-8')

    def _decrypt(self, encrypted_str: str) -> Any:
        try:
            decrypted_bytes = self._shared_cipher.decrypt(encrypted_str.encode('utf-8'))
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception as e:
            raise ValueError(f"CryptoDB[{self._table_name}] 데이터 복호화 실패: {e}")

    # public -----------------------

    @classmethod
    def initialize(cls, password: str) -> bool:
        """
        앱 시작 시 비밀번호로 DB를 초기화하고 검증합니다.

        Args:
            password: 데이터 암호화에 사용할 비밀번호

        Returns:
            bool: 비밀번호 검증 성공 여부
        """
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = TinyDB(DB_PATH)
        meta_table = db.table(_DEFAULT_TABLE)

        meta = meta_table.get(Query().type == "auth")

        if not meta:
            # 최초 실행 - 동적 Salt 생성
            salt = os.urandom(16)
            cipher = cls._derive_cipher(password, salt)
            encrypted_canary = cipher.encrypt(_CANARY_TEXT.encode("utf-8")).decode("utf-8")

            meta_table.insert({
                "type": "auth",
                "salt": base64.b64encode(salt).decode("utf-8"),
                "canary": encrypted_canary
            })
        else:
            # 기존 DB - Salt 불러오기 및 비밀번호 즉시 검증
            salt = base64.b64decode(meta["salt"].encode("utf-8"))
            cipher = cls._derive_cipher(password, salt)

            try:
                decrypted = cipher.decrypt(meta["canary"].encode("utf-8")).decode("utf-8")
                if decrypted != _CANARY_TEXT:
                    raise ValueError("비밀번호 검증에 실패했습니다.")
            except InvalidToken:
                return False

        cls._shared_db = db
        cls._shared_cipher = cipher
        return True

    def create(self, key: str, value: Any, encrypt: bool = False, exist_ok: bool = False) -> Any:
        """새로운 키-값 쌍을 데이터베이스에 저장합니다.

        Args:
            key (str): 저장할 데이터의 고유 키입니다.
            value (Any): 저장할 데이터 값입니다.
            encrypt (bool, optional): True일 경우 값을 암호화하여 저장합니다. (기본값: False)
            exist_ok (bool, optional): True일 경우 키가 이미 존재하면 예외를 발생시키지 않고 '기존에 저장된 값'을 반환합니다. (기본값: False)

        Returns:
            Any: 새로 저장된 값(value)을 반환하거나, 이미 존재할 경우(exist_ok=True) 기존 DB에 있던 값을 반환합니다.

        Raises:
            KeyError: exist_ok가 False이면서 해당 'key'가 이미 존재하는 경우 발생합니다.
            TypeError: 저장 불가능한 데이터가 들어올 경우 발생합니다.
        """
        if not isinstance(value, ALLOW_TYPE):
            raise TypeError(
                f"CryptoDB 저장 실패: '{type(value).__name__}' 타입은 저장할 수 없습니다. "
                f"(허용 타입: str, int, float, bool, type(None))"
            )
        existing_record = self._table.get(self._query.key == key)

        if existing_record:
            if exist_ok:
                return self.read(key)

            raise KeyError(f"CryptoDB[{self._table_name}] create 실패: '{key}' 키가 이미 존재합니다.")

        final_value = self._encrypt(value) if encrypt else value

        self._table.insert({
            'key': key,
            'value': final_value,
            'is_encrypted': encrypt
        })
        return value

    def read(self, key: str, default: Any = _MISSING) -> Any:
        """데이터베이스에서 특정 키와 일치하는 값을 조회합니다.

        Args:
            key (str): 조회할 데이터의 고유 키입니다.
            default (Any, optional): 키를 찾을 수 없을 때 반환할 기본값입니다. 지정하지 않으면 KeyError가 발생합니다.

        Returns:
            Any: 조회된 데이터의 값입니다. 암호화되어 저장된 경우 복호화된 값을 반환합니다.

        Raises:
            KeyError: default 값이 지정되지 않았고, 해당 'key'를 찾을 수 없는 경우 발생합니다.
        """
        result = self._table.search(self._query.key == key)
        if not result:
            if default is _MISSING:
                raise KeyError(f"CryptoDB[{self._table_name}] read 실패: '{key}' 키를 찾을 수 없습니다.")
            return default

        record = result[0]
        if record['is_encrypted']:
            return self._decrypt(record['value'])
        return record['value']

    def update(self, key: str, value: Any) -> Any:
        """데이터베이스에 존재하는 특정 키의 값을 수정합니다.
        기존에 암호화되어 저장된 데이터라면 수정 시에도 자동으로 암호화가 적용됩니다.

        Args:
            key (str): 수정할 데이터의 고유 키입니다.
            value (Any): 새로 덮어쓸 데이터 값입니다.

        Returns:
            Any: 수정이 완료된 데이터의 값(value)을 반환합니다.

        Raises:
            KeyError: 수정하려는 'key'가 데이터베이스에 존재하지 않는 경우 발생합니다.
            TypeError: 저장 불가능한 데이터가 들어올 경우 발생합니다.
        """
        if not isinstance(value, ALLOW_TYPE):
            raise TypeError(
                f"CryptoDB 저장 실패: '{type(value).__name__}' 타입은 저장할 수 없습니다. "
                f"(허용 타입: str, int, float, bool, type(None))"
            )

        result = self._table.search(self._query.key == key)
        if not result:
            raise KeyError(f"CryptoDB[{self._table_name}] update 실패: '{key}' 키를 찾을 수 없습니다.")

        should_encrypt = result[0]['is_encrypted']
        final_value = self._encrypt(value) if should_encrypt else value

        self._table.update(
            {'value': final_value, 'is_encrypted': should_encrypt},
            self._query.key == key
        )
        return value

    def delete(self, key: str, missing_ok: bool = True) -> None:
        """데이터베이스에서 특정 키와 일치하는 데이터를 삭제합니다.

        Args:
            key (str): 삭제할 데이터의 고유 키입니다.
            missing_ok (bool, optional): True일 경우 키가 존재하지 않아도 예외를 발생시키지 않고 조용히 넘어갑니다. (기본값: True)

        Raises:
            KeyError: missing_ok가 False이면서 삭제하려는 'key'가 존재하지 않는 경우 발생합니다.
        """
        if missing_ok:
            self._table.remove(self._query.key == key)
        else:
            item = self._table.get(self._query.key == key)
            if item is None:
                raise KeyError(f"CryptoDB[{self._table_name}] delete 실패: '{key}' 키가 존재하지 않습니다.")
            self._table.remove(self._query.key == key)


def is_password_setting() -> bool:
    """DB 비밀번호 최초 설정이 필요한지 확인합니다.

    Returns:
        bool: 초기화 여부 (이미 비밀번호가 세팅되어 있을 시 True)
    """
    if not DB_PATH.exists():
        return False

    with TinyDB(DB_PATH) as db:
        meta_table = db.table(_DEFAULT_TABLE)
        auth_meta = meta_table.get(Query().type == "auth")
        return auth_meta is not None
