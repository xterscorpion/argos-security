import os
import numpy as np
import cv2
import face_recognition
import mediapipe as mp
import pygame
import time
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
KNOWN_FACES_DIR = "images"
UNKNOWN_FACES_DIR = "unknown_faces"
UNKNOWN_FULL_DIR = "unknown_full"
ENCODINGS_FILE = "face_data.npz"
ALERT_SOUND_FILE = "alert.mp3"
TOLERANCE = 0.5
ALERT_COOLDOWN_SECONDS = 5
MAX_PREVIEW = 3

# -----------------------------
# FOLDERS
# -----------------------------
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FULL_DIR, exist_ok=True)

# -----------------------------
# ALERT SOUND
# -----------------------------
pygame.mixer.init()
try:
    alert_sound = pygame.mixer.Sound(ALERT_SOUND_FILE)
except Exception as e:
    print(f"โหลดเสียงไม่สำเร็จ: {e}")
    alert_sound = None

last_alert_time = 0
def play_alert():
    global last_alert_time
    now = time.time()
    if alert_sound and (now - last_alert_time >= ALERT_COOLDOWN_SECONDS) and not pygame.mixer.get_busy():
        alert_sound.play()
        last_alert_time = now

# -----------------------------
# MEDIA PIPE FACE MESH
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=5,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# -----------------------------
# TRAINING DATABASE
# -----------------------------
def train_database():
    known_encodings = []
    known_names = []

    print("สร้างฐานข้อมูลจาก folder KNOWN_FACES_DIR ...")
    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        if not os.path.isdir(person_dir):
            continue
        for f in os.listdir(person_dir):
            if f.lower().endswith((".jpg",".jpeg",".png")):
                path = os.path.join(person_dir,f)
                image = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(image)
                if encs:
                    known_encodings.append(encs[0])
                    known_names.append(name)
    np.savez(ENCODINGS_FILE, encodings=known_encodings, names=known_names)
    print(f"Training เสร็จสิ้น. Saved to {ENCODINGS_FILE}")

# -----------------------------
# LOAD DATABASE
# -----------------------------
if not os.path.exists(ENCODINGS_FILE):
    train_database()

data = np.load(ENCODINGS_FILE, allow_pickle=True)
known_encodings = data["encodings"].tolist()
known_names = data["names"].tolist()

# -----------------------------
# LOAD PREVIEW IMAGES
# -----------------------------
def load_previews():
    previews = {}
    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        if not os.path.isdir(person_dir):
            continue
        files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if files:
            path = os.path.join(person_dir, files[0])
            img = cv2.imread(path)
            if img is not None:
                previews[name] = img
    return previews

known_previews = load_previews()

# -----------------------------
# UNKNOWN TRACKER
# -----------------------------
class UnknownTracker:
    def __init__(self):
        self.unknown_records = []

    def register_unknown(self, encoding):
        now = datetime.now()
        for i, (enc, last_seen) in enumerate(self.unknown_records):
            if face_recognition.compare_faces([enc], encoding, tolerance=0.45)[0]:
                self.unknown_records[i] = (enc, now)
                return False
        self.unknown_records.append((encoding, now))
        return True

unknown_tracker = UnknownTracker()

# -----------------------------
# CAMERA
# -----------------------------
cap = cv2.VideoCapture(0)

# -----------------------------
# FULL SCREEN MODE
# -----------------------------
cv2.namedWindow("Face Recognition Full Screen", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Face Recognition Full Screen", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("ระบบ Face Monitoring แบบ Full Screen พร้อมทำงาน (กด ESC เพื่อออก)")

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    ret, frame = cap.read()
    if not ret:
        continue

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    face_locations = []

    if results.multi_face_landmarks:
        h, w, _ = frame.shape
        for face_landmarks in results.multi_face_landmarks:
            xs = [lm.x * w for lm in face_landmarks.landmark]
            ys = [lm.y * h for lm in face_landmarks.landmark]
            top, bottom = int(min(ys)), int(max(ys))
            left, right = int(min(xs)), int(max(xs))
            face_locations.append((top, right, bottom, left))

    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    names = []

    for i, enc in enumerate(encodings):
        matches = face_recognition.compare_faces(known_encodings, enc, tolerance=TOLERANCE)
        name = "Unknown"
        if True in matches:
            name = known_names[matches.index(True)]
        else:
            is_new = unknown_tracker.register_unknown(enc)
            if is_new:
                print("[ALERT] Unknown detected!")
                play_alert()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_face = f"Unknown_{timestamp}.jpg"
                filename_full = f"UnknownFull_{timestamp}.jpg"

                (top, right, bottom, left) = face_locations[i]
                face_img = frame[top:bottom, left:right]
                if face_img.size > 0:
                    cv2.imwrite(os.path.join(UNKNOWN_FACES_DIR, filename_face), face_img)
                cv2.imwrite(os.path.join(UNKNOWN_FULL_DIR, filename_full), frame)
        names.append(name)

    # -----------------------------
    # DRAW FACES
    # -----------------------------
    for (top, right, bottom, left), name in zip(face_locations, names):
        color = (0,255,0) if name != "Unknown" else (0,0,255)
        cv2.rectangle(frame, (left,top), (right,bottom), color, 2)
        cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    # -----------------------------
    # BUILD PREVIEW PANEL
    # -----------------------------
    screen_w = 1920  # Full HD default
    screen_h = 1080

    panel_w = int(screen_w * 0.27)
    preview_size = int(screen_h * 0.27)

    panel = np.zeros((screen_h, panel_w, 3), dtype=np.uint8)
    panel[:] = (25, 35, 60)

    cv2.putText(panel, "FACE MONITORING SYSTEM", (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 3)
    cv2.putText(panel, "RECOGNIZED FACES", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,230,255), 2)

    detected_knowns = [n for n in names if n != "Unknown"]
    detected_knowns = list(dict.fromkeys(detected_knowns))[:MAX_PREVIEW]

    y_start = 150
    for i, name in enumerate(detected_knowns):
        y = y_start + i * (preview_size + 40)
        x = (panel_w - preview_size) // 2
        if name in known_previews:
            img = cv2.resize(known_previews[name], (preview_size, preview_size))
            panel[y:y+preview_size, x:x+preview_size] = img
            cv2.rectangle(panel, (x, y), (x+preview_size, y+preview_size), (255,255,255), 2)
            cv2.putText(panel, name, (x+10, y+preview_size+35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)

    frame_resized = cv2.resize(frame, (screen_w - panel_w, screen_h))
    combined = np.hstack((frame_resized, panel))

    cv2.imshow("Face Recognition Full Screen", combined)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
pygame.quit()
