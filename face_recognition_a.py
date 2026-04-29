"""
OPTION A — Front face only
--------------------------
- 1 photo per student stored in /faces/StudentName.jpg
- Threaded: camera reads on Thread 1, recognition runs on Thread 2
- No lag, smooth MJPEG stream to browser
- Works with IP camera (RTSP) or webcam (index 0)
- Scales to classroom distance (~4–6 meters with good lighting)
"""

import face_recognition
import cv2
import numpy as np
import os
import threading
import time
import requests


# ── CONFIG ────────────────────────────────────────────────────────────────────

FACES_DIR       = "faces"           # folder: faces/JohnDoe.jpg
SCALE           = 0.5               # 0.5 = larger input → detects smaller/farther faces
RECOGNITION_FPS = 4                 # reduced: 0.5 scale is heavier, 4fps keeps it smooth
CAMERA_SOURCE   = 0                 # 0 = webcam, or "rtsp://user:pass@ip:554/..." for IP cam
FRAME_WIDTH     = 1280
FRAME_HEIGHT    = 720

# ── CLOUD SYNC CONFIG ─────────────────────────────────────────────────────────
# When a face is recognized locally, the result is immediately sent to the
# Render server which saves it to Neon PostgreSQL — instructors see it live.
CLOUD_URL       = "https://attendance-system-xapv.onrender.com"
CLOUD_SYNC      = True              # Set False to disable cloud push (offline mode)
INSTRUCTOR_EMAIL = ""               # Set this at runtime via set_session()
CLASS_CODE       = ""               # Set this at runtime via set_session()
SECTION          = ""               # Set this at runtime via set_session()
SUBJECT          = ""               # Set this at runtime via set_session()


# ── FACE ENCODER ──────────────────────────────────────────────────────────────

