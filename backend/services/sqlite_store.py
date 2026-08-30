import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.auth import hash_password

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "cryptotrace.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            payload TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(email: str, password_hash: str, full_name: str = "") -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
        (email.lower().strip(), password_hash, full_name.strip()),
    )
    conn.commit()
    user_id = cursor.lastrowid
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else {}


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_case(case_id: str, payload: Dict[str, Any], user_id: Optional[int] = None) -> str:
    init_db()
    conn = get_connection()
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    conn.execute(
        """
        INSERT INTO cases (case_id, user_id, payload, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(case_id) DO UPDATE SET
            user_id = excluded.user_id,
            payload = excluded.payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (case_id, user_id, payload_json),
    )
    conn.commit()
    conn.close()
    return case_id


def load_case(case_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT payload FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["payload"])


def list_cases(user_id: Optional[int] = None) -> List[str]:
    init_db()
    conn = get_connection()
    if user_id is not None:
        rows = conn.execute("SELECT case_id FROM cases WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT case_id FROM cases ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [row["case_id"] for row in rows]


def list_case_metadata(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    if user_id is not None:
        rows = conn.execute(
            "SELECT case_id, user_id, created_at, updated_at FROM cases WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT case_id, user_id, created_at, updated_at FROM cases ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def ensure_demo_user(email: str = "demo@cryptotrace.test", password: str = "Password123!", full_name: str = "Demo Analyst") -> Dict[str, Any]:
    init_db()
    existing = get_user_by_email(email)
    if existing:
        return existing

    user = create_user(email, hash_password(password), full_name)
    return user if user else {"email": email, "full_name": full_name}


def ensure_seed_users() -> None:
    ensure_demo_user()
    ensure_demo_user("nikhiltailor7388@gmail.com", "Password123!", "Nikhil Tailor")


def count_users() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    conn.close()
    return int(row["total"]) if row else 0
