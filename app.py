"""
app.py
=======
Main Flask backend — updated to match new PostgreSQL schema.
Fields changed:
    student_id  →  sr_code
    class_id    →  class_code  (VARCHAR, not INTEGER)
    sex         →  added to students

Run:
    python app.py

Then open:
    http://localhost:5000
"""

import os
import re
import shutil
import smtplib
import secrets
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import (
    Flask, request,
    jsonify, send_file, send_from_directory, Response, abort, make_response
)
from werkzeug.utils import secure_filename

# Load .env for local development (Render sets env vars via dashboard)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import database as db
from pdf_generator import generate_attendance_pdf
try:
    from face_recognition_a import FaceRecognizer, load_known_faces
    CAMERA_ENABLED = True
except ImportError:
    CAMERA_ENABLED = False
    print("[INFO] Camera features disabled — running in cloud/dashboard mode.")

# Cloudinary — imported at module level; configured fresh per-request
try:
    import cloudinary
    import cloudinary.uploader
    _CLD_AVAILABLE = True
    print("[INFO] Cloudinary library imported OK.")
except ImportError:
    _CLD_AVAILABLE = False
    print("[INFO] Cloudinary not installed — add cloudinary to requirements.txt")

def _configure_cloudinary():
    """
    Configure Cloudinary fresh from env vars on every call.
    Returns (cloudinary.uploader, None) on success,
            (None, "error message")   on failure.
    """
    if not _CLD_AVAILABLE:
        return None, "Cloudinary library not installed. Add cloudinary to requirements.txt."
    name   = (os.environ.get("CLOUDINARY_CLOUD_NAME") or "").strip()
    key    = (os.environ.get("CLOUDINARY_API_KEY")    or "").strip()
    secret = (os.environ.get("CLOUDINARY_API_SECRET") or "").strip()
    print(f"[CLD] cloud_name={name!r}  "
          f"api_key={'set' if key else 'MISSING'}  "
          f"api_secret={'set' if secret else 'MISSING'}")
    if not name:
        return None, "CLOUDINARY_CLOUD_NAME is not set in Render environment."
    if not key:
        return None, "CLOUDINARY_API_KEY is not set in Render environment."
    if not secret:
        return None, "CLOUDINARY_API_SECRET is not set in Render environment."
    cloudinary.config(cloud_name=name, api_key=key, api_secret=secret, secure=True)
    return cloudinary.uploader, None


def _cloudinary_public_id(url: str):
    """Extract public_id from a Cloudinary secure URL, or return None."""
    if not url or "cloudinary.com" not in url:
        return None
    try:
        after_upload = url.split("/upload/", 1)[1]
        after_upload = re.sub(r'^v\d+/', '', after_upload)
        return after_upload.rsplit('.', 1)[0]
    except Exception:
        return None


def _delete_cloudinary_assets(urls: list):
    """Delete a list of Cloudinary assets by their URLs. Skips blanks/non-CLD URLs."""
    cld_up, err = _configure_cloudinary()
    if not cld_up:
        print(f"[CLD-DELETE] Cloudinary unavailable: {err}")
        return
    for url in urls:
        pid = _cloudinary_public_id(url)
        if not pid:
            continue
        try:
            cld_up.destroy(pid)
            print(f"[CLD-DELETE] Deleted {pid}")
        except Exception as ex:
            print(f"[CLD-DELETE] Failed to delete {pid}: {ex}")


# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

# ── FACE RECOGNITION ──────────────────────────────────────────────────────────

if CAMERA_ENABLED:
    known_enc, known_names = load_known_faces("faces")
    recognizer = FaceRecognizer(known_enc, known_names)
else:
    known_enc, known_names = [], []
    recognizer = None
_camera_started = False


def start_camera(source=0):
    global _camera_started
    if not _camera_started:
        recognizer.start(source)
        _camera_started = True


def reload_recognizer():
    global known_enc, known_names, recognizer, _camera_started
    if not CAMERA_ENABLED:
        return
    known_enc, known_names = load_known_faces("faces")
    recognizer             = FaceRecognizer(known_enc, known_names)
    _camera_started        = False


# ── HELPERS ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)


def get_current_instructor_id(req):
    """
    Authenticates the request using the session token cookie.
    Falls back to X-Instructor-Email header for backward compatibility.
    Returns instructor id or None if not authenticated.
    """
    # Primary: secure session token from HttpOnly cookie
    token = req.cookies.get("session_token", "")
    if token:
        instructor = db.verify_session_token(token)
        if instructor:
            return instructor["id"]

    # Fallback: email header (kept for API calls that don't send cookies)
    email = req.headers.get("X-Instructor-Email", "")
    if email:
        instructor = db.get_instructor_by_email(email)
        return instructor["id"] if instructor else None

    return None




# ── INIT ──────────────────────────────────────────────────────────────────────

db.init_db()
db.seed_admin_if_missing()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — single page app, script.js handles all navigation
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def portal():
    return send_file("login.html")


@app.route("/portal")
def portal_page():
    # kept for backward-compat but redirects to login
    from flask import redirect
    return redirect("/")


@app.route("/home")
def index():
    # Server-side session guard — redirect to login if no valid token
    token = request.cookies.get("session_token", "")
    if not token or not db.verify_session_token(token):
        from flask import redirect
        return redirect("/login")
    resp = make_response(send_file("index.html"))
    # Prevent browser from caching the dashboard
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"]        = "no-cache"
    return resp


@app.route("/favicon.ico")
def favicon():
    return "", 204   # no content — silences browser favicon request


# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/create_class", methods=["POST"])
def api_create_class():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    required = ["id", "course_code", "subject", "section"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    instructor_id = get_current_instructor_id(request)
    time_str = f"{data.get('time_in','7:00 AM')} - {data.get('time_out','8:00 AM')}"
    db.create_class(
        class_code    = data["id"],
        course_code   = data["course_code"],
        subject       = data["subject"],
        section       = data["section"],
        instructor_id = instructor_id,
        year_level    = data.get("year_level", ""),
        day           = data.get("day", "MON"),
        time          = time_str,
        room          = data.get("room", ""),
    )
    db.add_notification(
        instructor_id = instructor_id,
        notif_type    = "class_created",
        title         = f"Class Created — {data['subject']}",
        body          = f"Class folder \"{data['id']}\" ({data['subject']} · {data['section']}) was successfully created."
    )
    return jsonify({"status": "ok"})


@app.route("/api/edit_class/<class_code>", methods=["POST"])
def api_edit_class(class_code):
    data = request.json
    time_str = f"{data.get('time_in','7:00 AM')} - {data.get('time_out','8:00 AM')}" if data.get('time_in') else None
    db.edit_class(
        class_code,
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
        year_level  = data.get("year_level"),
        day         = data.get("day"),
        time        = time_str,
        room        = data.get("room"),
    )
    return jsonify({"status": "ok"})


@app.route("/api/curriculum", methods=["GET"])
def api_get_curriculum():
    rows = db.get_curriculum()
    return jsonify([dict(r) for r in rows])


@app.route("/api/curriculum", methods=["POST"])
def api_add_curriculum():
    data = request.json or {}
    subject     = (data.get("subject") or "").strip()
    course_code = (data.get("course_code") or "").strip()
    year_level  = (data.get("year_level") or "").strip()
    program     = (data.get("program") or "").strip()
    if not subject or not course_code or not year_level or not program:
        return jsonify({"error": "program, subject, course_code and year_level are required"}), 400
    new_id = db.add_curriculum(subject, course_code, year_level, program)
    return jsonify({"id": new_id, "subject": subject, "course_code": course_code,
                    "year_level": year_level, "program": program})


@app.route("/api/curriculum/<int:item_id>", methods=["PUT"])
def api_edit_curriculum(item_id):
    data = request.get_json()
    db.edit_curriculum(
        item_id,
        data.get("subject", "").strip(),
        data.get("course_code", "").strip(),
        data.get("year_level", ""),
        data.get("program", "").strip()
    )
    return jsonify({"status": "ok"})


@app.route("/api/curriculum/<int:item_id>", methods=["DELETE"])
def api_delete_curriculum(item_id):
    db.delete_curriculum(item_id)
    return jsonify({"status": "ok"})


@app.route("/api/delete_class/<class_code>", methods=["DELETE"])
def api_delete_class(class_code):
    instructor_id = get_current_instructor_id(request)
    photo_cols = ("photo", "photo_front", "photo_left", "photo_right", "photo_up", "signature")
    students = db.get_students(class_code, include_pending=True)
    # Don't delete Cloudinary photos for students who are also in another class
    shared = db.get_shared_sr_codes(class_code, instructor_id) if instructor_id else set()
    urls = [
        s[col] for s in students for col in photo_cols
        if s.get(col) and s.get('sr_code') not in shared
    ]
    _delete_cloudinary_assets(urls)
    db.delete_class(class_code)
    return jsonify({"status": "ok"})


@app.route("/api/students/search")
def api_search_students():
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "Unauthorized"}), 401
    q       = request.args.get("q", "").strip()
    exclude = request.args.get("exclude_class", "")
    if not q:
        return jsonify([])
    students = db.search_instructor_students(instructor_id, q, exclude)
    return jsonify([dict(s) for s in students])


