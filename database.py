"""
database.py
============
PostgreSQL database layer for the Attendance Monitoring System.
Matches the updated schema:
    classes    — id (VARCHAR), course_code, subject, section
    students   — sr_code (UNIQUE), class_code (FK), sex added
    attendance — sr_code (FK to students), class_code (FK)
    schedules  — class_code (FK)

Requirements:
    pip install psycopg2-binary

Update DB_CONFIG below to match your PostgreSQL setup.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
import os

# Load .env file if present — must happen before reading os.environ below.
# On Render, variables are set in the dashboard so .env is not needed there.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # python-dotenv not installed — rely on system env vars


# ── CONNECTION CONFIG ─────────────────────────────────────────────────────────
# ALL credentials are read from environment variables.
# Local development: put these in a .env file (never commit .env to GitHub).
# Render deployment: set them in the Render dashboard → Environment tab.
#
# Required variables:
#   DB_HOST      = your Neon host
#   DB_PORT      = 5432
#   DB_NAME      = neondb
#   DB_USER      = neondb_owner
#   DB_PASSWORD  = your Neon password
#
# Optional (falls back to Neon if not set):
#   DB_HOST_LOCAL, DB_NAME_LOCAL, DB_USER_LOCAL, DB_PASSWORD_LOCAL

# ── Read credentials from environment (populated by .env via dotenv above) ────
_DB_HOST = os.environ.get("DB_HOST", "").strip()
_DB_PORT = int(os.environ.get("DB_PORT", 5432))
_DB_NAME = os.environ.get("DB_NAME", "").strip()
_DB_USER = os.environ.get("DB_USER", "").strip()
_DB_PASS = os.environ.get("DB_PASSWORD", "").strip()

# Validate — give a clear error instead of a confusing SSL/localhost crash
_missing = [k for k, v in {
    "DB_HOST": _DB_HOST, "DB_NAME": _DB_NAME,
    "DB_USER": _DB_USER, "DB_PASSWORD": _DB_PASS
}.items() if not v]

if _missing:
    raise EnvironmentError(
        f"\n\n[DATABASE] Missing environment variable(s): {', '.join(_missing)}\n"
        f"Create a .env file in your project folder with:\n"
        f"  DB_HOST=your_neon_host\n"
        f"  DB_NAME=neondb\n"
        f"  DB_USER=neondb_owner\n"
        f"  DB_PASSWORD=your_password\n"
        f"Then run: pip install python-dotenv\n"
    )

DB_CONFIG = {
    "host":     _DB_HOST,
    "port":     _DB_PORT,
    "database": _DB_NAME,
    "user":     _DB_USER,
    "password": _DB_PASS,
    "sslmode":  "require",
}

print(f"[DB] Connecting to {_DB_HOST} / {_DB_NAME} as {_DB_USER}")


# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db():
    """
    Returns a live PostgreSQL connection to Neon.
    Raises a clear error if credentials are missing or the host is unreachable.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        err = str(e)
        if "SSL" in err:
            raise ConnectionError(
                "\n[DB] SSL error — make sure DB_HOST points to your Neon host,\n"
                "not localhost. Check your .env file."
            ) from e
        if "password" in err.lower():
            raise ConnectionError(
                "\n[DB] Authentication failed — check DB_USER and DB_PASSWORD in .env."
            ) from e
        raise


