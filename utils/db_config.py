import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'attendance_system.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

EMB_DIR = os.path.join(BASE_DIR, '..', 'students_embeddings')
os.makedirs(EMB_DIR, exist_ok=True)
EMB_NPZ_PATH = os.path.join(EMB_DIR, 'student_db.npz')
