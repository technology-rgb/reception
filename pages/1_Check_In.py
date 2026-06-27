import streamlit as st
from database import init_db, check_in_visitor

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
        check_in_visitor(name, phone, email, organization, purpose, host, department, consented=True)
        st.success(f"✅ **{name.strip()}** checked in successfully!")
        st.balloons()
