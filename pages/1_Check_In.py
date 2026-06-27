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
                    st.success(f"✅ **{visitor['name']}** confirmed — now checked in!")
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
    name = col1.text_input("Full Name *")
    phone = col2.text_input("Phone Number *")
    email = col1.text_input("Email (optional)")
    organization = col2.text_input("Organization / Institution (optional)")

    st.subheader("Visit Details")
    col3, col4 = st.columns(2)
    purpose = col3.selectbox("Purpose of Visit *", PURPOSES)
    department = col4.selectbox("Department to Visit *", DEPARTMENTS)
    host = st.text_input("Whom to Meet (Name) *")

    st.divider()
    consent = st.checkbox(
        "I consent to my personal data being recorded for visitor-management and security purposes. "
        "Records are retained for **30 days** and then permanently deleted (DPDP Act compliance).",
    )

    submitted = st.form_submit_button("Check In", type="primary", use_container_width=True)

if submitted:
    if not name.strip():
        st.error("Visitor name is required.")
    elif not phone.strip():
        st.error("Phone number is required.")
    elif not host.strip():
        st.error("Please enter the name of the person to meet.")
    elif not consent:
        st.error("Please accept the data consent statement before checking in.")
    else:
        existing = get_todays_active_checkin(phone)
        if existing:
            status_label = "pending confirmation" if existing["status"] == "pending" else "already inside"
            st.warning(
                f"⚠️ This phone number is {status_label} today "
                f"(checked in at {existing['check_in']}). "
                f"Verify with the visitor before proceeding."
            )
        else:
            check_in_visitor(
                name, phone, email, organization, purpose, host, department,
                consented=True, pending=False,
            )
            st.success(f"✅ **{name.strip()}** checked in successfully!")
            st.balloons()
