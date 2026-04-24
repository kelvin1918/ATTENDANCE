"""
agent.py — Attendance Camera Agent (Local Plugin)
==================================================
This is the "plugin" that instructors download and run on the classroom PC.
It bridges the local IP camera / webcam with the online Render dashboard.

HOW IT WORKS:
  1. Agent starts and loads face photos from the faces/ folder
  2. Every 3 seconds it polls the Render server: "Should I start scanning?"
  3. When the instructor clicks "Start Camera" on the website, the server
     signals this agent with the class info
  4. Agent opens the camera (webcam or RTSP IP cam), runs face recognition
  5. Every time a face is detected, it pushes the result to Render → Neon
  6. Instructor sees the attendance update live on the website from anywhere
  7. When instructor clicks "Stop", agent stops the camera and waits again

SETUP:
  1. Put this file in your project folder
  2. Create a faces/ folder with student photos named: StudentName.jpg
  3. Edit the CONFIG section below (RENDER_URL and your email)
  4. Run: python agent.py
  OR double-click start_agent.bat

NO BROWSER NEEDED on the classroom PC — just this script running in background.
"""

import face_recognition
import cv2
import numpy as np
import os
import threading
import time
import requests
import sys
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — Edit these before running
# ══════════════════════════════════════════════════════════════════════════════

RENDER_URL       = "https://attendance-system-xapv.onrender.com"  # Your Render URL
INSTRUCTOR_EMAIL = ""        # Your login email — agent uses this to identify itself
FACES_DIR        = "faces"   # Folder with student face photos
POLL_INTERVAL    = 3         # Seconds between status checks
HEARTBEAT_INTERVAL = 5       # Seconds between heartbeat pings
SCALE            = 0.5       # Frame scale for recognition (0.5 = faster)
RECOGNITION_FPS  = 4         # Recognition frames per second
FRAME_WIDTH      = 1280
FRAME_HEIGHT     = 720

# ══════════════════════════════════════════════════════════════════════════════


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── FACE LOADER ───────────────────────────────────────────────────────────────

def sync_faces_from_server(faces_dir):
    """
    Downloads student photos from the Render server into the local faces/ folder.
    This ensures the agent always has the latest registered students.
    Photos are stored as: faces/FirstName_LastName.jpg
    """
    os.makedirs(faces_dir, exist_ok=True)
    try:
        res = requests.get(
            f"{RENDER_URL}/api/students/photos",
            headers={"X-Instructor-Email": INSTRUCTOR_EMAIL},
            timeout=10
        )
        if res.status_code != 200:
            log(f"Could not sync faces from server (status {res.status_code}). Using local faces only.")
            return
        students = res.json()
        synced = 0
        for s in students:
            name     = s.get("name", "").strip().replace(" ", "_")
            photo_url= s.get("photo_url", "")
            if not name or not photo_url:
                continue
            # Build local filename
            ext       = os.path.splitext(photo_url)[-1] or ".jpg"
            local_path= os.path.join(faces_dir, f"{name}{ext}")
            # Skip if already downloaded
            if os.path.exists(local_path):
                continue
            try:
                img_res = requests.get(photo_url, timeout=10)
                if img_res.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(img_res.content)
                    log(f"SYNCED FACE: {name}")
                    synced += 1
            except Exception as e:
                log(f"Could not download photo for {name}: {e}")
        if synced > 0:
            log(f"Downloaded {synced} new student photo(s) from server.")
        else:
            log("Faces are up to date.")
    except Exception as e:
        log(f"Face sync failed: {e}. Using local faces only.")


def load_known_faces(faces_dir):
    known_encodings = []
    known_names     = []
    if not os.path.exists(faces_dir):
        log(f"WARNING: faces/ folder not found at '{faces_dir}'")
        return known_encodings, known_names
    for filename in os.listdir(faces_dir):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        path  = os.path.join(faces_dir, filename)
        name  = os.path.splitext(filename)[0]
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            log(f"WARNING: No face found in {filename}, skipping.")
            continue
        known_encodings.append(encodings[0])
        known_names.append(name)
        log(f"LOADED: {name}")
    log(f"READY: {len(known_names)} student(s) loaded.")
    return known_encodings, known_names


# ── RECOGNIZER ────────────────────────────────────────────────────────────────

