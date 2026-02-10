import streamlit as st
import sys
import os
import time
from datetime import date

# Add project root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_config import DB_PATH
from utils.db_helper import fetch_query, execute_query

# ----------------------------
# Sidebar: Logout
# ----------------------------
if st.session_state.get("logged_in"):
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{st.session_state.get('role').capitalize()}`")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("✅ Logged out successfully.")
            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")

# ----------------------------
# Auth Guard
# ----------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ You must log in to access this page.")
    st.stop()

if st.session_state.get("role") != "student":
    st.warning("🚫 Access Denied. Only students can submit errors.")
    st.stop()

st.title("📝 Report Attendance Error")

# Auto-fetch student enrollment and semester
student_enroll = st.session_state.get("enroll", "")
student_semester = st.session_state.get("semester", 5)

# ----------------------------
# Fetch subjects for student's semester
# ----------------------------
subjects, err = fetch_query(
    "SELECT DISTINCT subject FROM Faculty WHERE semester = ? ORDER BY subject",
    (student_semester,)
)
subjects_list = [row[0] for row in subjects] if subjects else []
if not subjects_list:
    st.warning("⚠️ No subjects found for your semester.")
    st.stop()

selected_subject = st.selectbox("Select Subject", subjects_list)

# ----------------------------
# Fetch available lectures for selected subject
# ----------------------------
lectures, err = fetch_query(
    "SELECT id, date FROM Lecture WHERE subject = ? AND semester = ? ORDER BY date ASC",
    (selected_subject, student_semester)
)
lecture_dates = [row[1] for row in lectures] if lectures else []

if not lecture_dates:
    st.warning("⚠️ No lectures found for this subject.")
    st.stop()

selected_date = st.selectbox("Select Lecture Date", lecture_dates)

# Resolve lecture_id
lecture_id = next((lec[0] for lec in lectures if lec[1] == selected_date), None)
if not lecture_id:
    st.error("❌ Unable to resolve lecture. Please contact admin.")
    st.stop()

# ----------------------------
# Predefined attendance error options
# ----------------------------
error_options = [
    "Marked Absent but Present",
    "Marked Present but Absent",
    "Not Detected",
    "Multiple Detection",
    "Other"
]

issue = st.selectbox("Select Attendance Error", error_options)
submit = st.button("Submit Error")

if submit:
    success, err = execute_query(
        "INSERT INTO Error_Report (lecture_id, enrollment_number, issue, status) VALUES (?, ?, ?, ?)",
        (lecture_id, student_enroll.strip(), issue, "Pending")
    )
    if success:
        st.success("✅ Issue submitted successfully and marked as Pending.")
    else:
        st.error(f"❌ Database error: {err}")
