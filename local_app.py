"""
local_app.py — BatStateU Attendance Local Station
===================================================
Purpose : Camera-first kiosk for in-room use only.
Runs at  : http://127.0.0.1:5000
Serves   : local.html  (single page — login → class select → camera)

Responsibilities
----------------
  ✓  Instructor login   (syncs against Neon via Render API or direct DB)
  ✓  Class list         (pulled from DB, filtered to today's schedule)
  ✓  Student registration (photo → /faces/, signature → /uploads/signatures/)
  ✓  Camera feed        (MJPEG stream via face_recognition_a.py)
  ✓  Live check-in      (POST to Render /api/live_checkin + local LIVE row)
  ✓  Save attendance    (purge LIVE, write permanent, notify Render)
  ✓  Session summary    (present count before closing)
  ✓  Offline fallback   (class list cached to local_cache.json)
  ✓  /ping              (CORS-open — Render detects if .exe is running)
  ✓  Port fallback      (tries 5000 → 5001 → 5002)

NOT included (Render handles these)
-------------------------------------
  ✗  Dashboard / analytics
  ✗  History / PDF viewer
  ✗  Admin panel
  ✗  Schedule manager
  ✗  Notifications
  ✗  Email / SMTP
"""

import os, json, shutil, socket, webbrowser, threading, time
from datetime import datetime, date

# ── LOAD .env FIRST — before any module that reads os.environ ─────────────────
# database.py reads DB_HOST/DB_PASSWORD at import time.
# If load_dotenv() runs after that, the env vars are already missed.
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[ENV] .env loaded ✓")
except ImportError:
    print("[ENV] python-dotenv not installed — using system environment variables")

from flask import (
    Flask, request, jsonify, send_file,
    send_from_directory, Response, abort
)
from flask_cors import CORS
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf

# ── CLOUDINARY CONFIG ─────────────────────────────────────────────────────────
# Credentials are read from environment variables — never hardcode these.
# Set them in a .env file locally, or in the Render dashboard for cloud.
#
#   CLOUDINARY_CLOUD_NAME = your_cloud_name
#   CLOUDINARY_API_KEY    = your_api_key
#   CLOUDINARY_API_SECRET = your_api_secret
#
# If any are missing, Cloudinary uploads are skipped and files remain local-only.

try:
    import cloudinary
    import cloudinary.uploader
    _CLOUDINARY_CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    _CLOUDINARY_KEY   = os.environ.get("CLOUDINARY_API_KEY",    "")
    _CLOUDINARY_SEC   = os.environ.get("CLOUDINARY_API_SECRET", "")

    if _CLOUDINARY_CLOUD and _CLOUDINARY_KEY and _CLOUDINARY_SEC:
        cloudinary.config(
            cloud_name = _CLOUDINARY_CLOUD,
            api_key    = _CLOUDINARY_KEY,
            api_secret = _CLOUDINARY_SEC,
            secure     = True,
        )
        CLOUDINARY_ENABLED = True
        print("[CLOUD] Cloudinary configured ✓")
    else:
        CLOUDINARY_ENABLED = False
        print("[CLOUD] Cloudinary credentials missing — uploads will be local only")
except ImportError:
    CLOUDINARY_ENABLED = False
    print("[CLOUD] cloudinary package not installed — pip install cloudinary")

# ── CAMERA ───────────────────────────────────────────────────────────────────
try:
    from face_recognition_a import FaceRecognizer, load_known_faces, _build_app
    CAMERA_ENABLED = True
except ImportError:
    CAMERA_ENABLED = False
    print("[LOCAL] Camera disabled — face_recognition not installed.")

# ── CLOUD HUB URL ─────────────────────────────────────────────────────────────
CLOUD_URL = "https://attendance-system-xapv.onrender.com"

# ── APP SETUP ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
CORS(app, origins="*")   # allow Render to ping us

ALLOWED_EXT = {"jpg", "jpeg", "png"}
CACHE_FILE  = "local_cache.json"

# Base folders — class subfolders are created at registration/camera-start time
for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

db.init_db()

# ── FACE RECOGNIZER STATE ─────────────────────────────────────────────────────
# Faces are NOT loaded at startup anymore.
# They are loaded per-class when the camera starts (class-scoped folder).
# This means startup is instant regardless of how many students are enrolled.

known_enc, known_names = [], []
recognizer             = None
_camera_active         = False
_current_class_code    = None   # tracks which class folder is loaded


def _class_faces_dir(class_code: str) -> str:
    """Return the faces subfolder for a specific class. Creates it if missing."""
    path = os.path.join("faces", _safe_code(class_code))
    os.makedirs(path, exist_ok=True)
    return path


def _class_students_dir(class_code: str) -> str:
    path = os.path.join("uploads", "students", _safe_code(class_code))
    os.makedirs(path, exist_ok=True)
    return path


def _class_signatures_dir(class_code: str) -> str:
    path = os.path.join("uploads", "signatures", _safe_code(class_code))
    os.makedirs(path, exist_ok=True)
    return path


