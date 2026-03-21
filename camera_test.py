"""
Quick camera test — run this directly to confirm:
1. Your camera opens correctly
2. Face recognition loads your faces/ folder
3. Detection and bounding boxes work

Run with:  python camera_test.py
Press Q to quit.
"""

import face_recognition
import cv2
import numpy as np
import os
import threading
import time

FACES_DIR     = "faces"
SCALE         = 0.25
CAMERA_SOURCE = 0         # change to "rtsp://..." for IP camera


def load_faces(faces_dir):
    known_encodings = []
    known_names = []
    for filename in os.listdir(faces_dir):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(faces_dir, filename)
        name = os.path.splitext(filename)[0]
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            print(f"[SKIP] No face in {filename}")
            continue
        known_encodings.append(encodings[0])
        known_names.append(name)
        print(f"[OK] Loaded: {name}")
    print(f"\nTotal loaded: {len(known_names)} student(s)\n")
    return known_encodings, known_names


def main():
    known_encodings, known_names = load_faces(FACES_DIR)

    cap = cv2.VideoCapture(CAMERA_SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("[ERROR] Camera not found. Check CAMERA_SOURCE value.")
        return

    # Shared state
    lock = threading.Lock()
    latest_frame = [None]
    face_locations = [[]]
    face_names = [[]]

    # Recognition thread
    def recognition_loop():
        while True:
            with lock:
                frame = latest_frame[0]
            if frame is None:
                time.sleep(0.05)
                continue

            small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locs = face_recognition.face_locations(rgb, model="hog")
            encs = face_recognition.face_encodings(rgb, locs)

            names = []
            for enc in encs:
                name = "Unknown"
                if known_encodings:
                    distances = face_recognition.face_distance(known_encodings, enc)
                    best = np.argmin(distances)
                    if distances[best] < 0.50:
                        name = known_names[best]
                names.append(name)

            inv = int(1 / SCALE)
            scaled = [(t*inv, r*inv, b*inv, l*inv) for (t, r, b, l) in locs]

            with lock:
                face_locations[0] = scaled
                face_names[0]     = names

            time.sleep(1.0 / 8)   # 8 recognitions per second

    t = threading.Thread(target=recognition_loop, daemon=True)
    t.start()

    print("Camera test running. Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        with lock:
            latest_frame[0] = frame.copy()
            locs  = list(face_locations[0])
            names = list(face_names[0])

        # Draw boxes
        for (top, right, bottom, left), name in zip(locs, names):
            color = (0, 200, 80) if name != "Unknown" else (100, 100, 100)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 32), (right, bottom), color, -1)
            cv2.putText(frame, name, (left + 6, bottom - 8),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1)

        # FPS counter
        cv2.putText(frame, "Camera test — press Q to quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Camera Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\nDone.")


if __name__ == "__main__":
    main()