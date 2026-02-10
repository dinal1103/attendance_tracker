import streamlit as st
from datetime import datetime
import time
import os
import shutil
import subprocess
from pathlib import Path
import sys
import uuid
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRIPT_PATH = os.path.join(ROOT_DIR, "mark_attendance.py")

sys.path.append(ROOT_DIR)
from utils.db_config import DB_PATH
from utils.db_helper import execute_query, fetch_query

#------------------------ Session Checks ------------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ You must log in to access this page.")
    st.stop()

if st.session_state.get("role") != "faculty":
    st.warning("Access Denied. This page is for faculty only.")
    st.stop()

#------------------------ Sidebar Logout ------------------------
if st.session_state.get("logged_in"):
    with st.sidebar:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.get('role').capitalize()}`")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("✅ Logged out successfully.")
            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")

st.title("Upload Classroom Photo - Attendance")

#------------------------ File Uploader ------------------------
uploaded_photos = st.file_uploader(
    "Upload classroom photos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

#------------------------ Form ------------------------
with st.form("upload_form"):

    # Prefill subject and semester from login session
    subject = st.session_state.get("subject", "")

    semester_value = st.session_state.get("semester", 1)
    try:
        semester = int(semester_value)
    except (ValueError, TypeError):
        semester = 1

    st.text_input("Subject", value=subject, disabled=True)
    st.number_input("Semester", value=semester, min_value=1, max_value=8, disabled=True)

    # 🔴 CHANGED: calendar-based date picker instead of text input
    today_default = datetime.now().date()
    date_input = st.date_input(
        "Lecture Date",
        value=today_default,
        format="YYYY-MM-DD"
    )

    faculty_email = st.session_state.get("faculty_email")
    faculty_name = st.session_state.get("faculty_name", "Unknown")

    previous_lectures = []
    lecture_no = None
    today_count = 0

    if faculty_email and subject.strip():
        rows, error = fetch_query(
            "SELECT id FROM Faculty WHERE email=? AND subject=? AND semester=?",
            (faculty_email, subject.strip(), semester)
        )

        if rows:
            faculty_id = rows[0][0]

            previous_lectures, _ = fetch_query(
                "SELECT id, date FROM Lecture WHERE faculty_id=? AND subject=? AND semester=? ORDER BY date ASC",
                (faculty_id, subject.strip(), semester)
            )

            total_lectures = len(previous_lectures)
            lecture_no = total_lectures + 1

            today_count = sum(
                1 for _, lec_date in previous_lectures
                if lec_date == today_default.strftime("%Y-%m-%d")
            )

    if lecture_no:
        st.info(
            f"Current lecture number for **{subject.strip()} (Sem {semester})**: **{lecture_no}** "
            f"(Total so far: {len(previous_lectures)}, Today: {today_count})"
        )

    if previous_lectures:
        st.markdown("### 📜 Previous Lectures")
        for i, (lec_id, lec_date) in enumerate(previous_lectures, start=1):
            st.text(f"Lecture {i}: {lec_date}")

    submit = st.form_submit_button("Submit")

# ------------------------ Session Defaults ------------------------
if "report_ready" not in st.session_state:
    st.session_state["report_ready"] = False
if "lecture_id" not in st.session_state:
    st.session_state["lecture_id"] = None
if "lecture_date" not in st.session_state:
    st.session_state["lecture_date"] = None

# ------------------------ Processing ------------------------
if uploaded_photos and submit:

    if not subject.strip():
        st.error("❌ Subject is required.")
        st.stop()

    # 🔴 CHANGED: date_input is already a date object (no parsing needed)
    lecture_date = date_input.strftime("%Y-%m-%d")

    if not faculty_email:
        st.error("Faculty email missing from session. Please re-login.")
        st.stop()

    rows, error = fetch_query(
        "SELECT id FROM Faculty WHERE email=? AND subject=? AND semester=?",
        (faculty_email, subject.strip(), semester)
    )

    if not rows:
        st.error("Faculty record not found. Please contact admin.")
        st.stop()

    faculty_id = rows[0][0]

    success, error = execute_query(
        "INSERT INTO Lecture (faculty_id, subject, semester, date) VALUES (?, ?, ?, ?)",
        (faculty_id, subject.strip(), semester, lecture_date)
    )
    if not success:
        st.error(f"❌ Failed to insert Lecture: {error}")
        st.stop()

    rows, _ = fetch_query(
        "SELECT id FROM Lecture WHERE faculty_id=? AND subject=? AND semester=? AND date=? ORDER BY id DESC LIMIT 1",
        (faculty_id, subject.strip(), semester, lecture_date)
    )
    lecture_id = rows[0][0]

    st.session_state["report_ready"] = True
    st.session_state["lecture_id"] = lecture_id
    st.session_state["lecture_date"] = lecture_date

    save_dir = Path(ROOT_DIR) / "class_images"
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_subject = subject.strip().replace(" ", "_")
    safe_faculty = faculty_name.strip().replace(" ", "_")

    st.markdown("### 📷 Uploaded Images with Attendance Processing")

    for uploaded_photo in uploaded_photos:
        ext = uploaded_photo.name.split(".")[-1].lower()
        file_name = (
            f"{lecture_date}_{safe_subject}_Lecture{lecture_no}_"
            f"{safe_faculty}_Sem{semester}_{uuid.uuid4().hex[:6]}.{ext}"
        )
        file_path = save_dir / file_name

        with open(file_path, "wb") as f:
            shutil.copyfileobj(uploaded_photo, f)

        success, error = execute_query(
            "INSERT INTO LectureImage (lecture_id, image_path) VALUES (?, ?)",
            (lecture_id, str(file_path))
        )

        if not success:
            st.error(f"❌ Failed to save LectureImage: {error}")
            continue

        with st.spinner(f"⏳ Processing attendance for {file_name}..."):
            result = subprocess.run(
                [sys.executable, SCRIPT_PATH, str(file_path), str(lecture_id)],
                capture_output=True,
                text=True,
                cwd=ROOT_DIR
            )

            if result.returncode == 0:
                st.image(str(file_path), caption=file_name, use_container_width=True)
                st.success(f"{file_name}: ✅ Attendance processed.")
            else:
                st.error(f"❌ Error occurred while marking attendance for {file_name}!")
                if result.stderr:
                    st.code(result.stderr)
                elif result.stdout:
                    st.code(result.stdout)

    st.success("✅ All uploaded photos processed.")

# ------------------------ Attendance Report ------------------------
if (
    st.session_state.get("report_ready")
    and st.session_state.get("lecture_date")
    and st.session_state.get("lecture_id")
):
    st.markdown("## 📊 Attendance Report for This Lecture")

    if st.button("🔍 Show Attendance Report"):
        lecture_id = st.session_state.get("lecture_id")
        lecture_date = st.session_state.get("lecture_date")

        query = """
            SELECT 
                s.enrollment_number,
                s.name AS student_name,
                a.status,
                l.date,
                l.subject,
                l.semester,
                f.name AS faculty_name,
                f.email AS faculty_email
            FROM Attendance a
            JOIN Student s ON a.enrollment_number = s.enrollment_number
            JOIN Lecture l ON a.lecture_id = l.id
            JOIN Faculty f ON l.faculty_id = f.id
            WHERE l.id = ?
            ORDER BY s.enrollment_number
        """

        rows, error = fetch_query(query, params=(lecture_id,))

        if error:
            st.error(f"❌ Database error: {error}")
        elif rows:
            df = pd.DataFrame(rows, columns=[
                "enrollment_number", "student_name", "status",
                "date", "subject", "semester",
                "faculty_name", "faculty_email"
            ])
            st.success(f"✅ Found {len(df)} records.")
            st.dataframe(df)

            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                file_name=f"attendance_{lecture_date}_sem{semester}.csv"
            )
        else:
            st.warning("⚠️ No attendance found for this lecture.")
