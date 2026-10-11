use std::fs;
use std::path::PathBuf;
use std::sync::OnceLock;
use rusqlite::{Connection, OptionalExtension};
use tauri::{AppHandle, Manager};
use tokio::sync::Mutex;

pub type Error = Box<dyn std::error::Error + Send + Sync>;
pub type Result<T> = std::result::Result<T, Error>;

static INSTANCE: OnceLock<SystemDB> = OnceLock::new();

pub struct SystemDB {
    conn: Mutex<Connection>,
    db_path: PathBuf,
}

impl SystemDB {
    /// AppHandle을 통해 각 OS별 로컬 유저 데이터 폴더(manilet/aetaforum/setting.db)로 데이터베이스 초기화 및 싱글톤 등록
    pub async fn init_db(app: &AppHandle) -> Result<&'static SystemDB> {
        if let Some(db) = INSTANCE.get() {
            return Ok(db);
        }

        let db_path = app
            .path()
            .local_data_dir()?
            .join("manilet")
            .join("aetaforum")
            .join("setting.db");

        if let Some(parent) = db_path.parent() {
            fs::create_dir_all(parent)?;
        }

        let conn = Connection::open(&db_path)?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;
             CREATE TABLE IF NOT EXISTS settings (
                 key TEXT PRIMARY KEY NOT NULL,
                 value TEXT NOT NULL
             );"
        )?;

        let db = SystemDB {
            conn: Mutex::new(conn),
            db_path,
        };

        let _ = INSTANCE.set(db);
        INSTANCE
            .get()
            .ok_or_else(|| "Failed to retrieve initialized SystemDB instance".into())
    }

    /// 어디서든 전역 싱글톤 인스턴스에 접근
    pub fn global() -> &'static SystemDB {
        INSTANCE
            .get()
            .expect("SystemDB is not initialized. Please call SystemDB::init_db first.")
    }

    /// 싱글톤 인스턴스에 안전하게 접근 (초기화되지 않은 경우 None 반환)
    pub fn try_global() -> Option<&'static SystemDB> {
        INSTANCE.get()
    }

    /// 키와 값을 저장. 이미 키가 존재하면 변경하지 않고 기존 값을 반환, 없으면 저장 후 반환.
    pub async fn ensure(&self, key: &str, value: &str) -> Result<String> {
        let conn = self.conn.lock().await;
        let existing: Option<String> = conn
            .query_row(
                "SELECT value FROM settings WHERE key = ?1",
                [key],
                |row| row.get(0),
            )
            .optional()?;

        if let Some(val) = existing {
            return Ok(val);
        }

        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?1, ?2)",
            [key, value],
        )?;

        Ok(value.to_string())
    }

    /// 키에 해당하는 값을 반환. 키가 없으면 에러 반환.
    pub async fn get(&self, key: &str) -> Result<String> {
        let conn = self.conn.lock().await;
        let val: Option<String> = conn
            .query_row(
                "SELECT value FROM settings WHERE key = ?1",
                [key],
                |row| row.get(0),
            )
            .optional()?;

        match val {
            Some(v) => Ok(v),
            None => Err(format!("Key not found: '{}'", key).into()),
        }
    }

    /// 키의 값을 새 값으로 변경. 키가 없으면 에러 반환.
    pub async fn set(&self, key: &str, new_value: &str) -> Result<()> {
        let conn = self.conn.lock().await;
        let affected = conn.execute(
            "UPDATE settings SET value = ?1 WHERE key = ?2",
            [new_value, key],
        )?;

        if affected == 0 {
            Err(format!("Key not found: '{}'", key).into())
        } else {
            Ok(())
        }
    }

    /// 데이터베이스 파일 경로 반환
    pub fn db_path(&self) -> &PathBuf {
        &self.db_path
    }
}