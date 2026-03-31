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
from datetime import datetime
from flask import (
    Flask, request,
    jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf
from face_recognition_a import FaceRecognizer, load_known_faces

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

# ── FACE RECOGNITION ──────────────────────────────────────────────────────────

known_enc, known_names = load_known_faces("faces")
recognizer = FaceRecognizer(known_enc, known_names)
_camera_started = False


def start_camera(source=0):
    global _camera_started
    if not _camera_started:
        recognizer.start(source)
        _camera_started = True


def reload_recognizer():
    global known_enc, known_names, recognizer, _camera_started
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
    form = request.form
    db.edit_student(
        student_id,
        name    = form.get("name", ""),
        address = form.get("address", ""),
        number  = form.get("number", ""),
        sr_code = form.get("sr_code", ""),
        age     = int(form.get("age") or 0),
        sex     = form.get("sex", ""),
        email   = form.get("email", ""),
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_student/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    db.delete_student(student_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — CAMERA / ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/video_feed")
def video_feed():
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/present_students")
def api_present_students():
    return jsonify(recognizer.get_present_students())


@app.route("/api/save_attendance", methods=["POST"])
def api_save_attendance():
    """
    Body JSON:
    {
        "class_code": "CPET-3201-2026",
        "section":    "CPET-3201",
        "subject":    "CPT-113",
        "records": [
            {"name": "JohnDoe",   "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            {"name": "AnnaSmith", "sr_code": "2021-0002",
             "status": "Late",    "timestamp": "07:15:10"},
            {"name": "MarkLee",   "sr_code": "2021-0003",
             "status": "Absent",  "timestamp": ""}
        ]
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    db.save_attendance(
        class_code = data["class_code"],
        section    = data["section"],
        subject    = data["subject"],
        records    = data["records"],
    )
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


@app.route("/api/reset_attendance", methods=["POST"])
def api_reset_attendance():
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/recent")
def api_recent():
    rows = db.get_recent_activity(limit=10)
    return jsonify([dict(r) for r in rows])


@app.route("/api/absences")
def api_absences():
    return jsonify(db.get_absence_counts())


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
    db.edit_schedule(schedule_id, data["time"], data["subject"], data["room"])
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def api_delete_schedule(schedule_id):
    db.delete_schedule(schedule_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# PDF DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/download_pdf/<class_code>/<date>")
def api_download_pdf(class_code, date):
    cls     = db.get_class(class_code)
    records = db.get_attendance_session(class_code, date)

    if not cls:
        return jsonify({"error": "class not found"}), 404

    schedules = db.get_schedules(class_code)
    room      = schedules[0]["room"] if schedules else "TBA"

    filepath = generate_attendance_pdf(
        class_id = class_code,
        subject  = cls["subject"],
        section  = cls["section"],
        room     = room,
        date     = date,
        records  = records,
    )

    return send_file(
        filepath,
        as_attachment=True,
        download_name=os.path.basename(filepath),
        mimetype="application/pdf"
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
    rows = db.get_all_sessions()
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — ATTENDANCE RECORDS FOR ONE SESSION
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/attendance/<class_code>/<date>", methods=["GET"])
def api_get_attendance(class_code, date):
    rows = db.get_attendance_session(class_code, date)
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
    return jsonify({"status": "ok", "email": user["email"]})


@app.route("/api/register", methods=["POST"])
def api_register():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    if not email or not pwd:
        return jsonify({"error": "Fill all fields."}), 400
    existing = db.get_instructor_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered."}), 409
    db.register_instructor(email, pwd)
    return jsonify({"status": "ok"})


@app.route("/api/instructors", methods=["GET"])
def api_get_instructors():
    rows = db.get_all_instructors()
    return jsonify([dict(r) for r in rows])


@app.route("/api/instructors/<int:instructor_id>/approve", methods=["POST"])
def api_approve_instructor(instructor_id):
    db.approve_instructor(instructor_id)
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

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)