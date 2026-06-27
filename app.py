import streamlit as st
import pandas as pd
from database import init_db, get_today_stats, get_active_visitors
from utils import get_local_ip, start_public_tunnel, make_qr_bytes

init_db()

st.set_page_config(
    page_title="Reception — Avantika University",
    page_icon="🏫",
    layout="wide",
)

st.title("Reception Desk")
st.caption("Avantika University — Visitor Management System")


@st.cache_resource(show_spinner="Starting public access tunnel...")
def _public_url():
    return start_public_tunnel()


# ── Layout: stats + QR side by side ─────────────────────────────────────────
left, right = st.columns([3, 1])

with left:
    stats = get_today_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Visitors Today", stats["total"])
    c2.metric("Currently Inside", stats["inside"])
    c3.metric("Checked Out", stats["total"] - stats["inside"])

    st.divider()

    if stats["hourly"]:
        st.subheader("Check-ins by Hour")
        df_hourly = pd.DataFrame(stats["hourly"])
        df_hourly["hour"] = df_hourly["hour"].apply(lambda h: f"{int(h):02d}:00")
        df_hourly = df_hourly.set_index("hour")
        st.bar_chart(df_hourly["count"])
    else:
        st.info("No visitors checked in today yet.")

    st.divider()

    st.subheader("Currently Inside")
    active = get_active_visitors()
    if active:
        df = pd.DataFrame(active)[["name", "phone", "host", "department", "purpose", "check_in"]]
        df.columns = ["Name", "Phone", "Host", "Department", "Purpose", "Check-In"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No visitors currently inside.")

with right:
    # On Streamlit Cloud, APP_URL is set as a secret so the QR points to the live URL.
    # Locally: try SSH tunnel → fall back to local IP.
    try:
        app_url = st.secrets.get("APP_URL", "")
    except Exception:
        app_url = ""

    if app_url:
        checkin_url = f"{app_url.rstrip('/')}/Check_In"
        st.success("🌐 Public — any network")
    else:
        public_url = _public_url()
        if public_url:
            checkin_url = f"{public_url}/Check_In"
            st.success("🌐 Public — any network")
        else:
            checkin_url = f"http://{get_local_ip()}:8501/Check_In"
            st.warning("📡 Local network only")

    st.markdown("### Visitor Check-In")
    st.markdown("Scan to fill the form:")
    st.image(make_qr_bytes(checkin_url), width=220)
    st.caption(f"`{checkin_url}`")