def _safe_code(class_code: str) -> str:
    """Sanitise class code for use as a folder name."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in class_code)


# ── PROGRESSIVE LOAD STATE ────────────────────────────────────────────────────
# Shared between the background encoding thread and the /api/local/load_progress
# poll endpoint so the frontend can show a live counter.
_load_progress = {"loaded": 0, "total": 0, "done": True, "error": None}
_load_lock     = threading.Lock()


def _load_class_faces_bg(class_code, session_meta):
    """
    Background thread — loads InsightFace buffalo_l model and encodes all
    faces for this class. Updates _load_progress after each image.
    Starts the camera automatically when all faces are encoded.
    """
    global known_enc, known_names, recognizer, _camera_active
    global _current_class_code, _load_progress

    faces_dir   = _class_faces_dir(class_code)
    image_files = [
        f for f in os.listdir(faces_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ] if os.path.isdir(faces_dir) else []

    total = len(image_files)
    with _load_lock:
        _load_progress = {"loaded": 0, "total": total, "done": False, "error": None}

    # Build InsightFace app once for this session
    from face_recognition_a import _build_app as _insight_build
    import cv2 as _cv2, numpy as _np

    angle_suffixes = ("_front", "_left", "_right", "_up")

    app = _insight_build()
    enc_list  = []
    name_list = []

    for i, filename in enumerate(image_files):
        path     = os.path.join(faces_dir, filename)
        raw_name = os.path.splitext(filename)[0]

        # Strip angle suffix to get display name
        display_name = raw_name
        for sfx in angle_suffixes:
            if raw_name.lower().endswith(sfx):
                display_name = raw_name[:-len(sfx)]
                break
        display_name = display_name.replace("_", " ")

        try:
            img   = _cv2.imread(path)
            if img is None:
                print(f"[FACES] ✗ Cannot read {filename}")
            else:
                faces = app.get(img) if app else []
                if faces:
                    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                    enc_list.append(face.normed_embedding)
                    name_list.append(display_name)
                    print(f"[FACES] ✓ {display_name} ({i+1}/{total})")
                else:
                    print(f"[FACES] ✗ No face in {filename}")
        except Exception as e:
            print(f"[FACES] ✗ Error {filename}: {e}")

        with _load_lock:
            _load_progress["loaded"] = i + 1

    # All encoded — start the camera now
    try:
        source  = session_meta["source"]
        email   = session_meta["email"]
        section = session_meta["section"]
        subject = session_meta["subject"]

        if _camera_active and recognizer:
            recognizer.stop_and_reset()

        known_enc, known_names = enc_list, name_list
        _current_class_code    = class_code
        recognizer             = FaceRecognizer(known_enc, known_names, app)
        recognizer.set_session(email, class_code, section, subject)
        recognizer.start(source)
        _camera_active = True
        print(f"[CAMERA] Started — {len(known_names)} embedding(s) for {class_code}")

        with _load_lock:
            _load_progress["done"] = True

    except Exception as e:
        with _load_lock:
            _load_progress["done"]  = True
            _load_progress["error"] = str(e)
        print(f"[CAMERA] Start error: {e}")


def _load_class_faces(class_code: str):
    """
    Load face encodings for ONE class only.
    Called when camera starts — not at boot, not at registration.
    Returns (encodings_list, names_list).
    """
    faces_dir = _class_faces_dir(class_code)
    if CAMERA_ENABLED:
        encs, names, app = load_known_faces(faces_dir)
        return encs, names, app
    return [], [], None


def _add_single_face(image_path: str, display_name: str):
    """
    Encode ONE face image and append its InsightFace embedding to the live recognizer.
    Called for each angle photo after registration.
    Runs in a background thread so the HTTP response returns immediately.
    """
    if not CAMERA_ENABLED or recognizer is None:
        return
    # Delegate to FaceRecognizer.add_known_face which uses InsightFace internally
    recognizer.add_known_face(image_path, display_name)


def _cloudinary_upload(local_path: str, public_id: str, folder: str) -> str:
    """
    Upload a file to Cloudinary and return its secure public URL.
    Returns "" if Cloudinary is disabled, credentials are missing, or upload fails.
    Caller should fall back to the local path in that case.
    """
    if not CLOUDINARY_ENABLED:
        return ""
    try:
        result = cloudinary.uploader.upload(
            local_path,
            public_id     = public_id,
            folder        = folder,
            overwrite     = True,
            resource_type = "image",
            transformation = [{"flags": "strip_profile", "angle": "exif"}],
        )
        url = result.get("secure_url", "")
        print(f"[CLOUD] ✓ {public_id} → {url}")
        return url
    except Exception as e:
        print(f"[CLOUD] ✗ Upload failed {public_id}: {e}")
        return ""


def _register_bg(class_code, name, safe_base,
                 face_files,       # list of (local_path, angle_label)
                 photo_local,      # front photo for display (students/ folder)
                 sig_local,        # signature file
                 form_data):
    """
    Background thread for student registration (4-angle InsightFace version):
      1. Encode all angle photos and add to live recognizer
      2. Upload all angle photos + signature to Cloudinary
      3. Save student record to Neon DB
    HTTP response is already returned before this runs.

    face_files: [(path, label), ...] e.g.
        [("faces/CLASS/Name_front.jpg", "front"),
         ("faces/CLASS/Name_left.jpg",  "left"), ...]
    """
    safe_class = _safe_code(class_code)

    # Step 1 — lazy encode ALL angle photos into live recognizer
    for face_path, angle_label in face_files:
        if face_path and os.path.isfile(face_path):
            _add_single_face(face_path, name)

    # Step 2 — Cloudinary uploads
    # Front photo → students/ folder (for display on Render)
    photo_url = _cloudinary_upload(photo_local, safe_base, f"students/{safe_class}")                 if photo_local else ""

    # Angle photos → faces/ folder on Cloudinary (for sync to new PCs)
    angle_urls = {}
    for face_path, label in face_files:
        if face_path and os.path.isfile(face_path):
            url = _cloudinary_upload(
                face_path,
                f"{safe_base}_{label}",
                f"faces/{safe_class}"
            )
            angle_urls[f"photo_{label}"] = url

    # Signature
    sig_url = _cloudinary_upload(sig_local, safe_base + "_sig", f"signatures/{safe_class}")               if sig_local else ""

    # Step 3 — DB
    try:
        db.add_student(
            class_code   = class_code,
            name         = name,
            address      = form_data.get("address", ""),
            number       = form_data.get("number",  ""),
            sr_code      = form_data.get("sr_code", ""),
            age          = int(form_data.get("age") or 0),
            sex          = form_data.get("sex",     ""),
            email        = form_data.get("email",   ""),
            photo        = photo_url  or photo_local or "",
            signature    = sig_url    or sig_local   or "",
            photo_front  = angle_urls.get("photo_front",  ""),
            photo_left   = angle_urls.get("photo_left",   ""),
            photo_right  = angle_urls.get("photo_right",  ""),
            photo_up     = angle_urls.get("photo_up",     ""),
        )
        print(f"[REG] ✓ {name} saved — {len(face_files)} angle(s), "
              f"sig={'Cloudinary' if sig_url else 'local'}")
    except Exception as e:
        print(f"[REG] ✗ DB error for {name}: {e}")


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ── CACHE HELPERS ─────────────────────────────────────────────────────────────
def _save_cache(email, classes, schedules):
    """Persist class + schedule data for offline fallback."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"email": email, "classes": classes,
                       "schedules": schedules, "ts": time.time()}, f)
    except Exception:
        pass


