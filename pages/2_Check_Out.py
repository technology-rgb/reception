import hashlib
import os
import streamlit as st
from database import init_db, get_active_visitors, check_out_visitor

init_db()

st.set_page_config(page_title="Check Out", page_icon="🚪", layout="centered")
st.title("Visitor Check-Out")

# ── Admin authentication ─────────────────────────────────────────────────────
# Read from Streamlit secrets (cloud) → env var → default
try:
    _ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD", "admin123")
except Exception:
    _ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
_ADMIN_HASH = hashlib.sha256(_ADMIN_PASSWORD.encode()).hexdigest()


def _require_admin():
    if st.session_state.get("admin_ok"):
        col1, col2 = st.columns([4, 1])
        col1.caption(f"Logged in as Admin")
        if col2.button("Logout", key="logout"):
            st.session_state.admin_ok = False
            st.rerun()
        return True

    st.info("This page is restricted to admin staff.")
    with st.form("admin_login"):
        pwd = st.text_input("Admin Password", type="password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
    if submitted:
        if hashlib.sha256(pwd.encode()).hexdigest() == _ADMIN_HASH:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not _require_admin():
    st.stop()

# ── Checkout UI (admin only) ─────────────────────────────────────────────────
active = get_active_visitors()

if not active:
    st.info("No visitors are currently inside.")
    st.stop()

search = st.text_input("Search by name or phone", placeholder="e.g. Rahul or 98765...")

filtered = active
if search.strip():
    q = search.strip().lower()
    filtered = [v for v in active if q in v["name"].lower() or q in v["phone"]]

if not filtered:
    st.warning("No matching visitor found.")
    st.stop()

st.write(f"**{len(filtered)} visitor(s) currently inside:**")

for visitor in filtered:
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"**{visitor['name']}**  \n"
                f"📞 {visitor['phone']}  \n"
                f"Meeting: {visitor['host']} · {visitor['department']}  \n"
                f"Purpose: {visitor['purpose']}  \n"
                f"Checked in at: {visitor['check_in']}"
            )
        with col2:
            if st.button("Check Out", key=f"co_{visitor['id']}", type="primary"):
                check_out_visitor(visitor["id"])
                st.success(f"{visitor['name']} checked out.")
                st.rerun()
