import streamlit as st
import sys, os,time
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_helper import fetch_query

# ------------------------ Page Setup ------------------------
st.set_page_config(page_title="📊 Attendance Report", layout="wide")
st.title("📊 Attendance Report")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ You must log in to access this page.")
    st.stop()

if st.session_state.get("logged_in"):
    with st.sidebar:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.get('role').capitalize()}`")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("✅ Logged out successfully.")
            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")
# ------------------------ Auth Check ------------------------

# ------------------------ Select Subject & Semester ------------------------
subjects_q = "SELECT DISTINCT subject FROM Lecture ORDER BY subject"
subjects, err = fetch_query(subjects_q)
if err:
    st.error(f"❌ Database error: {err}")
    st.stop()

if not subjects:
    st.warning("⚠️ No subjects found in the database.")
    st.stop()

subject = st.selectbox("📘 Select Subject", [s[0] for s in subjects])

semesters_q = "SELECT DISTINCT semester FROM Lecture WHERE subject=? ORDER BY semester"
semesters, _ = fetch_query(semesters_q, (subject,))
semester = st.selectbox("🎓 Select Semester", [s[0] for s in semesters])

# ------------------------ Generate Report ------------------------
if st.button("🔍 Show Attendance Report"):
    # Fetch all lectures for subject+semester
    lectures_q = """
        SELECT id, date FROM Lecture 
        WHERE subject=? AND semester=? 
        ORDER BY date
    """
    lectures, err = fetch_query(lectures_q, (subject, semester))
    if err:
        st.error(f"❌ Database error: {err}")
        st.stop()

    if not lectures:
        st.warning("⚠️ No lectures found for this subject/semester.")
        st.stop()

    lecture_ids = [lec[0] for lec in lectures]
    lecture_dates = [lec[1] for lec in lectures]

    # Fetch all students in this semester
    students_q = "SELECT enrollment_number, name FROM Student WHERE semester=? ORDER BY enrollment_number"
    students, _ = fetch_query(students_q, (semester,))
    if not students:
        st.warning("⚠️ No students registered for this semester.")
        st.stop()

    # Fetch attendance records
    attendance_q = """
        SELECT a.enrollment_number, l.date, a.status
        FROM Lecture l
        LEFT JOIN Attendance a ON a.lecture_id = l.id
        WHERE l.subject=? AND l.semester=?
    """
    attendance, _ = fetch_query(attendance_q, (subject, semester))
    att_df = pd.DataFrame(attendance, columns=["enroll", "date", "status"]) if attendance else pd.DataFrame(columns=["enroll","date","status"])

    # ------------------------ Build Matrix ------------------------
    data = []
    for sid, sname in students:
        row = {"Enrollment": sid, "Name": sname}
        total_present = 0
        for lec_id, lec_date in lectures:
            status = "Absent"
            rec = att_df[(att_df["enroll"] == sid) & (att_df["date"] == lec_date)]
            if not rec.empty and rec.iloc[0]["status"] == "Present":
                status = "Present"
                total_present += 1
            row[lec_date] = status
        row["% Attendance"] = f"{(total_present/len(lectures))*100:.1f}%"
        data.append(row)

    report_df = pd.DataFrame(data)

    # ------------------------ Color Formatting ------------------------
    def highlight_cells(val):
        if val == "Present":
            return "background-color: lightgreen; color: black; font-weight: bold;"
        elif val == "Absent":
            return "background-color: lightcoral; color: black; font-weight: bold;"
        return ""

    styled_df = report_df.style.applymap(highlight_cells)

    # ------------------------ Show Table ------------------------
    st.success(f"✅ Attendance Report for {subject} (Semester {semester})")
    st.dataframe(styled_df, use_container_width=True)

    # ------------------------ Download CSV ------------------------
    csv = report_df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV Report",
        csv,
        file_name=f"attendance_{subject}_sem{semester}.csv"
    )
