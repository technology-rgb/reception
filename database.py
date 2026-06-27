import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

_DB_PATH = Path(__file__).parent / "reception.db"


def _get_db_url() -> str | None:
    """Called at runtime (not import time) so st.secrets is always ready."""
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return os.getenv("DATABASE_URL")


def _connect():
    db_url = _get_db_url()
    if db_url:
        import psycopg2
        import psycopg2.extras
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=unquote(parsed.password or ""),
            sslmode="require",
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, cur, True
    else:
        import sqlite3
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        return conn, cur, False


def _sql(q: str, pg: bool) -> str:
    if pg:
        q = q.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        q = q.replace("?", "%s")
        q = q.replace("IN ('pending', 'inside')", "IN ('pending', 'inside')")
    return q


def _run(query: str, params=()):
    conn, cur, pg = _connect()
    try:
        cur.execute(_sql(query, pg), params)
        conn.commit()
    finally:
        conn.close()


def _fetch(query: str, params=()) -> list[dict]:
    conn, cur, pg = _connect()
    try:
        cur.execute(_sql(query, pg), params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    _run("""
        CREATE TABLE IF NOT EXISTS visitors (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT NOT NULL,
            phone             TEXT NOT NULL,
            email             TEXT,
            organization      TEXT,
            purpose           TEXT NOT NULL,
            host              TEXT NOT NULL,
            department        TEXT NOT NULL,
            check_in          TEXT NOT NULL,
            check_out         TEXT,
            visit_date        TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'inside',
            consented_at      TEXT,
            confirmation_code TEXT
        )
    """)
    # Migrate existing databases — safe to re-run, errors mean column exists
    for ddl in [
        "ALTER TABLE visitors ADD COLUMN consented_at TEXT",
        "ALTER TABLE visitors ADD COLUMN confirmation_code TEXT",
    ]:
        try:
            _run(ddl)
        except Exception:
            pass


# ── Write operations ──────────────────────────────────────────────────────────

def check_in_visitor(name, phone, email, organization, purpose, host, department,
                     consented=False, pending=False):
    """
    Insert a visitor record.
    pending=True  → status='pending', generates a 4-digit confirmation_code, returns the code.
    pending=False → status='inside'  (staff-assisted, already confirmed), returns None.
    """
    from random import randint
    now = datetime.now()
    consented_at = now.isoformat() if consented else None
    status = "pending" if pending else "inside"
    code = str(randint(1000, 9999)) if pending else None
    _run("""
        INSERT INTO visitors
          (name, phone, email, organization, purpose, host, department,
           check_in, visit_date, status, consented_at, confirmation_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name.strip(), phone.strip(), email.strip() or None,
        organization.strip() or None, purpose.strip(),
        host.strip(), department.strip(),
        now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"),
        status, consented_at, code,
    ))
    return code


def check_out_visitor(visitor_id):
    _run(
        "UPDATE visitors SET check_out = ?, status = 'left' WHERE id = ?",
        (datetime.now().strftime("%H:%M:%S"), visitor_id),
    )


def confirm_visitor_by_code(code: str) -> dict | None:
    """Confirm a pending visitor using their 4-digit code. Returns the record or None."""
    rows = _fetch(
        "SELECT * FROM visitors WHERE confirmation_code = ? AND visit_date = ? AND status = 'pending'",
        (code.strip(), date.today().isoformat()),
    )
    if not rows:
        return None
    v = rows[0]
    _run("UPDATE visitors SET status = 'inside' WHERE id = ?", (v["id"],))
    return v


# ── Read operations ───────────────────────────────────────────────────────────

def get_todays_active_checkin(phone: str) -> dict | None:
    """Return today's pending/inside record for this phone number, or None."""
    rows = _fetch(
        "SELECT id, name, check_in, status FROM visitors "
        "WHERE phone = ? AND visit_date = ? AND status IN ('pending', 'inside')",
        (phone.strip(), date.today().isoformat()),
    )
    return rows[0] if rows else None


def get_pending_visitors() -> list[dict]:
    return _fetch(
        "SELECT * FROM visitors WHERE status = 'pending' AND visit_date = ? ORDER BY check_in DESC",
        (date.today().isoformat(),),
    )


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
    rows = _fetch(
        "SELECT COUNT(*) AS n FROM visitors WHERE visit_date = ? AND status != 'pending'", (today,)
    )
    total = rows[0]["n"]
    rows = _fetch(
        "SELECT COUNT(*) AS n FROM visitors WHERE visit_date = ? AND status = 'inside'", (today,)
    )
    inside = rows[0]["n"]
    rows = _fetch(
        "SELECT COUNT(*) AS n FROM visitors WHERE visit_date = ? AND status = 'pending'", (today,)
    )
    pending = rows[0]["n"]
    hourly = _fetch("""
        SELECT substr(check_in, 1, 2) AS hour, COUNT(*) AS count
        FROM visitors WHERE visit_date = ? AND status != 'pending'
        GROUP BY hour ORDER BY hour
    """, (today,))
    return {"total": total, "inside": inside, "pending": pending, "hourly": hourly}
