import streamlit as st
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_helper import fetch_query   
from utils.db_config import DB_PATH


st.set_page_config(page_title="🔐 Login - AI Attendance System", layout="centered")
st.title("🔐 Login to AI Attendance System")

if st.session_state.get("logged_in"):

    with st.sidebar:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.get('role').capitalize()}`")

        if st.button("🚪 Logout"):

            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.pop("enroll", None)
            st.session_state.pop("faculty_name", None)
            st.session_state.pop("faculty_email", None)
            st.session_state.pop("subject", None)
            st.session_state.pop("semester", None)
            st.success("✅ Logged out successfully.")
            
            with st.spinner("⏳ Redirecting..."):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")


role = st.selectbox("Select Role", ["Faculty", "Student"])

#-------------------------faculty login--------------------------

if role == "Faculty":
    email = st.text_input("Enter your Email ID")
    password = st.text_input("Enter your Password", type="password")
    subject = st.text_input("Enter Subject")
    semester = st.number_input("Enter Semester", min_value=1, max_value=8, step=1)

    if st.button("➡️ Login as Faculty"):
        rows, error = fetch_query(
            "SELECT * FROM Faculty WHERE email=? AND password=? AND subject=? AND semester=?",
            (email.strip(), password.strip(), subject.strip(), semester)
        )

        if error:
            st.error(f"Database error: {error}")

        elif rows:
            result = rows[0]
            st.success("✅ Faculty Logged in successfully")
            st.session_state.logged_in = True
            st.session_state.role = "faculty"
            st.session_state.faculty_name = result[1]
            st.session_state.faculty_email = email.strip()
            st.session_state.subject = result[3]  
            st.session_state.semester = result[4]  
            
            with st.spinner("⏳ Redirecting to 📸 Upload Class Photo ..."):
                time.sleep(2)       
            st.switch_page("pages/5_Upload_Class_Photo.py")

        else:
            st.error("❌ Invalid faculty credentials for this Subject/Semester.")

#---------------------------------------student login-------------------------------

elif role == "Student":
    enroll = st.text_input("🎓 Enrollment Number")

    if st.button("➡️ Login as Student"):
        rows, error = fetch_query(
            "SELECT name FROM Student WHERE enrollment_number=?",
            (enroll.strip(),)
        )

        if error:
            st.error(f"Database error: {error}")

        elif rows:
            st.success("✅ Student Login Successful")
            st.session_state.logged_in = True
            st.session_state.role = "student"
            st.session_state.enroll = enroll.strip()
            
            with st.spinner("⏳ Opening Your Attendance 📊 ..."):
                time.sleep(2)
            st.switch_page("pages/7_View_Attendance.py")

        else:
            st.error("❌ Invalid enrollment number.")
