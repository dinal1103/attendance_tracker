import streamlit as st
import sys
import os
import time
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_config import DB_PATH
from utils.db_helper import execute_query

ADMIN_CODE = "FACULTY2025"

if st.session_state.get("logged_in"):

    with st.sidebar:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.get('role').capitalize()}`")

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("✅ Logged out successfully.")

            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")

st.title("Faculty Registration")

admin_code = st.text_input("Enter Admin Code", type="password")

if admin_code == ADMIN_CODE:

    with st.form("faculty_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        subject = st.text_input("Subject")
        semester = st.number_input("Semester", min_value=1, max_value=8, step=1)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Register")

        if submitted:

            if not name.strip() or not email.strip() or not subject.strip() or not password.strip():
                st.error("⚠️ All fields are required.")

            elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                st.error("⚠️ Invalid email format.")

            else:
                
                query = "INSERT INTO Faculty (name, email, subject, semester, password) VALUES (?, ?, ?, ?, ?)"
                params = (name.strip(), email.strip(), subject.strip(), semester, password.strip())
                success, error = execute_query(query, params)

                if success:

                    st.success("✅ Faculty Registered Successfully")

                    with st.spinner("⏳ Redirecting to Login Page in 2 seconds"):
                        time.sleep(2)
                    st.switch_page("pages/2_Login.py")

                else:
                    
                    if "UNIQUE constraint failed" in str(error):
                        st.error("❌ Faculty account for this Subject and Semester already exists.")

                    else:
                        st.error(f"Database error: {error}")

else:
    st.warning("🔑 Please enter a valid Admin Code.")
