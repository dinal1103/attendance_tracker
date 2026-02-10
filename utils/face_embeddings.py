import os  
import glob
import numpy as np
import cv2         
from insightface.app import FaceAnalysis

MODEL_SET = "buffalo_l"
DET_SIZE = (640, 640)
EMB_SIZE = 512            
_app = None

def get_app():
    
    global _app
    if _app is None:
        _app = FaceAnalysis(name=MODEL_SET, providers=['CPUExecutionProvider'])
        _app.prepare(ctx_id=0, det_size=DET_SIZE)
    return _app

def _l2norm(v):
   
    return v / (np.linalg.norm(v) + 1e-12)

def face_embed_from_bgr(img_bgr):
    
    app = get_app()                 
    faces = app.get(img_bgr)        
    
    if not faces:
        return None                 
    
    f = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]))
    
    emb = getattr(f, "normed_embedding", None)
    if emb is None:
        emb = _l2norm(f.embedding)
    
    return emb.astype(np.float32)  

def compute_student_embedding(student_folder):
   
    img_paths = [p for p in glob.glob(os.path.join(student_folder, "*"))
                 if p.lower().endswith((".jpg",".jpeg",".png"))]

    emb_list = []  
    for p in img_paths:
        img = cv2.imread(p)          
        if img is None:
            continue                 
        
        emb = face_embed_from_bgr(img)
        if emb is not None:
            emb_list.append(emb)     

    if len(emb_list) < 3:
        return None, len(emb_list)

    E = np.vstack(emb_list)
    m = E.mean(axis=0)
    
    return _l2norm(m).astype(np.float32), len(emb_list)

def load_npz(npz_path):
    
    if not os.path.exists(npz_path):
        return [], [], np.zeros((0, EMB_SIZE), dtype=np.float32)
    
    data = np.load(npz_path, allow_pickle=True)
    ids = list(map(str, data.get("ids", np.array([], dtype=str))))
    names = list(map(str, data.get("names", np.array([], dtype=str))))
    embs = data.get("embs", np.zeros((0, EMB_SIZE), dtype=np.float32))
    
    return ids, names, embs

def save_npz(npz_path, ids, names, embs):
    
    np.savez(npz_path, ids=np.array(ids), names=np.array(names), embs=embs.astype(np.float32))

def upsert_embedding(npz_path, enrollment_number, name, embedding):
    
    ids, names, embs = load_npz(npz_path)
    if embs.ndim != 2 or embs.shape[1] != EMB_SIZE:
        ids, names, embs = [], [], np.zeros((0, EMB_SIZE), dtype=np.float32)

    if enrollment_number in ids:
        idx = ids.index(enrollment_number)
        embs[idx] = embedding
        names[idx] = name
        action = "updated"
    else:
        ids.append(enrollment_number)
        names.append(name)
        if embs.size:
            embs = np.vstack([embs, embedding[None, :]])
        else:
            embs = embedding[None, :]
        action = "inserted"

    save_npz(npz_path, ids, names, embs)

    return action, len(ids)
