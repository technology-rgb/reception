import re
from datetime import datetime
from pathlib import Path

import streamlit as st
from database import (
    init_db, check_in_visitor,
    get_todays_active_checkin, get_pending_visitors, confirm_visitor_by_code,
)

init_db()

st.set_page_config(page_title="Check In", page_icon="✅", layout="centered")
st.title("Visitor Check-In")

DEPARTMENTS = [
    "Administration", "Academics", "Admissions", "Accounts / Finance",
    "Library", "Hostel", "IT Department", "Director's Office", "Other",
]

PURPOSES = [
    "Meeting / Appointment", "Admission Enquiry", "Fee Payment",
    "Document Submission", "Interview", "Delivery", "Maintenance", "Other",
]

# ── Visitor badge (shown after confirmation) ──────────────────────────────────
def show_badge(v: dict):
    issued = datetime.now().strftime("%d %b %Y · %I:%M %p")
    logo_path = Path(__file__).parent.parent / "mobile" / "logo.png"

    with st.container(border=True):
        col_logo, col_hdr = st.columns([1, 5])
        if logo_path.exists():
            col_logo.image(str(logo_path), width=64)
        with col_hdr:
            st.markdown("**🎫 VISITOR PASS**")
            st.caption(f"Issued: {issued}")

        st.markdown(f"## {v['name']}")
        st.divider()

        c1, c2 = st.columns(2)
        c1.markdown(f"**⏰ Time In**  \n{v.get('check_in', '—')}")
        c2.markdown(f"**🏢 Department**  \n{v.get('department', '—')}")
        c1.markdown(f"**🤝 Host**  \n{v.get('host', '—')}")
        c2.markdown(f"**📋 Purpose**  \n{v.get('purpose', '—')}")

        st.caption("✔  Valid for today only")
        if st.button("✕  Clear badge", key="clear_badge"):
            del st.session_state["badge_visitor"]
            st.rerun()

if st.session_state.get("badge_visitor"):
    show_badge(st.session_state["badge_visitor"])
    st.divider()

# ── Confirm pending visitors (mobile self-check-in) ───────────────────────────
pending = get_pending_visitors()
if pending:
    with st.expander(f"⏳ {len(pending)} pending check-in(s) awaiting confirmation", expanded=True):
        col_code, col_btn = st.columns([3, 1])
        code_input = col_code.text_input(
            "Visitor's 4-digit code",
            max_chars=4, placeholder="e.g. 3847",
            key="confirm_code_input",
            label_visibility="collapsed",
        )
        confirmed = col_btn.button("✓ Confirm", type="primary", use_container_width=True)
        if confirmed:
            if not code_input.strip():
                st.error("Enter the visitor's 4-digit code.")
            else:
                visitor = confirm_visitor_by_code(code_input.strip())
                if visitor:
                    st.session_state["badge_visitor"] = visitor
                    st.rerun()
                else:
                    st.error("Code not found or already confirmed.")

        st.caption("Pending visitors:")
        for v in pending:
            c1, c2 = st.columns([4, 1])
            c1.markdown(
                f"**{v['name']}** &nbsp;·&nbsp; {v['phone']} &nbsp;·&nbsp; "
                f"{v['host']} ({v['department']}) &nbsp;·&nbsp; submitted {v['check_in']}"
            )
            c2.code(v["confirmation_code"] or "—", language=None)

st.divider()

# ── New check-in form ─────────────────────────────────────────────────────────
with st.form("checkin_form", clear_on_submit=True):
    st.subheader("Visitor Details")
    col1, col2 = st.columns(2)
    name         = col1.text_input("Full Name *")
    phone        = col2.text_input("Phone Number *")
    email        = col1.text_input("Email (optional)")
    organization = col2.text_input("Organization / Institution (optional)")
    vehicle_number = st.text_input(
        "Vehicle Number (optional)",
        placeholder="e.g. MP 09 AB 1234",
        help="Leave blank if visitor arrived on foot.",
    )

    st.subheader("Visit Details")
    col3, col4 = st.columns(2)
    purpose    = col3.selectbox("Purpose of Visit *", PURPOSES)
    department = col4.selectbox("Department to Visit *", DEPARTMENTS)
    host       = st.text_input("Whom to Meet (Name) *")

    st.divider()
    consent = st.checkbox(
        "I consent to my personal data being recorded for visitor-management and security purposes. "
        "Records are retained for **30 days** and then permanently deleted (DPDP Act compliance).",
    )

    submitted = st.form_submit_button("Check In", type="primary", use_container_width=True)

if submitted:
    phone_digits = re.sub(r'\D', '', phone)
    if not name.strip():
        st.error("Visitor name is required.")
    elif not phone_digits:
        st.error("Phone number is required.")
    elif not re.fullmatch(r'[6-9]\d{9}', phone_digits):
        st.error("Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
    elif not host.strip():
        st.error("Please enter the name of the person to meet.")
    elif not consent:
        st.error("Please accept the data consent statement before checking in.")
    else:
        existing = get_todays_active_checkin(phone_digits)
        if existing:
            status_label = "pending confirmation" if existing["status"] == "pending" else "already inside"
            st.warning(
                f"⚠️ This phone number is {status_label} today "
                f"(checked in at {existing['check_in']}). "
                f"Verify with the visitor before proceeding."
            )
        else:
            check_in_visitor(
                name, phone_digits, email, organization, purpose, host, department,
                consented=True, pending=False,
                vehicle_number=vehicle_number or None,
            )
            st.success(f"✅ **{name.strip()}** checked in successfully!")
            st.balloons()
