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
from flask import (
    Flask, request, jsonify, send_file,
    send_from_directory, Response, abort
)
from flask_cors import CORS
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf

# ── CAMERA ───────────────────────────────────────────────────────────────────
try:
    from face_recognition_a import FaceRecognizer, load_known_faces
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

for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

db.init_db()

# ── FACE RECOGNIZER STATE ────────────────────────────────────────────────────
if CAMERA_ENABLED:
    known_enc, known_names = load_known_faces("faces")
    recognizer = FaceRecognizer(known_enc, known_names)
else:
    known_enc, known_names, recognizer = [], [], None

_camera_active = False


def reload_recognizer():
    global known_enc, known_names, recognizer, _camera_active
    if not CAMERA_ENABLED:
        return
    known_enc, known_names = load_known_faces("faces")
    recognizer             = FaceRecognizer(known_enc, known_names)
    _camera_active         = False


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
    """Return classes that have a schedule matching today's weekday."""
    today = _today_abbr()
    scheduled_codes = {
        s["class_code"] for s in schedules
        if (s.get("day") or "").upper() == today
    }
    # Return all if none scheduled today (instructor may override)
    if not scheduled_codes:
        return classes, []
    today_classes = [c for c in classes if c.get("class_code") in scheduled_codes]
    today_scheds  = [s for s in schedules if s.get("class_code") in scheduled_codes]
    return today_classes, today_scheds


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

    return jsonify({
        "status": "ok",
        "email":  user["email"],
        "name":   user["name"],
    })


# ══════════════════════════════════════════════════════════════════════════════
# CLASSES — today-filtered, with offline cache fallback
# ══════════════════════════════════════════════════════════════════════════════

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

@app.route("/api/local/students/<class_code>")
def api_local_students(class_code):
    rows = db.get_students(class_code)
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT REGISTRATION — photo → /faces/, signature → /uploads/signatures/
# Also pushes student record to cloud (Neon) via db.add_student
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/register_student", methods=["POST"])
def api_local_register_student():
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name are required."}), 400

    # ── Photo ─────────────────────────────────────────────────────────────────
    photo_path = ""
    if "photo" in request.files:
        f = request.files["photo"]
        if f and f.filename and allowed(f.filename):
            ext        = os.path.splitext(secure_filename(f.filename))[1]
            safe_name  = secure_filename(name.replace(" ", "_") + ext)
            photo_path = os.path.join("uploads/students", safe_name)
            f.save(photo_path)
            face_path  = os.path.join("faces", safe_name)
            if not os.path.exists(face_path):
                shutil.copy(photo_path, face_path)
                reload_recognizer()

    # ── Signature ─────────────────────────────────────────────────────────────
    sig_path = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and f.filename and allowed(f.filename):
            fname    = secure_filename(f.filename)
            sig_path = os.path.join("uploads/signatures", fname)
            f.save(sig_path)

    # ── Save to DB (Neon via database.py) ────────────────────────────────────
    try:
        db.add_student(
            class_code = class_code,
            name       = name,
            address    = form.get("address", ""),
            number     = form.get("number", ""),
            sr_code    = form.get("sr_code", ""),
            age        = int(form.get("age") or 0),
            sex        = form.get("sex", ""),
            email      = form.get("email", ""),
            photo      = photo_path,
            signature  = sig_path,
        )
    except Exception as e:
        return jsonify({"error": f"DB error: {e}"}), 500

    return jsonify({"status": "ok", "name": name})


# ══════════════════════════════════════════════════════════════════════════════
# CAMERA — start / stop / feed / present list
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/local/start_camera", methods=["POST"])
def api_local_start_camera():
    global _camera_active, recognizer, known_enc, known_names

    if not CAMERA_ENABLED:
        return jsonify({"error": "Camera not available on this machine."}), 503

    data       = request.json or {}
    source_raw = data.get("source", "0")
    source     = int(source_raw) if source_raw in ("0", "1") else source_raw

    class_code = data.get("class_code", "")
    section    = data.get("section", "")
    subject    = data.get("subject", "")
    email      = request.headers.get("X-Instructor-Email", "")

    try:
        if _camera_active:
            recognizer.stop_and_reset()
        recognizer = FaceRecognizer(known_enc, known_names)
        recognizer.set_session(email, class_code, section, subject)
        recognizer.start(source)
        _camera_active = True
        return jsonify({"status": "ok", "source": str(source)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    sig_dir   = os.path.join(os.getcwd(), "uploads", "signatures")
    safe_name = os.path.basename(filename)
    if not safe_name:
        abort(404)
    return send_from_directory(sig_dir, safe_name)


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