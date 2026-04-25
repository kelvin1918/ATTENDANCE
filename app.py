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
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import (
    Flask, request,
    jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf
try:
    from face_recognition_a import FaceRecognizer, load_known_faces
    CAMERA_ENABLED = True
except ImportError:
    CAMERA_ENABLED = False
    print("[INFO] Camera features disabled — running in cloud/dashboard mode.")

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
    Reads instructor email from the Authorization header sent by script.js
    and returns their instructor id from the database.
    Returns None if not found.
    """
    email = req.headers.get("X-Instructor-Email", "")
    if not email:
        return None
    instructor = db.get_instructor_by_email(email)
    return instructor["id"] if instructor else None




# ── INIT ──────────────────────────────────────────────────────────────────────

db.init_db()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — single page app, script.js handles all navigation
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def portal():
    return send_file("portal.html")


@app.route("/home")
def index():
    return send_file("index.html")


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
    db.create_class(
        class_code    = data["id"],
        course_code   = data["course_code"],
        subject       = data["subject"],
        section       = data["section"],
        instructor_id = instructor_id,
    )
    # Notify instructor that the class folder was created
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
    db.edit_class(
        class_code,
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_class/<class_code>", methods=["DELETE"])
def api_delete_class(class_code):
    db.delete_class(class_code)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/add_student", methods=["POST"])
def api_add_student():
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name required"}), 400

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

    # Save signature
    sig_path = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and f.filename and allowed_file(f.filename):
            fname    = secure_filename(f.filename)
            sig_path = os.path.join("uploads/signatures", fname)
            f.save(sig_path)

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
    db.delete_student(student_id)
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
            recognizer = FaceRecognizer(known_enc, known_names)
            recognizer.set_session(instr_email, class_code, section, subject)
            recognizer.start(source)
            _camera_started = True
        else:
            # Already running — stop, reinitialise with new source, restart
            recognizer.stop_and_reset()
            recognizer = FaceRecognizer(known_enc, known_names)
            recognizer.set_session(instr_email, class_code, section, subject)
            recognizer.start(source)
            # _camera_started stays True
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

    filepath = generate_attendance_pdf(
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

    return send_file(
        filepath,
        as_attachment = True,
        download_name = os.path.basename(filepath),
        mimetype      = "application/pdf"
    )



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
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS LIST FOR A CLASS (for openFolderView)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/students/<class_code>", methods=["GET"])
def api_get_students(class_code):
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
    return jsonify({"status": "ok", "email": user["email"], "name": user["name"]})


@app.route("/api/register", methods=["POST"])
def api_register():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    name  = data.get("name", "").strip()
    if not email or not pwd or not name:
        return jsonify({"error": "Fill all fields."}), 400
    existing = db.get_instructor_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered."}), 409
    db.register_instructor(email, pwd, name)
    return jsonify({"status": "ok"})


@app.route("/api/instructors", methods=["GET"])
def api_get_instructors():
    rows = db.get_all_instructors()
    return jsonify([dict(r) for r in rows])


@app.route("/api/instructors/<int:instructor_id>/approve", methods=["POST"])
def api_approve_instructor(instructor_id):
    db.approve_instructor(instructor_id)
    # Notify the instructor that their account was approved
    db.add_notification(
        instructor_id = instructor_id,
        notif_type    = "approved",
        title         = "Account Approved",
        body          = "Your instructor account has been approved by the administrator. You can now create classes and record attendance."
    )
    return jsonify({"status": "ok"})


@app.route("/api/instructors/<int:instructor_id>", methods=["DELETE"])
def api_delete_instructor(instructor_id):
    db.delete_instructor(instructor_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# AUTH HTML PAGES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/login")
def login_page():
    return send_file("login.html")


@app.route("/admin")
def admin_page():
    return send_file("admin.html")

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

    smtp_user     = cfg["gmail"]    if cfg and cfg["gmail"]    else None
    smtp_password = cfg["app_pass"] if cfg and cfg["app_pass"] else None

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

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, data["to"], msg.as_string())

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


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)