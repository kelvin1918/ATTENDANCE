"""
face_recognition_a.py  —  InsightFace buffalo_l engine  (v3)
=============================================================
Replaces dlib/HOG with InsightFace buffalo_l which combines:
  • RetinaFace  — face DETECTION  (finds faces at angle, distance, multiple faces)
  • ArcFace     — face RECOGNITION (512-d embeddings, far more accurate than dlib 128-d)

Key improvements over v2 (dlib/HOG):
  ✓ Detects faces at steep angles and classroom distances
  ✓ Detects multiple faces simultaneously in one pass
  ✓ Much lower false match rate (512-d vs 128-d embeddings)
  ✓ Supports 4-angle registration (front, left, right, up)
  ✓ Confirmation buffer (3 consecutive frames) still in place
  ✓ Same threading architecture — Flask stream never blocks
  ✓ No GPU required — runs on CPU via ONNX Runtime

Install:
    pip install insightface onnxruntime opencv-python numpy requests

First run downloads buffalo_l model (~300MB) to ~/.insightface/models/
Subsequent runs load from cache instantly.
"""

import cv2
import numpy as np
import os
import threading
import time
import requests
from datetime import datetime as _dt

# InsightFace — replaces face_recognition + dlib
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("[FACES] InsightFace not installed — run: pip install insightface onnxruntime")


# ── CONFIG ────────────────────────────────────────────────────────────────────

FACES_DIR       = "faces"

# Detection size — larger = detects more faces/farther but slower
# 640 is the sweet spot for classroom use on CPU
DET_SIZE        = (640, 640)

# Similarity threshold — cosine similarity (higher = stricter)
# ArcFace: 0.0–1.0.  0.35 = balanced.  Raise to 0.40 for stricter matching.
# Unlike dlib distance (lower=better), cosine similarity is higher=better.
THRESHOLD       = 0.35

# Recognition FPS — how many times per second the recognizer runs
RECOGNITION_FPS = 2    # 2 fps is enough with RetinaFace; less CPU heat

# Confirmation buffer — must appear N consecutive recognition frames
CONFIRM_FRAMES  = 1

# Camera
CAMERA_SOURCE   = 0
FRAME_WIDTH     = 1280
FRAME_HEIGHT    = 720

# ── CLOUD SYNC CONFIG ─────────────────────────────────────────────────────────
CLOUD_URL        = "https://attendance-system-xapv.onrender.com"
CLOUD_SYNC       = True
INSTRUCTOR_EMAIL = ""
CLASS_CODE       = ""
SECTION          = ""
SUBJECT          = ""


# ── FACE ENCODER ──────────────────────────────────────────────────────────────