def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


# ── TODAY FILTER ──────────────────────────────────────────────────────────────
_DAY_MAP = {
    0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"
}

def _today_abbr():
    return _DAY_MAP[datetime.now().weekday()]


def _filter_today(classes, schedules):
    """
    Return classes that have a schedule on today's weekday.
    A class may appear more than once if it has multiple schedule slots today
    (e.g. Electronic Devices appears twice on Thursday).
    Both unique classes AND all matching schedule rows are returned so the
    frontend can show each time slot.
    """
    today = _today_abbr()
    today_scheds = [
        s for s in schedules
        if (s.get("day") or "").upper() == today
    ]
    if not today_scheds:
        # No schedule for today — return all classes so the instructor
        # can still select any class manually
        return classes, []

    scheduled_codes = {s["class_code"] for s in today_scheds}
    today_classes   = [c for c in classes if c.get("class_code") in scheduled_codes]
    return today_classes, today_scheds



# ══════════════════════════════════════════════════════════════════════════════
# FACE SYNC — download missing face images from Cloudinary on login
# ══════════════════════════════════════════════════════════════════════════════

# Shared sync progress (same pattern as _load_progress)
_sync_progress = {"done": True, "total": 0, "synced": 0, "skipped": 0, "error": None}
_sync_lock     = threading.Lock()


def _sync_faces_bg(instructor_id):
    """
    Background thread — runs after login on a fresh or existing PC.
    For every student in the instructor's classes:
      1. Check if faces/<CLASS_CODE>/Name.jpg already exists locally
      2. If missing AND photo is a Cloudinary URL → download it
      3. Update _sync_progress so the frontend can show a live counter
    Does NOT re-download files that already exist (incremental sync).
    """
    global _sync_progress

    try:
        students = db.get_students_with_photos(instructor_id)
    except Exception as e:
        with _sync_lock:
            _sync_progress = {"done": True, "total": 0, "synced": 0,
                              "skipped": 0, "error": str(e)}
        return

    total   = len(students)
    synced  = 0
    skipped = 0

    with _sync_lock:
        _sync_progress = {"done": False, "total": total,
                          "synced": 0, "skipped": 0, "error": None}

    import urllib.request as _ur

    def _dl(url, dest):
        """Download a URL to dest. Returns True on success."""
        if not url or not url.startswith("http"):
            return False
        if os.path.isfile(dest):
            return False   # already exists
        try:
            req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=10) as resp:
                with open(dest, "wb") as out:
                    out.write(resp.read())
            return True
        except Exception as e:
            print(f"[SYNC] ✗ download error {dest}: {e}")
            return False

    for s in students:
        class_code = s.get("class_code", "")
        name       = s.get("name", "")
        safe_name  = _safe_code(name.replace(" ", "_"))
        faces_dir  = _class_faces_dir(class_code)
        any_dl     = False

        # Try all 4 angle photos first (new registration format)
        angle_map = {
            "front": s.get("photo_front", "") or "",
            "left":  s.get("photo_left",  "") or "",
            "right": s.get("photo_right", "") or "",
            "up":    s.get("photo_up",    "") or "",
        }
        has_angles = any(v.startswith("http") for v in angle_map.values())

        if has_angles:
            for label, url in angle_map.items():
                if not url:
                    continue
                ext  = os.path.splitext(url.split("?")[0])[1] or ".jpg"
                dest = os.path.join(faces_dir, f"{safe_name}_{label}{ext}")
                if _dl(url, dest):
                    any_dl = True
                    print(f"[SYNC] ✓ {name} ({label})")
        else:
            # Legacy: single photo in photo column
            photo_url = s.get("photo", "") or ""
            ext  = os.path.splitext(photo_url.split("?")[0])[1] or ".jpg"
            dest = os.path.join(faces_dir, f"{safe_name}_front{ext}")
            if _dl(photo_url, dest):
                any_dl = True
                print(f"[SYNC] ✓ {name} (legacy front)")

        if any_dl:
            synced += 1
        else:
            skipped += 1

        with _sync_lock:
            _sync_progress["synced"]  = synced
            _sync_progress["skipped"] = skipped

    with _sync_lock:
        _sync_progress["done"]    = True
        _sync_progress["synced"]  = synced
        _sync_progress["skipped"] = skipped

    print(f"[SYNC] Complete — {synced} downloaded, {skipped} skipped")


