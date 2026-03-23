"""
database.py
============
Handles all database operations for the Attendance Monitoring System.
Uses SQLite by default (attendance.db) — swap to PostgreSQL by changing get_db().

Tables:
    classes      — subject + section folders
    students     — student records per class
    attendance   — daily attendance records
    schedules    — right panel schedule items
"""

import psycopg2
import psycopg2.extras   # for RealDictCursor (rows behave like dicts)
from datetime import datetime

DATABASE = "attendance.db"

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "attendance_fr",   # the database you created in pgAdmin
    "user":     "postgres",        # default PostgreSQL username
    "password": "kelvin123",   # your pgAdmin/PostgreSQL password
}

# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db(): # dito makikita at ma dedefine ang database connection sa Pgadmin
    
    """
    Returns a psycopg2 connection.
    RealDictCursor makes rows behave like dicts: row["name"]
    """

    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def get_cursor(conn):
    """Returns a RealDictCursor — rows come back as dicts automatically."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
 

# ── INIT — creates all tables ─────────────────────────────────────────────────
 
def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id           VARCHAR(50)  PRIMARY KEY,
            course_code  VARCHAR(20)  NOT NULL,
            subject      VARCHAR(50),
            section      VARCHAR(50),
            created      DATE DEFAULT CURRENT_DATE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name       VARCHAR(50)  NOT NULL,
            address    VARCHAR(100),
            number     VARCHAR(50),
            sr_code    VARCHAR(50)  UNIQUE,  --  unique for referencing
            age        INTEGER,
            sex        VARCHAR(10),
            email      VARCHAR(100),
            photo      TEXT,
            signature  TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50)  REFERENCES students(sr_code),  -- ✅ linked to students
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
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
            time        VARCHAR(50),
            subject     VARCHAR(50),
            room        VARCHAR(50)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] PostgreSQL tables ready.")
 


# ── CLASSES ───────────────────────────────────────────────────────────────────

def get_all_classes():
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_class(class_code):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes WHERE id = %s", (class_code,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def create_class(class_code, course_code, subject, section):
    conn = get_db()
    cur  = conn.cursor()
    created = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        "INSERT INTO classes (id, course_code, subject, section, created) VALUES (%s, %s, %s, %s, %s)",
        (class_code, course_code, subject, section, created)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_class(class_code, course_code, subject, section):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
    """UPDATE classes 
        SET course_code = %s, subject = %s, section = %s
        WHERE id = %s""",
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
    """Get all students in a class."""
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
    cur  = conn.cursor()
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
    cur  = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = %s", (student_db_id,))
    conn.commit()
    cur.close(); conn.close()


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

def save_attendance(class_code, section, subject, records, date=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "student_id": "2021-0001",
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
 
    # Remove existing records for this class+date before re-saving
    cur.execute(
        "DELETE FROM attendance WHERE class_code = %s AND date = %s",
        (class_code, date)
    )
 
    for r in records:
        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject,
                status, timestamp, date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                class_code, 
                r.get("student_id", ""),
                r["name"],
                section, 
                subject,
                r["status"], 
                r.get("timestamp", ""), #forgotten
                date)
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

def get_schedules(class_code=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if class_code:
        cur.execute(
            "SELECT * FROM schedules WHERE class_code = %s ORDER BY id",
            (class_code,)
        )
    else:
        cur.execute("SELECT * FROM schedules ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def add_schedule(class_code, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "INSERT INTO schedules (class_code, time, subject, room) VALUES (%s,%s,%s,%s)",
        (class_code, time, subject, room)
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