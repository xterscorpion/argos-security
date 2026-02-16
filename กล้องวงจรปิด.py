import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import cv2
import numpy as np
import face_recognition
import pygame
import requests
import time
import threading
from datetime import datetime, timezone, timedelta
from PIL import Image
import pillow_heif
import hashlib
import sys

# ============================================================
# 🎨 HIGH-CONTRAST UI CONFIG (ปรับให้อ่านง่ายสุดๆ)
# ============================================================
# Colors (BGR Format)
COLOR_NEON_BLUE  = (255, 200, 0)    # ฟ้าสว่าง
COLOR_NEON_GREEN = (50, 255, 50)    # เขียวสว่าง
COLOR_ALERT_RED  = (0, 0, 255)      # แดงสด
COLOR_WHITE      = (255, 255, 255)
COLOR_BLACK      = (0, 0, 0)
COLOR_DARK_BG    = (20, 20, 20)     # เทาเข้มเกือบดำ

# Fonts (ใช้แบบหนาเพื่อความชัด)
FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX
FONT_STD  = cv2.FONT_HERSHEY_SIMPLEX

# ============================================================
# SYSTEM CONFIG
# ============================================================
KNOWN_FACES_DIR = "images"
UNKNOWN_FACES_DIR = "unknown_faces"
UNKNOWN_FULL_DIR = "unknown_full"
ALERT_SOUND_FILE = "alert.mp3"
TOLERANCE = 0.50
DISPLAY_WINDOW_NAME = "SECURITY MONITOR - HIGH VISIBILITY"
UNKNOWN_RECHECK_MINUTES = 5
ALERT_COOLDOWN_SECONDS = 5
PROCESS_RES = (640, 360)
SCREEN_RES = (1920, 1080) # แนะนำ Full HD เพื่อความสวย
SAVE_RES = (1920, 1080)
CACHE_FILE = "face_cache.npz"
RENDER_URL = "https://final-latest-6n2a.onrender.com/upload"
UPLOAD_TOKEN = "MySecretToken123"

# ============================================================
# TELEGRAM CONFIG
# ============================================================
TELEGRAM_BOT_TOKEN = "8249586169:AAEdQCnsL6kUrXujLIeERNsaVori9TsQcCk"
TELEGRAM_CHAT_ID = 1961408502

# ============================================================
# UPLOAD FUNCTIONS
# ============================================================
def send_to_web(filename, folder_path, type_name):
    file_path = os.path.join(folder_path, filename)
    if not os.path.exists(file_path): return
    try:
        tz_th = timezone(timedelta(hours=7))
        now_utc = datetime.now(timezone.utc)
        now_th = now_utc.astimezone(tz_th)
        payload = {
            "timestamp_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timestamp_local": now_th.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "type": type_name
        }
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "image/jpeg")}
            headers = {"Authorization": UPLOAD_TOKEN}
            requests.post(RENDER_URL, files=files, headers=headers, data=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Upload Error: {e}")

def send_to_telegram(image_path, caption):
    if not os.path.exists(image_path): return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(image_path, "rb") as img:
            files = {"photo": img}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            requests.post(url, files=files, data=data, timeout=15)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")

# ============================================================
# SYSTEM UTILS
# ============================================================
cv2.setUseOptimized(True)
cv2.setNumThreads(4)
pygame.mixer.init()
try:
    alert_sound = pygame.mixer.Sound(ALERT_SOUND_FILE)
except:
    alert_sound = None
last_alert_time = 0

def play_alert():
    global last_alert_time
    now = time.time()
    if alert_sound and (now - last_alert_time >= ALERT_COOLDOWN_SECONDS) and not pygame.mixer.get_busy():
        alert_sound.play()
        last_alert_time = now

os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FULL_DIR, exist_ok=True)

def hash_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f: h.update(f.read())
    return h.hexdigest()

