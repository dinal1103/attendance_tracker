import os, sys, sqlite3, numpy as np, cv2
from datetime import datetime
from insightface.app import FaceAnalysis
import io
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_config import DB_PATH, EMB_NPZ_PATH

MODEL_SET = "buffalo_l"
DET_SIZE = (1600, 1600)          
MIN_FACE = 10                   
THRESH = 0.30                   
SAVE_FOLDER = "detected_faces"  
os.makedirs(SAVE_FOLDER, exist_ok=True)

if not os.path.exists(EMB_NPZ_PATH):
    print(f"❌ Embeddings DB not found at {EMB_NPZ_PATH}")
    sys.exit(1)

db = np.load(EMB_NPZ_PATH, allow_pickle=True)
IDS = db.get("ids", np.array([], dtype=str))
NAMES = db.get("names", np.array([], dtype=str))
EMBS = db.get("embs", np.zeros((len(IDS), 512), dtype=np.float32))

if EMBS.size == 0 or len(IDS) == 0:
    print("❌ No student embeddings found. Register students first.")
    sys.exit(1)

EMBS = EMBS / (np.linalg.norm(EMBS, axis=1, keepdims=True) + 1e-12)

app = FaceAnalysis(name=MODEL_SET, providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=DET_SIZE)

def best_match(face_emb: np.ndarray):
    """Return best match index and similarity score using cosine similarity"""
    sims = EMBS @ face_emb
    idx = int(np.argmax(sims))
    return idx, float(sims[idx])

def mark_from_image(img_path):
    """Detect faces, match embeddings, and return results list"""
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}")

    faces = app.get(img)
    results = []

    for f in faces:
        x1, y1, x2, y2 = map(int, f.bbox)
        width, height = x2 - x1, y2 - y1

        if min(width, height) < MIN_FACE:
            action, sid, conf = "failed", None, None
        else:
            emb = getattr(f, "normed_embedding", None)
            if emb is None:
                emb = f.embedding / (np.linalg.norm(f.embedding) + 1e-12)

            idx, conf = best_match(emb)
            sid = str(IDS[idx])
            action = "matched" if conf >= THRESH else "unknown"

        
        color = (0, 255, 0) if action == "matched" else ((0, 0, 255) if action == "unknown" else (0, 255, 255))
        label = sid if action == "matched" else action.capitalize()
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        results.append({
            "action": action,
            "enrollment_number": sid if action=="matched" else None,
            "confidence": conf
        })

    
    cv2.imwrite(img_path, img)
    return results

def write_to_db(face_results, lecture_id: int):
    """Insert DetectionLog and Attendance records"""
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for r in face_results:
        cur.execute("""
            INSERT INTO DetectionLog (lecture_id, enrollment_number, status, timestamp)
            VALUES (?, ?, ?, ?)
        """, (lecture_id, r["enrollment_number"], r["action"].capitalize(), now_ts))

    matched_sids = [r["enrollment_number"] for r in face_results if r["action"]=="matched" and r["enrollment_number"]]
    for sid in set(matched_sids):
        cur.execute("""
            INSERT OR IGNORE INTO Attendance (lecture_id, enrollment_number, status)
            VALUES (?, ?, 'Present')
        """, (lecture_id, sid))

    conn.commit()
    
    cur.execute("SELECT total_detected, matched, unknown, failed FROM Lecture WHERE id=?", (lecture_id,))
    summary = cur.fetchone()
    conn.close()

    totals = {"total_detected": 0, "matched": 0, "unknown": 0, "failed": 0}
    if summary:
        totals = {"total_detected": summary[0], "matched": summary[1], "unknown": summary[2], "failed": summary[3]}
    return totals

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mark_attendance.py <image_path> <lecture_id>")
        sys.exit(1)

    img_path = sys.argv[1]
    try:
        lecture_id = int(sys.argv[2])
    except ValueError:
        print("lecture_id must be an integer")
        sys.exit(1)

    try:
        face_results = mark_from_image(img_path)
        totals = write_to_db(face_results, lecture_id)
        print(f"✅ Attendance processed. Detected: {totals['total_detected']}, "
              f"Matched: {totals['matched']}, Unknown: {totals['unknown']}, Failed: {totals['failed']}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