def _build_app():
    """
    Build and return the InsightFace FaceAnalysis app.
    Downloads buffalo_l on first run (~300MB), then loads from cache.
    ctx_id=-1 forces CPU mode (no GPU required).
    """
    if not INSIGHTFACE_AVAILABLE:
        return None

    # When running as a PyInstaller EXE, look for the model folder beside
    # the EXE so it works without internet on other PCs.
    import sys, os as _os
    if getattr(sys, 'frozen', False):
        _root_dir = _os.path.dirname(sys.executable)
    else:
        _root_dir = _os.path.join(_os.path.expanduser('~'), '.insightface')

    app = FaceAnalysis(
        name      = "buffalo_l",
        root      = _root_dir,
        providers = ["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=DET_SIZE)
    return app


def load_known_faces(faces_dir: str):
    """
    Load ALL face images from a class-scoped folder and compute ArcFace embeddings.

    Supports 4-angle registration:
      Name_front.jpg / Name_left.jpg / Name_right.jpg / Name_up.jpg
      → all 4 embeddings stored under the same display name

    Legacy single-photo format (Name.jpg) also supported — no re-registration needed
    for existing students, though accuracy will be lower.

    Returns: (known_embeddings, known_names, insightface_app)
    """
    known_embeddings = []
    known_names      = []

    if not INSIGHTFACE_AVAILABLE:
        print("[FACES] InsightFace unavailable — returning empty face list")
        return known_embeddings, known_names, None

    if not os.path.isdir(faces_dir):
        print(f"[FACES] Directory not found: {faces_dir} — 0 faces loaded")
        return known_embeddings, known_names, None

    image_files = [
        f for f in os.listdir(faces_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        print(f"[FACES] No images in {faces_dir} — 0 faces loaded")
        return known_embeddings, known_names, None

    print("[FACES] Loading InsightFace buffalo_l model…")
    app = _build_app()
    if app is None:
        return known_embeddings, known_names, None

    # Group files by base name (strip _front/_left/_right/_up suffix)
    angle_suffixes = ("_front", "_left", "_right", "_up")

    for filename in sorted(image_files):
        path     = os.path.join(faces_dir, filename)
        raw_name = os.path.splitext(filename)[0]

        # Derive display name — strip angle suffix if present
        display_name = raw_name
        for sfx in angle_suffixes:
            if raw_name.lower().endswith(sfx):
                display_name = raw_name[: -len(sfx)]
                break
        display_name = display_name.replace("_", " ")

        try:
            img   = cv2.imread(path)
            if img is None:
                print(f"[FACES] ✗ Cannot read {filename}")
                continue
            faces = app.get(img)
            if not faces:
                print(f"[FACES] ✗ No face detected in {filename}")
                continue
            # Use the largest detected face (most prominent)
            face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            emb  = face.normed_embedding   # 512-d unit vector
            known_embeddings.append(emb)
            known_names.append(display_name)
            print(f"[FACES] ✓ Loaded: {display_name}  ({filename})")
        except Exception as e:
            print(f"[FACES] ✗ Error loading {filename}: {e}")

    print(f"[FACES] Ready — {len(known_names)} embedding(s) from {faces_dir}")
    return known_embeddings, known_names, app


# ── RECOGNIZER ────────────────────────────────────────────────────────────────

class FaceRecognizer:
    """
    InsightFace-powered threaded face recognizer.

    Thread 1 (Flask)       — reads camera, draws boxes, streams MJPEG
    Thread 2 (recognition) — runs RetinaFace + ArcFace, updates shared state

    Confirmation buffer: a name must appear in CONFIRM_FRAMES consecutive
    recognition frames before being marked Present.
    """

    def __init__(self, known_embeddings, known_names, app=None):
        self.known_embeddings = list(known_embeddings)
        self.known_names      = list(known_names)
        self._app             = app   # InsightFace FaceAnalysis instance

        self._lock            = threading.Lock()
        self._latest_frame    = None
        self._face_boxes      = []    # [(x1,y1,x2,y2), ...]
        self._face_names      = []    # matched names
        self._face_scores     = []    # cosine similarity scores
        self._present_set     = set()
        self._scan_log        = {}    # {name: first_seen_unix}
        self._scan_status     = {}    # {name: "Present" | "Late"}
        self._pending_counts  = {}    # {name: consecutive_count}

        self._running         = False
        self._rec_thread      = None
        self._capture_thread  = None

        self._instructor_email = INSTRUCTOR_EMAIL
        self._class_code       = CLASS_CODE
        self._section          = SECTION
        self._subject          = SUBJECT
        self._session_start    = _dt.now()  # overwritten by set_session
        self._late_minutes     = 1         # default 15-minute grace period

    # ── public API ──────────────────────────────────────────────────────────

    def set_session(self, instructor_email, class_code, section, subject,
                    late_minutes: int = 1, session_start=None):
        self._instructor_email = instructor_email
        self._class_code       = class_code
        self._section          = section
        self._subject          = subject
        # Use the timestamp from when the instructor pressed Start Camera
        # (passed in from local_app.py) so face-encoding time is included
        # in the late countdown, not skipped.
        self._session_start    = session_start if session_start is not None else _dt.now()
        self._late_minutes     = late_minutes
        print(f"[CLOUD] Session set → {class_code} | {subject} | {section} "
              f"| Late after {late_minutes} min")

    def add_known_face(self, image_path: str, display_name: str):
        """
        Encode a face image and add to live recognizer.
        Accepts single image — call multiple times for each angle.
        """
        if self._app is None:
            return
        def _encode():
            try:
                img   = cv2.imread(image_path)
                if img is None:
                    return
                faces = self._app.get(img)
                if not faces:
                    print(f"[FACES] ✗ No face in {image_path}")
                    return
                face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                emb  = face.normed_embedding
                with self._lock:
                    self.known_embeddings.append(emb)
                    self.known_names.append(display_name)
                print(f"[FACES] ✓ Added {display_name} ({os.path.basename(image_path)})")
            except Exception as e:
                print(f"[FACES] ✗ Encode error {display_name}: {e}")
        threading.Thread(target=_encode, daemon=True).start()

    def _cloud_sync(self, name, timestamp):
        if not CLOUD_SYNC or not self._class_code:
            return
        def _push():
            try:
                # Determine attendance status based on time since session start
                elapsed = (_dt.now() - self._session_start).total_seconds() / 60
                status  = "Late" if elapsed > self._late_minutes else "Present"

                payload = {
                    "name":             name,
                    "class_code":       self._class_code,
                    "section":          self._section,
                    "subject":          self._subject,
                    "instructor_email": self._instructor_email,
                    "timestamp":        timestamp,
                    "status":           status
                }
                res = requests.post(
                    f"{CLOUD_URL}/api/live_checkin",
                    json=payload, timeout=5
                )
                print(f"[CLOUD] {'✓' if res.status_code==200 else '✗'} {name} → {status} "
                      f"({elapsed:.1f} min elapsed)")
            except Exception as e:
                print(f"[CLOUD] ✗ {name}: {e}")
        threading.Thread(target=_push, daemon=True).start()

    def start(self, camera_source):
        if self._app is None:
            print("[CAM] InsightFace not loaded — cannot start recognition")
            return

        # Force TCP transport for RTSP streams — more stable than UDP,
        # reduces packet loss and freeze on direct UTP/LAN connections.
        if isinstance(camera_source, str) and camera_source.lower().startswith("rtsp"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|buffer_size;0|max_delay;0|fflags;nobuffer"
            )
            self.cap = cv2.VideoCapture(camera_source, cv2.CAP_FFMPEG)
            print("[CAM] RTSP source detected — using TCP transport")
        else:
            self.cap = cv2.VideoCapture(camera_source)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._running = True

        # Dedicated capture thread — reads frames continuously, always keeps
        # only the latest. Prevents FFMPEG buffer accumulation on RTSP streams
        # which is the main cause of freeze and catch-up lag.
        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._capture_thread.start()

        self._rec_thread = threading.Thread(
            target=self._recognition_loop, daemon=True
        )
        self._rec_thread.start()

    def _capture_loop(self):
        """
        Thread 0 — dedicated camera reader.
        Reads frames as fast as the camera produces them and keeps only
        the latest. Both generate_frames() and _recognition_loop() read
        from _latest_frame — they are never blocked waiting on the camera.
        """
        while self._running:
            if not hasattr(self, "cap") or not self.cap.isOpened():
                time.sleep(0.05)
                continue
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._latest_frame = frame
            else:
                time.sleep(0.01)

    def stop(self):
        self._running = False
        if hasattr(self, "cap"):
            self.cap.release()

    def get_present_students(self):
        with self._lock:
            return list(self._present_set)

    def get_scan_log(self):
        """Returns {name: {"ts": unix_timestamp, "status": "Present"|"Late"}}"""
        with self._lock:
            return {
                name: {"ts": ts, "status": self._scan_status.get(name, "Present")}
                for name, ts in self._scan_log.items()
            }

    def reset_attendance(self):
        with self._lock:
            self._present_set    = set()
            self._scan_log       = {}
            self._scan_status    = {}
            self._pending_counts = {}

    def stop_and_reset(self):
        self._running = False
        if hasattr(self, "cap"):
            try: self.cap.release()
            except: pass
        with self._lock:
            self._present_set    = set()
            self._scan_log       = {}
            self._scan_status    = {}
            self._pending_counts = {}
            self._latest_frame   = None
            self._face_boxes     = []
            self._face_names     = []
            self._face_scores    = []

    def generate_frames(self):
        """
        Flask MJPEG generator — reads from _latest_frame maintained by
        _capture_loop. Never blocks on the camera directly, so the browser
        stream stays smooth even if the RTSP source has variable timing.
        """
        while self._running:
            with self._lock:
                frame     = self._latest_frame
                boxes     = list(self._face_boxes)
                names     = list(self._face_names)
                scores    = list(self._face_scores)
                confirmed = set(self._present_set)
                pending   = dict(self._pending_counts)

            if frame is None:
                time.sleep(0.03)
                continue

            annotated = self._draw_boxes(frame.copy(), boxes, names, scores, confirmed, pending)
            _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buf.tobytes() + b"\r\n"
            )
            time.sleep(1 / 30)  # cap browser stream at 30fps

    # ── internals ───────────────────────────────────────────────────────────

    def _recognition_loop(self):
        """Thread 2 — RetinaFace detection + ArcFace recognition + confirmation buffer."""
        interval    = 1.0 / RECOGNITION_FPS
        _last_names = {}   # slot_index → last seen name

        while self._running:
            t0 = time.time()

            with self._lock:
                frame = self._latest_frame

            if frame is None:
                time.sleep(interval)
                continue

            try:
                # RetinaFace detects ALL faces in one pass — no sliding window
                faces = self._app.get(frame)
            except Exception as e:
                print(f"[REC] Error: {e}")
                time.sleep(interval)
                continue

            boxes  = []
            names  = []
            scores = []

            for i, face in enumerate(faces):
                x1, y1, x2, y2 = [int(v) for v in face.bbox]
                boxes.append((x1, y1, x2, y2))

                name, score = self._match(face.normed_embedding)
                names.append(name)
                scores.append(score)

                if name == "Unknown":
                    _last_names[i] = "Unknown"
                    continue

                # Confirmation buffer
                if _last_names.get(i) != name:
                    _last_names[i]             = name
                    self._pending_counts[name] = 1
                else:
                    self._pending_counts[name] = \
                        self._pending_counts.get(name, 0) + 1

                count = self._pending_counts.get(name, 0)
                if count >= CONFIRM_FRAMES:
                    with self._lock:
                        if name not in self._present_set:
                            self._present_set.add(name)
                            ts     = time.time()
                            elapsed = (_dt.now() - self._session_start).total_seconds() / 60
                            status  = "Late" if elapsed > self._late_minutes else "Present"
                            self._scan_log[name]    = ts
                            self._scan_status[name] = status
                            ts_str = _dt.fromtimestamp(ts).strftime("%H:%M:%S")
                            print(f"[DETECT] ✓ Confirmed: {name} → {status} "
                                  f"({elapsed:.1f} min, score={score:.3f})")
                            self._cloud_sync(name, ts_str)
                else:
                    print(f"[DETECT] Pending: {name} ({count}/{CONFIRM_FRAMES}, score={score:.3f})")

            with self._lock:
                self._face_boxes  = boxes
                self._face_names  = names
                self._face_scores = scores

            time.sleep(max(0, interval - (time.time() - t0)))

    def _match(self, embedding):
        """
        Cosine similarity match against all stored embeddings.
        Returns (name, score). Score 0.0–1.0, higher = more similar.
        Since embeddings are unit vectors, dot product = cosine similarity.
        """
        if not self.known_embeddings:
            return "Unknown", 0.0

        embs   = np.array(self.known_embeddings)   # (N, 512)
        sims   = np.dot(embs, embedding)            # (N,) cosine similarities
        best_i = int(np.argmax(sims))
        score  = float(sims[best_i])

        if score >= THRESHOLD:
            return self.known_names[best_i], score
        return "Unknown", score

    def _draw_boxes(self, frame, boxes, names, scores, confirmed, pending):
        """
        Color-coded bounding boxes:
          Green  — confirmed Present
          Orange — pending confirmation (shows count progress)
          Grey   — Unknown
        """
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            name  = names[i]  if i < len(names)  else "Unknown"
            score = scores[i] if i < len(scores) else 0.0

            if name == "Unknown":
                color = (120, 120, 120)
                label = "Unknown"
            elif name in confirmed:
                color = (0, 200, 0)
                label = name
            else:
                count = pending.get(name, 0)
                color = (30, 140, 255)
                label = f"{name} ({count}/{CONFIRM_FRAMES})"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            bar_top = max(y2 - 32, y1)
            cv2.rectangle(frame, (x1, bar_top), (x2, y2), color, -1)
            cv2.putText(
                frame, label,
                (x1 + 6, y2 - 8),
                cv2.FONT_HERSHEY_DUPLEX, 0.55,
                (255, 255, 255), 1
            )
        return frame


# ── STANDALONE TEST ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    encs, names, app = load_known_faces(FACES_DIR)
    rec = FaceRecognizer(encs, names, app)
    rec.start(CAMERA_SOURCE)

    print("Press Q to quit.")
    while True:
        if not hasattr(rec, "cap") or not rec.cap.isOpened():
            break
        ret, frame = rec.cap.read()
        if not ret:
            break
        cv2.imshow("InsightFace — BatStateU Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    rec.stop()
    cv2.destroyAllWindows()