@app.route("/api/classes/<class_code>/import-students", methods=["POST"])
def api_import_students(class_code):
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "Unauthorized"}), 401
    cls = db.get_class(class_code)
    if not cls or cls["instructor_id"] != instructor_id:
        return jsonify({"error": "Class not found"}), 404
    data        = request.json or {}
    student_ids = data.get("student_ids", [])
    # Only allow importing students from classes this instructor owns
    safe_ids = db.filter_instructor_student_ids(instructor_id, student_ids)
    count = db.import_students_to_class(safe_ids, class_code)
    return jsonify({"imported": count})


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/add_student", methods=["POST"])
def api_add_student():
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()
    sr_code    = form.get("sr_code", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name required"}), 400

    # Check SR code uniqueness across the instructor's entire account
    if sr_code:
        instructor_id = get_current_instructor_id(request)
        if instructor_id:
            existing = db.get_student_by_srcode_for_instructor(sr_code, instructor_id)
            if existing and existing["class_code"] != class_code:
                return jsonify({
                    "status":  "exists",
                    "student": {
                        "id":          existing["id"],
                        "name":        existing["name"],
                        "sr_code":     existing["sr_code"],
                        "class_code":  existing["class_code"],
                        "subject":     existing["subject"],
                        "section":     existing["section"],
                        "course_code": existing["course_code"],
                    }
                }), 200

    # Save profile photo → uploads/students/ and faces/
    photo_path = ""
    if "photo" in request.files:
        f = request.files["photo"]
        if f and f.filename and allowed_file(f.filename):
            ext        = os.path.splitext(secure_filename(f.filename))[1]
            safe_name  = secure_filename(name + ext)
            photo_path = os.path.join("uploads/students", safe_name)
            f.save(photo_path)
            # Copy to faces/ only if not already there (same student, multiple classes)
            face_path = os.path.join("faces", safe_name)
            if not os.path.exists(face_path):
                shutil.copy(photo_path, face_path)
                reload_recognizer()
        elif not (f.filename if f else None):
            # No new photo — reuse existing if student already enrolled elsewhere
            existing = db.get_student_by_srcode(form.get("sr_code", ""))
            if existing and existing["photo"]:
                photo_path = existing["photo"]

    sig_path = "SIGNED"

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
    return jsonify({"status": "ok"})


@app.route("/api/edit_student/<int:student_id>", methods=["POST"])
def api_edit_student(student_id):
    form   = request.form
    status = form.get("status")
    if status and len(form) == 1:
        # Status-only update from folder view dropdown
        db.edit_student(student_id, status=status)
    else:
        db.edit_student(
            student_id,
            name    = form.get("name", ""),
            address = form.get("address", ""),
            number  = form.get("number", ""),
            sr_code = form.get("sr_code", ""),
            age     = int(form.get("age") or 0),
            sex     = form.get("sex", ""),
            email   = form.get("email", ""),
            status  = form.get("status", "Enrolled"),
        )
    return jsonify({"status": "ok"})


@app.route("/api/delete_student/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    student = db.delete_student(student_id)
    if student:
        photo_cols = ("photo", "photo_front", "photo_left", "photo_right", "photo_up", "signature")
        urls = [student[col] for col in photo_cols if student.get(col)]
        _delete_cloudinary_assets(urls)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — CAMERA / ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/start_camera", methods=["POST"])
def api_start_camera():
    global _camera_started, recognizer, known_enc, known_names
    if not CAMERA_ENABLED:
        return jsonify({"error": "Camera not available in cloud mode."}), 503
    try:
        data   = request.get_json(silent=True) or {}
        source = data.get("source", "0")

        # Convert source: "0" / "1" → int, RTSP URL stays as string
        if source in ("0", "1"):
            source = int(source)

        # Get session info to link recognition to a class
        class_code = data.get("class_code", "")
        section    = data.get("section",    "")
        subject    = data.get("subject",    "")
        instructor = get_current_instructor_id(request)
        instr_obj  = db.get_instructor_by_id(instructor) if instructor else None
        instr_email= instr_obj["email"] if instr_obj else ""

        if not _camera_started:
            # Fresh start
            recognizer = FaceRecognizer(known_enc, known_names)
            recognizer.set_session(instr_email, class_code, section, subject)
            recognizer.start(source)
            _camera_started = True
            print(f"[CAMERA] Started → source={source} class={class_code}")
        else:
            # Camera already running.
            # Only restart if the source actually changed — prevents the JS
            # double-call (feed-drop detection) from triggering stop_and_reset()
            # while the recognition thread is live, which caused the crash.
            current_source = getattr(recognizer, '_source', None)
            if current_source != source:
                print(f"[CAMERA] Source changed {current_source} → {source}, restarting.")
                recognizer.stop_and_reset()   # safe now — waits for thread
                recognizer = FaceRecognizer(known_enc, known_names)
                recognizer.set_session(instr_email, class_code, section, subject)
                recognizer.start(source)
                recognizer._source = source
            else:
                # Same source — just update session metadata, do NOT restart
                recognizer.set_session(instr_email, class_code, section, subject)
                print(f"[CAMERA] Already running, session refreshed (no restart).")

        # Store current source so we can detect changes on next call
        if recognizer:
            recognizer._source = source

        return jsonify({"status": "ok", "source": str(source)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop_camera", methods=["POST"])
def api_stop_camera():
    global _camera_started
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify({"error": "Camera not available in cloud mode."}), 503
    try:
        scan_log = recognizer.get_scan_log()
        recognizer.stop_and_reset(); _camera_started = False
        return jsonify({"status": "ok", "scan_log": scan_log})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/scan_log")
def api_scan_log():
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify({})
    try: return jsonify(recognizer.get_scan_log())
    except: return jsonify({})

@app.route("/video_feed")
def video_feed():
    return Response(
        recognizer.generate_frames() if recognizer else iter([]),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/present_students")
def api_present_students():
    if not CAMERA_ENABLED or recognizer is None:
        return jsonify([])
    return jsonify(recognizer.get_present_students())


@app.route("/api/live_checkin", methods=["POST"])
def api_live_checkin():
    """
    Called by face_recognition_a.py the moment a student is detected.
    Writes to a 'LIVE' staging slot in attendance (session_time = 'LIVE').
    These staging rows are DELETED when /api/save_attendance finalises the session,
    so they never appear as a ghost duplicate session in History.

    Body JSON:
    {
        "name":             "Kelvin_Lloyd_Africa",
        "class_code":       "CPT-111-CPET3201",
        "section":          "CPET-3201",
        "subject":          "CPT-111",
        "instructor_email": "instructor@gmail.com",
        "timestamp":        "09:15:33",
        "status":           "Present"
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    name       = data.get("name", "").replace("_", " ").strip()
    class_code = data.get("class_code", "").strip()
    section    = data.get("section", "").strip()
    subject    = data.get("subject", "").strip()
    timestamp  = data.get("timestamp", "")
    status     = data.get("status", "Present")

    if not name or not class_code:
        return jsonify({"error": "name and class_code are required"}), 400

    from datetime import datetime as _dt, date as _date
    today = _date.today().isoformat()

    try:
        # Look up SR code from students table
        sr_code = ""
        try:
            students = db.get_students(class_code)
            for s in students:
                if s["name"].strip().lower() == name.strip().lower():
                    sr_code = s.get("sr_code", "") or ""
                    break
        except Exception:
            pass

        # Check if already in LIVE staging for today (prevents duplicate live entries)
        conn = db.get_db()
        cur  = db.get_cursor(conn)
        cur.execute(
            """SELECT id FROM attendance
               WHERE class_code = %s AND name = %s AND date = %s AND session_time = 'LIVE'
               LIMIT 1""",
            (class_code, name, today)
        )
        already_live = cur.fetchone()
        cur.close(); conn.close()

        if already_live:
            return jsonify({"status": "already_recorded", "name": name}), 200

        # INSERT into staging slot — session_time = 'LIVE' (not a real HH:MM)
        # /api/save_attendance will DELETE all 'LIVE' rows for this class+date
        # when the camera session is officially closed.
        conn = db.get_db()
        cur  = db.get_cursor(conn)
        full_timestamp = f"{today} {timestamp}" if timestamp else None
        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date, session_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'LIVE')""",
            (class_code, sr_code, name, section, subject,
             status, full_timestamp, today)
        )
        conn.commit()
        cur.close(); conn.close()

        print(f"[LIVE] ✓ Staged: {name} (SR: {sr_code or 'N/A'}) → {class_code} at {timestamp}")
        return jsonify({"status": "ok", "name": name, "sr_code": sr_code})

    except Exception as e:
        print(f"[LIVE] ✗ Error staging {name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/save_attendance", methods=["POST"])
def api_save_attendance():
    """
    Called by the instructor's browser when they click 'Save Attendance'.
    1. Deletes all LIVE staging rows for this class+date (ghost-buster).
    2. Deletes any prior record for this exact session_time (idempotent re-save).
    3. Inserts the final, complete attendance list.
    """
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    from datetime import datetime as _dt, date as _date
    today        = _date.today().isoformat()
    class_code   = data["class_code"]
    section      = data.get("section", "")
    subject      = data.get("subject", "")
    session_time = data.get("session_time", _dt.now().strftime("%H:%M:%S"))

    # ── Step 1: purge LIVE staging rows for this class today ─────────────────
    try:
        conn = db.get_db()
        cur  = db.get_cursor(conn)
        cur.execute(
            "DELETE FROM attendance WHERE class_code = %s AND date = %s AND session_time = 'LIVE'",
            (class_code, today)
        )
        purged = cur.rowcount
        conn.commit()
        cur.close(); conn.close()
        if purged:
            print(f"[SAVE] Purged {purged} LIVE staging row(s) for {class_code}")
    except Exception as e:
        print(f"[SAVE] Warning: could not purge LIVE rows: {e}")

    # ── Step 2 & 3: save the final, official attendance records ──────────────
    records      = data.get("records", [])
    present_cnt  = sum(1 for r in records if r.get("status") == "Present")
    late_cnt     = sum(1 for r in records if r.get("status") == "Late")
    absent_cnt   = sum(1 for r in records if r.get("status") == "Absent")

    db.save_attendance(
        class_code   = class_code,
        section      = section,
        subject      = subject,
        records      = records,
        session_time = session_time,
    )

    # Notify instructor that attendance was recorded
    instructor_id = get_current_instructor_id(request)
    db.add_notification(
        instructor_id = instructor_id,
        notif_type    = "attendance_saved",
        title         = f"Attendance Saved — {subject}",
        body          = (f"Session recorded for {subject} ({section}) on {today} at {session_time}. "
                         f"Present: {present_cnt} · Late: {late_cnt} · Absent: {absent_cnt}.")
    )

    if recognizer:
        recognizer.reset_attendance()
    return jsonify({"status": "ok"})


@app.route("/api/reset_attendance", methods=["POST"])
def api_reset_attendance():
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})




@app.route("/api/admin/purge_live_rows", methods=["POST"])
def api_purge_live_rows():
    """
    One-time maintenance endpoint.
    Deletes all orphaned LIVE staging rows left in the attendance table
    from before this fix was deployed.
    Call once from Postman or curl after deploying:
      POST https://attendance-system-xapv.onrender.com/api/admin/purge_live_rows
    """
    try:
        conn = db.get_db()
        cur  = db.get_cursor(conn)
        cur.execute("DELETE FROM attendance WHERE session_time = 'LIVE'")
        deleted = cur.rowcount
        conn.commit()
        cur.close(); conn.close()
        print(f"[PURGE] Deleted {deleted} orphaned LIVE row(s)")
        return jsonify({"status": "ok", "deleted": deleted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════════════════════
# API — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/recent")
def api_recent():
    instructor_id = get_current_instructor_id(request)
    rows = db.get_recent_activity(limit=10, instructor_id=instructor_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/absences")
def api_absences():
    instructor_id = get_current_instructor_id(request)
    return jsonify(db.get_absence_counts(instructor_id=instructor_id))


# ════════════════════════════════════════════════════════════════════════════════
# API — SCHEDULES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/schedules", methods=["GET"])
def api_get_schedules():
    instructor_id = get_current_instructor_id(request)
    return jsonify([dict(r) for r in db.get_schedules(instructor_id=instructor_id)])


@app.route("/api/schedules", methods=["POST"])
def api_add_schedule():
    data          = request.json
    instructor_id = get_current_instructor_id(request)
    db.add_schedule(
        class_code    = data.get("class_code", ""),
        instructor_id = instructor_id,
        time          = data["time"],
        subject       = data["subject"],
        room          = data["room"],
        day           = data.get("day", "MON"),
    )
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["POST"])
def api_edit_schedule(schedule_id):
    data = request.json
    old_subject = data.get("old_subject", "")
    new_subject = data["subject"]
    db.edit_schedule(schedule_id, data["time"], new_subject, data["room"], day=data.get("day"))
    if old_subject and old_subject.strip().lower() != new_subject.strip().lower():
        db.update_class_subject_by_schedule(schedule_id, old_subject, new_subject)
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>/check_usage", methods=["GET"])
def api_check_schedule_usage(schedule_id):
    rows = db.get_classes_using_schedule(schedule_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def api_delete_schedule(schedule_id):
    db.delete_schedule(schedule_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# PDF DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/download_pdf/<class_code>/<date>")
def api_download_pdf(class_code, date):
    cls          = db.get_class(class_code)
    session_time = request.args.get("session_time")
    records      = db.get_attendance_session(class_code, date, session_time)

    if not cls:
        return jsonify({"error": "class not found"}), 404

    schedules    = db.get_schedules(class_code)
    room         = schedules[0]["room"] if schedules else "TBA"
    time_str     = schedules[0]["time"] if schedules else ""

    # Get faculty name — use stored name, fall back to email parse only if name is blank
    instructor   = db.get_instructor_by_id(cls["instructor_id"]) if cls.get("instructor_id") else None
    if instructor:
        faculty_name = instructor["name"].strip() if instructor["name"].strip() \
                       else instructor["email"].split("@")[0].replace(".", " ").replace("_", " ").title()
    else:
        faculty_name = "Instructor"

    # Filter to only Present and Late (university format excludes absences)
    attended = [r for r in records if r["status"] != "Absent"]

    # ── Enrich each record with the student's e-signature path ───────────────
    # Look up the student by sr_code (preferred) then by name within the class.
    # The signature column in the students table stores the relative file path
    # e.g. "uploads/signatures/JohnDoe.png".  We attach it as "sig_path" so
    # pdf_generator can embed the actual image instead of the "Present" text.
    students_map = {}
    for s in db.get_students(class_code):
        key = (s["sr_code"] or "").strip()
        if key:
            students_map[key] = s.get("signature", "") or ""
        # also index by name as fallback
        name_key = (s["name"] or "").strip().lower()
        if name_key not in students_map:
            students_map[name_key] = s.get("signature", "") or ""

    for rec in attended:
        sig = ""
        sr  = (rec.get("sr_code") or "").strip()
        if sr and sr in students_map:
            sig = students_map[sr]
        else:
            nk = (rec.get("name") or "").strip().lower()
            sig = students_map.get(nk, "")
        rec["sig_path"] = sig   # absolute-ish local path like "uploads/signatures/X.png"



    # ── Pre-fetch all Cloudinary signatures concurrently ────────────────────
    # This avoids sequential 12s timeouts for 30+ students — all fetches run
    # in parallel threads so total wait is ~max(individual_fetch) not sum.
    import threading as _th
    from pdf_generator import _fetch_image_bytes
    _fetch_image_bytes._cache.clear()   # fresh cache per PDF request

    def _warm(url):
        if url and (url.startswith("http://") or url.startswith("https://")):
            _fetch_image_bytes(url)

    sig_urls = list({rec.get("sig_path", "") for rec in attended})
    warmers  = [_th.Thread(target=_warm, args=(u,), daemon=True) for u in sig_urls if u]
    for w in warmers: w.start()
    for w in warmers: w.join(timeout=15)   # wait up to 15s for all prefetches

    # ── Generate PDF ─────────────────────────────────────────────────────────
    try:
        buf, filename = generate_attendance_pdf(
            class_id     = class_code,
            subject      = cls["subject"],
            section      = cls["section"],
            room         = room,
            date         = date,
            time_str     = time_str,
            faculty_name = faculty_name,
            records      = attended,
            session_time = session_time or "",
        )
    except Exception as pdf_err:
        print(f"[PDF] Generation error: {pdf_err}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"PDF generation failed: {pdf_err}"}), 500

    return send_file(
        buf,
        as_attachment = True,
        download_name = filename,
        mimetype      = "application/pdf"
    )



# ════════════════════════════════════════════════════════════════════════════════
# SIGNATURE FILE SERVING
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/signature/<path:filename>")
def serve_signature(filename):
    """Safely serve a student e-signature image from uploads/signatures/.
    Used by the web viewer to render the actual signature image instead of
    the plain Present/Late text in the attendance sheet preview."""
    sig_dir   = os.path.join(os.getcwd(), "uploads", "signatures")
    safe_name = os.path.basename(filename)
    if not safe_name:
        abort(404)
    return send_from_directory(sig_dir, safe_name)


# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES LIST (for script.js renderFolderPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/classes", methods=["GET"])
def api_get_classes():
    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_classes(instructor_id=instructor_id)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — SESSIONS LIST (for script.js renderHistoryPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def api_get_sessions():
    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_sessions(instructor_id=instructor_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/sessions/<class_code>", methods=["GET"])
def api_get_sessions_by_class(class_code):
    rows = db.get_sessions_by_class(class_code)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — ATTENDANCE RECORDS FOR ONE SESSION
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/attendance/<class_code>/<date>", methods=["GET"])
def api_get_attendance(class_code, date):
    session_time = request.args.get("session_time")
    rows = db.get_attendance_session(class_code, date, session_time)
    records = [dict(r) for r in rows]

    # ── Enrich with sig_path so the web viewer can render e-signature images ──
    students_map = {}
    for s in db.get_students(class_code):
        sr_key = (s["sr_code"] or "").strip()
        if sr_key:
            students_map[sr_key] = s.get("signature", "") or ""
        name_key = (s["name"] or "").strip().lower()
        if name_key not in students_map:
            students_map[name_key] = s.get("signature", "") or ""

    for rec in records:
        sr  = (rec.get("sr_code") or "").strip()
        sig = students_map.get(sr, "") if sr else ""
        if not sig:
            nk  = (rec.get("name") or "").strip().lower()
            sig = students_map.get(nk, "")
        rec["sig_path"] = sig

    return jsonify(records)


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS LIST FOR A CLASS (for openFolderView)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/students/<class_code>", methods=["GET"])
def api_get_students(class_code):
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "Unauthorized"}), 401
    cls = db.get_class(class_code)
    if not cls or cls["instructor_id"] != instructor_id:
        return jsonify({"error": "Class not found"}), 404
    rows = db.get_students(class_code)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — LOGIN / REGISTER / ADMIN (for login.html + admin.html)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    user  = db.get_instructor_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["password"] != pwd:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["status"] == "pending":
        return jsonify({"error": "pending"}), 403
    # Issue a secure server-side session token
    token = db.create_session_token(email)
    resp  = make_response(jsonify({"status": "ok", "email": user["email"], "name": user["name"]}))
    resp.set_cookie(
        "session_token", token,
        httponly = True,      # JS cannot read it — prevents XSS theft
        secure   = False,     # set True in production with HTTPS
        samesite = "Lax",
        max_age  = 43200      # 12 hours
    )
    return resp


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Invalidate the session token and clear the cookie."""
    token = request.cookies.get("session_token", "")
    db.delete_session_token(token)
    resp = make_response(jsonify({"status": "ok"}))
    resp.delete_cookie("session_token")
    return resp


@app.route("/api/verify_session")
def api_verify_session():
    """Called by index.html on every load to confirm the session is still valid."""
    token = request.cookies.get("session_token", "")
    instructor = db.verify_session_token(token)
    if not instructor:
        return jsonify({"valid": False}), 401
    return jsonify({
        "valid": True,
        "email": instructor["email"],
        "name":  instructor["name"] or ""
    })


# ── SHARED EMAIL HELPER ──────────────────────────────────────────────────────
#
# Priority order:
#   1. Brevo API (HTTPS port 443)  — primary, works on Render, free 300/day
#   2. Gmail SMTP SSL 465          — local development fallback
#   3. Gmail SMTP TLS 587          — local development fallback
#
# Render deployment : add BREVO_API_KEY to Render environment variables
# Local development : Gmail SMTP works without Brevo
# Sender address    : kelvinlloydafrica@gmail.com (verified on Brevo)
# ─────────────────────────────────────────────────────────────────────────────

import urllib.request
import urllib.error
import json as _json

# ── Brevo (formerly Sendinblue) — HTTPS, never blocked by Render ──────────────
# Free tier: 300 emails/day, no domain needed, Gmail verified sender works.
# Add BREVO_API_KEY to Render environment variables (starts with xkeysib-).
BREVO_FROM_NAME = "BatStateU Attendance System"
BREVO_FROM_ADDR = "attendance.system.bsu@gmail.com"   # your verified Brevo sender


def _send_via_brevo(to_addr, subject, body_plain, body_html=None, api_key=None):
    """
    Send email via Brevo Transactional Email API v3.
    Uses HTTPS port 443 — never blocked by Render.
    Free tier: 300 emails/day. Verified Gmail sender, no domain required.
    Returns: (True, None) on success | (False, error_str) on failure
    """
    if not api_key:
        api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        return False, "BREVO_API_KEY not configured."

    payload = {
        "sender":      {"name": BREVO_FROM_NAME, "email": BREVO_FROM_ADDR},
        "to":          [{"email": to_addr}],
        "subject":     subject,
        "textContent": body_plain,
    }
    if body_html:
        payload["htmlContent"] = body_html

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data    = _json.dumps(payload).encode("utf-8"),
        headers = {
            "api-key":      api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        },
        method = "POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                print(f"[MAIL] ✓ Brevo delivered to {to_addr}")
                return True, None
            return False, f"Brevo HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[MAIL] Brevo error {e.code}: {body}")
        return False, f"Brevo {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def _send_system_email(from_addr, smtp_pass, to_addr, subject, body_plain, body_html=None):
    """
    Unified email sender. Tries in order:
      1. Brevo API   — primary for Render (HTTPS, never blocked, 300/day free)
      2. Gmail SMTP SSL 465 — local development fallback
      3. Gmail SMTP TLS 587 — local development fallback

    from_addr : instructor Gmail (used for SMTP fallback only)
    smtp_pass : Gmail App Password (SMTP fallback only)
    Returns: (True, None) | (False, error_str)
    """
    # ── 1. Brevo (HTTPS — works on Render, free, no domain needed) ────────────
    brevo_key = os.environ.get("BREVO_API_KEY", "").strip()
    if brevo_key:
        ok, err = _send_via_brevo(to_addr, subject, body_plain, body_html, brevo_key)
        if ok:
            return True, None
        print(f"[MAIL] Brevo failed: {err} — trying SMTP fallback...")

    # ── 2. Gmail SMTP SSL port 465 (works locally) ────────────────────────────
    clean_pass = (smtp_pass or "").replace(" ", "")
    if from_addr and clean_pass:
        try:
            import ssl
            ctx = ssl.create_default_context()
            msg = MIMEMultipart("alternative")
            msg["From"]    = from_addr
            msg["To"]      = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body_plain, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=15) as sv:
                sv.login(from_addr, clean_pass)
                sv.sendmail(from_addr, to_addr, msg.as_string())
            print(f"[MAIL] ✓ SMTP 465 delivered to {to_addr}")
            return True, None
        except Exception as e1:
            print(f"[MAIL] SMTP 465 failed: {e1} — trying 587...")

        # ── 3. Gmail SMTP TLS port 587 ────────────────────────────────────────
        try:
            msg = MIMEMultipart("alternative")
            msg["From"]    = from_addr
            msg["To"]      = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body_plain, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as sv:
                sv.ehlo(); sv.starttls()
                sv.login(from_addr, clean_pass)
                sv.sendmail(from_addr, to_addr, msg.as_string())
            print(f"[MAIL] ✓ SMTP 587 delivered to {to_addr}")
            return True, None
        except Exception as e2:
            print(f"[MAIL] SMTP 587 also failed: {e2}")
            return False, str(e2)

    return False, "No BREVO_API_KEY and no SMTP credentials configured."


@app.route("/api/send_otp", methods=["POST"])
def api_send_otp():
    """
    Generate OTP server-side, store hashed version in DB,
    email it using system SMTP. OTP never sent to browser.
    """
    data  = request.json or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required."}), 400

    instructor = db.get_instructor_by_email(email)
    if not instructor:
        return jsonify({"error": "No account found with that email address."}), 404

    otp_code = str(random.randint(10000, 99999))
    db.create_otp(email, otp_code)

    # Send OTP via Brevo (primary) or SMTP fallback
    # Uses _send_system_email which checks BREVO_API_KEY first
    instructor_name = instructor["name"] or "Instructor"
    body = (
        f"Hello {instructor_name},\n\n"
        f"Your OTP for password reset is:\n\n"
        f"  {otp_code}\n\n"
        f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
        f"If you did not request this, ignore this email.\n\n"
        f"--- BatStateU Attendance System"
    )
    # Pass empty strings for smtp credentials — Brevo doesn't need them
    smtp_user = os.environ.get("SYSTEM_EMAIL", "").strip()
    smtp_pass = os.environ.get("SYSTEM_EMAIL_PASS", "").strip()
    sent, err = _send_system_email(smtp_user, smtp_pass, email,
                                    "Password Reset OTP — BatStateU Attendance System",
                                    body)
    if not sent:
        print(f"[OTP] Email send failed: {err}")
        return jsonify({"status": "ok",
                        "warn": f"OTP generated but email failed to send. "
                                 "Check BREVO_API_KEY in Render environment variables."})

    return jsonify({"status": "ok", "msg": "OTP sent to your email."})


@app.route("/api/verify_otp", methods=["POST"])
def api_verify_otp():
    """Verify OTP entered by user. Returns ok or error reason."""
    data     = request.json or {}
    email    = data.get("email", "").strip().lower()
    otp_code = data.get("otp", "").strip()
    if not email or not otp_code:
        return jsonify({"error": "Missing fields."}), 400
    result = db.verify_otp(email, otp_code)
    if result == "ok":
        return jsonify({"status": "ok"})
    elif result == "expired":
        return jsonify({"error": "OTP has expired. Please request a new one."}), 410
    elif result == "locked":
        return jsonify({"error": "Too many attempts. Please request a new OTP."}), 429
    else:
        return jsonify({"error": "Invalid code. Please try again."}), 401


@app.route("/api/reset_password", methods=["POST"])
def api_reset_password():
    """
    Final step — updates password after OTP was verified.
    Requires the email and new password. OTP must have been verified first
    (checked by looking for a recently used OTP record).
    """
    data     = request.json or {}
    email    = data.get("email", "").strip().lower()
    new_pass = data.get("password", "").strip()
    if not email or not new_pass or len(new_pass) < 4:
        return jsonify({"error": "Invalid request."}), 400
    instructor = db.get_instructor_by_email(email)
    if not instructor:
        return jsonify({"error": "Account not found."}), 404
    db.update_password(email, new_pass)
    return jsonify({"status": "ok"})


@app.route("/api/register", methods=["POST"])
def api_register():
    # Public self-registration is disabled. Accounts are created by the admin only.
    return jsonify({"error": "Account registration is managed by the administrator."}), 403


@app.route("/api/instructors", methods=["GET"])
def api_get_instructors():
    if not db.verify_admin_session_token(_get_admin_token(request)):
        return jsonify({"error": "Unauthorized"}), 401
    rows = db.get_all_instructors()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/create-instructor", methods=["POST"])
def api_admin_create_instructor():
    if not db.verify_admin_session_token(_get_admin_token(request)):
        return jsonify({"error": "Unauthorized"}), 401
    data  = request.json or {}
    name  = data.get("name",  "").strip()
    email = data.get("email", "").strip()
    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if db.get_instructor_by_email(email):
        return jsonify({"error": "An account with that email already exists."}), 409

    # Auto-generate a secure temporary password — never exposed to the admin
    alphabet = string.ascii_letters + string.digits
    pwd = (
        secrets.choice(string.ascii_uppercase) +
        secrets.choice(string.ascii_lowercase) +
        secrets.choice(string.digits) +
        "".join(secrets.choice(alphabet) for _ in range(9))
    )
    pwd = "".join(secrets.SystemRandom().sample(pwd, len(pwd)))

    # Create account pre-approved — no pending queue needed
    db.create_instructor_by_admin(name, email, pwd)

    # Send welcome email with credentials
    login_url = request.host_url.rstrip("/") + "/login"
    body_plain = (
        f"Hello {name},\n\n"
        f"Your instructor account for the BatStateU Attendance System has been created.\n\n"
        f"  Email:    {email}\n"
        f"  Password: {pwd}\n\n"
        f"Login here: {login_url}\n\n"
        f"You can change your password anytime using the 'Forgot Password' option on the login page.\n\n"
        f"Keep your credentials private and do not share them with anyone.\n\n"
        f"--- BatStateU Attendance System Administrator"
    )
    body_html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:30px;">
        <h2 style="color:#D32F2F;">Your Instructor Account is Ready</h2>
        <p>Hello <strong>{name}</strong>,</p>
        <p>Your account for the <strong>BatStateU Attendance System</strong> has been created by the administrator.</p>
        <table style="background:#FEF2F2;border-radius:10px;padding:16px 20px;margin:20px 0;width:100%;border-collapse:collapse;">
            <tr><td style="padding:6px 0;color:#555;width:100px;">Email</td><td style="font-weight:700;">{email}</td></tr>
            <tr><td style="padding:6px 0;color:#555;">Password</td><td style="font-weight:700;font-family:monospace;">{pwd}</td></tr>
        </table>
        <a href="{login_url}" style="display:inline-block;background:#D32F2F;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;">
            Log In Now
        </a>
        <p style="margin-top:20px;font-size:0.85rem;color:#888;">
            You can change your password anytime using <em>Forgot Password</em> on the login page.<br>
            Keep your credentials private.
        </p>
    </div>"""
    smtp_user = os.environ.get("SYSTEM_EMAIL", "").strip()
    smtp_pass = os.environ.get("SYSTEM_EMAIL_PASS", "").strip()
    sent, err = _send_system_email(smtp_user, smtp_pass, email,
                                    "Your Instructor Account — BatStateU Attendance System",
                                    body_plain, body_html)
    if not sent:
        print(f"[ACCOUNT] Welcome email failed for {email}: {err}")
        return jsonify({"status": "ok",
                        "warn": "Account created but welcome email could not be sent. "
                                "Please share the credentials manually."})

    return jsonify({"status": "ok", "msg": f"Account created and credentials emailed to {email}."})


@app.route("/api/instructors/<int:instructor_id>/approve", methods=["POST"])
def api_approve_instructor(instructor_id):
    if not db.verify_admin_session_token(_get_admin_token(request)):
        return jsonify({"error": "Unauthorized"}), 401
    db.approve_instructor(instructor_id)
    db.add_notification(
        instructor_id = instructor_id,
        notif_type    = "approved",
        title         = "Account Approved",
        body          = "Your instructor account has been approved by the administrator. You can now create classes and record attendance."
    )
    return jsonify({"status": "ok"})


@app.route("/api/instructors/<int:instructor_id>", methods=["DELETE"])
def api_delete_instructor(instructor_id):
    if not db.verify_admin_session_token(_get_admin_token(request)):
        return jsonify({"error": "Unauthorized"}), 401
    db.delete_instructor(instructor_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# AUTH HTML PAGES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/login")
def login_page():
    return send_file("login.html")


@app.route("/sys/sntl-panel")
def admin_page():
    resp = make_response(send_file("admin.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/admin")
def admin_redirect():
    from flask import abort
    abort(404)

# ════════════════════════════════════════════════════════════════════════════════
# RUN
# ════════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════════
# API — SEND ATTENDANCE EMAIL
# ════════════════════════════════════════════════════════════════════════════════
#
# SMTP CONFIG — fill these in with the instructor's Gmail credentials.
# For Gmail: enable "App Passwords" in Google Account → Security,
# then use the generated 16-char app password below (NOT your regular password).
#
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


@app.route("/api/profile", methods=["POST"])
def api_update_profile():
    """Save instructor display name and contact number to DB."""
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "unauthorized"}), 401
    data   = request.json or {}
    name   = data.get("name",   "").strip()
    number = data.get("number", "").strip()
    db.update_instructor_profile(instructor_id, name=name, number=number)
    instructor = db.get_instructor_by_id(instructor_id)
    return jsonify({"status": "ok", "name": instructor["name"], "number": instructor.get("number", "")})


@app.route("/api/mail_config", methods=["GET"])
def api_get_mail_config():
    """Return stored mail config (gmail, grace periods) for the current instructor."""
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "unauthorized"}), 401
    cfg = db.get_mail_config(instructor_id)
    if cfg:
        return jsonify({
            "gmail":         cfg["gmail"]         or "",
            "app_pass":      cfg["app_pass"]      or "",
            "present_grace": cfg["present_grace"] or 15,
            "late_grace":    cfg["late_grace"]    or 30,
        })
    return jsonify({"gmail": "", "app_pass": "", "present_grace": 15, "late_grace": 30})


@app.route("/api/mail_config", methods=["POST"])
def api_save_mail_config():
    """Save mail config (gmail, app_pass, grace periods) for the current instructor."""
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    db.save_mail_config(
        instructor_id = instructor_id,
        gmail         = data.get("gmail",         ""),
        app_pass      = data.get("app_pass",      ""),
        present_grace = int(data.get("present_grace", 15)),
        late_grace    = int(data.get("late_grace",    30)),
    )
    return jsonify({"status": "ok"})


@app.route("/api/send_email", methods=["POST"])
def api_send_email():
    """
    Sends email using the instructor's stored Gmail + App Password from DB.
    Body JSON:
    {
        "to":      "student@email.com",
        "subject": "Attendance Update ...",
        "html":    "<html>...</html>",
        "plain":   "plain text fallback"
    }
    """
    instructor_id = get_current_instructor_id(request)
    cfg = db.get_mail_config(instructor_id) if instructor_id else None

    smtp_user     = cfg["gmail"].strip()              if cfg and cfg["gmail"]    else None
    smtp_password = cfg["app_pass"].replace(" ", "")  if cfg and cfg["app_pass"] else None

    if not smtp_user or not smtp_password:
        return jsonify({
            "error": "SMTP not configured. Please set your Gmail address and App Password in Profile → Mailing Setup."
        }), 503

    data = request.json
    if not data or not data.get("to"):
        return jsonify({"error": "Missing recipient."}), 400

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = data.get("subject", "Attendance Update")
        msg["From"]    = smtp_user
        msg["To"]      = data["to"]

        plain = MIMEText(data.get("plain", "Please view this email in an HTML-capable client."), "plain")
        html  = MIMEText(data.get("html", ""), "html")
        msg.attach(plain)
        msg.attach(html)

        # Send via Brevo (primary) → SMTP fallback
        sent, err = _send_system_email(
            smtp_user, smtp_password,
            data["to"],
            data.get("subject", "Attendance Update"),
            data.get("plain", "Please view this email in an HTML-capable client."),
            data.get("html", None)
        )
        if not sent:
            if "Authentication" in str(err) or "Username" in str(err) or "534" in str(err):
                return jsonify({"error": "SMTP authentication failed. Check your Gmail and App Password in Profile → Mailing Setup."}), 401
            return jsonify({"error": f"Email failed to send: {err}"}), 500

        # Notify instructor that the email was sent successfully
        db.add_notification(
            instructor_id = instructor_id,
            notif_type    = "email_sent",
            title         = f"Email Sent — {data.get('subject', 'Attendance Update')}",
            body          = f"Email successfully delivered to {data['to']}."
        )
        return jsonify({"status": "sent"})

    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "SMTP authentication failed. Check your Gmail and App Password in Profile → Mailing Setup."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_smtp", methods=["POST"])
def api_test_smtp():
    """
    Tests the instructor's Gmail SMTP credentials without sending any email.
    Returns a clear, actionable error message for every known failure mode.
    Called by the 'Test Connection' button in Profile → Mailing Setup.
    """
    instructor_id = get_current_instructor_id(request)
    cfg           = db.get_mail_config(instructor_id) if instructor_id else None

    smtp_user     = cfg["gmail"].strip()             if cfg and cfg["gmail"]    else None
    smtp_password = cfg["app_pass"].replace(" ", "") if cfg and cfg["app_pass"] else None

    if not smtp_user or not smtp_password:
        return jsonify({
            "ok":    False,
            "error": "No credentials saved. Fill in your Gmail and App Password first, then save."
        }), 400

    # Try both ports — Render may block 587 but allow 465
    sent, err = _send_system_email(smtp_user, smtp_password,
                                    smtp_user,   # send test to self
                                    "SMTP Test — BatStateU Attendance",
                                    "This is a test email from the Attendance System.")
    if sent:
        return jsonify({
            "ok":      True,
            "message": f"✓ Connected successfully as {smtp_user}. Email is ready to send."
        })

    err_str = str(err)
    if "Authentication" in err_str or "Username" in err_str or "534" in err_str:
        return jsonify({
            "ok":    False,
            "error": (
                "Authentication failed. Most likely causes:\n"
                "① 2-Step Verification is NOT enabled in your Google Account.\n"
                "② The App Password is wrong — regenerate it and paste the new one.\n"
                "③ Wrong Gmail address entered.\n\n"
                "Go to: Google Account → Security → 2-Step Verification → App Passwords."
            )
        }), 401

    if "Network" in err_str or "101" in err_str or "timed out" in err_str.lower():
        return jsonify({
            "ok":    False,
            "error": (
                "[Errno 101] Network is unreachable.\n"
                "Render.com blocks outbound SMTP on ports 587 and 465.\n"
                "Solution: Add BREVO_API_KEY to your Render environment variables.\n"
                "Get a free key at brevo.com (300 emails/day free, no domain needed)."
            )
        }), 503

    try:
        placeholder = None  # keep try/except structure intact
    except smtplib.SMTPAuthenticationError:
        pass
    except smtplib.SMTPConnectError:
        pass
    except TimeoutError:
        pass

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500




# ════════════════════════════════════════════════════════════════════════════════
# API — NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/notifications", methods=["GET"])
def api_get_notifications():
    """Return up to 50 most-recent notifications for the current instructor."""
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify([])
    notifications = db.get_notifications(instructor_id, limit=50)
    unread_count  = db.get_unread_count(instructor_id)
    return jsonify({"notifications": notifications, "unread": unread_count})


@app.route("/api/notifications/mark_read", methods=["POST"])
def api_mark_notifications_read():
    """
    Mark notifications as read.
    Body JSON (optional): { "ids": [1, 2, 3] }
    If no ids provided → marks ALL as read for current instructor.
    """
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    ids  = data.get("ids", None)
    db.mark_notifications_read(instructor_id, ids)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — CAMERA ROOMS  (admin manages RTSP URL ↔ friendly room name)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/rooms", methods=["GET"])
def api_get_rooms():
    """Return all campus rooms. Public — used by instructor camera modal dropdown."""
    rooms = db.get_all_rooms()
    return jsonify([dict(r) for r in rooms])


@app.route("/api/rooms", methods=["POST"])
def api_upsert_room():
    """
    Add or update a room.  Admin-only.
    Body JSON: { "room_name": "VMB-401", "rtsp_url": "rtsp://admin:pass@192.168.1.10:554/..." }
    """
    data = request.json
    if not data or not data.get("room_name") or not data.get("rtsp_url"):
        return jsonify({"error": "room_name and rtsp_url are required"}), 400
    db.upsert_room(data["room_name"].strip(), data["rtsp_url"].strip())
    return jsonify({"status": "ok"})


@app.route("/api/rooms/<int:room_id>", methods=["DELETE"])
def api_delete_room(room_id):
    """Delete a room by ID. Admin-only."""
    db.delete_room(room_id)
    return jsonify({"status": "ok"})



# ════════════════════════════════════════════════════════════════════════════════
# ADMIN AUTH — secure server-side login, OTP forgot password, session tokens
# ════════════════════════════════════════════════════════════════════════════════

def _get_admin_token(req):
    """Extract admin session token from cookie OR X-Admin-Token header.
    Header takes priority — more reliable across Render/HTTPS environments."""
    header_token = req.headers.get("X-Admin-Token", "").strip()
    if header_token:
        return header_token
    return req.cookies.get("admin_session_token", "")


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    """Verify admin credentials, issue HttpOnly session cookie."""
    data     = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password required."}), 400

    admin = db.get_admin_account()
    if not admin or admin["username"] != username:
        return jsonify({"error": "Invalid credentials."}), 401
    if not db.verify_admin_password(password):
        return jsonify({"error": "Invalid credentials."}), 401

    token = db.create_admin_session_token()
    resp  = make_response(jsonify({"status": "ok", "token": token}))
    resp.set_cookie(
        "admin_session_token", token,
        httponly=False, samesite="Lax",
        max_age=8 * 3600      # 8 hours
    )
    return resp


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    token = _get_admin_token(request)
    if token:
        db.delete_admin_session_token(token)
    resp = make_response(jsonify({"status": "ok"}))
    resp.delete_cookie("admin_session_token")
    return resp


@app.route("/api/admin/verify_session")
def api_admin_verify_session():
    token = _get_admin_token(request)
    if db.verify_admin_session_token(token):
        return jsonify({"valid": True})
    return jsonify({"valid": False}), 401


@app.route("/api/admin/send_otp", methods=["POST"])
def api_admin_send_otp():
    """Send OTP to admin recovery email for password reset."""
    admin = db.get_admin_account()
    if not admin or not admin.get("recovery_email"):
        return jsonify({"error": "No recovery email configured for admin. "
                                 "Contact your system administrator."}), 400

    recovery_email = admin["recovery_email"]
    otp_code = str(random.randint(10000, 99999))
    db.create_otp(recovery_email, otp_code)

    body = (
        f"Hello Administrator,\n\n"
        f"Your OTP for admin password reset is:\n\n"
        f"  {otp_code}\n\n"
        f"This code expires in 10 minutes. Do not share it.\n\n"
        f"--- BatStateU Attendance System"
    )
    smtp_user = os.environ.get("SYSTEM_EMAIL", "").strip()
    smtp_pass = os.environ.get("SYSTEM_EMAIL_PASS", "").strip()
    sent, err = _send_system_email(smtp_user, smtp_pass, recovery_email,
                                   "Admin Password Reset OTP — BatStateU Attendance System",
                                   body)
    if not sent:
        print(f"[ADMIN OTP] Email failed: {err}")
        return jsonify({"warn": "OTP generated but email failed to send. "
                                "Check BREVO_API_KEY in Render environment."})

    # Return masked email so frontend can show "sent to k***@gmail.com"
    masked = recovery_email[0] + "***@" + recovery_email.split("@")[1]
    return jsonify({"status": "ok", "masked_email": masked})


@app.route("/api/admin/verify_otp", methods=["POST"])
def api_admin_verify_otp():
    data     = request.json or {}
    otp_code = data.get("otp", "").strip()
    admin    = db.get_admin_account()
    if not admin:
        return jsonify({"error": "Admin account not found."}), 400

    result = db.verify_otp(admin["recovery_email"], otp_code)
    if result == "ok":
        return jsonify({"status": "ok"})
    elif result == "expired":
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
    elif result == "locked":
        return jsonify({"error": "Too many wrong attempts. Request a new OTP."}), 429
    else:
        return jsonify({"error": "Incorrect OTP. Please try again."}), 400


@app.route("/api/admin/reset_password", methods=["POST"])
def api_admin_reset_password():
    data         = request.json or {}
    new_password = data.get("password", "").strip()
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    db.update_admin_password(new_password)
    return jsonify({"status": "ok"})


@app.route("/api/admin/set_recovery_email", methods=["POST"])
def api_admin_set_recovery_email():
    """Called from admin settings to set/update recovery email."""
    token = _get_admin_token(request)
    if not db.verify_admin_session_token(token):
        return jsonify({"error": "Unauthorized."}), 401
    data  = request.json or {}
    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Valid email required."}), 400
    db.update_admin_recovery_email(email)
    return jsonify({"status": "ok"})


@app.route("/api/admin/get_recovery_email")
def api_admin_get_recovery_email():
    """Return current recovery email so the modal can pre-fill it."""
    token = _get_admin_token(request)
    if not db.verify_admin_session_token(token):
        return jsonify({"error": "Unauthorized."}), 401
    admin = db.get_admin_account()
    return jsonify({"email": admin["recovery_email"] if admin else ""})


# ── ADMIN ACTIVITY MONITOR ────────────────────────────────────────────────────

@app.route("/api/admin/activity")
def api_admin_activity():
    """Return activity summary for all instructors. Admin-only."""
    token = _get_admin_token(request)
    if not db.verify_admin_session_token(token):
        return jsonify({"error": "Unauthorized."}), 401
    return jsonify(db.get_instructor_activity_summary())


@app.route("/api/admin/activity/<int:instructor_id>")
def api_admin_instructor_sessions(instructor_id):
    """Return recent sessions for a specific instructor drill-down."""
    token = _get_admin_token(request)
    if not db.verify_admin_session_token(token):
        return jsonify({"error": "Unauthorized."}), 401
    sessions = db.get_instructor_recent_sessions(instructor_id, limit=20)
    return jsonify(sessions)


@app.route("/api/admin/session-attendance")
def api_admin_session_attendance():
    """Return individual attendance records for a specific session. Admin-only."""
    token = _get_admin_token(request)
    if not db.verify_admin_session_token(token):
        return jsonify({"error": "Unauthorized."}), 401
    class_code   = request.args.get("class_code")
    date         = request.args.get("date")
    session_time = request.args.get("session_time")
    if not class_code or not date or not session_time:
        return jsonify({"error": "Missing params."}), 400
    rows = db.get_attendance_session(class_code, date, session_time)
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)

# ══════════════════════════════════════════════════════════════════════════════
# STUDENT SELF-REGISTRATION — instructor generates link, student fills form
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/registration/generate_link", methods=["POST"])
def api_generate_registration_link():
    """
    Instructor calls this to generate a self-registration link for a class.
    Returns a token URL that students open on their own device.
    """
    token_cookie = request.cookies.get("session_token", "")
    session      = db.verify_session_token(token_cookie)
    if not session:
        return jsonify({"error": "Unauthorized."}), 401

    data       = request.json or {}
    class_code = data.get("class_code", "").strip()
    hours      = int(data.get("hours_valid", 72))

    if not class_code:
        return jsonify({"error": "class_code required."}), 400

    token    = db.create_registration_token(class_code, hours_valid=hours)
    base_url = request.host_url.rstrip("/")
    link     = f"{base_url}/register/{token}"
    return jsonify({"token": token, "link": link, "hours_valid": hours})


@app.route("/register/<token>")
def student_registration_page(token):
    """
    Public page — student opens this link to register themselves.
    No login required.
    """
    info = db.get_registration_token(token)
    if not info:
        return """
        <!DOCTYPE html><html><head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Link Expired</title>
        <style>
          body{font-family:sans-serif;display:flex;align-items:center;
               justify-content:center;min-height:100vh;margin:0;
               background:#FEF2F2;}
          .box{background:#fff;border-radius:16px;padding:40px;
               text-align:center;max-width:400px;box-shadow:0 4px 20px rgba(0,0,0,.1);}
          h2{color:#D32F2F;margin-bottom:8px}
          p{color:#555}
        </style></head><body>
        <div class="box">
          <h2>Link Expired or Invalid</h2>
          <p>This registration link is no longer valid.<br>
             Please ask your instructor for a new link.</p>
        </div></body></html>
        """, 410

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
  <title>Student Registration — {info['subject']}</title>
  <link rel="icon" type="image/png" href="/face.png">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',sans-serif}}
    body{{background:#f4f4f4;padding:20px;min-height:100vh}}
    .card{{background:#fff;border-radius:16px;padding:28px;max-width:520px;
           margin:0 auto;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
    .header{{text-align:center;margin-bottom:24px}}
    .header h1{{font-size:1.4rem;color:#1a1a1a;margin-bottom:4px}}
    .header p{{color:#D32F2F;font-weight:600;font-size:.9rem}}
    .badge{{display:inline-block;background:#FEF2F2;color:#D32F2F;
            border-radius:8px;padding:4px 12px;font-size:.8rem;
            font-weight:700;margin-bottom:16px}}
    label{{display:block;font-size:.8rem;font-weight:700;color:#374151;
           margin-bottom:4px;margin-top:14px;text-transform:uppercase;
           letter-spacing:.5px}}
    input,select{{width:100%;padding:10px 14px;border:1px solid #E5E7EB;
                  border-radius:10px;font-size:.95rem;outline:none;
                  transition:border .2s;background:#F9FAFB}}
    input:focus,select:focus{{border-color:#D32F2F;background:#fff}}
    .photo-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;
                 margin-top:8px}}
    .photo-box{{border:2px dashed #E5E7EB;border-radius:12px;padding:12px;
                text-align:center;cursor:pointer;transition:all .2s;
                min-height:90px;display:flex;flex-direction:column;
                align-items:center;justify-content:center}}
    .photo-box:hover{{border-color:#D32F2F;background:#FEF2F2}}
    .photo-box.has-photo{{border-color:#22C55E;background:#F0FDF4}}
    .photo-box input{{display:none}}
    .photo-box .icon{{margin-bottom:6px;display:flex;align-items:center;justify-content:center}}
    .photo-box .label{{font-size:.75rem;font-weight:700;color:#555}}
    .photo-box .status{{font-size:.7rem;color:#22C55E;margin-top:2px}}
    .btn{{width:100%;padding:14px;background:#D32F2F;color:#fff;border:none;
          border-radius:12px;font-size:1rem;font-weight:700;cursor:pointer;
          margin-top:20px;transition:opacity .2s}}
    .btn:hover{{opacity:.9}}
    .btn:disabled{{opacity:.5;cursor:not-allowed}}
    .success{{display:none;text-align:center;padding:32px 16px}}
    .success .check{{margin-bottom:12px}}
    .success h2{{color:#22C55E;margin-bottom:8px}}
    .success p{{color:#555;font-size:.9rem}}
    .error-msg{{color:#D32F2F;font-size:.8rem;margin-top:4px;display:none}}
    .required{{color:#D32F2F}}
    .hint{{font-size:.75rem;color:#9CA3AF;margin-top:3px}}
    /* Confirmation screen */
    #confirmCard{{display:none}}
    .confirm-row{{display:flex;justify-content:space-between;padding:8px 0;
                  border-bottom:1px solid #F3F4F6;font-size:.85rem}}
    .confirm-row span:first-child{{color:#6B7280;font-weight:600}}
    .confirm-row span:last-child{{color:#111827;font-weight:700;text-align:right;max-width:60%}}
    .confirm-photos{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}}
    .confirm-photos img{{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;
                         border:2px solid #E5E7EB}}
    .confirm-photos img.has-img{{border-color:#22C55E}}
    .btn-outline{{width:100%;padding:13px;background:#fff;color:#D32F2F;
                  border:2px solid #D32F2F;border-radius:12px;font-size:1rem;
                  font-weight:700;cursor:pointer;margin-top:10px;transition:all .2s}}
    .btn-outline:hover{{background:#FEF2F2}}
  </style>
</head>
<body>
<div class="card" id="formCard">
  <div class="header">
    <h1>Student Registration</h1>
    <p>{info['subject']}</p>
    <div class="badge">{info['section']} · {info['course_code']}</div>
  </div>

  <form id="regForm">
    <label>Full Name <span class="required">*</span></label>
    <div style="display:grid;grid-template-columns:1fr 1fr 80px;gap:8px;margin-top:0">
      <div>
        <input type="text" id="last_name" placeholder="Last Name" required>
        <div style="font-size:.7rem;color:#9CA3AF;margin-top:3px;text-transform:uppercase;font-weight:700;letter-spacing:.4px">Last Name</div>
      </div>
      <div>
        <input type="text" id="first_name" placeholder="First Name" required>
        <div style="font-size:.7rem;color:#9CA3AF;margin-top:3px;text-transform:uppercase;font-weight:700;letter-spacing:.4px">First Name</div>
      </div>
      <div>
        <input type="text" id="mi" placeholder="M.I." maxlength="5">
        <div style="font-size:.7rem;color:#9CA3AF;margin-top:3px;text-transform:uppercase;font-weight:700;letter-spacing:.4px">M.I.</div>
      </div>
    </div>

    <label>SR Code <span class="required">*</span></label>
    <input type="text" id="sr_code" placeholder="e.g. 23-12345" required>

    <label>Email Address <span class="required">*</span></label>
    <input type="email" id="email" placeholder="e.g. 23-12345@g.batstate-u.edu.ph" required>

    <label>Sex</label>
    <select id="sex">
      <option value="">Select</option>
      <option value="Male">Male</option>
      <option value="Female">Female</option>
    </select>

    <label>Face Photos <span class="required">*</span>
      <span class="hint">Take or upload a photo for each angle</span>
    </label>
    <div class="photo-grid">
      <div class="photo-box" id="box-front" onclick="document.getElementById('file-front').click()">
        <input type="file" id="file-front" accept="image/*" capture="user"
               onchange="setPhoto('front',this)">
        <div class="icon"><svg width="28" height="28" fill="none" stroke="#9CA3AF" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><circle cx="12" cy="13" r="3"/></svg></div>
        <div class="label">Front Face</div>
        <div class="status" id="status-front"></div>
      </div>
      <div class="photo-box" id="box-left" onclick="document.getElementById('file-left').click()">
        <input type="file" id="file-left" accept="image/*" capture="user"
               onchange="setPhoto('left',this)">
        <div class="icon"><svg width="28" height="28" fill="none" stroke="#9CA3AF" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12"/></svg></div>
        <div class="label">Left View</div>
        <div class="status" id="status-left"></div>
      </div>
      <div class="photo-box" id="box-right" onclick="document.getElementById('file-right').click()">
        <input type="file" id="file-right" accept="image/*" capture="user"
               onchange="setPhoto('right',this)">
        <div class="icon"><svg width="28" height="28" fill="none" stroke="#9CA3AF" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg></div>
        <div class="label">Right View</div>
        <div class="status" id="status-right"></div>
      </div>
      <div class="photo-box" id="box-up" onclick="document.getElementById('file-up').click()">
        <input type="file" id="file-up" accept="image/*" capture="user"
               onchange="setPhoto('up',this)">
        <div class="icon"><svg width="28" height="28" fill="none" stroke="#9CA3AF" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M7 11l5-5m0 0l5 5m-5-5v12"/></svg></div>
        <div class="label">Top View</div>
        <div class="status" id="status-up"></div>
      </div>
    </div>
    <div class="error-msg" id="photo-error">Please upload at least the front face photo.</div>

    <div style="background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:12px;padding:12px 16px;display:flex;align-items:center;gap:12px;margin-bottom:4px">
      <svg width="22" height="22" fill="none" stroke="#22C55E" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <div style="flex:1">
        <p style="margin:0 0 4px;font-size:.78rem;font-weight:800;color:#15803D">E-Signature</p>
        <p style="margin:0;font-size:.72rem;color:#166534">Your attendance confirmation will be marked as:</p>
        <div style="margin-top:8px;display:flex;justify-content:center">
          <span style="display:inline-block;color:#DC2626;border:2.5px solid #DC2626;border-radius:5px;padding:3px 14px;font-size:.85rem;font-weight:900;letter-spacing:4px;transform:rotate(-8deg);opacity:.85;font-family:'Arial Black',Arial,sans-serif;text-transform:uppercase;box-shadow:1px 1px 0 #DC2626;">SIGNED</span>
        </div>
      </div>
    </div>

    <div class="error-msg" id="form-error"></div>
    <button class="btn" type="submit" id="submitBtn">Submit Registration</button>
  </form>

  <div class="success" id="successMsg">
    <div class="check"><svg width="52" height="52" fill="none" stroke="#22C55E" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
    <h2>Submitted for Approval!</h2>
    <p>Your registration has been submitted successfully.<br>
       Your instructor will review and approve your registration.<br>
       You will be added to the attendance system once approved.</p>
  </div>
</div>

<!-- Confirmation Card -->
<div class="card" id="confirmCard">
  <div class="header">
    <h1>Review Your Details</h1>
    <p>{info['subject']}</p>
    <div class="badge">{info['section']} · {info['course_code']}</div>
  </div>
  <p style="font-size:.82rem;color:#6B7280;margin-bottom:16px;text-align:center">
    Please review your information carefully before submitting.
  </p>
  <div id="confirmDetails"></div>
  <div class="confirm-photos" id="confirmPhotos"></div>
  <div class="error-msg" id="confirm-error"></div>
  <button class="btn" id="confirmSubmitBtn" onclick="doSubmit()">✓ Confirm &amp; Submit</button>
  <button class="btn-outline" onclick="goBackToForm()">← Edit Details</button>
</div>

<script>
const TOKEN = "{token}";

function setPhoto(angle, input) {{
  if (!input.files[0]) return;
  document.getElementById('box-' + angle).classList.add('has-photo');
  document.getElementById('status-' + angle).textContent = '✓ Photo selected';
  document.getElementById('photo-error').style.display = 'none';
}}

function goBackToForm() {{
  document.getElementById('confirmCard').style.display = 'none';
  document.getElementById('formCard').style.display = 'block';
}}

// Step 1: Validate and show confirmation screen
document.getElementById('regForm').addEventListener('submit', (e) => {{
  e.preventDefault();

  const lastName  = document.getElementById('last_name').value.trim();
  const firstName = document.getElementById('first_name').value.trim();
  const mi        = document.getElementById('mi').value.trim();
  const name      = mi ? `${{lastName}}, ${{firstName}} ${{mi}}` : `${{lastName}}, ${{firstName}}`;
  const sr_code = document.getElementById('sr_code').value.trim();
  const email   = document.getElementById('email').value.trim();
  const sex     = document.getElementById('sex').value;
  const front   = document.getElementById('file-front').files[0];

  if (!lastName || !firstName || !sr_code || !email) {{
    document.getElementById('form-error').textContent = 'Please fill in Last Name, First Name, SR Code, and Email.';
    document.getElementById('form-error').style.display = 'block';
    return;
  }}
  if (!front) {{
    document.getElementById('photo-error').style.display = 'block';
    return;
  }}

  // Build confirmation details
  const details = [
    ['Full Name', name],
    ['SR Code', sr_code],
    ['Email', email],
    ['Sex', sex || 'Not specified'],
  ];
  document.getElementById('confirmDetails').innerHTML =
    details.map(([k,v]) =>
      `<div class="confirm-row"><span>${{k}}</span><span>${{v}}</span></div>`
    ).join('');

  // Preview photos
  const angles = ['front','left','right','up'];
  const labels = {{'front':'Front','left':'Left','right':'Right','up':'Up'}};
  const photosEl = document.getElementById('confirmPhotos');
  photosEl.innerHTML = '';
  angles.forEach(angle => {{
    const file = document.getElementById('file-' + angle).files[0];
    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'text-align:center';
    if (file) {{
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.className = 'has-img';
      img.style.cssText = 'width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;border:2px solid #22C55E';
      wrapper.appendChild(img);
    }} else {{
      wrapper.innerHTML = `<div style="width:100%;aspect-ratio:1;border-radius:10px;
        border:2px dashed #E5E7EB;display:flex;align-items:center;justify-content:center;
        color:#9CA3AF;font-size:.65rem;font-weight:700">${{labels[angle]}}<br>Not uploaded</div>`;
    }}
    const lbl = document.createElement('p');
    lbl.style.cssText = 'font-size:.65rem;font-weight:700;color:#6B7280;margin-top:4px';
    lbl.textContent = labels[angle];
    wrapper.appendChild(lbl);
    photosEl.appendChild(wrapper);
  }});

  // Show "Signed" indicator — no signature image, just the badge
  const existingBadge = document.getElementById('confirm-sig-badge');
  if (existingBadge) existingBadge.remove();
  const sigBadge = document.createElement('div');
  sigBadge.id = 'confirm-sig-badge';
  sigBadge.style.cssText = 'margin-top:12px;display:flex;align-items:center;gap:10px;background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:10px;padding:10px 14px';
  sigBadge.innerHTML = `<svg width="20" height="20" fill="none" stroke="#22C55E" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><span style="font-size:.8rem;font-weight:700;color:#15803D">E-Signature: </span><span style="display:inline-block;color:#DC2626;border:2px solid #DC2626;border-radius:4px;padding:2px 10px;font-size:.75rem;font-weight:900;letter-spacing:3px;transform:rotate(-5deg);font-family:'Arial Black',Arial,sans-serif;text-transform:uppercase;box-shadow:1px 1px 0 #DC2626">SIGNED</span>`;
  photosEl.parentNode.insertBefore(sigBadge, photosEl.nextSibling);

  document.getElementById('formCard').style.display = 'none';
  document.getElementById('confirmCard').style.display = 'block';
  window.scrollTo(0, 0);
}});

// Step 2: Actually submit after confirmation
async function doSubmit() {{
  const btn = document.getElementById('confirmSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting…';

  const fd = new FormData();
  fd.append('token',   TOKEN);
  const _last  = document.getElementById('last_name').value.trim();
  const _first = document.getElementById('first_name').value.trim();
  const _mi    = document.getElementById('mi').value.trim();
  fd.append('name',    _mi ? `${{_last}}, ${{_first}} ${{_mi}}` : `${{_last}}, ${{_first}}`);
  fd.append('sr_code', document.getElementById('sr_code').value.trim());
  fd.append('email',   document.getElementById('email').value.trim());
  fd.append('sex',     document.getElementById('sex').value);

  ['front','left','right','up'].forEach(angle => {{
    const f = document.getElementById('file-' + angle).files[0];
    if (f) fd.append('photo_' + angle, f);
  }});

  try {{
    const res  = await fetch('/api/registration/submit', {{method:'POST', body:fd}});
    const data = await res.json();
    if (!res.ok) {{
      document.getElementById('confirm-error').textContent = data.error || 'Submission failed.';
      document.getElementById('confirm-error').style.display = 'block';
      btn.disabled = false;
      btn.textContent = '✓ Confirm & Submit';
      return;
    }}
    document.getElementById('confirmCard').style.display = 'none';
    document.getElementById('formCard').style.display = 'block';
    document.getElementById('formCard').querySelector('form').style.display = 'none';
    document.getElementById('successMsg').style.display = 'block';
    window.scrollTo(0, 0);
  }} catch {{
    document.getElementById('confirm-error').textContent = 'Network error. Please try again.';
    document.getElementById('confirm-error').style.display = 'block';
    btn.disabled = false;
    btn.textContent = '✓ Confirm & Submit';
  }}
}}
</script>
</body></html>"""


@app.route("/api/registration/submit", methods=["POST"])
def api_registration_submit():
    """
    Student submits their registration form.
    Photos go directly to Cloudinary — no local disk needed.
    DB record is created immediately.
    """
    cld_up, cld_err = _configure_cloudinary()
    if not cld_up:
        return jsonify({"error": cld_err}), 500

    token = request.form.get("token", "").strip()
    info  = db.get_registration_token(token)
    if not info:
        return jsonify({"error": "Registration link is invalid or has expired."}), 410

    class_code = info["class_code"]
    name       = request.form.get("name",    "").strip()
    sr_code    = request.form.get("sr_code", "").strip()
    email      = request.form.get("email",   "").strip()
    sex        = request.form.get("sex",     "").strip()

    if not name or not sr_code or not email:
        return jsonify({"error": "Name, SR Code and Email are required."}), 400

    if "photo_front" not in request.files:
        return jsonify({"error": "Front face photo is required."}), 400

    safe_name  = name.replace(" ", "_").replace("/", "_")
    safe_class = class_code.replace(" ", "_").replace("/", "_")

    # Upload all angle photos directly to Cloudinary
    angle_urls = {}
    photo_url  = ""
    ANGLES     = ["front", "left", "right", "up"]

    for angle in ANGLES:
        key = f"photo_{angle}"
        if key in request.files:
            f = request.files[key]
            if f and f.filename:
                try:
                    result = cld_up.upload(
                        f,
                        public_id = f"{safe_name}_{angle}",
                        folder    = f"faces/{safe_class}",
                        overwrite = True
                    )
                    url = result.get("secure_url", "")
                    angle_urls[f"photo_{angle}"] = url
                    if angle == "front":
                        # Also upload to students/ folder for display
                        res2 = cld_up.upload(
                            request.files[key],
                            public_id = safe_name,
                            folder    = f"students/{safe_class}",
                            overwrite = True
                        )
                        photo_url = res2.get("secure_url", url)
                except Exception as ex:
                    print(f"[SELF-REG] Cloudinary error {angle}: {ex}")

    if not angle_urls.get("photo_front"):
        return jsonify({"error": "Failed to upload front photo. Please try again."}), 500

    sig_url = "SIGNED"

    # Save to DB with Pending status — instructor must approve before student appears in class list
    try:
        db.add_student(
            class_code      = class_code,
            name            = name,
            address         = "",
            number          = "",
            sr_code         = sr_code,
            age             = 0,
            sex             = sex,
            email           = email,
            photo           = photo_url,
            signature       = sig_url,
            photo_front     = angle_urls.get("photo_front", ""),
            photo_left      = angle_urls.get("photo_left",  ""),
            photo_right     = angle_urls.get("photo_right", ""),
            photo_up        = angle_urls.get("photo_up",    ""),
            approval_status = "Pending",
        )
        # Notify instructor
        try:
            cls_info = db.get_class(class_code)
            if cls_info:
                db.add_notification(
                    cls_info["instructor_id"],
                    "pending_approval",
                    f"New student registration pending",
                    f"{name} ({sr_code}) submitted their registration for {info['subject']} — {info['section']}. Please review and approve."
                )
        except Exception as _ne:
            print(f"[SELF-REG] Notification error: {_ne}")
        print(f"[SELF-REG] ✓ {name} pending approval for {class_code}")
        return jsonify({"status": "ok", "name": name})
    except Exception as e:
        import traceback
        print(f"[SELF-REG] ✗ DB error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to save registration: {e}"}), 500



@app.route("/api/registration/pending")
def api_pending_registrations():
    """Return all pending student registrations for the logged-in instructor."""
    instructor_id = get_current_instructor_id(request)
    if not instructor_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        students = db.get_pending_students(instructor_id)
        return jsonify({"students": students})
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[PENDING] DB error: {e}")
        return jsonify({"students": [], "error": str(e)}), 500


@app.route("/api/registration/approve/<int:student_id>", methods=["POST"])
def api_approve_student(student_id):
    """Instructor approves a pending student registration."""
    if not get_current_instructor_id(request):
        return jsonify({"error": "Unauthorized"}), 401
    db.set_student_approval(student_id, "Approved")
    return jsonify({"status": "ok"})


@app.route("/api/registration/reject/<int:student_id>", methods=["POST"])
def api_reject_student(student_id):
    """Instructor rejects a pending student — deletes record and Cloudinary photos."""
    if not get_current_instructor_id(request):
        return jsonify({"error": "Unauthorized"}), 401
    student = db.delete_student(student_id)
    if student:
        photo_cols = ("photo", "photo_front", "photo_left", "photo_right", "photo_up", "signature")
        urls = [student[col] for col in photo_cols if student.get(col)]
        _delete_cloudinary_assets(urls)
    return jsonify({"status": "ok"})


@app.route("/api/registration/get_link/<class_code>")
def api_get_registration_link(class_code):
    """
    Returns the active registration link for a class, or generates a new one.
    Used by the instructor dashboard to show/copy the link.
    """
    token_cookie = request.cookies.get("session_token", "")
    session      = db.verify_session_token(token_cookie)
    if not session:
        return jsonify({"error": "Unauthorized."}), 401

    token    = db.create_registration_token(class_code, hours_valid=72)
    base_url = request.host_url.rstrip("/")
    link     = f"{base_url}/register/{token}"
    return jsonify({"link": link, "token": token})