from pathlib import Path
from datetime import date, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, get_report_data

init_db()

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
st.title("Visitor Reports")

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def _auto_save_csv(df: pd.DataFrame, label: str, from_date: date, to_date: date):
    filename = REPORTS_DIR / f"{label}_{from_date}_{to_date}.csv"
    if not filename.exists():
        df.to_csv(filename, index=False)


def render_report(from_date: date, to_date: date, label: str):
    rows = get_report_data(from_date.isoformat(), to_date.isoformat())
    if not rows:
        st.info(f"No visitor data for this {label.lower()} period.")
        return

    df = pd.DataFrame(rows)

    # ── Summary metrics ──────────────────────────────────────────────────────
    avg_dur = df["duration_minutes"].dropna()
    peak_hour = int(df["hour"].mode().iloc[0]) if not df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Visitors", len(df))
    c2.metric("Departments Visited", df["department"].nunique())
    c3.metric("Avg Visit Duration", f"{avg_dur.mean():.0f} min" if not avg_dur.empty else "N/A")
    c4.metric("Peak Hour", f"{peak_hour:02d}:00–{peak_hour+1:02d}:00" if peak_hour is not None else "N/A")

    st.divider()

    # ── Charts ───────────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        daily = df.groupby("visit_date").size().reset_index(name="Visitors")
        fig = px.bar(
            daily, x="visit_date", y="Visitors",
            title="Daily Visitor Count",
            labels={"visit_date": "Date"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        dept = (
            df.groupby("department").size()
            .reset_index(name="Visitors")
            .sort_values("Visitors", ascending=False)
        )
        fig2 = px.bar(
            dept, x="department", y="Visitors",
            title="Visitors by Department",
            labels={"department": "Department"},
            color="Visitors", color_continuous_scale="Blues",
        )
        fig2.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        purp = df.groupby("purpose").size().reset_index(name="Count")
        fig3 = px.pie(purp, names="purpose", values="Count", title="Visit Purpose Breakdown", hole=0.35)
        st.plotly_chart(fig3, use_container_width=True)

        hourly = df.groupby("hour").size().reset_index(name="Check-Ins")
        hourly["Time"] = hourly["hour"].apply(lambda h: f"{h:02d}:00")
        fig4 = px.bar(
            hourly, x="Time", y="Check-Ins",
            title="Check-ins by Hour of Day",
            color="Check-Ins", color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Top hosts
    st.divider()
    st.subheader("Top 10 Hosts")
    top_hosts = (
        df.groupby("host").size()
        .reset_index(name="Visitors")
        .sort_values("Visitors", ascending=False)
        .head(10)
    )
    st.dataframe(top_hosts, use_container_width=True, hide_index=True)

    # ── Auto-save + download ──────────────────────────────────────────────────
    _auto_save_csv(df, label, from_date, to_date)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {label} Data (CSV)",
        data=csv,
        file_name=f"visitor_report_{from_date}_{to_date}.csv",
        mime="text/csv",
    )
    st.caption(f"Reports are also auto-saved to `reports/` each time this page loads.")


# ── Tabs ─────────────────────────────────────────────────────────────────────
today = date.today()
tab_weekly, tab_monthly, tab_custom = st.tabs(["This Week", "This Month", "Custom Range"])

with tab_weekly:
    week_start = today - timedelta(days=today.weekday())  # Monday
    st.caption(f"{week_start.strftime('%d %b %Y')} — {today.strftime('%d %b %Y')}")
    render_report(week_start, today, "Weekly")

with tab_monthly:
    month_start = today.replace(day=1)
    st.caption(f"{today.strftime('%B %Y')}")
    render_report(month_start, today, "Monthly")

with tab_custom:
    col1, col2 = st.columns(2)
    from_d = col1.date_input("From", value=today - timedelta(days=30))
    to_d = col2.date_input("To", value=today)
    if from_d > to_d:
        st.error("'From' must be before 'To'.")
    else:
        render_report(from_d, to_d, "Custom")
