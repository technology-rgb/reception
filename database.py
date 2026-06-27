import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

# DATABASE_URL can come from Streamlit secrets (cloud) or env var (local).
# Unset → SQLite is used automatically.
def _get_db_url():
    try:
        import streamlit as st
        return st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    except Exception:
        return os.getenv("DATABASE_URL")

_DATABASE_URL = _get_db_url()
_DB_PATH = Path(__file__).parent / "reception.db"
_PG = bool(_DATABASE_URL)


# ── Connection helpers ────────────────────────────────────────────────────────

def _connect():
    if _PG:
        import psycopg2
        import psycopg2.extras
        parsed = urlparse(_DATABASE_URL)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=unquote(parsed.password or ""),
            sslmode="require",
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    return conn, cur


def _sql(q: str) -> str:
    """Translate SQLite dialect to PostgreSQL when needed."""
    if _PG:
        q = q.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        q = q.replace("?", "%s")
    return q


def _run(query: str, params=()):
    conn, cur = _connect()
    try:
        cur.execute(_sql(query), params)
        conn.commit()
    finally:
        conn.close()


def _fetch(query: str, params=()) -> list[dict]:
    conn, cur = _connect()
    try:
        cur.execute(_sql(query), params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    _run("""
        CREATE TABLE IF NOT EXISTS visitors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            phone        TEXT NOT NULL,
            email        TEXT,
            organization TEXT,
            purpose      TEXT NOT NULL,
            host         TEXT NOT NULL,
            department   TEXT NOT NULL,
            check_in     TEXT NOT NULL,
            check_out    TEXT,
            visit_date   TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'inside'
        )
    """)


# ── Write operations ──────────────────────────────────────────────────────────

def check_in_visitor(name, phone, email, organization, purpose, host, department):
    now = datetime.now()
    _run("""
        INSERT INTO visitors
          (name, phone, email, organization, purpose, host, department,
           check_in, visit_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'inside')
    """, (
        name.strip(), phone.strip(), email.strip() or None,
        organization.strip() or None, purpose.strip(),
        host.strip(), department.strip(),
        now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"),
    ))


def check_out_visitor(visitor_id):
    _run(
        "UPDATE visitors SET check_out = ?, status = 'left' WHERE id = ?",
        (datetime.now().strftime("%H:%M:%S"), visitor_id),
    )


# ── Read operations ───────────────────────────────────────────────────────────

def get_active_visitors():
    return _fetch(
        "SELECT * FROM visitors WHERE status = 'inside' AND visit_date = ? ORDER BY check_in DESC",
        (date.today().isoformat(),),
    )


def get_visitors_log(from_date=None, to_date=None, search=None):
    q = "SELECT * FROM visitors WHERE 1=1"
    params = []
    if from_date:
        q += " AND visit_date >= ?"
        params.append(from_date)
    if to_date:
        q += " AND visit_date <= ?"
        params.append(to_date)
    if search:
        q += " AND (name LIKE ? OR phone LIKE ? OR host LIKE ? OR department LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    q += " ORDER BY visit_date DESC, check_in DESC"
    return _fetch(q, params)


def get_report_data(from_date: str, to_date: str):
    rows = _fetch("""
        SELECT visit_date, department, purpose, host, check_in, check_out
        FROM visitors
        WHERE visit_date BETWEEN ? AND ?
        ORDER BY visit_date, check_in
    """, (from_date, to_date))
    for r in rows:
        try:
            r["hour"] = int(str(r["check_in"])[:2])
        except Exception:
            r["hour"] = 0
        try:
            if r["check_out"]:
                ci = datetime.strptime(str(r["check_in"]), "%H:%M:%S")
                co = datetime.strptime(str(r["check_out"]), "%H:%M:%S")
                r["duration_minutes"] = (co - ci).seconds / 60
            else:
                r["duration_minutes"] = None
        except Exception:
            r["duration_minutes"] = None
    return rows


def get_today_stats():
    today = date.today().isoformat()
    rows = _fetch("SELECT COUNT(*) AS n FROM visitors WHERE visit_date = ?", (today,))
    total = rows[0]["n"]
    rows = _fetch(
        "SELECT COUNT(*) AS n FROM visitors WHERE visit_date = ? AND status = 'inside'", (today,)
    )
    inside = rows[0]["n"]
    hourly = _fetch("""
        SELECT substr(check_in, 1, 2) AS hour, COUNT(*) AS count
        FROM visitors WHERE visit_date = ?
        GROUP BY hour ORDER BY hour
    """, (today,))
    return {"total": total, "inside": inside, "hourly": hourly}
