# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Locally it uses SQLite; on cloud it uses PostgreSQL (set `DATABASE_URL`).

## Architecture

Single-file SQLite database (`reception.db`, auto-created) accessed only through `database.py`.

```
app.py                 — Dashboard: today's stats, active visitor table, QR code for visitor self-check-in
utils.py               — get_local_ip(), make_qr_bytes(url) — used by app.py to generate the QR
database.py            — All SQL: schema init, CRUD helpers, stats + report queries
pages/
  1_Check_In.py        — Visitor self-check-in form (linked from QR code)
  2_Check_Out.py       — Admin-only: password gate, then search active visitors and mark as left
  3_Visitor_Log.py     — Filterable history with date range picker and CSV export
  4_Reports.py         — Weekly / monthly / custom-range reports with Plotly charts; auto-saves CSV to reports/
reports/               — Auto-created; CSVs are saved here each time the Reports page loads
reception.db           — Auto-created SQLite file (not committed)
.env.example           — Template for ADMIN_PASSWORD env var
```

Streamlit's multi-page convention drives sidebar navigation; files in `pages/` appear in filename order.

## Data Model

Single `visitors` table. Key columns:
- `status`: `'inside'` (checked in) or `'left'` (checked out)
- `visit_date`: `YYYY-MM-DD` string for daily filtering
- `check_in` / `check_out`: `HH:MM:SS` time strings

`database.py` exports:
- `init_db()` — called at the top of every page to ensure the table exists
- `check_in_visitor(...)` — inserts row with `status='inside'`
- `get_active_visitors()` — today's `status='inside'` rows
- `check_out_visitor(id)` — sets check_out time and `status='left'`
- `get_visitors_log(from_date, to_date, search)` — filtered history
- `get_report_data(from_date, to_date)` — records with computed `hour` and `duration_minutes` for charts
- `get_today_stats()` — counts + hourly breakdown for the dashboard

## Admin Authentication

The Check-Out page requires a password. It is read from the `ADMIN_PASSWORD` environment variable (default: `admin123`). Auth state lives in `st.session_state["admin_ok"]` — it resets when the browser tab is closed or refreshed.

To change the password, set the env var before launching:
```bash
$env:ADMIN_PASSWORD = "yourpassword"   # PowerShell
streamlit run app.py
```

## QR Code Check-In

On startup, `app.py` calls `utils.start_public_tunnel()` (cached via `@st.cache_resource`) which opens an SSH reverse tunnel to `localhost.run` — a free service that requires no account or extra install. SSH is built into Windows 10/11.

The tunnel gives a public `https://*.lhr.life` URL that works from any network. The QR on the dashboard always shows the current URL. If the tunnel fails (e.g. SSH blocked by firewall), it falls back to the local network IP automatically.

## Cloud Deployment (Streamlit Community Cloud + Supabase)

Both are free. Steps:

1. **Supabase** — create a free project at supabase.com → Settings → Database → copy the **Connection string (URI)** (`postgresql://...`)
2. **GitHub** — push this repo to a GitHub repository
3. **Streamlit Cloud** — go to share.streamlit.io → New app → connect your repo → set these secrets in the dashboard:
   ```
   DATABASE_URL = "postgresql://..."   # from Supabase
   ADMIN_PASSWORD = "yourpassword"
   ```
4. Deploy — the app is now live at a permanent public URL. The QR on the dashboard will point to it automatically (no SSH tunnel needed when hosted on cloud).

The SSH tunnel (`localhost.run`) only activates when `DATABASE_URL` is not set, i.e. running locally. On cloud, the app's own URL is used for the QR.

## Reports

`pages/4_Reports.py` shows three tabs: This Week, This Month, Custom Range. Each tab calls `get_report_data()` and renders four Plotly charts (daily trend, by department, purpose pie, peak hours) plus a Top 10 Hosts table. Every render auto-saves a CSV to `reports/<label>_<from>_<to>.csv` if that file doesn't already exist.
