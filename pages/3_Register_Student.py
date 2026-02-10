import streamlit as st
import sys
import os
import re
import time
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_DIR)

from utils.db_config import DB_PATH, EMB_NPZ_PATH
from utils.face_embeddings import compute_student_embedding, upsert_embedding
from utils.db_helper import execute_query, fetch_query

if st.session_state.get("logged_in"):

    with st.sidebar:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.get('role').capitalize()}`")

        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("✅ Logged out successfully.")

            with st.spinner("⏳ Redirecting to Login Page"):
                time.sleep(1)
            st.switch_page("pages/2_Login.py")

st.title("📝 Student Registration")

#------------------------------------Registration form--------------------------------

with st.form("student_form"):

    name = st.text_input("🧑‍💼 Full Name")
    enroll = st.text_input("🆔 Enrollment Number")
    sex = st.selectbox("⚧️ Select Gender", options=["Male", "Female"])
    year_label = st.selectbox("🎓 Select Year", options=["1st","2nd","3rd","4th"], index=2)
    year_map = {"1st":1,"2nd":2,"3rd":3,"4th":4}
    year = year_map[year_label]
    semester_options = list(range(1, 9))
    semester = st.selectbox("📘 Select Semester (1-8)", options=semester_options, index=4)

    st.info("📸 Upload at least 3 clear face images.")
    images = st.file_uploader("🖼️ Upload at least 3 Images", type=["jpg","jpeg","png"], accept_multiple_files=True)

    submitted = st.form_submit_button("📩 Register")


if submitted:

    #--------------------------validations-------------------------------

    if not name:
        st.error("❗Full name is required.")

    elif not re.match(r"^[A-Za-z\s]+$", name):
        st.error("❗Name must contain only alphabets and spaces.")

    elif not enroll.strip().isdigit():
        st.error("❗Enrollment number must contain digits only.")

    elif len(images) < 3:
        st.warning("❗Please upload at least 3 face images.")

    else:
        name = ' '.join([part.capitalize() for part in name.strip().split()])
        enroll = enroll.strip()

        rows, error = fetch_query(
            "SELECT 1 FROM Student WHERE enrollment_number=?",
            (enroll,)
        )

        if error:
            st.error(f"Database error: {error}")
            st.stop()

        if rows:
            st.error(f"❌ Enrollment {enroll} already exists")
            st.stop()

        #---------------------------------save images------------------------------------------

        folder = os.path.join(ROOT_DIR, "student_images", enroll)
        os.makedirs(folder, exist_ok=True)

        for i, img in enumerate(images):

            img_path = os.path.join(folder, f"{enroll}-{i+1}.jpg")
            with open(img_path, "wb") as f:
                f.write(img.read())

        #----------------------------------embeddings generation-------------------------------

        with st.spinner("Checking face images and generating embeddings..."):
            embeddings_list, used = compute_student_embedding(folder)

            if embeddings_list is None:
                st.error(f"Registration failed. Only {used} valid face(s) detected. At least 3 are required.")
                shutil.rmtree(folder, ignore_errors=True)
                st.stop()

        success, error = execute_query(
            """INSERT INTO Student (enrollment_number, name, semester, year, sex)
               VALUES (?, ?, ?, ?, ?)""",
            (enroll, name, semester, year, sex)
            )

        if not success:
            st.error(f"Database error while inserting student: {error}")
            shutil.rmtree(folder, ignore_errors=True)
            st.stop()


        try:
            action, total = upsert_embedding(EMB_NPZ_PATH, enroll, name, embeddings_list)
            st.success(f"✅ Embeddings {action}. Total students in NPZ: {total}")
            st.toast("🎉 Registration completed successfully!", icon="✅")

        except Exception as e:
            st.error(f"❌ Error updating embeddings: {e}")
            shutil.rmtree(folder, ignore_errors=True)
            st.stop()

        st.markdown(f"""
            **Student Details:**  
            - Name: {name}  
            - Enrollment: {enroll}  
            - Year: {year_label}  
            - Semester: {semester}  
            - Gender: {sex}  
            - Images Uploaded: {len(images)}  
        """)
        
        with st.spinner("⏳ Redirecting to Login Page in 2 seconds..."):
            time.sleep(15)
        st.switch_page("pages/2_Login.py")
