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


# ── CONNECTION CONFIG ─────────────────────────────────────────────────────────
# Change these to match your PostgreSQL / pgAdmin setup

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "attendance_fr",   # create this in pgAdmin first
    "user":     "postgres",
    "password": "kelvin123",    # your pgAdmin password
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
            UNIQUE (class_code, sr_code)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50),
            name        VARCHAR(50)  NOT NULL,
            section     VARCHAR(50),
            subject     VARCHAR(50),
            status      VARCHAR(20)  NOT NULL,
            timestamp   TIMESTAMP(0) DEFAULT NOW(),
            date        DATE         NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code    VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
            instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE,
            time          VARCHAR(50),
            subject       VARCHAR(50),
            room          VARCHAR(50),
            day           VARCHAR(10)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email    VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            status   VARCHAR(20) DEFAULT 'pending'
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


def edit_student(student_db_id, name, address, number,
                 sr_code, age, sex, email):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE students
           SET name=%s, address=%s, number=%s,
               sr_code=%s, age=%s, sex=%s, email=%s
           WHERE id=%s""",
        (name, address, number, sr_code, age, sex, email, student_db_id)
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

def save_attendance(class_code, section, subject, records, date=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    Deletes existing records for this class+date before inserting
    so the teacher can re-save without duplicates.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cur  = get_cursor(conn)

    # Remove existing records for this session (allow re-save)
    cur.execute(
        "DELETE FROM attendance WHERE class_code = %s AND date = %s",
        (class_code, date)
    )

    for r in records:
        # Build full timestamp: combine date + scan time from camera
        # e.g. date="2026-03-16", timestamp="07:02:34" → "2026-03-16 07:02:34"
        scan_time      = r.get("timestamp", "")
        full_timestamp = f"{date} {scan_time}" if scan_time else None

        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                class_code,
                r.get("sr_code", ""),
                r["name"],
                section,
                subject,
                r["status"],
                full_timestamp,   # "2026-03-16 07:02:34" — actual scan time
                date
            )
        )

    conn.commit()
    cur.close(); conn.close()


def get_attendance_session(class_code, date):
    """All attendance rows for one class on one date, sorted Present→Late→Absent."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT * FROM attendance
           WHERE class_code = %s AND date = %s
           ORDER BY
             CASE status
               WHEN 'Present' THEN 1
               WHEN 'Late'    THEN 2
               WHEN 'Absent'  THEN 3
             END,
             name""",
        (class_code, date)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_all_sessions():
    """One row per (class_code, date) — for the History page list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               a.class_code,
               a.date,
               a.section,
               a.subject,
               COUNT(*)                                          AS total,
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


def get_recent_activity(limit=10):
    """Most recent sessions for the dashboard Recent Activities list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               class_code,
               date,
               section,
               subject,
               MIN(timestamp::text) AS time
           FROM attendance
           GROUP BY class_code, date, section, subject
           ORDER BY date DESC, time DESC
           LIMIT %s""",
        (limit,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_absence_counts():
    """Students with at least one absence — for the dashboard chart."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT name, COUNT(*) AS count
           FROM attendance
           WHERE status = 'Absent'
           GROUP BY name
           ORDER BY count DESC"""
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"name": r["name"], "count": r["count"]} for r in rows]


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


def edit_schedule(schedule_id, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "UPDATE schedules SET time=%s, subject=%s, room=%s WHERE id=%s",
        (time, subject, room, schedule_id)
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

def register_instructor(email, password):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "INSERT INTO instructors (email, password, status) VALUES (%s, %s, %s)",
        (email, password, 'pending')
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