class AgentRecognizer:
    def __init__(self, known_encodings, known_names):
        self.known_encodings = known_encodings
        self.known_names     = known_names
        self._lock           = threading.Lock()
        self._latest_frame   = None
        self._scan_log       = {}      # {name: first_seen_unix}
        self._running        = False
        self._class_code     = ""
        self._section        = ""
        self._subject        = ""

    def start(self, source, class_code, section, subject):
        self._class_code = class_code
        self._section    = section
        self._subject    = subject
        self._scan_log   = {}
        self._running    = True

        # Convert source
        if str(source) in ("0", "1"):
            source = int(source)

        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Capture thread
        self._cap_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._cap_thread.start()

        # Recognition thread
        self._rec_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self._rec_thread.start()

        log(f"CAMERA STARTED → {class_code} | {subject} | {section}")

    def stop(self):
        self._running = False
        if hasattr(self, "cap"):
            try:
                self.cap.release()
            except Exception:
                pass
        log("CAMERA STOPPED")

    def _capture_loop(self):
        while self._running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self._latest_frame = frame.copy()
            else:
                time.sleep(0.03)

    def _recognition_loop(self):
        interval = 1.0 / RECOGNITION_FPS
        while self._running:
            start = time.time()
            with self._lock:
                frame = self._latest_frame
            if frame is None:
                time.sleep(interval)
                continue

            small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, locations)

            for enc in encodings:
                name = self._match(enc)
                if name != "Unknown":
                    with self._lock:
                        if name not in self._scan_log:
                            first_seen = time.time()
                            self._scan_log[name] = first_seen
                            ts_str = datetime.fromtimestamp(first_seen).strftime("%H:%M:%S")
                            display = name.replace("_", " ")
                            log(f"DETECTED: {display} at {ts_str}")
                            # Push to cloud in background
                            threading.Thread(
                                target=self._push_to_cloud,
                                args=(name, ts_str),
                                daemon=True
                            ).start()

            elapsed = time.time() - start
            time.sleep(max(0, interval - elapsed))

    def _match(self, encoding):
        if not self.known_encodings:
            return "Unknown"
        distances = face_recognition.face_distance(self.known_encodings, encoding)
        best_idx  = np.argmin(distances)
        if distances[best_idx] < 0.50:
            return self.known_names[best_idx]
        return "Unknown"

    def _push_to_cloud(self, raw_name, timestamp):
        display_name = raw_name.replace("_", " ")
        try:
            res = requests.post(
                f"{RENDER_URL}/api/live_checkin",
                json={
                    "name":             display_name,
                    "class_code":       self._class_code,
                    "section":          self._section,
                    "subject":          self._subject,
                    "instructor_email": INSTRUCTOR_EMAIL,
                    "timestamp":        timestamp,
                    "status":           "Present"
                },
                headers={"X-Instructor-Email": INSTRUCTOR_EMAIL},
                timeout=8
            )
            if res.status_code == 200:
                log(f"SYNCED ✓ {display_name}")
            else:
                log(f"SYNC FAILED ({res.status_code}): {display_name}")
        except requests.exceptions.ConnectionError:
            log(f"NO INTERNET — {display_name} not synced")
        except Exception as e:
            log(f"SYNC ERROR: {e}")


# ── MAIN AGENT LOOP ───────────────────────────────────────────────────────────

def main():
    # Get instructor email
    global INSTRUCTOR_EMAIL
    if not INSTRUCTOR_EMAIL:
        INSTRUCTOR_EMAIL = input("Enter your instructor email: ").strip()
    if not INSTRUCTOR_EMAIL:
        log("ERROR: Instructor email is required.")
        sys.exit(1)

    log(f"Agent starting for: {INSTRUCTOR_EMAIL}")
    log(f"Render URL: {RENDER_URL}")

    # Sync student photos from server before loading faces
    log("Syncing student faces from server...")
    sync_faces_from_server(FACES_DIR)

    # Load faces
    known_enc, known_names = load_known_faces(FACES_DIR)

    recognizer   = AgentRecognizer(known_enc, known_names)
    current_status = "idle"
    last_heartbeat = 0

    log("Agent running — waiting for signal from dashboard...")
    log("Press Ctrl+C to stop.\n")

    while True:
        try:
            now = time.time()

            # ── Heartbeat every 5 seconds ─────────────────────────────────────
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                try:
                    requests.post(
                        f"{RENDER_URL}/api/agent/heartbeat",
                        headers={"X-Instructor-Email": INSTRUCTOR_EMAIL},
                        timeout=5
                    )
                    last_heartbeat = now
                except Exception:
                    pass  # Heartbeat failure is non-critical

            # ── Poll for signal ───────────────────────────────────────────────
            try:
                res  = requests.get(
                    f"{RENDER_URL}/api/agent/poll",
                    headers={"X-Instructor-Email": INSTRUCTOR_EMAIL},
                    timeout=5
                )
                if res.status_code == 200 and res.text.strip():
                    data = res.json()
                else:
                    log(f"Server not ready yet (status {res.status_code}) — retrying...")
                    time.sleep(POLL_INTERVAL)
                    continue
            except requests.exceptions.ConnectionError:
                log("Cannot reach Render — check internet connection. Retrying...")
                time.sleep(POLL_INTERVAL)
                continue
            except ValueError:
                log("Server returned empty response — Render may still be waking up. Retrying...")
                time.sleep(POLL_INTERVAL)
                continue
            except Exception as e:
                log(f"Poll error: {e} — retrying...")
                time.sleep(POLL_INTERVAL)
                continue

            server_status = data.get("status", "idle")

            # ── State transitions ─────────────────────────────────────────────
            if server_status == "active" and current_status != "active":
                # Start camera
                current_status = "active"
                recognizer.start(
                    source     = data.get("source",     "0"),
                    class_code = data.get("class_code", ""),
                    section    = data.get("section",    ""),
                    subject    = data.get("subject",    ""),
                )

            elif server_status == "idle" and current_status == "active":
                # Stop camera
                current_status = "idle"
                recognizer.stop()
                # Reinitialise for next session
                recognizer = AgentRecognizer(known_enc, known_names)
                log("Waiting for next session...")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("Agent stopped by user.")
            if current_status == "active":
                recognizer.stop()
            break
        except Exception as e:
            log(f"Unexpected error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()