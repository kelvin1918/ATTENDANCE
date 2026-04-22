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


# ── CONNECTION CONFIG ─────────────────────────────────────────────────────────
# Change these to match your PostgreSQL / pgAdmin setup

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "ep-cool-darkness-ao4fnwdj-pooler.c-2.ap-southeast-1.aws.neon.tech"),
    "port":     int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME",     "neondb"),
    "user":     os.environ.get("DB_USER",     "neondb_owner"),
    "password": os.environ.get(""),
    "sslmode":  "require"
}

DB_CONFIG_LOCAL = {
    "host":     "localhost",
    "port":     5432,
    "database": "attendance_fr",   # the database you created in pgAdmin
    "user":     "postgres",        # default PostgreSQL username
    "password": "kelvin123",   # your pgAdmin/PostgreSQL password
}


# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db():
    """Returns a PostgreSQL connection."""
    conn = psycopg2.connect(**DB_CONFIG)

    return conn


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

    # ── 7. camera_sessions — agent polls this to know when to start/stop ────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS camera_sessions (
            id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            instructor_id INTEGER UNIQUE REFERENCES instructors(id) ON DELETE CASCADE,
            class_code    VARCHAR(50),
            section       VARCHAR(50),
            subject       VARCHAR(50),
            source        TEXT    DEFAULT '0',
            status        VARCHAR(20) DEFAULT 'idle',
            updated_at    TIMESTAMP DEFAULT NOW()
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

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] PostgreSQL tables ready.")


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
                sr_code, age, sex, email, photo, signature):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """INSERT INTO students
           (class_code, name, address, number,
            sr_code, age, sex, email, photo, signature)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (class_code, name, address, number,
         sr_code, age, sex, email, photo, signature)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_student(student_db_id, name=None, address=None, number=None,
                 sr_code=None, age=None, sex=None, email=None, status=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if status and name is None:
        # Status-only update (from folder view dropdown)
        cur.execute(
            "UPDATE students SET status=%s WHERE id=%s",
            (status, student_db_id)
        )
    else:
        cur.execute(
            """UPDATE students
               SET name=%s, address=%s, number=%s,
                   sr_code=%s, age=%s, sex=%s, email=%s, status=COALESCE(%s, status)
               WHERE id=%s""",
            (name, address, number, sr_code, age, sex, email, status, student_db_id)
        )
    conn.commit()
    cur.close(); conn.close()


def delete_student(student_db_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM students WHERE id = %s", (student_db_id,))
    conn.commit()
    cur.close(); conn.close()


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
               WHERE c.instructor_id = %s
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
           WHERE a.class_code = %s
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
               WHERE c.instructor_id = %s
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
                   , 1)                                             AS pct_absent
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s
               GROUP BY a.subject
               ORDER BY pct_absent DESC""",
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
                   , 1)                                             AS pct_absent
               FROM attendance a
               GROUP BY a.subject
               ORDER BY pct_absent DESC"""
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {
            "name":          r["name"],
            "total_absent":  r["total_absent"],
            "total_records": r["total_records"],
            "total_sessions":r["total_sessions"],
            "avg_absent":    float(r["avg_absent"]  or 0),
            "pct_absent":    float(r["pct_absent"]  or 0),
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
    """Check if a student already has an attendance record for today's session."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        """SELECT id FROM attendance
           WHERE class_code = %s AND name = %s AND date = %s
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

# ── CAMERA SESSION (Agent Control) ───────────────────────────────────────────

def upsert_camera_session(instructor_id, class_code, section, subject, source, status):
    """Create or update the camera session row for this instructor."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        INSERT INTO camera_sessions (instructor_id, class_code, section, subject, source, status, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (instructor_id) DO UPDATE
            SET class_code = EXCLUDED.class_code,
                section    = EXCLUDED.section,
                subject    = EXCLUDED.subject,
                source     = EXCLUDED.source,
                status     = EXCLUDED.status,
                updated_at = NOW()
    """, (instructor_id, class_code, section, subject, source, status))
    conn.commit(); cur.close(); conn.close()

def get_camera_session(instructor_id):
    """Get current camera session for an instructor."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM camera_sessions WHERE instructor_id=%s", (instructor_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def get_camera_session_by_email(email):
    """Get camera session by instructor email — used by the agent."""
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("""
        SELECT cs.*, i.email, i.name as instructor_name
        FROM camera_sessions cs
        JOIN instructors i ON i.id = cs.instructor_id
        WHERE i.email = %s
    """, (email,))
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