def load_known_faces_with_cache():
    print("⏳ LOADING DATABASE...")
    known_encodings = []
    known_names = []
    file_hashes = {}
    if os.path.exists(CACHE_FILE):
        try:
            data = np.load(CACHE_FILE, allow_pickle=True)
            known_encodings = list(data["encodings"])
            known_names = list(data["names"])
            file_hashes = dict(data["hashes"].item())
        except: pass

    updated = False
    for name_folder in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name_folder)
        if not os.path.isdir(person_dir): continue
        for filename in os.listdir(person_dir):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".heic")): continue
            path = os.path.join(person_dir, filename)
            file_hash = hash_file(path)
            if path in file_hashes and file_hashes[path] == file_hash: continue
            try:
                if filename.lower().endswith(".heic"):
                    heif_file = pillow_heif.read_heif(path)
                    image = np.array(Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw"))
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                else:
                    image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(name_folder)
                    file_hashes[path] = file_hash
                    updated = True
            except: pass

    if updated:
        np.savez_compressed(CACHE_FILE, encodings=known_encodings, names=known_names, hashes=file_hashes)
    print(f"✅ READY: {len(known_names)} USERS")
    return known_encodings, known_names

known_encodings, known_names = load_known_faces_with_cache()

# ============================================================
# 🖌 UI HELPER FUNCTIONS (ตัวช่วยวาดกราฟิกให้ชัด)
# ============================================================

def draw_text_shadow(img, text, pos, font, scale, color, thick):
    x, y = pos
    # วาดเงาสีดำหนาๆ ด้านหลัง
    cv2.putText(img, text, (x+2, y+2), font, scale, (0,0,0), thick+2, cv2.LINE_AA)
    # วาดตัวหนังสือจริงทับลงไป
    cv2.putText(img, text, (x, y), font, scale, color, thick, cv2.LINE_AA)

def put_timestamp_file(img, line1_text):
    """ แปะ Timestamp ลงในไฟล์รูป (มุมขวาล่าง แบบชัดๆ) """
    h, w = img.shape[:2]
    # กล่องดำรองหลัง
    cv2.rectangle(img, (0, h-60), (w, h), (0,0,0), -1)
    # ข้อความ
    text = f"REC: {line1_text} | SECURITY CAM 01"
    cv2.putText(img, text, (20, h-20), FONT_STD, 1.0, COLOR_WHITE, 2, cv2.LINE_AA)

def draw_cyber_box(img, pt1, pt2, color, name, confidence=""):
    """ วาดกรอบหน้าคน แบบหนาและชัด """
    x1, y1 = pt1
    x2, y2 = pt2
    line_len = int((x2 - x1) * 0.3) # ความยาวเส้นมุม
    thick = 4 # เส้นหนาขึ้น

    # วาดมุม 4 ด้าน
    cv2.line(img, (x1, y1), (x1 + line_len, y1), color, thick)
    cv2.line(img, (x1, y1), (x1, y1 + line_len), color, thick)

    cv2.line(img, (x2, y1), (x2 - line_len, y1), color, thick)
    cv2.line(img, (x2, y1), (x2, y1 + line_len), color, thick)

    cv2.line(img, (x1, y2), (x1 + line_len, y2), color, thick)
    cv2.line(img, (x1, y2), (x1, y2 - line_len), color, thick)

    cv2.line(img, (x2, y2), (x2 - line_len, y2), color, thick)
    cv2.line(img, (x2, y2), (x2, y2 - line_len), color, thick)

    # ป้ายชื่อ (Header Label)
    label_text = f" {name} {confidence} "
    font_scale = 0.8
    (tw, th), _ = cv2.getTextSize(label_text, FONT_BOLD, font_scale, 2)
    
    # พื้นหลังป้ายชื่อ (สีเดียวกับกรอบ)
    cv2.rectangle(img, (x1, y1 - th - 20), (x1 + tw, y1), color, -1)
    # ข้อความชื่อ (สีดำ ตัดกับสีพื้นหลังกรอบ)
    cv2.putText(img, label_text, (x1, y1 - 10), FONT_BOLD, font_scale, COLOR_BLACK, 2, cv2.LINE_AA)

def draw_big_dashboard(img, fps, total, unknown, is_alert):
    """ Dashboard ด้านล่างแบบใหญ่ อ่านง่าย แบ่ง 3 ช่อง """
    h, w = img.shape[:2]
    dash_h = 120 # เพิ่มความสูงเป็น 120px
    
    # 1. Background Bar (สีดำโปร่งแสง)
    overlay = img.copy()
    cv2.rectangle(overlay, (0, h - dash_h), (w, h), COLOR_DARK_BG, -1)
    cv2.addWeighted(overlay, 0.9, img, 0.1, 0, img)

    # เส้นแบ่งสีตามสถานะ
    status_color = COLOR_ALERT_RED if is_alert else COLOR_NEON_GREEN
    cv2.line(img, (0, h - dash_h), (w, h - dash_h), status_color, 4)

    # Zone 1: DATE & TIME (ซ้าย) - 30% ของจอ
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%a %d %b %Y")
    
    # เวลาตัวใหญ่
    draw_text_shadow(img, time_str, (30, h - 45), FONT_BOLD, 2.0, COLOR_WHITE, 3)
    # วันที่ตัวเล็ก
    draw_text_shadow(img, date_str, (35, h - 15), FONT_STD, 0.7, (200,200,200), 1)

    # Zone 2: STATUS (กลาง)
    center_x = w // 2
    if is_alert:
        stat_txt = "INTRUDER DETECTED"
        stat_col = COLOR_ALERT_RED
    else:
        stat_txt = "SYSTEM SECURE"
        stat_col = COLOR_NEON_GREEN
    
    (sw, sh), _ = cv2.getTextSize(stat_txt, FONT_BOLD, 1.5, 3)
    draw_text_shadow(img, stat_txt, (center_x - sw//2, h - 45), FONT_BOLD, 1.5, stat_col, 3)

    # Zone 3: STATS (ขวา)
    # จัดเรียงแนวตั้งให้อ่านง่าย
    x_stats = w - 300
    draw_text_shadow(img, f"FPS: {int(fps)}", (x_stats, h - 75), FONT_STD, 0.7, COLOR_WHITE, 1)
    draw_text_shadow(img, f"TOTAL: {total}", (x_stats, h - 45), FONT_STD, 0.7, COLOR_NEON_BLUE, 1)
    draw_text_shadow(img, f"UNK: {unknown}", (x_stats + 120, h - 45), FONT_STD, 0.7, COLOR_ALERT_RED, 1)

# ============================================================
# MAIN APP
# ============================================================
USE_PICAMERA2 = False
try:
    from picamera2 import Picamera2
    USE_PICAMERA2 = True
except: pass

class VideoStream:
    def __init__(self):
        if USE_PICAMERA2:
            self.picam2 = Picamera2()
            self.picam2.configure(self.picam2.create_preview_configuration(main={"size": SCREEN_RES}))
            self.picam2.start()
            self.running = True
        else:
            self.capture = cv2.VideoCapture(0)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_RES[0])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_RES[1])
            self.ret, self.frame = self.capture.read()
            self.running = True
            threading.Thread(target=self.update, daemon=True).start()
    def update(self):
        while self.running and not USE_PICAMERA2:
            self.ret, self.frame = self.capture.read()
    def read(self):
        if USE_PICAMERA2:
            return True, cv2.cvtColor(self.picam2.capture_array(), cv2.COLOR_RGB2BGR)
        return self.ret, self.frame
    def stop(self):
        self.running = False
        if USE_PICAMERA2: self.picam2.stop()
        else: self.capture.release()

class UnknownTracker:
    def __init__(self):
        self.unknown_records = []
    def register_unknown(self, encoding):
        now = datetime.now()
        for i, (enc, last_seen, level) in enumerate(self.unknown_records):
            match = face_recognition.compare_faces([enc], encoding, tolerance=0.45)[0]
            if match:
                if (now - last_seen).total_seconds() < UNKNOWN_RECHECK_MINUTES * 60:
                    self.unknown_records[i] = (enc, now, level)
                    return False
                else:
                    self.unknown_records[i] = (enc, now, level + 1)
                    return True
        self.unknown_records.append((encoding, now, 1))
        return True

unknown_tracker = UnknownTracker()
stream = VideoStream()

face_data = {"encodings": [], "locations": []}
face_lock = threading.Lock()
detect_thread = None

def detect_faces(frame):
    rgb_small = cv2.cvtColor(cv2.resize(frame, PROCESS_RES), cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb_small, model="hog")
    encodings = face_recognition.face_encodings(rgb_small, locations)
    
    scale_x = frame.shape[1] / PROCESS_RES[0]
    scale_y = frame.shape[0] / PROCESS_RES[1]
    
    locations_orig = []
    for (top, right, bottom, left) in locations:
        locations_orig.append((int(top * scale_y), int(right * scale_x), int(bottom * scale_y), int(left * scale_x)))
    
    with face_lock:
        face_data["encodings"] = encodings
        face_data["locations"] = locations_orig

# --- MAIN LOOP ---
cv2.namedWindow(DISPLAY_WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(DISPLAY_WINDOW_NAME, SCREEN_RES[0], SCREEN_RES[1])
# cv2.setWindowProperty(DISPLAY_WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

fps_time = time.time()
frame_count = 0

print("🚀 SYSTEM LAUNCHED")

while True:
    ret, frame = stream.read()
    if not ret: continue

    frame_disp = cv2.resize(frame, SCREEN_RES)
    orig_h, orig_w = frame.shape[:2]
    disp_w, disp_h = SCREEN_RES
    ratio_x = disp_w / orig_w
    ratio_y = disp_h / orig_h

    if detect_thread is None or not detect_thread.is_alive():
        detect_thread = threading.Thread(target=detect_faces, args=(frame.copy(),))
        detect_thread.start()

    with face_lock:
        face_locations = face_data["locations"]
        face_encodings = face_data["encodings"]

    face_infos = []
    known_count, unknown_count = 0, 0
    alert_active = False

    for i, face_encoding in enumerate(face_encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=TOLERANCE)
        dists = face_recognition.face_distance(known_encodings, face_encoding)
        
        name = "UNKNOWN"
        conf_str = ""
        is_unknown = True
        
        if True in matches:
            best_idx = np.argmin(dists)
            conf = max(0, min(100, int((1 - dists[best_idx]) ** 2 * 100)))
            if conf >= 35:
                name = known_names[best_idx].upper()
                conf_str = f"{conf}%"
                known_count += 1
                is_unknown = False
            else:
                unknown_count += 1
        else:
            unknown_count += 1

        face_infos.append((name, conf_str, is_unknown))

        # --- LOGIC การแจ้งเตือนและบันทึก ---
        if is_unknown:
            alert_active = True
            is_new = unknown_tracker.register_unknown(face_encoding)
            
            if is_new:
                print(f"🚨 ALERT! Unknown detected.")
                play_alert()
                
                # Setup Timestamp
                now = datetime.now()
                ts_file = now.strftime("%d-%m-%Y_%H%M%S")
                ts_show = now.strftime("%d/%m/%Y %H:%M:%S")
                
                (top, right, bottom, left) = face_locations[i]
                expand = 60
                s_top = max(0, top - expand)
                s_bottom = min(frame.shape[0], bottom + expand)
                s_left = max(0, left - expand)
                s_right = min(frame.shape[1], right + expand)

                # 1. FULL IMAGE (วาดกรอบ + Timestamp)
                full_img = frame.copy()
                draw_cyber_box(full_img, (left, top), (right, bottom), COLOR_ALERT_RED, "INTRUDER")
                put_timestamp_file(full_img, ts_show)
                
                full_fn = f"{ts_file}_full.jpg"
                full_path = os.path.join(UNKNOWN_FULL_DIR, full_fn)
                cv2.imwrite(full_path, cv2.resize(full_img, SAVE_RES))

                # 2. FACE CROP
                face_crop = frame[s_top:s_bottom, s_left:s_right].copy()
                if face_crop.size > 0:
                    face_crop = cv2.resize(face_crop, (500, 500))
                    put_timestamp_file(face_crop, ts_show)
                    face_fn = f"{ts_file}_face.jpg"
                    face_path = os.path.join(UNKNOWN_FACES_DIR, face_fn)
                    cv2.imwrite(face_path, face_crop)

                    # Send
                    threading.Thread(target=send_to_web, args=(face_fn, UNKNOWN_FACES_DIR, "face"), daemon=True).start()
                    threading.Thread(target=send_to_web, args=(full_fn, UNKNOWN_FULL_DIR, "full"), daemon=True).start()
                    caption = f"🚨 INTRUDER ALERT!\n🕒 {ts_show}"
                    threading.Thread(target=send_to_telegram, args=(full_path, caption), daemon=True).start()

    # --- DRAWING ON SCREEN ---
    for (top, right, bottom, left), (name, conf, is_unk) in zip(face_locations, face_infos):
        # Scale coordinates
        d_top = int(top * ratio_y)
        d_right = int(right * ratio_x)
        d_bottom = int(bottom * ratio_y)
        d_left = int(left * ratio_x)

        color = COLOR_ALERT_RED if is_unk else COLOR_NEON_GREEN
        draw_cyber_box(frame_disp, (d_left, d_top), (d_right, d_bottom), color, name, conf)

    # คำนวณ FPS
    fps = 1.0 / (time.time() - fps_time)
    fps_time = time.time()

    # แสดงผล Dashboard ใหญ่
    draw_big_dashboard(frame_disp, fps, len(face_locations), unknown_count, alert_active)

    # Effect ขอบจอแดงกระพริบ
    if alert_active and (frame_count % 12 < 6):
        cv2.rectangle(frame_disp, (0,0), (disp_w, disp_h), COLOR_ALERT_RED, 8)

    cv2.imshow(DISPLAY_WINDOW_NAME, frame_disp)
    frame_count += 1
    if cv2.waitKey(1) & 0xFF == 27:
        break

stream.stop()
cv2.destroyAllWindows()
pygame.quit()