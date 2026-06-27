import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import init_db, get_visitors_log

init_db()

st.set_page_config(page_title="Visitor Log", page_icon="📋", layout="wide")
st.title("Visitor Log")

col1, col2, col3 = st.columns([2, 2, 3])
today = date.today()
from_date = col1.date_input("From", value=today - timedelta(days=7))
to_date = col2.date_input("To", value=today)
search = col3.text_input("Search (name, phone, host, department)", placeholder="Type to filter...")

if from_date > to_date:
    st.error("'From' date must be before 'To' date.")
    st.stop()

rows = get_visitors_log(
    from_date=from_date.isoformat(),
    to_date=to_date.isoformat(),
    search=search.strip() or None,
)

if not rows:
    st.info("No records found for the selected filters.")
    st.stop()

df = pd.DataFrame(rows)
df = df[["visit_date", "name", "phone", "email", "organization",
         "host", "department", "purpose", "check_in", "check_out", "status"]]
df.columns = ["Date", "Name", "Phone", "Email", "Organization",
              "Host", "Department", "Purpose", "Check-In", "Check-Out", "Status"]
df["Status"] = df["Status"].map({"inside": "Inside", "left": "Left"})

st.write(f"**{len(df)} record(s)**")
st.dataframe(df, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download as CSV",
    data=csv,
    file_name=f"visitor_log_{from_date}_to_{to_date}.csv",
    mime="text/csv",
)
