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

if st.session_state.get("role") != "faculty":
    st.warning("🚫 Access Denied. Only faculty can update attendance and resolve errors.")
    st.stop()

st.title("📝 Manual Attendance Update & Error Resolution")

faculty_email = st.session_state.get("faculty_email")
faculty_semester = st.session_state.get("semester", 1)

# ----------------------------
# Auto-fetch faculty subject and semester from DB
# ----------------------------
subject_row, err = fetch_query(
    "SELECT DISTINCT subject FROM Faculty WHERE email = ? AND semester = ?",
    (faculty_email, faculty_semester)
)
if not subject_row:
    st.warning("⚠️ No subject assigned to you for your semester.")
    st.stop()

faculty_subject = subject_row[0][0]
st.markdown(f"**Subject:** {faculty_subject} | **Semester:** {faculty_semester}")

# ----------------------------
# Fetch lectures for this faculty
# ----------------------------
lectures, err = fetch_query(
    "SELECT id, date FROM Lecture WHERE subject = ? AND semester = ? AND faculty_email = ? ORDER BY date ASC",
    (faculty_subject, faculty_semester, faculty_email)
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
# Display pending errors for this lecture
# ----------------------------
st.subheader("📋 Pending Student Errors")

errors, err = fetch_query(
    "SELECT id, enrollment_number, student_name, issue FROM Error_Report "
    "WHERE lecture_id = ? AND status = 'Pending' ORDER BY id ASC",
    (lecture_id,)
)

error_resolution_options = ["Pending", "Resolved", "Rejected"]

if not errors:
    st.info("✅ No pending errors for this lecture.")
else:
    for err_record in errors:
        error_id, enroll, student_name, issue_text = err_record
        st.markdown(f"**{student_name} ({enroll})**: {issue_text}")
        resolution = st.selectbox(
            f"Resolve Error ID {error_id}",
            error_resolution_options,
            key=f"error_{error_id}"
        )
        if st.button(f"Update Error ID {error_id}", key=f"btn_{error_id}"):
            success, err = execute_query(
                "UPDATE Error_Report SET status = ? WHERE id = ?",
                (resolution, error_id)
            )
            if success:
                st.success(f"✅ Error ID {error_id} marked as {resolution}.")
            else:
                st.error(f"❌ Database error: {err}")

# ----------------------------
# Manual attendance update (only Present or Absent)
# ----------------------------
st.subheader("📝 Update Attendance")
enroll_att = st.text_input("Student Enrollment Number", key="att_enroll")
new_status = st.selectbox("New Status", ["Present", "Absent"], key="att_status")

if st.button("Update Attendance"):
    if not enroll_att.strip():
        st.warning("⚠️ Enter a valid enrollment number.")
    else:
        success, err = execute_query(
            "UPDATE Attendance SET status = ? WHERE enrollment_number = ? AND lecture_id = ?",
            (new_status, enroll_att.strip(), lecture_id)
        )
        if success:
            # Confirm update
            rows_affected, err2 = fetch_query(
                "SELECT COUNT(*) FROM Attendance WHERE enrollment_number = ? AND lecture_id = ? AND status = ?",
                (enroll_att.strip(), lecture_id, new_status)
            )
            if rows_affected and rows_affected[0][0] == 0:
                st.warning("⚠️ No matching attendance record found to update.")
            else:
                st.success("✅ Attendance updated successfully.")
        else:
            st.error(f"❌ Database error: {err}")
