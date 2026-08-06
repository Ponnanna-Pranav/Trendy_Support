"""
Lightweight persistence so state survives a restart/redeploy — the thing an
in-memory dict can't do, which matters the moment this is a real product and
not a demo. SQLite (stdlib, zero extra infra) is the right call at this
scale; see README productization notes for when to graduate to Postgres.
"""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_db_env = os.environ.get("TRENDLY_DB_PATH")
DB_PATH = _db_env if _db_env else str(Path(__file__).parent.parent / "data_store.sqlite3")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            history_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS rmas (
            rma_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS credits (
            credit_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")


# ---- sessions ----

def get_session(session_id: str) -> list[dict]:
    with _conn() as c:
        row = c.execute("SELECT history_json FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return json.loads(row["history_json"]) if row else []


def save_session(session_id: str, history: list[dict]):
    with _conn() as c:
        c.execute(
            "INSERT INTO sessions (session_id, history_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(session_id) DO UPDATE SET history_json=excluded.history_json, updated_at=CURRENT_TIMESTAMP",
            (session_id, json.dumps(history)),
        )


def delete_session(session_id: str):
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))


# ---- generic record store (tickets / rmas / credits) ----

_PK = {"tickets": "ticket_id", "rmas": "rma_id", "credits": "credit_id"}


def save_record(table: str, record_id: str, data: dict):
    with _conn() as c:
        c.execute(
            f"INSERT INTO {table} ({_PK[table]}, data_json) VALUES (?, ?)",
            (record_id, json.dumps(data, default=str)),
        )


def get_record(table: str, record_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(f"SELECT data_json FROM {table} WHERE {_PK[table]}=?", (record_id,)).fetchone()
        return json.loads(row["data_json"]) if row else None


def list_records(table: str, limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute(f"SELECT data_json FROM {table} ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r["data_json"]) for r in rows]


def get_max_id_suffix(table: str, pk_field: str, prefix_len: int) -> int | None:
    try:
        with _conn() as c:
            rows = c.execute(f"SELECT {pk_field} FROM {table}").fetchall()
            max_num = None
            for row in rows:
                val = row[pk_field]
                if val:
                    try:
                        num = int(val[prefix_len:])
                        if max_num is None or num > max_num:
                            max_num = num
                    except ValueError:
                        pass
            return max_num
    except Exception:
        return None


init_db()