# ══════════════════════════════════════════════════════════════════════════════
# CORE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return send_file("local.html")

@app.route("/local.html")
def local_html():
    return send_file("local.html")

@app.route("/favicon.ico")
def favicon():
    return "", 204


# ══════════════════════════════════════════════════════════════════════════════
# /ping — Render detects .exe is running via this endpoint
# CORS is fully open so the browser on Render can fetch it
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/ping")
def ping():
    return jsonify({"status": "local_station_running", "version": "1.0.0"})


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — Login only (no registration — accounts managed on Render)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/login", methods=["POST"])
def api_local_login():
    data  = request.json or {}
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()

    if not email or not pwd:
        return jsonify({"error": "Email and password required."}), 400

    user = db.get_instructor_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["password"] != pwd:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["status"] == "pending":
        return jsonify({"error": "Account pending approval. See administrator."}), 403

    # ── Trigger face sync in background after successful login ───────────────
    # This runs on every login but is incremental — already-downloaded faces
    # are skipped instantly, so it's fast after the first run.
    instructor_id = user.get("id")
    if instructor_id:
        with _sync_lock:
            global _sync_progress
            _sync_progress = {"done": False, "total": 0,
                              "synced": 0, "skipped": 0, "error": None}
        threading.Thread(
            target=_sync_faces_bg,
            args=(instructor_id,),
            daemon=True
        ).start()

    return jsonify({
        "status":        "ok",
        "email":         user["email"],
        "name":          user["name"],
        "instructor_id": instructor_id,
        "sync_started":  True,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CLASSES — today-filtered, with offline cache fallback
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/sync_progress")
def api_sync_progress():
    """
    Polled by the frontend during the post-login sync screen.
    Returns { done, total, synced, skipped, error }
    When done=true → proceed to class list.
    """
    with _sync_lock:
        return jsonify(dict(_sync_progress))


@app.route("/api/local/sync_faces", methods=["POST"])
def api_sync_faces():
    """
    Manual re-sync trigger (e.g. instructor presses 'Sync Now' button).
    Kicks off _sync_faces_bg in a background thread and returns immediately.
    """
    email = request.headers.get("X-Instructor-Email", "")
    user  = db.get_instructor_by_email(email) if email else None
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    with _sync_lock:
        global _sync_progress
        _sync_progress = {"done": False, "total": 0,
                          "synced": 0, "skipped": 0, "error": None}

    threading.Thread(
        target=_sync_faces_bg,
        args=(user["id"],),
        daemon=True
    ).start()

    return jsonify({"status": "sync_started"})


@app.route("/api/local/classes")
def api_local_classes():
    email = request.headers.get("X-Instructor-Email", "")
    instructor = db.get_instructor_by_email(email) if email else None
    if not instructor:
        return jsonify({"error": "unauthorized"}), 401

    instructor_id = instructor["id"]

    try:
        classes   = [{ **dict(r), "class_code": r["id"] } for r in db.get_all_classes(instructor_id=instructor_id)]
        schedules = [dict(r) for r in db.get_schedules(instructor_id=instructor_id)]
        _save_cache(email, classes, schedules)
        all_ok = True
    except Exception:
        # Offline fallback
        cache = _load_cache()
        if cache and cache.get("email") == email:
            classes   = cache["classes"]
            schedules = cache["schedules"]
            all_ok    = False
        else:
            return jsonify({"error": "Cannot reach database and no local cache."}), 503

    today_classes, today_scheds = _filter_today(classes, schedules)

    return jsonify({
        "all_classes":    classes,
        "today_classes":  today_classes,
        "today_schedules":today_scheds,
        "all_schedules":  schedules,
        "offline":        not all_ok,
        "today":          _today_abbr(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# CAMERA ROOMS — returns admin-configured room names + RTSP URLs
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/rooms")
def api_local_rooms():
    """Return all campus_rooms so the frontend can build a named dropdown."""
    email = request.headers.get("X-Instructor-Email", "")
    if not email:
        return jsonify({"error": "unauthorized"}), 401
    try:
        rooms = [dict(r) for r in db.get_all_rooms()]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"rooms": rooms})


# ══════════════════════════════════════════════════════════════════════════════
# STUDENTS — for selected class
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/delete_student/<int:student_id>", methods=["DELETE"])
def api_local_delete_student(student_id):
    """
    Deletes a student completely:
      1. Fetches photo/signature paths from DB BEFORE deleting
      2. Deletes the DB row (returns file paths)
      3. Removes Cloudinary assets (photo + signature)
      4. Removes local face file from faces/<CLASS_CODE>/
      5. Removes local student photo and signature files
    Safe to call even if files don't exist — all steps are individually
    guarded so one failure doesn't block the others.
    """
    email = request.headers.get("X-Instructor-Email", "")
    if not email:
        return jsonify({"error": "unauthorized"}), 401

    # ── Step 1+2: DB delete (returns file info) ───────────────────────────
    student = db.delete_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    name       = student.get("name", "")
    class_code = student.get("class_code", "")
    photo      = student.get("photo", "") or ""
    signature  = student.get("signature", "") or ""
    safe_base  = _safe_code(name.replace(" ", "_"))
    safe_class = _safe_code(class_code)

    deleted_cloud = []
    deleted_local = []
    errors        = []

    # ── Step 3: Cloudinary cleanup ────────────────────────────────────────
    if CLOUDINARY_ENABLED:
        for cld_path, label in [
            (f"students/{safe_class}/{safe_base}",        "photo"),
            (f"signatures/{safe_class}/{safe_base}_sig",  "signature"),
        ]:
            try:
                result = cloudinary.uploader.destroy(cld_path)
                if result.get("result") == "ok":
                    deleted_cloud.append(label)
                    print(f"[CLOUD] ✓ Deleted {cld_path}")
                else:
                    print(f"[CLOUD] ✗ Not found on Cloudinary: {cld_path}")
            except Exception as e:
                errors.append(f"Cloudinary {label}: {e}")
                print(f"[CLOUD] ✗ Error deleting {cld_path}: {e}")

    # ── Step 4: Local face file ───────────────────────────────────────────
    faces_dir = _class_faces_dir(class_code)
    for ext in (".jpg", ".jpeg", ".png"):
        face_path = os.path.join(faces_dir, safe_base + ext)
        if os.path.isfile(face_path):
            try:
                os.remove(face_path)
                deleted_local.append(f"faces/{safe_base}{ext}")
                print(f"[LOCAL] ✓ Deleted face: {face_path}")
            except Exception as e:
                errors.append(f"face file: {e}")

    # ── Step 5: Local student photo + signature files ─────────────────────
    for local_path in [photo, signature]:
        if local_path and not local_path.startswith("http") and os.path.isfile(local_path):
            try:
                os.remove(local_path)
                deleted_local.append(local_path)
                print(f"[LOCAL] ✓ Deleted: {local_path}")
            except Exception as e:
                errors.append(f"local file {local_path}: {e}")

    # ── Also remove from live recognizer if camera is running ─────────────
    if recognizer and name:
        try:
            with recognizer._lock:
                if name in recognizer.known_names:
                    idx = recognizer.known_names.index(name)
                    recognizer.known_names.pop(idx)
                    recognizer.known_encodings.pop(idx)
                    print(f"[FACES] ✓ Removed {name} from live recognizer")
        except Exception as e:
            errors.append(f"recognizer removal: {e}")

    return jsonify({
        "status":        "deleted",
        "name":          name,
        "deleted_cloud": deleted_cloud,
        "deleted_local": deleted_local,
        "errors":        errors,
    })


@app.route("/api/local/students/<class_code>")
def api_local_students(class_code):
    rows = db.get_students(class_code)
    result = []
    faces_dir = _class_faces_dir(class_code)

    for r in rows:
        s = dict(r)
        # Check if face file actually exists on LOCAL disk
        # (DB photo field might be a Cloudinary URL but file may not be downloaded yet)
        name_base = _safe_code((s.get("name") or "").replace(" ", "_"))
        has_face_local = any(
            os.path.isfile(os.path.join(faces_dir, name_base + ext))
            for ext in (".jpg", ".jpeg", ".png")
        )
        # Check if signature exists — either local file or Cloudinary URL
        sig = s.get("signature", "") or ""
        has_sig = (
            sig.startswith("http") or
            (sig and os.path.isfile(sig))
        )
        s["has_face_local"] = has_face_local
        s["has_sig"]        = has_sig
        result.append(s)

    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# EDIT STUDENT — update any field, optionally replace photo/signature
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/edit_student/<int:student_id>", methods=["POST"])
def api_local_edit_student(student_id):
    """
    Updates an existing student record.
    Accepts multipart/form-data (same as registration).

    Rules:
      - SR code is read-only — ignored even if sent
      - Photo/signature are optional — omit to keep existing files
      - If a new photo is uploaded: saves locally to faces/ and uploads to Cloudinary
      - If a new signature is uploaded: saves locally and uploads to Cloudinary
      - DB is updated with Cloudinary URLs (fallback to local path)
    Returns immediately — heavy work runs in background thread.
    """
    email = request.headers.get("X-Instructor-Email", "")
    if not email:
        return jsonify({"error": "unauthorized"}), 401

    # Fetch existing student so we know current values
    student = db.get_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    student   = dict(student)
    form      = request.form
    class_code = student["class_code"]
    safe_base  = secure_filename(
        (form.get("name") or student["name"]).replace(" ", "_")
    )

    # ── Save angle photos + signature synchronously before response ──────────
    # request.files is gone after the HTTP response — save everything now.
    ANGLES = ["front", "left", "right", "up"]
    new_angle_files = {}   # {angle: local_path}
    new_photo_local = ""   # front photo for display (students/ folder)

    for angle in ANGLES:
        key = f"photo_{angle}"
        if key in request.files:
            f = request.files[key]
            if f and f.filename and allowed(f.filename):
                ext       = os.path.splitext(secure_filename(f.filename))[1]
                face_path = os.path.join(
                    _class_faces_dir(class_code),
                    f"{safe_base}_{angle}{ext}"
                )
                # Delete old angle file(s) for this slot before saving new one
                for old_ext in (".jpg", ".jpeg", ".png"):
                    old = os.path.join(_class_faces_dir(class_code),
                                       f"{safe_base}_{angle}{old_ext}")
                    if os.path.isfile(old) and old != face_path:
                        try: os.remove(old)
                        except: pass
                f.save(face_path)
                new_angle_files[angle] = face_path
                if angle == "front":
                    new_photo_local = os.path.join(
                        _class_students_dir(class_code), safe_base + ext
                    )
                    shutil.copy(face_path, new_photo_local)

    new_sig_local = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and f.filename and allowed(f.filename):
            ext           = os.path.splitext(secure_filename(f.filename))[1]
            new_sig_local = os.path.join(
                _class_signatures_dir(class_code), safe_base + "_sig" + ext
            )
            f.save(new_sig_local)

    # ── Build info dict for background thread ────────────────────────────────
    update_info = {
        "name":    form.get("name",    "").strip() or None,
        "address": form.get("address", "").strip() or None,
        "number":  form.get("number",  "").strip() or None,
        "age":     int(form.get("age") or 0) or None,
        "sex":     form.get("sex",     "").strip() or None,
        "email":   form.get("email",   "").strip() or None,
    }

    def _edit_bg():
        safe_class   = _safe_code(class_code)
        display_name = update_info["name"] or student["name"]

        # ── Upload each new angle photo to Cloudinary (replaces old) ─────────
        angle_urls = {}
        for angle, face_path in new_angle_files.items():
            # Add the new embedding to the live recognizer
            _add_single_face(face_path, display_name)
            # Cloudinary public_id is identical to old one → overwrite=True
            # replaces the old image automatically (no manual delete needed)
            url = _cloudinary_upload(
                face_path,
                f"{safe_base}_{angle}",
                f"faces/{safe_class}"
            )
            angle_urls[f"photo_{angle}"] = url
            print(f"[EDIT] ✓ Angle '{angle}' → Cloudinary: {bool(url)}")

        # ── Front photo display copy (students/ folder) ───────────────────────
        new_photo_url = ""
        if new_photo_local:
            new_photo_url = _cloudinary_upload(
                new_photo_local, safe_base,
                f"students/{safe_class}"
            )

        # ── Signature ─────────────────────────────────────────────────────────
        new_sig_url = ""
        if new_sig_local:
            new_sig_url = _cloudinary_upload(
                new_sig_local, safe_base + "_sig",
                f"signatures/{safe_class}"
            )

        # ── DB update — only pass fields that have new values ─────────────────
        try:
            db.edit_student(
                student_id,
                name        = update_info["name"],
                address     = update_info["address"],
                number      = update_info["number"],
                age         = update_info["age"],
                sex         = update_info["sex"],
                email       = update_info["email"],
                photo       = (new_photo_url or new_photo_local) if new_photo_local else None,
                signature   = (new_sig_url   or new_sig_local)   if new_sig_local   else None,
                photo_front = angle_urls.get("photo_front") or None,
                photo_left  = angle_urls.get("photo_left")  or None,
                photo_right = angle_urls.get("photo_right") or None,
                photo_up    = angle_urls.get("photo_up")    or None,
            )
            print(f"[EDIT] ✓ Student {student_id} ({display_name}) updated — "
                  f"{len(new_angle_files)} angle(s) replaced")
        except Exception as e:
            print(f"[EDIT] ✗ DB error: {e}")

    threading.Thread(target=_edit_bg, daemon=True).start()
    return jsonify({"status": "ok", "student_id": student_id})


# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURE-ONLY UPLOAD — quick upload without full re-registration
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/upload_signature/<int:student_id>", methods=["POST"])
def api_local_upload_signature(student_id):
    """
    Uploads a signature image for an existing student.
    Does NOT touch the photo or face file.
    Returns immediately — Cloudinary upload runs in background.
    """
    email = request.headers.get("X-Instructor-Email", "")
    if not email:
        return jsonify({"error": "unauthorized"}), 401

    student = db.get_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    student    = dict(student)
    class_code = student["class_code"]
    safe_base  = secure_filename(student["name"].replace(" ", "_"))

    if "signature" not in request.files:
        return jsonify({"error": "No signature file provided"}), 400

    f = request.files["signature"]
    if not f or not f.filename or not allowed(f.filename):
        return jsonify({"error": "Invalid file — JPG or PNG required"}), 400

    ext       = os.path.splitext(secure_filename(f.filename))[1]
    sig_local = os.path.join(
        _class_signatures_dir(class_code), safe_base + "_sig" + ext
    )
    f.save(sig_local)

    def _sig_bg():
        safe_class = _safe_code(class_code)
        sig_url    = _cloudinary_upload(
            sig_local, safe_base + "_sig",
            f"signatures/{safe_class}"
        )
        try:
            db.update_signature_only(student_id, sig_url or sig_local)
            print(f"[SIG] ✓ Signature updated for student {student_id}")
        except Exception as e:
            print(f"[SIG] ✗ DB error: {e}")

    threading.Thread(target=_sig_bg, daemon=True).start()
    return jsonify({"status": "ok", "student_id": student_id})


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT REGISTRATION — photo → /faces/, signature → /uploads/signatures/
# Also pushes student record to cloud (Neon) via db.add_student
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/register_student", methods=["POST"])
def api_local_register_student():
    """
    Registers a student and returns immediately.
    Heavy work (face encoding + Cloudinary upload + DB save) runs in background.

    File flow:
      Photo  → saved locally to uploads/students/<CLASS>/ AND faces/<CLASS>/
             → uploaded to Cloudinary  students/<CLASS>/
             → Cloudinary URL stored in DB  (fallback: local path)
      Sig    → saved locally to uploads/signatures/<CLASS>/
             → uploaded to Cloudinary  signatures/<CLASS>/
             → Cloudinary URL stored in DB  (fallback: local path)
    """
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name are required."}), 400

    safe_base = secure_filename(name.replace(" ", "_"))

    # ── Save all 4 angle photos + signature synchronously ────────────────────
    # request.files is not accessible after the HTTP response, so all
    # file saves must happen before the background thread is spawned.

    ANGLES = ["front", "left", "right", "up"]
    face_files  = []   # list of (local_path, angle_label)
    photo_local = ""   # front photo path for display (students/ folder)

    for angle in ANGLES:
        key = f"photo_{angle}"
        if key in request.files:
            f = request.files[key]
            if f and f.filename and allowed(f.filename):
                ext        = os.path.splitext(secure_filename(f.filename))[1]
                face_path  = os.path.join(
                    _class_faces_dir(class_code),
                    f"{safe_base}_{angle}{ext}"
                )
                f.save(face_path)
                face_files.append((face_path, angle))
                if angle == "front":
                    # Also save to students/ folder for display
                    photo_local = os.path.join(
                        _class_students_dir(class_code), safe_base + ext
                    )
                    shutil.copy(face_path, photo_local)

    if not face_files:
        return jsonify({"error": "At least the front-facing photo is required."}), 400

    sig_local = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and f.filename and allowed(f.filename):
            ext       = os.path.splitext(secure_filename(f.filename))[1]
            sig_local = os.path.join(
                _class_signatures_dir(class_code), safe_base + "_sig" + ext
            )
            f.save(sig_local)

    # ── Offload encoding + Cloudinary + DB to background thread ───────────────
    threading.Thread(
        target = _register_bg,
        args   = (class_code, name, safe_base,
                  face_files, photo_local, sig_local, dict(form)),
        daemon = True,
    ).start()

    return jsonify({"status": "ok", "name": name})


# ══════════════════════════════════════════════════════════════════════════════
# CAMERA — start / stop / feed / present list
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/start_camera", methods=["POST"])
def api_local_start_camera():
    """
    Starts face encoding in a background thread and returns immediately.
    Frontend polls /api/local/load_progress until done=true,
    at which point the camera is already running.
    """
    global _load_progress

    if not CAMERA_ENABLED:
        return jsonify({"error": "Camera not available on this machine."}), 503

    data       = request.json or {}
    source_raw = data.get("source", "0")
    source     = int(source_raw) if str(source_raw) in ("0", "1") else source_raw

    class_code = data.get("class_code", "")
    section    = data.get("section", "")
    subject    = data.get("subject", "")
    email      = request.headers.get("X-Instructor-Email", "")

    if not class_code:
        return jsonify({"error": "class_code required"}), 400

    # Count faces so frontend can show total before encoding starts
    faces_dir  = _class_faces_dir(class_code)
    face_files = [
        f for f in os.listdir(faces_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ] if os.path.isdir(faces_dir) else []
    total = len(face_files)

    # Reset progress immediately — poll endpoint is correct from frame 1
    with _load_lock:
        _load_progress = {"loaded": 0, "total": total, "done": False, "error": None}

    session_meta = {
        "source":  source,
        "email":   email,
        "section": section,
        "subject": subject,
    }

    threading.Thread(
        target=_load_class_faces_bg,
        args=(class_code, session_meta),
        daemon=True
    ).start()

    return jsonify({"status": "loading", "total": total, "class_code": class_code})


@app.route("/api/local/load_progress")
def api_load_progress():
    """
    Polled by the frontend every 300 ms during face loading.
    Returns { loaded, total, done, error }.
    When done=true the camera is already running — frontend shows the feed.
    """
    with _load_lock:
        return jsonify(dict(_load_progress))


@app.route("/api/local/stop_camera", methods=["POST"])
def api_local_stop_camera():
    global _camera_active
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify({"scan_log": {}})
    try:
        scan_log = recognizer.get_scan_log()
        recognizer.stop_and_reset()
        _camera_active = False
        return jsonify({"status": "ok", "scan_log": scan_log})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/video_feed")
def video_feed():
    if not CAMERA_ENABLED or recognizer is None or not _camera_active:
        return Response(b"", mimetype="multipart/x-mixed-replace; boundary=frame")
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/local/present_students")
def api_local_present():
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify([])
    return jsonify(recognizer.get_present_students())


@app.route("/api/local/scan_log")
def api_local_scan_log():
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify({})
    return jsonify(recognizer.get_scan_log())


# ══════════════════════════════════════════════════════════════════════════════
# LIVE CHECK-IN — staging row (session_time = 'LIVE')
# Identical logic to main app.py so Render sees the same data pattern
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/live_checkin", methods=["POST"])
def api_live_checkin():
    data       = request.json or {}
    name       = data.get("name", "").replace("_", " ").strip()
    class_code = data.get("class_code", "").strip()
    section    = data.get("section", "").strip()
    subject    = data.get("subject", "").strip()
    timestamp  = data.get("timestamp", "")
    status     = data.get("status", "Present")
    today      = date.today().isoformat()

    if not name or not class_code:
        return jsonify({"error": "name and class_code required"}), 400

    try:
        sr_code = ""
        for s in db.get_students(class_code):
            if s["name"].strip().lower() == name.lower():
                sr_code = s.get("sr_code", "") or ""
                break

        conn = db.get_db()
        cur  = db.get_cursor(conn)
        cur.execute(
            "SELECT id FROM attendance WHERE class_code=%s AND name=%s AND date=%s AND session_time='LIVE' LIMIT 1",
            (class_code, name, today)
        )
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"status": "already_recorded"}), 200

        full_ts = f"{today} {timestamp}" if timestamp else None
        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date, session_time)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'LIVE')""",
            (class_code, sr_code, name, section, subject, status, full_ts, today)
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "ok", "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# SAVE ATTENDANCE — purge LIVE rows → write permanent records
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/save_attendance", methods=["POST"])
def api_local_save_attendance():
    data         = request.json or {}
    today        = date.today().isoformat()
    class_code   = data.get("class_code", "")
    section      = data.get("section", "")
    subject      = data.get("subject", "")
    session_time = data.get("session_time", datetime.now().strftime("%H:%M:%S"))
    records      = data.get("records", [])

    if not class_code:
        return jsonify({"error": "class_code required"}), 400

    # 1 — Purge LIVE staging rows
    try:
        conn = db.get_db()
        cur  = db.get_cursor(conn)
        cur.execute(
            "DELETE FROM attendance WHERE class_code=%s AND date=%s AND session_time='LIVE'",
            (class_code, today)
        )
        purged = cur.rowcount
        conn.commit(); cur.close(); conn.close()
        if purged:
            print(f"[LOCAL SAVE] Purged {purged} LIVE row(s) for {class_code}")
    except Exception as e:
        print(f"[LOCAL SAVE] LIVE purge warning: {e}")

    # 2 — Write permanent records
    try:
        db.save_attendance(
            class_code   = class_code,
            section      = section,
            subject      = subject,
            records      = records,
            session_time = session_time,
        )
    except Exception as e:
        return jsonify({"error": f"Save failed: {e}"}), 500

    if recognizer:
        recognizer.reset_attendance()

    present_cnt = sum(1 for r in records if r.get("status") == "Present")
    late_cnt    = sum(1 for r in records if r.get("status") == "Late")
    absent_cnt  = sum(1 for r in records if r.get("status") == "Absent")

    return jsonify({
        "status":      "ok",
        "present":     present_cnt,
        "late":        late_cnt,
        "absent":      absent_cnt,
        "session_time":session_time,
    })


# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURE SERVING (for web preview in local camera view)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/signature/<path:filename>")
def serve_signature(filename):
    """
    Serve signature images from class-scoped subfolders.
    Accepts both:
      /api/signature/BET-241/JohnDoe_sig.png   (new class-scoped path)
      /api/signature/JohnDoe_sig.png            (legacy flat path fallback)
    """
    # Sanitise — prevent path traversal
    parts     = [p for p in filename.replace("\\", "/").split("/") if p and p != ".."]
    safe_path = os.path.join("uploads", "signatures", *parts)

    if os.path.isfile(safe_path):
        directory = os.path.dirname(os.path.abspath(safe_path))
        fname     = os.path.basename(safe_path)
        return send_from_directory(directory, fname)

    # Flat fallback — search all class subfolders
    base_name = os.path.basename(filename)
    sig_root  = os.path.join(os.getcwd(), "uploads", "signatures")
    for root, dirs, files in os.walk(sig_root):
        if base_name in files:
            return send_from_directory(root, base_name)

    abort(404)


# ══════════════════════════════════════════════════════════════════════════════
# PORT RESOLUTION — tries 5000 → 5001 → 5002
# ══════════════════════════════════════════════════════════════════════════════

def _find_free_port(start=5000, attempts=3):
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start   # last resort — Flask will show the error


def _open_browser(port, delay=1.5):
    def _do():
        time.sleep(delay)
        webbrowser.open(f"http://127.0.0.1:{port}")
    threading.Thread(target=_do, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = _find_free_port()
    print(f"\n{'='*54}")
    print(f"  BatStateU Attendance  —  Local Station")
    print(f"  Running at: http://127.0.0.1:{port}")
    print(f"{'='*54}\n")
    _open_browser(port)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)