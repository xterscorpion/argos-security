import os
import cv2
import face_recognition
from flask import Flask, render_template, send_from_directory
from datetime import datetime
import numpy as np

# -------------------------------
# CONFIG
# -------------------------------
KNOWN_DIR = "images"
UNKNOWN_DIR = "unknown_faces"
UNKNOWN_FULL_DIR = "unknown_full"
VIDEO_SOURCE = 0  # 0 = default camera

os.makedirs(UNKNOWN_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FULL_DIR, exist_ok=True)

# -------------------------------
# LOAD KNOWN FACES
# -------------------------------
known_encodings = []
known_names = []

for person_name in os.listdir(KNOWN_DIR):
    person_path = os.path.join(KNOWN_DIR, person_name)
    if not os.path.isdir(person_path):
        continue
    for img_file in os.listdir(person_path):
        img_path = os.path.join(person_path, img_file)
        image = face_recognition.load_image_file(img_path)
        encs = face_recognition.face_encodings(image)
        if encs:
            known_encodings.append(encs[0])
            known_names.append(person_name)

print(f"[INFO] Loaded {len(known_encodings)} known faces.")

# -------------------------------
# FLASK APP
# -------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    people = os.listdir(KNOWN_DIR)
    return render_template("template.html", people=people)

@app.route("/images/<person>/<filename>")
def person_image(person, filename):
    return send_from_directory(os.path.join(KNOWN_DIR, person), filename)

# -------------------------------
# FACE DETECTION THREAD
# -------------------------------
def run_camera():
    cap = cv2.VideoCapture(VIDEO_SOURCE)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_names[best_match_index]

            # DRAW BOX AND LABEL
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 128, 255), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 128, 255), 2)

            # SAVE UNKNOWN FACES
            if name == "Unknown":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unknown_face_path = os.path.join(UNKNOWN_DIR, f"Unknown_{timestamp}.jpg")
                unknown_full_path = os.path.join(UNKNOWN_FULL_DIR, f"UnknownFull_{timestamp}.jpg")
                face_image = frame[top:bottom, left:right]
                cv2.imwrite(unknown_face_path, face_image)
                cv2.imwrite(unknown_full_path, frame)

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    import threading
    cam_thread = threading.Thread(target=run_camera)
    cam_thread.daemon = True
    cam_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
