import sqlite3 
import sys       
import os       

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

cursor.execute('''
CREATE TABLE IF NOT EXISTS Student (
    enrollment_number TEXT PRIMARY KEY,  -- Unique student ID
    name TEXT NOT NULL,                  -- Student name
    semester INTEGER,                    -- Current semester
    year INTEGER,                        -- Academic year
    sex TEXT                             -- Gender
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    semester INTEGER NOT NULL,
    password TEXT NOT NULL,
    UNIQUE (email, subject, semester)   -- Ensure one account per subject+semester
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Lecture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- Unique lecture ID
    faculty_id INTEGER NOT NULL,             -- Reference to faculty
    subject TEXT NOT NULL,                   -- Subject of the lecture
    semester INTEGER NOT NULL,               -- Semester of students
    date TEXT NOT NULL,                      -- Lecture date (YYYY-MM-DD)

    faculty_name TEXT,                       -- Snapshot of faculty name
    faculty_email TEXT,                      -- Snapshot of faculty email

    total_detected INTEGER DEFAULT 0,        -- Auto-calculated total students detected
    matched INTEGER DEFAULT 0,               -- Count of matched students
    unknown INTEGER DEFAULT 0,               -- Count of unknown faces
    failed INTEGER DEFAULT 0,                -- Count of failed detections

    FOREIGN KEY (faculty_id) REFERENCES Faculty(id),
    UNIQUE (faculty_id, subject, semester, date)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS LectureImage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    FOREIGN KEY (lecture_id) REFERENCES Lecture(id) ON DELETE CASCADE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    enrollment_number TEXT NOT NULL,
    status TEXT DEFAULT "Present",

    student_name TEXT,
    semester INTEGER,
    sex TEXT,

    FOREIGN KEY (enrollment_number) REFERENCES Student(enrollment_number) ON DELETE CASCADE,
    FOREIGN KEY (lecture_id) REFERENCES Lecture(id) ON DELETE CASCADE,
    UNIQUE (enrollment_number, lecture_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Error_Report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    enrollment_number TEXT,
    issue TEXT,

    student_name TEXT,
    semester INTEGER,
    year INTEGER,
    sex TEXT,

    status TEXT DEFAULT "Pending",  -- NEW: Track error status (Pending, Resolved, Rejected)

    FOREIGN KEY (enrollment_number) REFERENCES Student(enrollment_number),
    FOREIGN KEY (lecture_id) REFERENCES Lecture(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS DetectionLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    enrollment_number TEXT,
    status TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (enrollment_number) REFERENCES Student(enrollment_number),
    FOREIGN KEY (lecture_id) REFERENCES Lecture(id)
)
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_insert_attendance
AFTER INSERT ON Attendance
FOR EACH ROW
BEGIN
    UPDATE Attendance
    SET student_name = (SELECT name FROM Student WHERE enrollment_number = NEW.enrollment_number),
        semester = (SELECT semester FROM Student WHERE enrollment_number = NEW.enrollment_number),
        sex = (SELECT sex FROM Student WHERE enrollment_number = NEW.enrollment_number)
    WHERE id = NEW.id;
END;
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_insert_error
AFTER INSERT ON Error_Report
FOR EACH ROW
BEGIN
    UPDATE Error_Report
    SET student_name = (SELECT name FROM Student WHERE enrollment_number = NEW.enrollment_number),
        semester = (SELECT semester FROM Student WHERE enrollment_number = NEW.enrollment_number),
        year = (SELECT year FROM Student WHERE enrollment_number = NEW.enrollment_number),
        sex = (SELECT sex FROM Student WHERE enrollment_number = NEW.enrollment_number)
    WHERE id = NEW.id;
END;
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_insert_lecture
AFTER INSERT ON Lecture
FOR EACH ROW
BEGIN
    UPDATE Lecture
    SET faculty_name = (SELECT name FROM Faculty WHERE id = NEW.faculty_id),
        faculty_email = (SELECT email FROM Faculty WHERE id = NEW.faculty_id)
    WHERE id = NEW.id;
END;
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_update_lecture_summary
AFTER INSERT ON DetectionLog
FOR EACH ROW
BEGIN
    UPDATE Lecture
    SET total_detected = total_detected + 1,
        matched = matched + CASE WHEN NEW.status = 'Matched' THEN 1 ELSE 0 END,
        unknown = unknown + CASE WHEN NEW.status = 'Unknown' THEN 1 ELSE 0 END,
        failed = failed + CASE WHEN NEW.status = 'Failed' THEN 1 ELSE 0 END
    WHERE id = NEW.lecture_id;
END;
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_delete_student
AFTER DELETE ON Student
FOR EACH ROW
BEGIN
    DELETE FROM Attendance WHERE enrollment_number = OLD.enrollment_number;
    DELETE FROM Error_Report WHERE enrollment_number = OLD.enrollment_number;
    DELETE FROM DetectionLog WHERE enrollment_number = OLD.enrollment_number;
END;
''')

cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_enroll ON Attendance(enrollment_number);')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_lecture ON Attendance(lecture_id);')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_lecture_faculty_date ON Lecture(faculty_id, date);')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_detectionlog_lecture ON DetectionLog(lecture_id);')


conn.commit()
conn.close()

print(f"Database and all tables created with triggers at: {DB_PATH}")
