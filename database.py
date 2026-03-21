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
import os
from datetime import datetime

DATABASE = "attendance.db"


# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db():
    
    """
    Returns a database connection.
    SQLite: uses attendance.db file in project root.

    To switch to PostgreSQL, replace with:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="attendance_db",
            user="postgres",
            password="yourpassword"
        )
        return conn
    """


    conn = psycopg2.connect(
            host="localhost",
            database="attendance_db",
            user="postgres",
            password="kelvin123"
        )
    return conn

    """""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # rows behave like dicts: row["name"]
    return conn
    """""




# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    """
    Creates all tables if they don't exist yet.
    Called once when app.py starts.
    """
    db = get_db()
    db.executescript("""

        -- Class folders (subject + section)
        CREATE TABLE IF NOT EXISTS classes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT    NOT NULL,
            section     TEXT    NOT NULL,
            created     TEXT    NOT NULL
        );

        -- Students enrolled in a class
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code    INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            address     TEXT,
            number      TEXT,
            sr_code     TEXT,
            age         INTEGER,
            sex         TEXT,
            email       TEXT,
            photo       TEXT,
            signature   TEXT,
            FOREIGN KEY (class_code) REFERENCES classes(id)
        );

        -- Attendance records per session
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code     INTEGER NOT NULL,
            student_id  TEXT,
            name        TEXT    NOT NULL,
            section     TEXT,
            room        TEXT,
            instructor   TEXT,
            subject     TEXT,
            status      TEXT    NOT NULL,  -- 'Present', 'Late', 'Absent'
            timestamp   TEXT,
            date        TEXT    NOT NULL,
            FOREIGN KEY (class_code) REFERENCES classes(id)
        );

        -- Right panel schedule items
        CREATE TABLE IF NOT EXISTS schedules (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            time    TEXT,
            subject TEXT,
            room    TEXT
        );

    """)
    db.commit()
    db.close()
    print("[DB] Tables ready.")


# ── CLASSES ───────────────────────────────────────────────────────────────────

def get_all_classes():
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM classes ORDER BY id DESC"
    ).fetchall()
    db.close()
    return rows


def get_class(class_code):
    db  = get_db()
    row = db.execute(
        "SELECT * FROM classes WHERE id = ?", (class_code,)
    ).fetchone()
    db.close()
    return row


def create_class(subject, section):
    db = get_db()
    db.execute(
        "INSERT INTO classes (subject, section, created) VALUES (?, ?, ?)",
        (subject, section, datetime.now().strftime("%Y-%m-%d"))
    )
    db.commit()
    db.close()


def edit_class(class_code, subject, section):
    db = get_db()
    db.execute(
        "UPDATE classes SET subject = ?, section = ? WHERE id = ?",
        (subject, section, class_code)
    )
    db.commit()
    db.close()


def delete_class(class_code):
    db = get_db()
    db.execute("DELETE FROM classes    WHERE id       = ?", (class_code,))
    db.execute("DELETE FROM students   WHERE class_code = ?", (class_code,))
    db.execute("DELETE FROM attendance WHERE class_code = ?", (class_code,))
    db.commit()
    db.close()


# ── STUDENTS ──────────────────────────────────────────────────────────────────

def get_students(class_code):
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM students WHERE class_code = ? ORDER BY name",
        (class_code,)
    ).fetchall()
    db.close()
    return rows


def get_student(student_db_id):
    db  = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE id = ?", (student_db_id,)
    ).fetchone()
    db.close()
    return row


def add_student(class_code, name, address, number,
                sr_code, age, sex, email, photo, signature):
    db = get_db()
    db.execute(
        """INSERT INTO students
           (class_code, name, address, number, sr_code, age, sex, email, photo, signature)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (class_code, name, address, number,
         sr_code, age, sex, email, photo, signature)
    )
    db.commit()
    db.close()


def edit_student(student_db_id, name, address, number,
                 sr_code, age, sex, email):
    db = get_db()
    db.execute(
        """UPDATE students
           SET name=?, address=?, number=?, sr_code=?, age=?, sex=?, email=?
           WHERE id=?""",
        (name, address, number, sr_code, age, sex, email, student_db_id)
    )
    db.commit()
    db.close()


def delete_student(student_db_id):
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_db_id,))
    db.commit()
    db.close()


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

def save_attendance(class_code, section, subject, records, date=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "student_id": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    db = get_db()

    # Remove any existing records for this class+date (allow re-save)
    db.execute(
        "DELETE FROM attendance WHERE class_code = ? AND date = ?",
        (class_code, date)
    )

    for r in records:
        db.execute(
            """INSERT INTO attendance
               (class_code, student_id, name, section, subject,
                status, timestamp, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (class_code, r.get("student_id", ""),
             r["name"], section, subject,
             r["status"], r.get("timestamp", ""), date)
        )

    db.commit()
    db.close()


def get_attendance_session(class_code, date):
    """Returns all attendance rows for one class on one date."""
    db   = get_db()
    rows = db.execute(
        """SELECT * FROM attendance
           WHERE class_code = ? AND date = ?
           ORDER BY
             CASE status
               WHEN 'Present' THEN 1
               WHEN 'Late'    THEN 2
               WHEN 'Absent'  THEN 3
             END,
             name""",
        (class_code, date)
    ).fetchall()
    db.close()
    return rows


def get_all_sessions():
    """
    Returns one row per (class_code, date) combination — for the History page.
    """
    db   = get_db()
    rows = db.execute(
        """SELECT
               a.class_code,
               a.date,
               a.section,
               a.subject,
               COUNT(*) AS total,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status = 'Late'    THEN 1 ELSE 0 END) AS late,
               SUM(CASE WHEN a.status = 'Absent'  THEN 1 ELSE 0 END) AS absent
           FROM attendance a
           GROUP BY a.class_code, a.date
           ORDER BY a.date DESC""",
    ).fetchall()
    db.close()
    return rows


def get_recent_activity(limit=10):
    """
    Returns the most recent attendance sessions for the dashboard.
    One row per (class_id, date) — shown in Recent Activities list.
    """
    db   = get_db()
    rows = db.execute(
        """SELECT
               class_id,
               date,
               section,
               subject,
               MIN(timestamp) AS time
           FROM attendance
           GROUP BY class_id, date
           ORDER BY date DESC, time DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    db.close()
    return rows


def get_absence_counts():
    """
    Returns students who have at least one absence — for the dashboard chart.
    [{"name": "JohnDoe", "count": 3}, ...]
    """
    db   = get_db()
    rows = db.execute(
        """SELECT name, COUNT(*) AS count
           FROM attendance
           WHERE status = 'Absent'
           GROUP BY name
           ORDER BY count DESC"""
    ).fetchall()
    db.close()
    return [{"name": r["name"], "count": r["count"]} for r in rows]


# ── SCHEDULES ─────────────────────────────────────────────────────────────────

def get_schedules():
    db   = get_db()
    rows = db.execute("SELECT * FROM schedules ORDER BY id").fetchall()
    db.close()
    return rows


def add_schedule(time, subject, room):
    db = get_db()
    db.execute(
        "INSERT INTO schedules (time, subject, room) VALUES (?, ?, ?)",
        (time, subject, room)
    )
    db.commit()
    db.close()


def edit_schedule(schedule_id, time, subject, room):
    db = get_db()
    db.execute(
        "UPDATE schedules SET time=?, subject=?, room=? WHERE id=?",
        (time, subject, room, schedule_id)
    )
    db.commit()
    db.close()


def delete_schedule(schedule_id):
    db = get_db()
    db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    db.commit()
    db.close()