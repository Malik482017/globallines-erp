import sqlite3
import os
import requests

DB_NAME = "manpower_data.db"
ATTACHMENTS_DIR = "attachments"

class TursoCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []
        self.lastrowid = None

    def execute(self, sql, params=()):
        args = []
        for p in params:
            if p is None: args.append({"type": "null"})
            elif isinstance(p, bool): args.append({"type": "integer", "value": str(int(p))})
            elif isinstance(p, int): args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float): args.append({"type": "float", "value": p})
            else: args.append({"type": "text", "value": str(p)})
        res = requests.post(self.conn.url, headers=self.conn.headers, json={
            "requests": [{"type": "execute", "stmt": {"sql": sql, "args": args}}, {"type": "close"}]
        }, timeout=15).json()
        r0 = res["results"][0]
        if r0["type"] == "error":
            raise sqlite3.OperationalError(r0["error"]["message"])
        resp = r0["response"]["result"]
        self.lastrowid = resp.get("last_insert_rowid")
        self._rows = [tuple(None if c["type"] == "null" else (int(c["value"]) if c["type"] == "integer" else (float(c["value"]) if c["type"] == "float" else c["value"])) for c in row) for row in resp.get("rows", [])]
        return self

    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None

class TursoConn:
    def __init__(self, url, token):
        self.url = url.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    def cursor(self): return TursoCursor(self)
    def execute(self, sql, params=()): return self.cursor().execute(sql, params)
    def commit(self): pass
    def close(self): pass

def get_conn():
    try:
        import streamlit as st
        if "TURSO_URL" in st.secrets and "TURSO_TOKEN" in st.secrets:
            return TursoConn(st.secrets["TURSO_URL"], st.secrets["TURSO_TOKEN"])
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
