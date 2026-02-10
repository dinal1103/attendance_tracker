import streamlit as st
import time

st.set_page_config(page_title="AI-Based Face Recognition Attendance System", layout="centered")

#Session setup
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

#Sidebar logout button
if st.session_state.get("logged_in"):
    with st.sidebar:
        role = st.session_state.get("role")
        name = st.session_state.get("faculty_name", "Faculty") if role == "faculty" else st.session_state.get("student_name", "Student")

        st.markdown(f"**Logged in as:** `{role.capitalize()} - {name}`")

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.pop("enroll", None)
            st.session_state.pop("faculty_name", None)
            st.session_state.pop("student_name", None)
            st.success("✅ Logged out successfully.")
            
            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")

        
#Page content
st.markdown("<h1 style='text-align: left;'>🎓 AI-Based Face Recognition Attendance System</h1>", unsafe_allow_html=True)
st.markdown("<h5 style='text-align: left;'>Welcome to the AI-Based Face Recognition Attendance System</h5>", unsafe_allow_html=True)
st.markdown("---")
st.write("This system allows **teachers** to take classroom attendance using photos and **students** to register and track their attendance.")
st.write("Please choose your role below to proceed:")

col1, col_spacer1, col2, col_spacer2, col3 = st.columns([2, 0.5, 2, 0.5, 2])

with col1:
    if st.button("🔐 Login", use_container_width=True):
        st.switch_page("pages/2_Login.py")

with col2:
    if st.button("📝 Register Student", use_container_width=True):
        st.switch_page("pages/3_Register_Student.py")

with col3:
    if st.button("👨‍🏫 Register Faculty", use_container_width=True):
        st.switch_page("pages/4_Register_Faculty.py")