def get_cursor(conn):
    """
    Returns a DictCursor — rows behave like dicts: row["name"]
    Same feel as SQLite's row_factory = sqlite3.Row.
    """
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    """Creates all tables if they don't exist. Called once on app startup."""
    conn = get_db()
    cur  = conn.cursor()

    # ── 1. instructors first — other tables reference it ─────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name     VARCHAR(100) NOT NULL DEFAULT '',
            email    VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            status   VARCHAR(20)  DEFAULT 'pending'
        );
    """)
    cur.execute("ALTER TABLE instructors ADD COLUMN IF NOT EXISTS name   VARCHAR(100) NOT NULL DEFAULT '';")
    cur.execute("ALTER TABLE instructors ADD COLUMN IF NOT EXISTS number VARCHAR(30)  NOT NULL DEFAULT '';")

    # ── 2. mail_config — references instructors ───────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mail_config (
            instructor_id  INTEGER PRIMARY KEY REFERENCES instructors(id) ON DELETE CASCADE,
            gmail          VARCHAR(200) DEFAULT '',
            app_pass       VARCHAR(200) DEFAULT '',
            present_grace  INTEGER DEFAULT 15,
            late_grace     INTEGER DEFAULT 30
        );
    """)

    # ── 3. classes — references instructors ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id            VARCHAR(50)  PRIMARY KEY,
            course_code   VARCHAR(20)  NOT NULL,
            subject       VARCHAR(50),
            section       VARCHAR(50),
            created       DATE DEFAULT CURRENT_DATE,
            instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE
        );
    """)

    # ── 4. students — references classes ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name       VARCHAR(50)  NOT NULL,
            address    VARCHAR(100),
            number     VARCHAR(50),
            sr_code    VARCHAR(50),
            age        INTEGER,
            sex        VARCHAR(10),
            email      VARCHAR(100),
            photo      TEXT,
            signature  TEXT,
            status     VARCHAR(20) DEFAULT 'Enrolled',
            UNIQUE (class_code, sr_code)
        );
    """)
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Enrolled';")
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_front TEXT DEFAULT '';")
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_left  TEXT DEFAULT '';")
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_right TEXT DEFAULT '';")
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_up    TEXT DEFAULT '';")

    # ── 5. attendance — references classes ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code   VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code      VARCHAR(50),
            name         VARCHAR(50)  NOT NULL,
            section      VARCHAR(50),
            subject      VARCHAR(50),
            status       VARCHAR(20)  NOT NULL,
            timestamp    TIMESTAMP(0) DEFAULT NOW(),
            date         DATE         NOT NULL,
            session_time VARCHAR(8)
        );
    """)
    cur.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS session_time VARCHAR(8);")

    # ── 6. schedules — references classes + instructors ───────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code    VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
            instructor_id INTEGER      REFERENCES instructors(id) ON DELETE CASCADE,
            time          VARCHAR(50),
            subject       VARCHAR(50),
            room          VARCHAR(50),
            day           VARCHAR(10)
        );
    """)

    # ── 8. campus_rooms — maps friendly room name to RTSP URL ────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS campus_rooms (
            id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            room_name VARCHAR(50) UNIQUE NOT NULL,
            rtsp_url  TEXT NOT NULL
        );
    """)

    # ── 9. notifications — per-instructor activity feed ──────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE,
            type          VARCHAR(50)  NOT NULL,
            title         VARCHAR(200) NOT NULL,
            body          TEXT         NOT NULL,
            is_read       BOOLEAN      DEFAULT FALSE,
            created_at    TIMESTAMP(0) DEFAULT NOW()
        );
    """)    

    # ── 10. otp_resets — server-side OTP for password reset ──────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS otp_resets (
            id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email      VARCHAR(100) NOT NULL,
            otp_hash   VARCHAR(200) NOT NULL,
            expires_at TIMESTAMP    NOT NULL,
            attempts   INTEGER      DEFAULT 0,
            used       BOOLEAN      DEFAULT FALSE
        );
    """)

    # ── 11. session_tokens — server-side login sessions ───────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS session_tokens (
            token      VARCHAR(64)  PRIMARY KEY,
            email      VARCHAR(100) NOT NULL,
            created_at TIMESTAMP    DEFAULT NOW(),
            expires_at TIMESTAMP    NOT NULL
        );

        -- ── 13. admin_account — secure admin credentials ───────────────────
        CREATE TABLE IF NOT EXISTS admin_account (
            id             SERIAL       PRIMARY KEY,
            username       VARCHAR(50)  NOT NULL UNIQUE DEFAULT 'admin',
            password_hash  VARCHAR(255) NOT NULL,
            recovery_email VARCHAR(100) NOT NULL,
            updated_at     TIMESTAMP    DEFAULT NOW()
        );

        -- ── 14. admin_session_tokens — separate from instructor sessions ────
        CREATE TABLE IF NOT EXISTS admin_session_tokens (
            token      VARCHAR(64)  PRIMARY KEY,
            created_at TIMESTAMP    DEFAULT NOW(),
            expires_at TIMESTAMP    NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] PostgreSQL tables ready.")


# ── SESSION TOKEN FUNCTIONS ───────────────────────────────────────────────────

def create_session_token(email):
    """Generate a secure random token, store it in DB, return the token string."""
    import secrets
    from datetime import timedelta
    token = secrets.token_hex(32)           # 64-char hex string
    expires = datetime.now() + timedelta(hours=12)
    conn = get_db(); cur = conn.cursor()
    # Clean old tokens for this email first
    cur.execute("DELETE FROM session_tokens WHERE email = %s", (email,))
    cur.execute(
        "INSERT INTO session_tokens (token, email, expires_at) VALUES (%s, %s, %s)",
        (token, email, expires)
    )
    conn.commit(); cur.close(); conn.close()
    return token

def verify_session_token(token):
    """Return the instructor row if token is valid and not expired, else None."""
    if not token:
        return None
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "SELECT email FROM session_tokens WHERE token = %s AND expires_at > NOW()",
        (token,)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        return None
    return get_instructor_by_email(row["email"])

def delete_session_token(token):
    """Remove a session token (logout)."""
    if not token:
        return
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM session_tokens WHERE token = %s", (token,))
    conn.commit(); cur.close(); conn.close()


# ── OTP RESET FUNCTIONS ───────────────────────────────────────────────────────

def create_otp(email, otp_code):
    """Hash and store OTP for this email, expiring in 10 minutes."""
    import hashlib
    from datetime import timedelta
    otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    expires   = datetime.now() + timedelta(minutes=10)
    conn = get_db(); cur = conn.cursor()
    # Remove any previous OTPs for this email
    cur.execute("DELETE FROM otp_resets WHERE email = %s", (email,))
    cur.execute(
        "INSERT INTO otp_resets (email, otp_hash, expires_at) VALUES (%s, %s, %s)",
        (email, otp_hash, expires)
    )
    conn.commit(); cur.close(); conn.close()

def verify_otp(email, otp_code):
    """
    Check OTP for email. Returns: 'ok' | 'invalid' | 'expired' | 'locked'
    Increments attempt counter; locks after 5 wrong attempts.
    """
    import hashlib
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "SELECT * FROM otp_resets WHERE email = %s AND used = FALSE ORDER BY id DESC LIMIT 1",
        (email,)
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return "invalid"

    if row["attempts"] >= 5:
        cur.close(); conn.close()
        return "locked"

    if datetime.now() > row["expires_at"]:
        cur.close(); conn.close()
        return "expired"

    entered_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    if entered_hash != row["otp_hash"]:
        # Increment attempts
        wc = conn.cursor()
        wc.execute("UPDATE otp_resets SET attempts = attempts + 1 WHERE id = %s", (row["id"],))
        conn.commit(); wc.close(); cur.close(); conn.close()
        return "invalid"

    # Mark as used
    wc = conn.cursor()
    wc.execute("UPDATE otp_resets SET used = TRUE WHERE id = %s", (row["id"],))
    conn.commit(); wc.close(); cur.close(); conn.close()
    return "ok"

def update_password(email, new_password):
    """Update instructor password after successful OTP verification."""
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE instructors SET password = %s WHERE email = %s", (new_password, email))
    conn.commit(); cur.close(); conn.close()


# ── CLASSES ───────────────────────────────────────────────────────────────────

def get_all_classes(instructor_id=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if instructor_id:
        cur.execute(
            "SELECT * FROM classes WHERE instructor_id = %s ORDER BY created DESC",
            (instructor_id,)
        )
    else:
        cur.execute("SELECT * FROM classes ORDER BY created DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_class(class_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row




def create_class(class_code, course_code, subject, section, instructor_id):
    """
    class_code    = unique ID e.g. "CPT113-CPET3201-INS1"
    course_code   = e.g. "CPT-113"
    subject       = e.g. "Computer Programming"
    section       = e.g. "CPET-3201"
    instructor_id = FK to instructors table
    created       = auto-set to today's date
    """
    conn    = get_db()
    cur     = get_cursor(conn)
    created = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        """INSERT INTO classes (id, course_code, subject, section, created, instructor_id)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (id) DO NOTHING""",
        (class_code, course_code, subject, section, created, instructor_id)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_class(class_code, course_code, subject, section):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE classes
           SET course_code=%s, subject=%s, section=%s
           WHERE id=%s""",
        (course_code, subject, section, class_code)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_class(class_code):
    """Deletes class + cascades to students, attendance, schedules."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM classes WHERE id = %s", (class_code,))
    conn.commit()
    cur.close(); conn.close()


# ── STUDENTS ──────────────────────────────────────────────────────────────────

def get_students(class_code):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "SELECT * FROM students WHERE class_code = %s ORDER BY name",
        (class_code,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_students_with_photos(instructor_id):
    """
    Return all students for all classes belonging to this instructor,
    including their photo and signature URLs/paths.
    Used by the local sync-on-login to download face images from Cloudinary.
    Only returns students with a non-empty photo field.
    """
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT s.id, s.class_code, s.name, s.sr_code, s.photo, s.signature
           FROM students s
           JOIN classes c ON c.id = s.class_code
           WHERE c.instructor_id = %s
             AND s.photo IS NOT NULL
             AND s.photo != ''
             AND s.status != 'Dropped'
           ORDER BY s.class_code, s.name""",
        (instructor_id,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


def get_student(student_db_id):
    """Get one student by their auto-increment id."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE id = %s", (student_db_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def get_student_by_srcode(sr_code):
    """Get one student by their SR code (unique student number)."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE sr_code = %s", (sr_code,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def add_student(class_code, name, address, number,
                sr_code, age, sex, email, photo, signature,
                photo_front="", photo_left="", photo_right="", photo_up=""):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """INSERT INTO students
           (class_code, name, address, number,
            sr_code, age, sex, email, photo, signature,
            photo_front, photo_left, photo_right, photo_up)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (class_code, name, address, number,
         sr_code, age, sex, email, photo, signature,
         photo_front, photo_left, photo_right, photo_up)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_student(student_db_id, name=None, address=None, number=None,
                 sr_code=None, age=None, sex=None, email=None,
                 status=None, photo=None, signature=None,
                 photo_front=None, photo_left=None,
                 photo_right=None, photo_up=None):
    """
    Update a student record. Only non-None fields are written.
    photo and signature accept either a local path or a Cloudinary URL.
    Pass photo=None to leave the existing photo untouched.
    Pass photo="" to explicitly clear the photo field.
    photo_front/left/right/up are the 4-angle Cloudinary URLs.
    """
    conn = get_db()
    cur  = get_cursor(conn)

    if status and name is None and photo is None and signature is None:
        # Status-only update (from folder view dropdown) — fast path
        cur.execute(
            "UPDATE students SET status=%s WHERE id=%s",
            (status, student_db_id)
        )
    else:
        # Build dynamic SET clause — only update fields that were passed
        fields = []
        values = []
        if name        is not None: fields.append("name=%s");        values.append(name)
        if address     is not None: fields.append("address=%s");     values.append(address)
        if number      is not None: fields.append("number=%s");      values.append(number)
        if age         is not None: fields.append("age=%s");         values.append(age)
        if sex         is not None: fields.append("sex=%s");         values.append(sex)
        if email       is not None: fields.append("email=%s");       values.append(email)
        if status      is not None: fields.append("status=%s");      values.append(status)
        if photo       is not None: fields.append("photo=%s");       values.append(photo)
        if signature   is not None: fields.append("signature=%s");   values.append(signature)
        if photo_front is not None: fields.append("photo_front=%s"); values.append(photo_front)
        if photo_left  is not None: fields.append("photo_left=%s");  values.append(photo_left)
        if photo_right is not None: fields.append("photo_right=%s"); values.append(photo_right)
        if photo_up    is not None: fields.append("photo_up=%s");    values.append(photo_up)

        if not fields:
            cur.close(); conn.close()
            return

        values.append(student_db_id)
        cur.execute(
            f"UPDATE students SET {', '.join(fields)} WHERE id=%s",
            values
        )

    conn.commit()
    cur.close(); conn.close()


def update_signature_only(student_db_id, signature_url):
    """
    Lightweight helper — updates only the signature field.
    Called after a quick signature-only upload.
    """
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "UPDATE students SET signature=%s WHERE id=%s",
        (signature_url, student_db_id)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_student(student_db_id):
    """
    Delete a student from the DB and return their file paths so the caller
    can clean up Cloudinary and local disk files.

    Returns dict: { "photo": str, "signature": str, "name": str,
                    "class_code": str, "sr_code": str }
    Returns None if student not found.
    """
    conn = get_db()
    cur  = get_cursor(conn)

    # Fetch file paths BEFORE deleting so the caller can clean up
    cur.execute(
        "SELECT name, class_code, sr_code, photo, signature FROM students WHERE id = %s",
        (student_db_id,)
    )
    student = cur.fetchone()

    if not student:
        cur.close(); conn.close()
        return None

    cur.execute("DELETE FROM students WHERE id = %s", (student_db_id,))
    conn.commit()
    cur.close(); conn.close()
    return dict(student)


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

def save_attendance(class_code, section, subject, records,
                    date=None, session_time=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    session_time = "HH:MM:SS" string — the camera-open time, used to group all
    students from one scanning session. Stored on every row so sessions are never
    mixed up even when students scan across different minutes.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    if session_time is None:
        session_time = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cur  = get_cursor(conn)

    # Delete existing records for this exact session (camera-open time HH:MM).
    # This allows re-saving without duplicates while keeping other sessions intact.
    cur.execute(
        """DELETE FROM attendance
           WHERE class_code = %s AND date = %s AND session_time = %s""",
        (class_code, date, session_time[:5])
    )

    for r in records:
        scan_time      = r.get("timestamp", "")
        full_timestamp = f"{date} {scan_time}" if scan_time else None

        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date, session_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                class_code,
                r.get("sr_code", ""),
                r["name"],
                section,
                subject,
                r["status"],
                full_timestamp,
                date,
                session_time[:5]   # store HH:MM as the session key
            )
        )

    conn.commit()
    cur.close(); conn.close()


def get_attendance_session(class_code, date, session_time=None):
    """All attendance rows for one class on one date (optionally one session),
    sorted Present→Late→Absent. Returns timestamp and date as plain strings."""
    conn = get_db()
    cur  = get_cursor(conn)
    if session_time:
        cur.execute(
            """SELECT
                   id, class_code, sr_code, name, section, subject, status,
                   TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
                   TO_CHAR(date, 'YYYY-MM-DD')                 AS date,
                   session_time
               FROM attendance
               WHERE class_code = %s AND date = %s AND session_time = %s
               ORDER BY
                 CASE status
                   WHEN 'Present' THEN 1
                   WHEN 'Late'    THEN 2
                   WHEN 'Absent'  THEN 3
                 END, name""",
            (class_code, date, session_time[:5])
        )
    else:
        cur.execute(
            """SELECT
                   id, class_code, sr_code, name, section, subject, status,
                   TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
                   TO_CHAR(date, 'YYYY-MM-DD')                 AS date,
                   session_time
               FROM attendance
               WHERE class_code = %s AND date = %s
               ORDER BY
                 CASE status
                   WHEN 'Present' THEN 1
                   WHEN 'Late'    THEN 2
                   WHEN 'Absent'  THEN 3
                 END, name""",
            (class_code, date)
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_all_sessions(instructor_id=None):
    """One row per (class_code, date) — for the History page list."""
    conn = get_db()
    cur  = get_cursor(conn)
    if instructor_id:
        cur.execute(
            """SELECT
                   a.class_code,
                   TO_CHAR(a.date, 'YYYY-MM-DD')                      AS date,
                   a.section,
                   a.subject,
                   COUNT(*)                                             AS total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
                   SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s AND a.session_time != 'LIVE'
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC""",
            (instructor_id,)
        )
    else:
        cur.execute(
            """SELECT
                   a.class_code,
                   TO_CHAR(a.date, 'YYYY-MM-DD')                      AS date,
                   a.section,
                   a.subject,
                   COUNT(*)                                             AS total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
                   SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
               FROM attendance a
               WHERE a.session_time != 'LIVE'
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC"""
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_sessions_by_class(class_code):
    """
    One row per (date, session_time) for a specific class.
    Groups by the stored session_time column (camera-open HH:MM) so each
    scanning session appears as exactly one file, regardless of how many
    minutes students were scanned across.
    """
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               a.class_code,
               TO_CHAR(a.date, 'YYYY-MM-DD')                              AS date,
               a.section,
               a.subject,
               COALESCE(a.session_time, TO_CHAR(MIN(a.timestamp), 'HH24:MI')) AS session_time,
               COUNT(*)                                                     AS total,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)         AS present,
               SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END)         AS late,
               SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END)         AS absent
           FROM attendance a
           WHERE a.class_code = %s AND a.session_time != 'LIVE'
           GROUP BY a.class_code, a.date, a.section, a.subject, a.session_time
           ORDER BY a.date DESC, a.session_time DESC""",
        (class_code,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_recent_activity(limit=10, instructor_id=None):
    """Most recent sessions for the dashboard Recent Activities list.
    Each camera session (identified by session_time) gets its own row,
    ordered by the actual session datetime so the very latest always appears first."""
    conn = get_db()
    cur  = get_cursor(conn)
    if instructor_id:
        cur.execute(
            """SELECT
                   a.class_code,
                   TO_CHAR(a.date, 'YYYY-MM-DD')                            AS date,
                   a.section,
                   a.subject,
                   COALESCE(a.session_time, TO_CHAR(MIN(a.timestamp), 'HH24:MI')) AS session_time,
                   TO_CHAR(MIN(a.timestamp), 'HH24:MI:SS')                  AS time
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s AND a.session_time != 'LIVE'
               GROUP BY a.class_code, a.date, a.section, a.subject, a.session_time
               ORDER BY a.date DESC, a.session_time DESC
               LIMIT %s""",
            (instructor_id, limit)
        )
    else:
        cur.execute(
            """SELECT
                   class_code,
                   TO_CHAR(date, 'YYYY-MM-DD')                              AS date,
                   section,
                   subject,
                   COALESCE(session_time, TO_CHAR(MIN(timestamp), 'HH24:MI')) AS session_time,
                   TO_CHAR(MIN(timestamp), 'HH24:MI:SS')                    AS time
               FROM attendance
               WHERE session_time != 'LIVE'
               GROUP BY class_code, date, section, subject, session_time
               ORDER BY date DESC, session_time DESC
               LIMIT %s""",
            (limit,)
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_absence_counts(instructor_id=None):
    """
    Per-class absence statistics for the dashboard chart.
    Returns for each class:
      - subject name (label)
      - total_absent: total absent records across all sessions
      - total_records: total attendance records across all sessions
      - avg_absent: average absences per session (rounded to 2 decimal places)
      - pct_absent: absence percentage = (total_absent / total_records) * 100
    """
    conn = get_db()
    cur  = get_cursor(conn)
    if instructor_id:
        cur.execute(
            """SELECT
                   a.subject                                        AS name,
                   COUNT(*) FILTER (WHERE a.status = 'Absent')     AS total_absent,
                   COUNT(*)                                         AS total_records,
                   COUNT(DISTINCT (a.date || '_' || COALESCE(a.session_time, '')))
                                                                    AS total_sessions,
                   ROUND(
                       COUNT(*) FILTER (WHERE a.status = 'Absent')::numeric
                       / NULLIF(COUNT(DISTINCT (a.date || '_' || COALESCE(a.session_time, ''))), 0)
                   , 2)                                             AS avg_absent,
                   ROUND(
                       COUNT(*) FILTER (WHERE a.status = 'Absent')::numeric
                       / NULLIF(COUNT(*), 0) * 100
                   , 1)                                             AS pct_absent,
                   MAX(a.date)                                      AS last_session_date,
                   MAX(COALESCE(a.session_time, '00:00:00'))        AS last_session_time
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s AND a.session_time != 'LIVE'
               GROUP BY a.subject
               ORDER BY last_session_date DESC, last_session_time DESC""",
            (instructor_id,)
        )
    else:
        cur.execute(
            """SELECT
                   a.subject                                        AS name,
                   COUNT(*) FILTER (WHERE a.status = 'Absent')     AS total_absent,
                   COUNT(*)                                         AS total_records,
                   COUNT(DISTINCT (a.date || '_' || COALESCE(a.session_time, '')))
                                                                    AS total_sessions,
                   ROUND(
                       COUNT(*) FILTER (WHERE a.status = 'Absent')::numeric
                       / NULLIF(COUNT(DISTINCT (a.date || '_' || COALESCE(a.session_time, ''))), 0)
                   , 2)                                             AS avg_absent,
                   ROUND(
                       COUNT(*) FILTER (WHERE a.status = 'Absent')::numeric
                       / NULLIF(COUNT(*), 0) * 100
                   , 1)                                             AS pct_absent,
                   MAX(a.date)                                      AS last_session_date,
                   MAX(COALESCE(a.session_time, '00:00:00'))        AS last_session_time
               FROM attendance a
               WHERE a.session_time != 'LIVE'
               GROUP BY a.subject
               ORDER BY last_session_date DESC, last_session_time DESC"""
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {
            "name":              r["name"],
            "total_absent":      r["total_absent"],
            "total_records":     r["total_records"],
            "total_sessions":    r["total_sessions"],
            "avg_absent":        float(r["avg_absent"]  or 0),
            "pct_absent":        float(r["pct_absent"]  or 0),
            "last_session_date": str(r["last_session_date"] or ""),
            "last_session_time": str(r["last_session_time"] or ""),
        }
        for r in rows
    ]


# ── SCHEDULES ─────────────────────────────────────────────────────────────────

def get_schedules(class_code=None, instructor_id=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if class_code:
        cur.execute(
            "SELECT * FROM schedules WHERE class_code = %s ORDER BY id",
            (class_code,)
        )
    elif instructor_id:
        cur.execute(
            "SELECT * FROM schedules WHERE instructor_id = %s ORDER BY id",
            (instructor_id,)
        )
    else:
        cur.execute("SELECT * FROM schedules ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def add_schedule(class_code, instructor_id, time, subject, room, day):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """INSERT INTO schedules 
           (class_code, instructor_id, time, subject, room, day) 
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (class_code, instructor_id, time, subject, room, day)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_schedule(schedule_id, time, subject, room, day=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if day:
        cur.execute(
            "UPDATE schedules SET time=%s, subject=%s, room=%s, day=%s WHERE id=%s",
            (time, subject, room, day, schedule_id)
        )
    else:
        cur.execute(
            "UPDATE schedules SET time=%s, subject=%s, room=%s WHERE id=%s",
            (time, subject, room, schedule_id)
        )
    conn.commit()
    cur.close(); conn.close()


def get_classes_using_schedule(schedule_id):
    """Returns classes linked to a given schedule (used before editing/deleting)."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT c.id, c.subject, c.section
           FROM classes c
           JOIN schedules s ON s.class_code = c.id
           WHERE s.id = %s""",
        (schedule_id,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def update_class_subject_by_schedule(schedule_id, old_subject, new_subject):
    """Updates the subject on classes linked to a schedule when the subject name changes."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE classes
           SET subject = %s
           WHERE id IN (SELECT class_code FROM schedules WHERE id = %s)
           AND subject = %s""",
        (new_subject, schedule_id, old_subject)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_schedule(schedule_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
    conn.commit()
    cur.close(); conn.close()


# ── INSTRUCTORS ───────────────────────────────────────────────────────────────

def get_all_instructors():
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT id, email, status FROM instructors ORDER BY id")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def get_instructor_by_email(email):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM instructors WHERE email = %s", (email,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def get_instructor_by_id(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM instructors WHERE id = %s", (instructor_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def register_instructor(email, password, name=''):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "INSERT INTO instructors (name, email, password, status) VALUES (%s, %s, %s, %s)",
        (name, email, password, 'pending')
    )
    conn.commit(); cur.close(); conn.close()

def approve_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("UPDATE instructors SET status='approved' WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()

def delete_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("DELETE FROM instructors WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()

def update_instructor_profile(instructor_id, name=None, number=None):
    """Update instructor display name and contact number in DB."""
    conn = get_db(); cur = get_cursor(conn)
    if name is not None:
        cur.execute("UPDATE instructors SET name=%s WHERE id=%s", (name, instructor_id))
    if number is not None:
        cur.execute("UPDATE instructors SET number=%s WHERE id=%s", (number, instructor_id))
    conn.commit(); cur.close(); conn.close()

def get_attendance_for_student(class_code, name, date):
    """Check if a student already has a LIVE staging row for today.
    Only looks at session_time='LIVE' — finalized sessions don't block re-detection."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        """SELECT id FROM attendance
           WHERE class_code = %s AND name = %s AND date = %s AND session_time = 'LIVE'
           LIMIT 1""",
        (class_code, name, date)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def save_mail_config(instructor_id, gmail='', app_pass='', present_grace=15, late_grace=30):
    """Upsert mail config (gmail, app password, grace periods) for an instructor."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        INSERT INTO mail_config (instructor_id, gmail, app_pass, present_grace, late_grace)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (instructor_id) DO UPDATE
            SET gmail         = EXCLUDED.gmail,
                app_pass      = EXCLUDED.app_pass,
                present_grace = EXCLUDED.present_grace,
                late_grace    = EXCLUDED.late_grace
    """, (instructor_id, gmail, app_pass, present_grace, late_grace))
    conn.commit(); cur.close(); conn.close()

def get_mail_config(instructor_id):
    """Return mail config row for an instructor, or None."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM mail_config WHERE instructor_id=%s", (instructor_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

# ── CAMPUS ROOMS ─────────────────────────────────────────────────────────────

def get_all_rooms():
    """Return all campus rooms (name + RTSP URL)."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM campus_rooms ORDER BY room_name")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def upsert_room(room_name, rtsp_url):
    """Add or update a campus room mapping."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        INSERT INTO campus_rooms (room_name, rtsp_url)
        VALUES (%s, %s)
        ON CONFLICT (room_name) DO UPDATE SET rtsp_url = EXCLUDED.rtsp_url
    """, (room_name, rtsp_url))
    conn.commit(); cur.close(); conn.close()

def delete_room(room_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("DELETE FROM campus_rooms WHERE id=%s", (room_id,))
    conn.commit(); cur.close(); conn.close()


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

def add_notification(instructor_id, notif_type, title, body):
    """
    Insert a notification row for the given instructor.
    notif_type  : 'approved' | 'email_sent' | 'attendance_saved' |
                  'class_created' | 'student_registered' | 'general'
    title       : Short headline shown in the bell dropdown.
    body        : Full detail line shown under the title.
    """
    if not instructor_id:
        return
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        """INSERT INTO notifications (instructor_id, type, title, body)
           VALUES (%s, %s, %s, %s)""",
        (instructor_id, notif_type, title, body)
    )
    conn.commit(); cur.close(); conn.close()


def get_notifications(instructor_id, limit=50):
    """
    Return up to `limit` most-recent notifications for this instructor.
    Returns list of dicts with keys:
      id, type, title, body, is_read, created_at (ISO string)
    """
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        """SELECT id, type, title, body, is_read,
                  TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at
           FROM notifications
           WHERE instructor_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (instructor_id, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def mark_notifications_read(instructor_id, notif_ids=None):
    """
    Mark notifications as read.
    If notif_ids is None → mark ALL unread for this instructor.
    If notif_ids is a list of ints → mark only those specific rows.
    """
    conn = get_db(); cur = get_cursor(conn)
    if notif_ids:
        cur.execute(
            """UPDATE notifications SET is_read = TRUE
               WHERE instructor_id = %s AND id = ANY(%s)""",
            (instructor_id, notif_ids)
        )
    else:
        cur.execute(
            "UPDATE notifications SET is_read = TRUE WHERE instructor_id = %s",
            (instructor_id,)
        )
    conn.commit(); cur.close(); conn.close()


def get_unread_count(instructor_id):
    """Return the count of unread notifications for the badge."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE instructor_id=%s AND is_read=FALSE",
        (instructor_id,)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    return row["cnt"] if row else 0

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ACCOUNT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_admin_account():
    """Return the single admin account row, or None if not yet seeded."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM admin_account LIMIT 1")
    row = cur.fetchone(); cur.close(); conn.close()
    return dict(row) if row else None


def seed_admin_if_missing(default_password="admin123"):
    """
    Called on app startup. If no admin account exists, create one with
    the default password so the system still works on first deploy.
    Admins should change the password immediately via the forgot-password flow.
    """
    import hashlib
    if get_admin_account():
        return  # already seeded
    conn = get_db(); cur = conn.cursor()
    pw_hash = hashlib.sha256(default_password.encode()).hexdigest()
    cur.execute(
        """INSERT INTO admin_account (username, password_hash, recovery_email)
           VALUES ('admin', %s, '') ON CONFLICT DO NOTHING""",
        (pw_hash,)
    )
    conn.commit(); cur.close(); conn.close()
    print("[DB] Admin account seeded with default password.")


def verify_admin_password(password):
    """Return True if password matches the stored hash."""
    import hashlib
    admin = get_admin_account()
    if not admin:
        return False
    return admin["password_hash"] == hashlib.sha256(password.encode()).hexdigest()


def update_admin_password(new_password):
    """Hash and store a new admin password."""
    import hashlib
    pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "UPDATE admin_account SET password_hash = %s, updated_at = NOW()",
        (pw_hash,)
    )
    conn.commit(); cur.close(); conn.close()


def update_admin_recovery_email(email):
    """Store / update the admin recovery email."""
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "UPDATE admin_account SET recovery_email = %s, updated_at = NOW()",
        (email.strip().lower(),)
    )
    conn.commit(); cur.close(); conn.close()


def create_admin_session_token():
    """Generate a secure token for the admin session (8-hour expiry)."""
    import secrets
    from datetime import timedelta
    token   = secrets.token_hex(32)
    expires = datetime.now() + timedelta(hours=8)
    conn = get_db(); cur = conn.cursor()
    # Keep only the latest token
    cur.execute("DELETE FROM admin_session_tokens")
    cur.execute(
        "INSERT INTO admin_session_tokens (token, expires_at) VALUES (%s, %s)",
        (token, expires)
    )
    conn.commit(); cur.close(); conn.close()
    return token


def verify_admin_session_token(token):
    """Return True if token exists and has not expired."""
    if not token:
        return False
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "SELECT token FROM admin_session_tokens WHERE token=%s AND expires_at > NOW()",
        (token,)
    )
    row = cur.fetchone(); cur.close(); conn.close()
    return row is not None


def delete_admin_session_token(token):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM admin_session_tokens WHERE token=%s", (token,))
    conn.commit(); cur.close(); conn.close()


# ── ADMIN ACTIVITY MONITOR ────────────────────────────────────────────────────

def get_instructor_activity_summary():
    """
    Returns one row per instructor showing:
      - name, email, status, total_classes, total_sessions,
        last_active (most recent attendance date), total_students
    Used by the admin Activity Monitor page.
    """
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        SELECT
            i.id,
            i.name,
            i.email,
            i.status,
            COUNT(DISTINCT c.id)                                   AS total_classes,
            COUNT(DISTINCT (a.class_code, a.date, a.session_time)) AS total_sessions,
            COUNT(DISTINCT s.id)                                   AS total_students,
            MAX(a.date)                                            AS last_active
        FROM instructors i
        LEFT JOIN classes  c ON c.instructor_id = i.id
        LEFT JOIN attendance a ON a.class_code = c.id
                               AND a.session_time != 'LIVE'
        LEFT JOIN students s ON s.class_id = c.id
        GROUP BY i.id, i.name, i.email, i.status
        ORDER BY last_active DESC NULLS LAST, i.name
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    result = []
    for r in rows:
        result.append({
            "id":              r["id"],
            "name":            r["name"] or r["email"],
            "email":           r["email"],
            "status":          r["status"],
            "total_classes":   r["total_classes"]  or 0,
            "total_sessions":  r["total_sessions"] or 0,
            "total_students":  r["total_students"] or 0,
            "last_active":     str(r["last_active"]) if r["last_active"] else None,
        })
    return result


def get_instructor_recent_sessions(instructor_id, limit=10):
    """
    Returns the most recent attendance sessions for a specific instructor.
    Used in the admin drill-down panel.
    """
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        SELECT
            a.class_code,
            c.subject,
            c.section,
            TO_CHAR(a.date, 'Mon DD, YYYY')                        AS date_fmt,
            a.session_time,
            COUNT(*)                                                AS total,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)   AS present,
            SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END)   AS absent,
            SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END)   AS late
        FROM attendance a
        JOIN classes c ON c.id = a.class_code
        WHERE c.instructor_id = %s AND a.session_time != 'LIVE'
        GROUP BY a.class_code, c.subject, c.section, a.date, a.session_time
        ORDER BY a.date DESC, a.session_time DESC
        LIMIT %s
    """, (instructor_id, limit))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) for r in rows]