def load_known_faces(faces_dir: str):
    """
    Load face images from a class-scoped folder.

    faces_dir should be faces/<CLASS_CODE>/ — only students in that class
    are encoded, so the recognizer never matches students from other classes.

    File name (without extension) becomes the display name.
    Underscores are converted to spaces to match the DB name format.
    e.g. "John_Doe.jpg" → "John Doe"
    """
    known_encodings = []
    known_names     = []

    if not os.path.isdir(faces_dir):
        print(f"[FACES] Directory not found: {faces_dir} — 0 faces loaded")
        return known_encodings, known_names

    image_files = [
        f for f in os.listdir(faces_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not image_files:
        print(f"[FACES] No images in {faces_dir} — 0 faces loaded")
        return known_encodings, known_names

    for filename in image_files:
        path = os.path.join(faces_dir, filename)
        # Convert filename to display name: underscores → spaces
        raw_name     = os.path.splitext(filename)[0]
        display_name = raw_name.replace("_", " ")

        try:
            image     = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if not encodings:
                print(f"[FACES] ✗ No face found in {filename}, skipping.")
                continue
            known_encodings.append(encodings[0])
            known_names.append(display_name)
            print(f"[FACES] ✓ Loaded: {display_name}")
        except Exception as e:
            print(f"[FACES] ✗ Error loading {filename}: {e}")

    print(f"[FACES] Ready — {len(known_names)} student(s) from {faces_dir}")
    return known_encodings, known_names


# ── RECOGNIZER ────────────────────────────────────────────────────────────────

class FaceRecognizer:
    """
    Runs face recognition on a background thread.
    The main thread only reads/annotates — never blocks on recognition.
    """

    def __init__(self, known_encodings, known_names):
        self.known_encodings = known_encodings
        self.known_names     = known_names

        # Shared state (thread-safe via lock)
        self._lock           = threading.Lock()
        self._latest_frame   = None          # raw BGR frame from camera
        self._face_locations = []            # scaled-up box coords
        self._face_names     = []            # matched names
        self._present_set    = set()         # names detected this session
        self._scan_log       = {}           # {name: first_seen_unix_time}

        self._running        = False
        self._rec_thread     = None

        # Cloud session info — set before starting camera
        self._instructor_email = INSTRUCTOR_EMAIL
        self._class_code       = CLASS_CODE
        self._section          = SECTION
        self._subject          = SUBJECT

    # ── public API ──────────────────────────────────────────────────────────

    def set_session(self, instructor_email, class_code, section, subject):
        """Call this before start() to link recognition to a class session."""
        self._instructor_email = instructor_email
        self._class_code       = class_code
        self._section          = section
        self._subject          = subject
        print(f"[CLOUD] Session set → {class_code} | {subject} | {section}")

    def _cloud_sync(self, name, timestamp):
        """
        Sends a single student check-in to the Render server in a background
        thread so it never blocks the recognition loop.
        The Render server saves it directly to Neon PostgreSQL.
        """
        if not CLOUD_SYNC or not self._class_code:
            return

        def _push():
            try:
                payload = {
                    "name":             name,
                    "class_code":       self._class_code,
                    "section":          self._section,
                    "subject":          self._subject,
                    "instructor_email": self._instructor_email,
                    "timestamp":        timestamp,
                    "status":           "Present"
                }
                res = requests.post(
                    f"{CLOUD_URL}/api/live_checkin",
                    json    = payload,
                    timeout = 5
                )
                if res.status_code == 200:
                    print(f"[CLOUD] ✓ Synced: {name}")
                else:
                    print(f"[CLOUD] ✗ Failed ({res.status_code}): {name}")
            except requests.exceptions.ConnectionError:
                print(f"[CLOUD] ✗ No internet — {name} saved locally only")
            except Exception as e:
                print(f"[CLOUD] ✗ Error: {e}")

        # Run in background so recognition loop never waits
        threading.Thread(target=_push, daemon=True).start()

    def start(self, camera_source):
        self.cap = cv2.VideoCapture(camera_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # only keep latest frame
        self._running = True

        self._rec_thread = threading.Thread(
            target=self._recognition_loop, daemon=True
        )
        self._rec_thread.start()

    def stop(self):
        self._running = False
        if hasattr(self, "cap"):
            self.cap.release()

    def get_present_students(self):
        with self._lock:
            return list(self._present_set)

    def get_scan_log(self):
        """Returns {name: first_seen_unix_timestamp} for all scanned students."""
        with self._lock:
            return dict(self._scan_log)

    def reset_attendance(self):
        """Clears present set and scan log for a new session."""
        with self._lock:
            self._present_set = set()
            self._scan_log    = {}

    def stop_and_reset(self):
        """Stops the camera capture and clears all session data."""
        self._running = False
        if hasattr(self, "cap"):
            try:
                self.cap.release()
            except Exception:
                pass
        with self._lock:
            self._present_set    = set()
            self._scan_log       = {}
            self._latest_frame   = None
            self._face_locations = []
            self._face_names     = []

    def generate_frames(self):
        """
        Generator used by Flask to stream MJPEG to the browser.
        Reads the camera, overlays bounding boxes, yields JPEG bytes.
        Runs in the Flask request thread — never blocks on recognition.
        """
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.03)
                continue

            # Store latest frame for the recognition thread
            with self._lock:
                self._latest_frame = frame.copy()
                locations = list(self._face_locations)
                names     = list(self._face_names)

            # Draw bounding boxes (uses LAST recognition result — no wait)
            annotated = self._draw_boxes(frame, locations, names)

            # Encode as JPEG and yield
            _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

    # ── internals ───────────────────────────────────────────────────────────

    def _recognition_loop(self):
        """
        Runs on Thread 2.
        Processes frames at RECOGNITION_FPS — independent of camera FPS.
        """
        interval = 1.0 / RECOGNITION_FPS

        while self._running:
            start = time.time()

            with self._lock:
                frame = self._latest_frame

            if frame is None:
                time.sleep(interval)
                continue

            # Shrink frame → much faster recognition
            small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, locations)

            names = []
            for enc in encodings:
                name = self._match(enc)
                names.append(name)
                if name != "Unknown":
                    with self._lock:
                        self._present_set.add(name)
                        if name not in self._scan_log:
                            first_seen = time.time()
                            self._scan_log[name] = first_seen
                            # ── CLOUD SYNC: push to Render → Neon on first detection
                            from datetime import datetime as _dt
                            ts_str = _dt.fromtimestamp(first_seen).strftime("%H:%M:%S")
                            self._cloud_sync(name, ts_str)

            # Scale coordinates back to original frame size
            inv = int(1 / SCALE)  # 2 — scales coords back to full frame
            scaled = [(t*inv, r*inv, b*inv, l*inv) for (t, r, b, l) in locations]

            with self._lock:
                self._face_locations = scaled
                self._face_names     = names

            # Sleep remainder of interval to hit target FPS
            elapsed = time.time() - start
            sleep   = max(0, interval - elapsed)
            time.sleep(sleep)

    def _match(self, encoding):
        if not self.known_encodings:
            return "Unknown"

        distances = face_recognition.face_distance(self.known_encodings, encoding)
        best_idx  = np.argmin(distances)

        # Tolerance: lower = stricter. 0.5 is a good balance.
        if distances[best_idx] < 0.50:
            return self.known_names[best_idx]
        return "Unknown"

    def _draw_boxes(self, frame, locations, names):
        for (top, right, bottom, left), name in zip(locations, names):
            color = (0, 0, 220) if name != "Unknown" else (120, 120, 120)

            # Display name with spaces instead of underscores
            display_name = name.replace("_", " ") if name != "Unknown" else "Unknown"

            # Box around face
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Label bar
            cv2.rectangle(frame, (left, bottom - 32), (right, bottom), color, -1)
            cv2.putText(
                frame, display_name,
                (left + 6, bottom - 8),
                cv2.FONT_HERSHEY_DUPLEX, 0.65,
                (255, 255, 255), 1
            )
        return frame


# ── FLASK INTEGRATION ─────────────────────────────────────────────────────────
#
# In your app.py add:
#
#   from face_recognition_a import FaceRecognizer, load_known_faces
#
#   known_enc, known_names = load_known_faces("faces")
#   recognizer = FaceRecognizer(known_enc, known_names)
#
#   @app.route("/camera/<int:class_id>")
#   def camera_page(class_id):
#       recognizer.start(CAMERA_SOURCE)
#       return render_template("camera.html", class_id=class_id)
#
#   @app.route("/video_feed")
#   def video_feed():
#       from flask import Response
#       return Response(
#           recognizer.generate_frames(),
#           mimetype="multipart/x-mixed-replace; boundary=frame"
#       )
#
#   @app.route("/api/present_students")
#   def present_students():
#       from flask import jsonify
#       return jsonify(recognizer.get_present_students())
#
# In camera.html:
#   <img src="/video_feed" width="100%">
#
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Standalone test (shows OpenCV window, not web)
    enc, names = load_known_faces(FACES_DIR)
    rec = FaceRecognizer(enc, names)
    rec.start(CAMERA_SOURCE)

    print("Press Q to quit.")
    for frame_bytes in rec.generate_frames():
        # Decode JPEG back to display in OpenCV window (test only)
        buf   = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is not None:
            cv2.imshow("Option A — Front Face", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    rec.stop()
    cv2.destroyAllWindows()