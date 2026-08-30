import sqlite3
from datetime import datetime
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tutors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subjects TEXT NOT NULL,
                mode TEXT NOT NULL,
                experience_years INTEGER DEFAULT 0,
                rate_etb INTEGER DEFAULT 0,
                bio TEXT DEFAULT '',
                telegram_id INTEGER,
                verified INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tutor_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                email TEXT,
                phone TEXT,
                subjects TEXT,
                mode TEXT,
                experience_years INTEGER,
                rate_etb INTEGER,
                bio TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                parent_name TEXT,
                email TEXT,
                phone TEXT,
                student_level TEXT,
                subject TEXT,
                message TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tutor_id INTEGER,
                chat_id INTEGER,
                parent_name TEXT,
                contact TEXT,
                preferred_time TEXT,
                message TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                FOREIGN KEY (tutor_id) REFERENCES tutors(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                subject TEXT,
                budget TEXT,
                mode TEXT,
                learning_style TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_users (
                chat_id INTEGER PRIMARY KEY,
                role TEXT,
                created_at TEXT
            )
        """)
        # Seed with the one live tutor from the website, if table is empty.
        row = conn.execute("SELECT COUNT(*) AS c FROM tutors").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO tutors (name, subjects, mode, experience_years, rate_etb, bio, verified, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "Michael Andualem",
                    "Mathematics,Physics,Biology,English",
                    "Hybrid",
                    1,
                    500,
                    "Previous experience with tutoring.",
                    1,
                    datetime.utcnow().isoformat(),
                ),
            )


def now():
    return datetime.utcnow().isoformat()


# ---------- Tutors ----------

def list_tutors(subject=None, mode=None, verified_only=True):
    query = "SELECT * FROM tutors WHERE 1=1"
    params = []
    if verified_only:
        query += " AND verified = 1"
    if subject:
        query += " AND subjects LIKE ?"
        params.append(f"%{subject}%")
    if mode:
        query += " AND mode = ?"
        params.append(mode)
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def get_tutor(tutor_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tutors WHERE id = ?", (tutor_id,)).fetchone()


def add_tutor(name, subjects, mode, experience_years, rate_etb, bio, telegram_id=None, verified=0):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tutors (name, subjects, mode, experience_years, rate_etb, bio, telegram_id, verified, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, subjects, mode, experience_years, rate_etb, bio, telegram_id, verified, now()),
        )
        return cur.lastrowid


# ---------- Tutor applications ----------

def add_tutor_application(chat_id, name, email, phone, subjects, mode, experience_years, rate_etb, bio):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tutor_applications (chat_id, name, email, phone, subjects, mode, experience_years, rate_etb, bio, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (chat_id, name, email, phone, subjects, mode, experience_years, rate_etb, bio, now()),
        )
        return cur.lastrowid


def list_pending_applications():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tutor_applications WHERE status = 'pending' ORDER BY id DESC"
        ).fetchall()


def get_application(app_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tutor_applications WHERE id = ?", (app_id,)).fetchone()


def approve_application(app_id):
    app = get_application(app_id)
    if not app or app["status"] != "pending":
        return None
    tutor_id = add_tutor(
        app["name"], app["subjects"], app["mode"], app["experience_years"],
        app["rate_etb"], app["bio"], app["chat_id"], verified=1,
    )
    with get_conn() as conn:
        conn.execute("UPDATE tutor_applications SET status = 'approved' WHERE id = ?", (app_id,))
    return tutor_id


def reject_application(app_id):
    with get_conn() as conn:
        conn.execute("UPDATE tutor_applications SET status = 'rejected' WHERE id = ?", (app_id,))


# ---------- Enquiries ----------

def add_enquiry(chat_id, parent_name, email, phone, student_level, subject, message):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO enquiries (chat_id, parent_name, email, phone, student_level, subject, message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, parent_name, email, phone, student_level, subject, message, now()),
        )
        return cur.lastrowid


def list_recent_enquiries(limit=10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM enquiries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


# ---------- Bookings ----------

def add_booking(tutor_id, chat_id, parent_name, contact, preferred_time, message):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO bookings (tutor_id, chat_id, parent_name, contact, preferred_time, message, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
            (tutor_id, chat_id, parent_name, contact, preferred_time, message, now()),
        )
        return cur.lastrowid


def list_recent_bookings(limit=10):
    with get_conn() as conn:
        return conn.execute("""
            SELECT bookings.*, tutors.name AS tutor_name
            FROM bookings LEFT JOIN tutors ON bookings.tutor_id = tutors.id
            ORDER BY bookings.id DESC LIMIT ?
        """, (limit,)).fetchall()


# ---------- Bot users (role: 'parent' or 'tutor') ----------

def set_user_role(chat_id, role):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bot_users (chat_id, role, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET role = excluded.role",
            (chat_id, role, now()),
        )


def get_user_role(chat_id):
    with get_conn() as conn:
        row = conn.execute("SELECT role FROM bot_users WHERE chat_id = ?", (chat_id,)).fetchone()
        return row["role"] if row else None


def get_latest_application_for_chat(chat_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tutor_applications WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()


def get_tutor_by_chat(chat_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tutors WHERE telegram_id = ? ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()


# ---------- Quiz leads ----------

def add_quiz_lead(chat_id, subject, budget, mode, learning_style):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO quiz_leads (chat_id, subject, budget, mode, learning_style, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, subject, budget, mode, learning_style, now()),
        )
        return cur.lastrowid
