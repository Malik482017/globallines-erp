import sqlite3
import os

DB_NAME = "manpower_data.db"
ATTACHMENTS_DIR = "attachments"

def get_conn():
    try:
        import streamlit as st
        if "TURSO_URL" in st.secrets and "TURSO_TOKEN" in st.secrets:
            import libsql_experimental as libsql
            return libsql.connect(DB_NAME, sync_url=st.secrets["TURSO_URL"], auth_token=st.secrets["TURSO_TOKEN"])
    except Exception:
        pass
    return sqlite3.connect(DB_NAME)

def init_db():
    if not os.path.exists(ATTACHMENTS_DIR):
        os.makedirs(ATTACHMENTS_DIR)

    conn = get_conn()
    if hasattr(conn, "sync"):
        conn.sync()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ar TEXT NOT NULL,
        name_en TEXT NOT NULL,
        cr_number TEXT,
        phone TEXT,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ar TEXT NOT NULL,
        name_en TEXT NOT NULL,
        id_type TEXT DEFAULT 'C',
        passport_id TEXT,
        bank_bic TEXT DEFAULT 'BMUSOMRX',
        bank_account TEXT DEFAULT 'OM000000000000000000',
        trade TEXT NOT NULL,
        daily_rate REAL NOT NULL,
        agreed_daily_hours REAL NOT NULL DEFAULT 10.0,
        ot_rate REAL NOT NULL DEFAULT 0.6,
        standard_days INTEGER NOT NULL DEFAULT 30,
        client_hourly_rate REAL NOT NULL,
        client_id INTEGER,
        salary_due_day INTEGER DEFAULT 28,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS timesheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        month_year TEXT NOT NULL,
        working_days REAL NOT NULL,
        actual_hours REAL DEFAULT 0,
        ot_hours REAL DEFAULT 0,
        advance_salary REAL DEFAULT 0,
        shortage_days REAL DEFAULT 0,
        shortage_hours REAL DEFAULT 0,
        deduction_amount REAL DEFAULT 0,
        net_salary REAL NOT NULL,
        billed_hours REAL NOT NULL,
        invoice_amount REAL NOT NULL,
        remarks TEXT,
        attachment_path TEXT,
        FOREIGN KEY (worker_id) REFERENCES workers(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_year TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT
    )
    """)

    for sql in (
        "ALTER TABLE workers ADD COLUMN agreed_daily_hours REAL DEFAULT 10.0",
        "ALTER TABLE timesheets ADD COLUMN actual_hours REAL DEFAULT 0",
        "ALTER TABLE timesheets ADD COLUMN shortage_hours REAL DEFAULT 0"
    ):
        try:
            cur.execute(sql)
        except Exception:
            pass

    conn.commit()
    if hasattr(conn, "sync"):
        conn.sync()
    conn.close()
