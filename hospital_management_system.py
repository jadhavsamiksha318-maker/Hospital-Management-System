"""
================================================================================
  SMART HOSPITAL MANAGEMENT SYSTEM
  A complete, professional desktop application for hospital administration.
  Built with Python, Tkinter, and SQLite.
  
  Modules:
    - Login System (Admin, Doctor, Receptionist)
    - Dashboard with live statistics
    - Patient Registration & Management
    - Doctor Management
    - Appointment Scheduling
    - Billing & Invoice Generation
    - Medicine Inventory
    - Medical History Tracking
    - CSV Export

  Run:  python hospital_management_system.py
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
import csv
import os
import re
import random
import string
from datetime import datetime, date
from functools import partial


# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR & STYLE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
COLOR = {
    "bg_dark":      "#0D1B2A",
    "bg_mid":       "#1B2838",
    "bg_card":      "#1E3448",
    "accent":       "#00B4D8",
    "accent2":      "#0077B6",
    "success":      "#2EC4B6",
    "warning":      "#FFB703",
    "danger":       "#E63946",
    "text_light":   "#E0E9F0",
    "text_dim":     "#8BA3B5",
    "border":       "#2A4560",
    "white":        "#FFFFFF",
    "highlight":    "#023E8A",
}

FONT = {
    "title":    ("Segoe UI", 22, "bold"),
    "heading":  ("Segoe UI", 14, "bold"),
    "subhead":  ("Segoe UI", 11, "bold"),
    "body":     ("Segoe UI", 10),
    "small":    ("Segoe UI", 9),
    "mono":     ("Courier New", 10),
}


# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────────────────────────────────────
class Database:
    """Handles all SQLite operations. Creates and migrates the schema on first run."""

    DB_FILE = "hospital.db"

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_FILE)
        self.conn.row_factory = sqlite3.Row          # dict-like rows
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._seed_default_users()

    # ── Schema ──────────────────────────────────────────────────────────────
    def _create_schema(self):
        cur = self.conn.cursor()

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('Admin','Doctor','Receptionist')),
                full_name   TEXT    NOT NULL,
                email       TEXT,
                phone       TEXT,
                active      INTEGER DEFAULT 1,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS doctors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id       TEXT    UNIQUE NOT NULL,
                full_name       TEXT    NOT NULL,
                specialization  TEXT    NOT NULL,
                qualification   TEXT,
                phone           TEXT,
                email           TEXT,
                fee             REAL    DEFAULT 0,
                available_days  TEXT,
                active          INTEGER DEFAULT 1,
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS patients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id      TEXT    UNIQUE NOT NULL,
                full_name       TEXT    NOT NULL,
                dob             TEXT,
                gender          TEXT,
                blood_group     TEXT,
                phone           TEXT,
                email           TEXT,
                address         TEXT,
                emergency_contact TEXT,
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id  TEXT    UNIQUE NOT NULL,
                patient_id      TEXT    NOT NULL,
                doctor_id       TEXT    NOT NULL,
                appt_date       TEXT    NOT NULL,
                appt_time       TEXT    NOT NULL,
                reason          TEXT,
                status          TEXT    DEFAULT 'Scheduled'
                                        CHECK(status IN ('Scheduled','Completed','Cancelled','No-Show')),
                notes           TEXT,
                created_at      TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY(doctor_id)  REFERENCES doctors(doctor_id)
            );

            CREATE TABLE IF NOT EXISTS billing (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id      TEXT    UNIQUE NOT NULL,
                patient_id      TEXT    NOT NULL,
                appointment_id  TEXT,
                total_amount    REAL    DEFAULT 0,
                paid_amount     REAL    DEFAULT 0,
                discount        REAL    DEFAULT 0,
                payment_method  TEXT    DEFAULT 'Cash',
                status          TEXT    DEFAULT 'Pending'
                                        CHECK(status IN ('Pending','Paid','Partial','Cancelled')),
                items_json      TEXT,
                created_at      TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
            );

            CREATE TABLE IF NOT EXISTS medicines (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                medicine_id     TEXT    UNIQUE NOT NULL,
                name            TEXT    NOT NULL,
                category        TEXT,
                manufacturer    TEXT,
                unit            TEXT    DEFAULT 'pcs',
                price           REAL    DEFAULT 0,
                stock           INTEGER DEFAULT 0,
                min_stock       INTEGER DEFAULT 10,
                expiry_date     TEXT,
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS medical_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id      TEXT    NOT NULL,
                visit_date      TEXT    NOT NULL,
                doctor_id       TEXT,
                diagnosis       TEXT,
                symptoms        TEXT,
                prescription    TEXT,
                notes           TEXT,
                created_at      TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
            );
        """)
        self.conn.commit()

    # ── Seed ────────────────────────────────────────────────────────────────
    def _seed_default_users(self):
        """Insert default admin / doctor / receptionist accounts if none exist."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            defaults = [
                ("admin",       "admin123",   "Admin",         "System Administrator"),
                ("doctor1",     "doctor123",  "Doctor",        "Dr. Sarah Johnson"),
                ("reception1",  "recep123",   "Receptionist",  "Mary Williams"),
            ]
            for uname, pw, role, name in defaults:
                self.create_user(uname, pw, role, name)

    # ── Helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def hash_password(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def gen_id(prefix: str, length: int = 6) -> str:
        digits = "".join(random.choices(string.digits, k=length))
        return f"{prefix}{digits}"

    # ── USERS ────────────────────────────────────────────────────────────────
    def create_user(self, username, password, role, full_name, email="", phone=""):
        try:
            self.conn.execute(
                "INSERT INTO users(username,password,role,full_name,email,phone) VALUES(?,?,?,?,?,?)",
                (username, self.hash_password(password), role, full_name, email, phone)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate(self, username: str, password: str):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND active=1",
            (username, self.hash_password(password))
        ).fetchone()
        return dict(row) if row else None

    def get_all_users(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,username,role,full_name,email,phone,active,created_at FROM users ORDER BY id"
        ).fetchall()]

    # ── PATIENTS ─────────────────────────────────────────────────────────────
    def add_patient(self, **kw):
        pid = self.gen_id("P")
        while self.conn.execute("SELECT 1 FROM patients WHERE patient_id=?", (pid,)).fetchone():
            pid = self.gen_id("P")
        self.conn.execute(
            """INSERT INTO patients(patient_id,full_name,dob,gender,blood_group,
               phone,email,address,emergency_contact) VALUES(?,?,?,?,?,?,?,?,?)""",
            (pid, kw["full_name"], kw.get("dob",""), kw.get("gender",""),
             kw.get("blood_group",""), kw.get("phone",""), kw.get("email",""),
             kw.get("address",""), kw.get("emergency_contact",""))
        )
        self.conn.commit()
        return pid

    def update_patient(self, pid, **kw):
        self.conn.execute(
            """UPDATE patients SET full_name=?,dob=?,gender=?,blood_group=?,
               phone=?,email=?,address=?,emergency_contact=? WHERE patient_id=?""",
            (kw["full_name"], kw.get("dob",""), kw.get("gender",""),
             kw.get("blood_group",""), kw.get("phone",""), kw.get("email",""),
             kw.get("address",""), kw.get("emergency_contact",""), pid)
        )
        self.conn.commit()

    def delete_patient(self, pid):
        self.conn.execute("DELETE FROM patients WHERE patient_id=?", (pid,))
        self.conn.commit()

    def get_patients(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute(
            """SELECT * FROM patients
               WHERE full_name LIKE ? OR patient_id LIKE ? OR phone LIKE ?
               ORDER BY created_at DESC""", (q, q, q)
        ).fetchall()]

    def get_patient_by_id(self, pid):
        row = self.conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
        return dict(row) if row else None

    # ── DOCTORS ──────────────────────────────────────────────────────────────
    def add_doctor(self, **kw):
        did = self.gen_id("D")
        while self.conn.execute("SELECT 1 FROM doctors WHERE doctor_id=?", (did,)).fetchone():
            did = self.gen_id("D")
        self.conn.execute(
            """INSERT INTO doctors(doctor_id,full_name,specialization,qualification,
               phone,email,fee,available_days) VALUES(?,?,?,?,?,?,?,?)""",
            (did, kw["full_name"], kw.get("specialization",""), kw.get("qualification",""),
             kw.get("phone",""), kw.get("email",""), kw.get("fee",0), kw.get("available_days",""))
        )
        self.conn.commit()
        return did

    def update_doctor(self, did, **kw):
        self.conn.execute(
            """UPDATE doctors SET full_name=?,specialization=?,qualification=?,
               phone=?,email=?,fee=?,available_days=? WHERE doctor_id=?""",
            (kw["full_name"], kw.get("specialization",""), kw.get("qualification",""),
             kw.get("phone",""), kw.get("email",""), kw.get("fee",0),
             kw.get("available_days",""), did)
        )
        self.conn.commit()

    def delete_doctor(self, did):
        self.conn.execute("DELETE FROM doctors WHERE doctor_id=?", (did,))
        self.conn.commit()

    def get_doctors(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute(
            """SELECT * FROM doctors
               WHERE full_name LIKE ? OR doctor_id LIKE ? OR specialization LIKE ?
               ORDER BY full_name""", (q, q, q)
        ).fetchall()]

    def get_doctor_by_id(self, did):
        row = self.conn.execute("SELECT * FROM doctors WHERE doctor_id=?", (did,)).fetchone()
        return dict(row) if row else None

    # ── APPOINTMENTS ─────────────────────────────────────────────────────────
    def add_appointment(self, **kw):
        aid = self.gen_id("A")
        while self.conn.execute("SELECT 1 FROM appointments WHERE appointment_id=?", (aid,)).fetchone():
            aid = self.gen_id("A")
        self.conn.execute(
            """INSERT INTO appointments(appointment_id,patient_id,doctor_id,
               appt_date,appt_time,reason,status,notes) VALUES(?,?,?,?,?,?,?,?)""",
            (aid, kw["patient_id"], kw["doctor_id"], kw["appt_date"],
             kw["appt_time"], kw.get("reason",""), kw.get("status","Scheduled"), kw.get("notes",""))
        )
        self.conn.commit()
        return aid

    def update_appointment(self, aid, **kw):
        self.conn.execute(
            """UPDATE appointments SET patient_id=?,doctor_id=?,appt_date=?,appt_time=?,
               reason=?,status=?,notes=? WHERE appointment_id=?""",
            (kw["patient_id"], kw["doctor_id"], kw["appt_date"], kw["appt_time"],
             kw.get("reason",""), kw.get("status","Scheduled"), kw.get("notes",""), aid)
        )
        self.conn.commit()

    def delete_appointment(self, aid):
        self.conn.execute("DELETE FROM appointments WHERE appointment_id=?", (aid,))
        self.conn.commit()

    def get_appointments(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute(
            """SELECT a.*,
                      p.full_name AS patient_name,
                      d.full_name AS doctor_name
               FROM appointments a
               LEFT JOIN patients p ON a.patient_id = p.patient_id
               LEFT JOIN doctors  d ON a.doctor_id  = d.doctor_id
               WHERE a.appointment_id LIKE ? OR p.full_name LIKE ?
                  OR d.full_name LIKE ? OR a.appt_date LIKE ?
               ORDER BY a.appt_date DESC, a.appt_time""",
            (q, q, q, q)
        ).fetchall()]

    # ── BILLING ───────────────────────────────────────────────────────────────
    def add_invoice(self, **kw):
        iid = self.gen_id("INV", 8)
        while self.conn.execute("SELECT 1 FROM billing WHERE invoice_id=?", (iid,)).fetchone():
            iid = self.gen_id("INV", 8)
        self.conn.execute(
            """INSERT INTO billing(invoice_id,patient_id,appointment_id,total_amount,
               paid_amount,discount,payment_method,status,items_json) VALUES(?,?,?,?,?,?,?,?,?)""",
            (iid, kw["patient_id"], kw.get("appointment_id",""),
             kw.get("total_amount",0), kw.get("paid_amount",0), kw.get("discount",0),
             kw.get("payment_method","Cash"), kw.get("status","Pending"), kw.get("items_json","[]"))
        )
        self.conn.commit()
        return iid

    def update_invoice(self, iid, **kw):
        self.conn.execute(
            """UPDATE billing SET paid_amount=?,discount=?,payment_method=?,status=?
               WHERE invoice_id=?""",
            (kw.get("paid_amount",0), kw.get("discount",0),
             kw.get("payment_method","Cash"), kw.get("status","Pending"), iid)
        )
        self.conn.commit()

    def get_invoices(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute(
            """SELECT b.*, p.full_name AS patient_name
               FROM billing b
               LEFT JOIN patients p ON b.patient_id = p.patient_id
               WHERE b.invoice_id LIKE ? OR p.full_name LIKE ? OR b.status LIKE ?
               ORDER BY b.created_at DESC""",
            (q, q, q)
        ).fetchall()]

    # ── MEDICINES ─────────────────────────────────────────────────────────────
    def add_medicine(self, **kw):
        mid = self.gen_id("M")
        while self.conn.execute("SELECT 1 FROM medicines WHERE medicine_id=?", (mid,)).fetchone():
            mid = self.gen_id("M")
        self.conn.execute(
            """INSERT INTO medicines(medicine_id,name,category,manufacturer,unit,
               price,stock,min_stock,expiry_date) VALUES(?,?,?,?,?,?,?,?,?)""",
            (mid, kw["name"], kw.get("category",""), kw.get("manufacturer",""),
             kw.get("unit","pcs"), kw.get("price",0), kw.get("stock",0),
             kw.get("min_stock",10), kw.get("expiry_date",""))
        )
        self.conn.commit()
        return mid

    def update_medicine(self, mid, **kw):
        self.conn.execute(
            """UPDATE medicines SET name=?,category=?,manufacturer=?,unit=?,
               price=?,stock=?,min_stock=?,expiry_date=? WHERE medicine_id=?""",
            (kw["name"], kw.get("category",""), kw.get("manufacturer",""),
             kw.get("unit","pcs"), kw.get("price",0), kw.get("stock",0),
             kw.get("min_stock",10), kw.get("expiry_date",""), mid)
        )
        self.conn.commit()

    def delete_medicine(self, mid):
        self.conn.execute("DELETE FROM medicines WHERE medicine_id=?", (mid,))
        self.conn.commit()

    def get_medicines(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute(
            """SELECT * FROM medicines
               WHERE name LIKE ? OR medicine_id LIKE ? OR category LIKE ?
               ORDER BY name""", (q, q, q)
        ).fetchall()]

    # ── MEDICAL HISTORY ───────────────────────────────────────────────────────
    def add_history(self, **kw):
        self.conn.execute(
            """INSERT INTO medical_history(patient_id,visit_date,doctor_id,
               diagnosis,symptoms,prescription,notes) VALUES(?,?,?,?,?,?,?)""",
            (kw["patient_id"], kw["visit_date"], kw.get("doctor_id",""),
             kw.get("diagnosis",""), kw.get("symptoms",""),
             kw.get("prescription",""), kw.get("notes",""))
        )
        self.conn.commit()

    def get_history(self, patient_id):
        return [dict(r) for r in self.conn.execute(
            """SELECT mh.*, d.full_name AS doctor_name
               FROM medical_history mh
               LEFT JOIN doctors d ON mh.doctor_id = d.doctor_id
               WHERE mh.patient_id=? ORDER BY mh.visit_date DESC""",
            (patient_id,)
        ).fetchall()]

    # ── DASHBOARD STATS ───────────────────────────────────────────────────────
    def get_stats(self):
        c = self.conn
        total_patients     = c.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        total_doctors      = c.execute("SELECT COUNT(*) FROM doctors WHERE active=1").fetchone()[0]
        total_appointments = c.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        today_appts        = c.execute(
            "SELECT COUNT(*) FROM appointments WHERE appt_date=?",
            (date.today().isoformat(),)
        ).fetchone()[0]
        total_revenue      = c.execute(
            "SELECT COALESCE(SUM(paid_amount),0) FROM billing"
        ).fetchone()[0]
        pending_bills      = c.execute(
            "SELECT COUNT(*) FROM billing WHERE status='Pending'"
        ).fetchone()[0]
        low_stock          = c.execute(
            "SELECT COUNT(*) FROM medicines WHERE stock <= min_stock"
        ).fetchone()[0]
        return {
            "total_patients":     total_patients,
            "total_doctors":      total_doctors,
            "total_appointments": total_appointments,
            "today_appointments": today_appts,
            "total_revenue":      total_revenue,
            "pending_bills":      pending_bills,
            "low_stock_medicines": low_stock,
        }

    def close(self):
        self.conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  REUSABLE UI WIDGETS
# ─────────────────────────────────────────────────────────────────────────────
class Widgets:
    """Factory methods for consistently styled widgets."""

    @staticmethod
    def label(parent, text, font=None, fg=None, bg=None, **kw):
        return tk.Label(
            parent, text=text,
            font=font or FONT["body"],
            fg=fg or COLOR["text_light"],
            bg=bg or COLOR["bg_mid"],
            **kw
        )

    @staticmethod
    def entry(parent, textvariable=None, width=30, show=None, **kw):
        e = tk.Entry(
            parent,
            textvariable=textvariable,
            font=FONT["body"],
            bg=COLOR["bg_dark"],
            fg=COLOR["text_light"],
            insertbackground=COLOR["accent"],
            relief="flat",
            highlightthickness=1,
            highlightcolor=COLOR["accent"],
            highlightbackground=COLOR["border"],
            width=width,
            **kw
        )
        if show:
            e.config(show=show)
        return e

    @staticmethod
    def button(parent, text, command, bg=None, fg=None, width=12, **kw):
        return tk.Button(
            parent, text=text, command=command,
            bg=bg or COLOR["accent2"],
            fg=fg or COLOR["white"],
            font=FONT["subhead"],
            relief="flat",
            activebackground=COLOR["accent"],
            activeforeground=COLOR["white"],
            cursor="hand2",
            width=width,
            padx=8, pady=4,
            **kw
        )

    @staticmethod
    def combo(parent, values, textvariable=None, width=28, **kw):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=COLOR["bg_dark"],
            background=COLOR["bg_dark"],
            foreground=COLOR["text_light"],
            arrowcolor=COLOR["accent"],
            bordercolor=COLOR["border"],
            lightcolor=COLOR["border"],
            darkcolor=COLOR["border"],
        )
        c = ttk.Combobox(
            parent, values=values,
            textvariable=textvariable,
            font=FONT["body"],
            style="Dark.TCombobox",
            state="readonly",
            width=width,
            **kw
        )
        return c

    @staticmethod
    def treeview(parent, columns, heights=15):
        """Create a dark-themed Treeview with scrollbars."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.Treeview",
            background=COLOR["bg_dark"],
            foreground=COLOR["text_light"],
            fieldbackground=COLOR["bg_dark"],
            rowheight=26,
            font=FONT["body"],
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=COLOR["highlight"],
            foreground=COLOR["accent"],
            font=FONT["subhead"],
            relief="flat",
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", COLOR["accent2"])],
            foreground=[("selected", COLOR["white"])],
        )

        frame = tk.Frame(parent, bg=COLOR["bg_dark"])
        tree = ttk.Treeview(
            frame, columns=columns, show="headings",
            height=heights, style="Dark.Treeview"
        )
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Zebra stripes
        tree.tag_configure("odd",  background="#162232")
        tree.tag_configure("even", background=COLOR["bg_dark"])
        tree.tag_configure("warn", background="#3D1A00", foreground=COLOR["warning"])

        return tree, frame

    @staticmethod
    def stat_card(parent, title, value, color, row, col):
        card = tk.Frame(parent, bg=color, padx=20, pady=14)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        tk.Label(card, text=str(value), font=("Segoe UI", 26, "bold"),
                 bg=color, fg=COLOR["white"]).pack()
        tk.Label(card, text=title, font=FONT["small"],
                 bg=color, fg=COLOR["white"]).pack()
        return card


# ─────────────────────────────────────────────────────────────────────────────
#  LOGIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class LoginWindow:
    def __init__(self, root: tk.Tk, db: Database, on_success):
        self.root = root
        self.db = db
        self.on_success = on_success
        self._build()

    def _build(self):
        self.root.title("Hospital Management System – Login")
        self.root.configure(bg=COLOR["bg_dark"])
        self.root.resizable(False, False)
        w, h = 900, 560
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Left panel (branding)
        left = tk.Frame(self.root, bg=COLOR["accent2"], width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="🏥", font=("Segoe UI", 56),
                 bg=COLOR["accent2"], fg=COLOR["white"]).pack(pady=(80, 10))
        tk.Label(left, text="Smart Hospital", font=("Segoe UI", 22, "bold"),
                 bg=COLOR["accent2"], fg=COLOR["white"]).pack()
        tk.Label(left, text="Management System", font=("Segoe UI", 16),
                 bg=COLOR["accent2"], fg="#BDE0F5").pack()
        tk.Label(left, text="v2.0", font=FONT["small"],
                 bg=COLOR["accent2"], fg="#BDE0F5").pack(pady=4)

        sep = tk.Frame(left, bg="#BDE0F5", height=1, width=200)
        sep.pack(pady=20)

        for line in ["✔  Patient Management", "✔  Doctor Scheduling",
                     "✔  Billing & Invoices", "✔  Medicine Inventory"]:
            tk.Label(left, text=line, font=FONT["body"],
                     bg=COLOR["accent2"], fg=COLOR["white"]).pack(pady=3)

        # Right panel (form)
        right = tk.Frame(self.root, bg=COLOR["bg_dark"])
        right.pack(side="right", fill="both", expand=True)

        inner = tk.Frame(right, bg=COLOR["bg_dark"])
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="Welcome Back", font=("Segoe UI", 20, "bold"),
                 bg=COLOR["bg_dark"], fg=COLOR["accent"]).grid(row=0, columnspan=2, pady=(0, 4))
        tk.Label(inner, text="Sign in to continue", font=FONT["small"],
                 bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).grid(row=1, columnspan=2, pady=(0, 24))

        for i, (lbl, attr, show) in enumerate([
            ("Username", "uname", None),
            ("Password", "pword", "●"),
        ]):
            tk.Label(inner, text=lbl, font=FONT["subhead"],
                     bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).grid(
                row=2+i*2, column=0, sticky="w", pady=(0, 2))
            var = tk.StringVar()
            setattr(self, attr, var)
            e = Widgets.entry(inner, textvariable=var, width=28, show=show)
            e.grid(row=3+i*2, column=0, columnspan=2, pady=(0, 12), ipady=6)
            if i == 0:
                e.focus()

        # Role selector
        tk.Label(inner, text="Login As", font=FONT["subhead"],
                 bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.role_var = tk.StringVar(value="Admin")
        Widgets.combo(inner, ["Admin", "Doctor", "Receptionist"],
                      textvariable=self.role_var, width=27).grid(row=7, columnspan=2, pady=(0, 18))

        Widgets.button(inner, "  LOGIN  ", self._login,
                       bg=COLOR["accent2"], width=30).grid(row=8, columnspan=2, ipady=6, pady=4)

        self.msg = tk.Label(inner, text="", font=FONT["small"],
                            bg=COLOR["bg_dark"], fg=COLOR["danger"])
        self.msg.grid(row=9, columnspan=2, pady=4)

        tk.Label(inner, text="Default: admin / admin123",
                 font=FONT["small"], bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).grid(row=10, columnspan=2)

        # Bind Enter key
        self.root.bind("<Return>", lambda e: self._login())

    def _login(self):
        uname = self.uname.get().strip()
        pword = self.pword.get().strip()
        if not uname or not pword:
            self.msg.config(text="Username and password are required.")
            return
        user = self.db.authenticate(uname, pword)
        if user:
            self.on_success(user)
        else:
            self.msg.config(text="Invalid credentials. Please try again.")
            self.pword.set("")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainApp:
    def __init__(self, root: tk.Tk, db: Database, user: dict):
        self.root = root
        self.db = db
        self.user = user
        self._build()

    # ── Window setup ──────────────────────────────────────────────────────────
    def _build(self):
        self.root.title(f"Smart Hospital Management System – {self.user['full_name']} ({self.user['role']})")
        self.root.configure(bg=COLOR["bg_dark"])
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{sw-40}x{sh-60}+20+20")
        self.root.resizable(True, True)

        self._build_sidebar()
        self._build_content()
        self._show_dashboard()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=COLOR["bg_mid"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        tk.Label(self.sidebar, text="🏥 HMS", font=("Segoe UI", 16, "bold"),
                 bg=COLOR["accent2"], fg=COLOR["white"],
                 padx=10, pady=18).pack(fill="x")

        # User badge
        badge = tk.Frame(self.sidebar, bg=COLOR["bg_card"], pady=10)
        badge.pack(fill="x", padx=0)
        tk.Label(badge, text=f"👤 {self.user['full_name']}", font=FONT["small"],
                 bg=COLOR["bg_card"], fg=COLOR["accent"]).pack()
        tk.Label(badge, text=self.user["role"], font=FONT["small"],
                 bg=COLOR["bg_card"], fg=COLOR["text_dim"]).pack()

        tk.Frame(self.sidebar, bg=COLOR["border"], height=1).pack(fill="x", pady=4)

        self.nav_btns = {}
        nav_items = [
            ("📊  Dashboard",         "dashboard"),
            ("👥  Patients",           "patients"),
            ("🩺  Doctors",            "doctors"),
            ("📅  Appointments",       "appointments"),
            ("💵  Billing",            "billing"),
            ("💊  Medicines",          "medicines"),
            ("📋  Medical History",    "history"),
        ]
        if self.user["role"] == "Admin":
            nav_items.append(("⚙️  User Management", "users"))

        for label, key in nav_items:
            btn = tk.Button(
                self.sidebar, text=label,
                font=FONT["body"],
                bg=COLOR["bg_mid"], fg=COLOR["text_light"],
                activebackground=COLOR["accent2"],
                activeforeground=COLOR["white"],
                relief="flat", anchor="w",
                padx=18, pady=10,
                cursor="hand2",
                command=partial(self._switch_tab, key),
            )
            btn.pack(fill="x")
            self.nav_btns[key] = btn

        # Logout at bottom
        tk.Frame(self.sidebar, bg=COLOR["border"], height=1).pack(fill="x", side="bottom", pady=4)
        Widgets.button(self.sidebar, "🚪 Logout", self._logout,
                       bg=COLOR["danger"], width=22).pack(side="bottom", pady=10, padx=14)

    # ── Content area ──────────────────────────────────────────────────────────
    def _build_content(self):
        self.content = tk.Frame(self.root, bg=COLOR["bg_dark"])
        self.content.pack(side="right", fill="both", expand=True)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _switch_tab(self, key):
        for k, btn in self.nav_btns.items():
            btn.config(bg=COLOR["bg_mid"], fg=COLOR["text_light"])
        if key in self.nav_btns:
            self.nav_btns[key].config(bg=COLOR["accent2"], fg=COLOR["white"])
        self._clear_content()
        {
            "dashboard":    self._show_dashboard,
            "patients":     self._show_patients,
            "doctors":      self._show_doctors,
            "appointments": self._show_appointments,
            "billing":      self._show_billing,
            "medicines":    self._show_medicines,
            "history":      self._show_history,
            "users":        self._show_users,
        }[key]()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            new_root = tk.Tk()
            App(new_root)
            new_root.mainloop()

    # ─────────────────────────────────────────────────────────────────────────
    #  DASHBOARD
    # ─────────────────────────────────────────────────────────────────────────
    def _show_dashboard(self):
        self._switch_highlight("dashboard")
        self._clear_content()
        stats = self.db.get_stats()

        # Header
        hdr = tk.Frame(self.content, bg=COLOR["bg_dark"])
        hdr.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(hdr, text="📊  Dashboard Overview",
                 font=FONT["title"], bg=COLOR["bg_dark"], fg=COLOR["accent"]).pack(side="left")
        tk.Label(hdr, text=f"Today: {date.today().strftime('%B %d, %Y')}",
                 font=FONT["body"], bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).pack(side="right")

        tk.Frame(self.content, bg=COLOR["border"], height=1).pack(fill="x", padx=20, pady=6)

        # Stat cards
        grid = tk.Frame(self.content, bg=COLOR["bg_dark"])
        grid.pack(padx=20, pady=10)

        cards = [
            ("Total Patients",     stats["total_patients"],      COLOR["accent2"],  0, 0),
            ("Active Doctors",     stats["total_doctors"],       COLOR["success"],  0, 1),
            ("Total Appointments", stats["total_appointments"],  "#5A3E9B",         0, 2),
            ("Today's Appts",      stats["today_appointments"],  COLOR["warning"][:7] if len(COLOR["warning"])>6 else COLOR["warning"], 0, 3),
            ("Total Revenue ₹",    f"{stats['total_revenue']:,.0f}", "#1B6F4E",     1, 0),
            ("Pending Bills",      stats["pending_bills"],       COLOR["danger"],   1, 1),
            ("Low-Stock Meds",     stats["low_stock_medicines"], "#7A3B00",         1, 2),
            ("DB Entries",
             stats["total_patients"]+stats["total_doctors"]+stats["total_appointments"],
             COLOR["highlight"], 1, 3),
        ]
        for title, val, color, r, c in cards:
            Widgets.stat_card(grid, title, val, color, r, c)
        for i in range(4):
            grid.columnconfigure(i, weight=1)

        # Recent appointments table
        tk.Label(self.content, text="📅  Recent Appointments",
                 font=FONT["heading"], bg=COLOR["bg_dark"], fg=COLOR["text_light"]
                 ).pack(anchor="w", padx=24, pady=(16, 4))

        cols = ("Appt ID", "Patient", "Doctor", "Date", "Time", "Status")
        tree, frame = Widgets.treeview(self.content, cols, heights=10)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="center")
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        for i, appt in enumerate(self.db.get_appointments()[:50]):
            tag = "warn" if appt["status"] == "Cancelled" else ("odd" if i % 2 else "even")
            tree.insert("", "end", values=(
                appt["appointment_id"],
                appt.get("patient_name", ""),
                appt.get("doctor_name", ""),
                appt["appt_date"],
                appt["appt_time"],
                appt["status"],
            ), tags=(tag,))

    def _switch_highlight(self, key):
        for k, btn in self.nav_btns.items():
            btn.config(bg=COLOR["bg_mid"], fg=COLOR["text_light"])
        if key in self.nav_btns:
            self.nav_btns[key].config(bg=COLOR["accent2"], fg=COLOR["white"])

    # ─────────────────────────────────────────────────────────────────────────
    #  PATIENTS MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_patients(self):
        self._clear_content()
        self._switch_highlight("patients")

        self._page_header("👥  Patient Management", "patients")

        # Toolbar
        tb = self._toolbar(self.content)
        self.pat_search = tk.StringVar()
        Widgets.entry(tb, textvariable=self.pat_search, width=30).pack(side="left", padx=4)
        Widgets.button(tb, "🔍 Search",   lambda: self._refresh_patients(), width=10).pack(side="left", padx=2)
        Widgets.button(tb, "➕ Add",      lambda: self._patient_form(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "✏️ Edit",     lambda: self._patient_edit(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "🗑️ Delete",   lambda: self._patient_delete(),   width=10, bg=COLOR["danger"]).pack(side="left", padx=2)
        Widgets.button(tb, "📤 Export",   lambda: self._export_csv("patients"), width=10, bg=COLOR["success"]).pack(side="left", padx=2)
        Widgets.button(tb, "🔄 Refresh",  lambda: self._refresh_patients(), width=10, bg=COLOR["bg_card"]).pack(side="right", padx=2)

        cols = ("Patient ID", "Full Name", "DOB", "Gender", "Blood", "Phone", "Email", "Registered")
        self.pat_tree, frame = Widgets.treeview(self.content, cols)
        widths = [90, 160, 100, 80, 60, 110, 160, 120]
        for col, w in zip(cols, widths):
            self.pat_tree.heading(col, text=col, command=lambda c=col: None)
            self.pat_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._refresh_patients()

    def _refresh_patients(self):
        q = self.pat_search.get() if hasattr(self, "pat_search") else ""
        for row in self.pat_tree.get_children():
            self.pat_tree.delete(row)
        for i, p in enumerate(self.db.get_patients(q)):
            tag = "odd" if i % 2 else "even"
            self.pat_tree.insert("", "end", values=(
                p["patient_id"], p["full_name"], p.get("dob",""),
                p.get("gender",""), p.get("blood_group",""), p.get("phone",""),
                p.get("email",""), p["created_at"][:10],
            ), tags=(tag,))

    def _patient_form(self, existing=None):
        """Add or edit patient in a Toplevel dialog."""
        dlg = self._dialog("Patient Record", 600, 500)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        fields = [
            ("Full Name *",          "full_name",         "entry"),
            ("Date of Birth",        "dob",               "entry"),
            ("Gender",               "gender",            ["Male","Female","Other"]),
            ("Blood Group",          "blood_group",       ["A+","A-","B+","B-","O+","O-","AB+","AB-",""]),
            ("Phone *",              "phone",             "entry"),
            ("Email",                "email",             "entry"),
            ("Address",              "address",           "text"),
            ("Emergency Contact",    "emergency_contact", "entry"),
        ]

        vars_ = {}
        text_widgets = {}
        row = 0
        for label, key, ftype in fields:
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"],
                     anchor="w").grid(row=row, column=0, sticky="w", padx=4, pady=3)
            if ftype == "entry":
                v = tk.StringVar(value=existing.get(key,"") if existing else "")
                vars_[key] = v
                Widgets.entry(frm, textvariable=v, width=35).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
            elif isinstance(ftype, list):
                v = tk.StringVar(value=existing.get(key,"") if existing else "")
                vars_[key] = v
                Widgets.combo(frm, ftype, textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
            elif ftype == "text":
                t = tk.Text(frm, font=FONT["body"], bg=COLOR["bg_dark"], fg=COLOR["text_light"],
                            width=35, height=3, insertbackground=COLOR["accent"])
                t.grid(row=row, column=1, sticky="ew", padx=4, pady=3)
                if existing and existing.get(key):
                    t.insert("1.0", existing.get(key,""))
                text_widgets[key] = t
            row += 1

        frm.columnconfigure(1, weight=1)

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            for k, t in text_widgets.items():
                data[k] = t.get("1.0","end-1c").strip()

            if not data.get("full_name"):
                messagebox.showerror("Validation", "Full Name is required.", parent=dlg)
                return
            if not data.get("phone"):
                messagebox.showerror("Validation", "Phone is required.", parent=dlg)
                return
            if data.get("phone") and not re.match(r"^\+?[\d\s\-]{7,15}$", data["phone"]):
                messagebox.showerror("Validation", "Invalid phone number.", parent=dlg)
                return
            if data.get("email") and not re.match(r"^[^@]+@[^@]+\.[^@]+$", data["email"]):
                messagebox.showerror("Validation", "Invalid email address.", parent=dlg)
                return

            if existing:
                self.db.update_patient(existing["patient_id"], **data)
                messagebox.showinfo("Success", f"Patient updated successfully.", parent=dlg)
            else:
                pid = self.db.add_patient(**data)
                messagebox.showinfo("Success", f"Patient registered! ID: {pid}", parent=dlg)
            dlg.destroy()
            self._refresh_patients()

        btn_frame = tk.Frame(dlg, bg=COLOR["bg_mid"])
        btn_frame.pack(pady=10)
        Widgets.button(btn_frame, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(btn_frame, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _patient_edit(self):
        sel = self.pat_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a patient to edit.")
            return
        pid = self.pat_tree.item(sel[0])["values"][0]
        patient = self.db.get_patient_by_id(pid)
        if patient:
            self._patient_form(existing=patient)

    def _patient_delete(self):
        sel = self.pat_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a patient to delete.")
            return
        pid = self.pat_tree.item(sel[0])["values"][0]
        name = self.pat_tree.item(sel[0])["values"][1]
        if messagebox.askyesno("Delete", f"Delete patient {name} ({pid})? This cannot be undone."):
            self.db.delete_patient(pid)
            messagebox.showinfo("Deleted", "Patient record deleted.")
            self._refresh_patients()

    # ─────────────────────────────────────────────────────────────────────────
    #  DOCTORS MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_doctors(self):
        self._clear_content()
        self._switch_highlight("doctors")
        self._page_header("🩺  Doctor Management", "doctors")

        tb = self._toolbar(self.content)
        self.doc_search = tk.StringVar()
        Widgets.entry(tb, textvariable=self.doc_search, width=30).pack(side="left", padx=4)
        Widgets.button(tb, "🔍 Search",  lambda: self._refresh_doctors(), width=10).pack(side="left", padx=2)
        Widgets.button(tb, "➕ Add",     lambda: self._doctor_form(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "✏️ Edit",    lambda: self._doctor_edit(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "🗑️ Delete",  lambda: self._doctor_delete(),   width=10, bg=COLOR["danger"]).pack(side="left", padx=2)
        Widgets.button(tb, "📤 Export",  lambda: self._export_csv("doctors"), width=10, bg=COLOR["success"]).pack(side="left", padx=2)

        cols = ("Doctor ID", "Full Name", "Specialization", "Qualification", "Phone", "Email", "Fee ₹", "Days")
        self.doc_tree, frame = Widgets.treeview(self.content, cols)
        widths = [90, 160, 140, 130, 110, 160, 80, 120]
        for col, w in zip(cols, widths):
            self.doc_tree.heading(col, text=col)
            self.doc_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._refresh_doctors()

    def _refresh_doctors(self):
        q = self.doc_search.get() if hasattr(self, "doc_search") else ""
        for row in self.doc_tree.get_children():
            self.doc_tree.delete(row)
        for i, d in enumerate(self.db.get_doctors(q)):
            tag = "odd" if i % 2 else "even"
            self.doc_tree.insert("", "end", values=(
                d["doctor_id"], d["full_name"], d.get("specialization",""),
                d.get("qualification",""), d.get("phone",""), d.get("email",""),
                f"{d.get('fee',0):.0f}", d.get("available_days",""),
            ), tags=(tag,))

    def _doctor_form(self, existing=None):
        dlg = self._dialog("Doctor Record", 600, 460)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        specs = ["Cardiology","Dermatology","Endocrinology","Gastroenterology",
                 "General Medicine","Gynecology","Neurology","Oncology",
                 "Ophthalmology","Orthopedics","Pediatrics","Psychiatry",
                 "Pulmonology","Radiology","Surgery","Urology","Other"]

        fields = [
            ("Full Name *",       "full_name",       "entry"),
            ("Specialization *",  "specialization",  specs),
            ("Qualification",     "qualification",   "entry"),
            ("Phone *",           "phone",           "entry"),
            ("Email",             "email",           "entry"),
            ("Consultation Fee ₹","fee",             "entry"),
            ("Available Days",    "available_days",  "entry"),
        ]

        vars_ = {}
        row = 0
        for label, key, ftype in fields:
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"],
                     anchor="w").grid(row=row, column=0, sticky="w", padx=4, pady=4)
            if ftype == "entry":
                v = tk.StringVar(value=str(existing.get(key,"")) if existing else "")
                vars_[key] = v
                Widgets.entry(frm, textvariable=v, width=35).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            elif isinstance(ftype, list):
                v = tk.StringVar(value=existing.get(key,"") if existing else "")
                vars_[key] = v
                Widgets.combo(frm, ftype, textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            row += 1
        frm.columnconfigure(1, weight=1)

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            if not data.get("full_name"):
                messagebox.showerror("Validation", "Full Name is required.", parent=dlg); return
            if not data.get("specialization"):
                messagebox.showerror("Validation", "Specialization is required.", parent=dlg); return
            try:
                data["fee"] = float(data.get("fee", 0) or 0)
            except ValueError:
                messagebox.showerror("Validation", "Fee must be a number.", parent=dlg); return

            if existing:
                self.db.update_doctor(existing["doctor_id"], **data)
                messagebox.showinfo("Success", "Doctor record updated.", parent=dlg)
            else:
                did = self.db.add_doctor(**data)
                messagebox.showinfo("Success", f"Doctor added! ID: {did}", parent=dlg)
            dlg.destroy()
            self._refresh_doctors()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _doctor_edit(self):
        sel = self.doc_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a doctor to edit."); return
        did = self.doc_tree.item(sel[0])["values"][0]
        doc = self.db.get_doctor_by_id(did)
        if doc:
            self._doctor_form(existing=doc)

    def _doctor_delete(self):
        sel = self.doc_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a doctor to delete."); return
        did = self.doc_tree.item(sel[0])["values"][0]
        name = self.doc_tree.item(sel[0])["values"][1]
        if messagebox.askyesno("Delete", f"Delete Dr. {name}?"):
            self.db.delete_doctor(did)
            messagebox.showinfo("Deleted", "Doctor record deleted.")
            self._refresh_doctors()

    # ─────────────────────────────────────────────────────────────────────────
    #  APPOINTMENTS MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_appointments(self):
        self._clear_content()
        self._switch_highlight("appointments")
        self._page_header("📅  Appointment Scheduling", "appointments")

        tb = self._toolbar(self.content)
        self.appt_search = tk.StringVar()
        Widgets.entry(tb, textvariable=self.appt_search, width=30).pack(side="left", padx=4)
        Widgets.button(tb, "🔍 Search",  lambda: self._refresh_appointments(), width=10).pack(side="left", padx=2)
        Widgets.button(tb, "➕ Add",     lambda: self._appt_form(),            width=10).pack(side="left", padx=2)
        Widgets.button(tb, "✏️ Edit",    lambda: self._appt_edit(),            width=10).pack(side="left", padx=2)
        Widgets.button(tb, "🗑️ Cancel",  lambda: self._appt_delete(),          width=10, bg=COLOR["danger"]).pack(side="left", padx=2)
        Widgets.button(tb, "📤 Export",  lambda: self._export_csv("appointments"), width=10, bg=COLOR["success"]).pack(side="left", padx=2)

        cols = ("Appt ID", "Patient ID", "Patient Name", "Doctor Name", "Date", "Time", "Reason", "Status")
        self.appt_tree, frame = Widgets.treeview(self.content, cols)
        widths = [90, 90, 150, 150, 100, 80, 160, 100]
        for col, w in zip(cols, widths):
            self.appt_tree.heading(col, text=col)
            self.appt_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._refresh_appointments()

    def _refresh_appointments(self):
        q = self.appt_search.get() if hasattr(self, "appt_search") else ""
        for row in self.appt_tree.get_children():
            self.appt_tree.delete(row)
        for i, a in enumerate(self.db.get_appointments(q)):
            tag = "warn" if a["status"] in ("Cancelled", "No-Show") else ("odd" if i % 2 else "even")
            self.appt_tree.insert("", "end", values=(
                a["appointment_id"], a["patient_id"],
                a.get("patient_name",""), a.get("doctor_name",""),
                a["appt_date"], a["appt_time"],
                a.get("reason",""), a["status"],
            ), tags=(tag,))

    def _appt_form(self, existing=None):
        dlg = self._dialog("Appointment", 600, 430)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        patients = self.db.get_patients()
        doctors  = self.db.get_doctors()
        pat_opts  = [f"{p['patient_id']} – {p['full_name']}" for p in patients]
        doc_opts  = [f"{d['doctor_id']} – Dr. {d['full_name']}" for d in doctors]

        fields = [
            ("Patient *",    "patient",  pat_opts),
            ("Doctor *",     "doctor",   doc_opts),
            ("Date * (YYYY-MM-DD)", "appt_date", "entry"),
            ("Time * (HH:MM)",     "appt_time", "entry"),
            ("Reason",       "reason",   "entry"),
            ("Status",       "status",   ["Scheduled","Completed","Cancelled","No-Show"]),
            ("Notes",        "notes",    "entry"),
        ]

        vars_ = {}
        def_vals = {}
        if existing:
            def_vals = {
                "patient":   next((o for o in pat_opts if o.startswith(existing["patient_id"])), ""),
                "doctor":    next((o for o in doc_opts if o.startswith(existing["doctor_id"])), ""),
                "appt_date": existing["appt_date"],
                "appt_time": existing["appt_time"],
                "reason":    existing.get("reason",""),
                "status":    existing["status"],
                "notes":     existing.get("notes",""),
            }

        row = 0
        for label, key, ftype in fields:
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"], anchor="w"
                     ).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            v = tk.StringVar(value=def_vals.get(key,""))
            vars_[key] = v
            if ftype == "entry":
                Widgets.entry(frm, textvariable=v, width=35).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            elif isinstance(ftype, list):
                Widgets.combo(frm, ftype, textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            row += 1
        frm.columnconfigure(1, weight=1)

        # Set default date/time if new
        if not existing:
            vars_["appt_date"].set(date.today().isoformat())
            vars_["appt_time"].set(datetime.now().strftime("%H:%M"))

        def save():
            raw = {k: v.get().strip() for k, v in vars_.items()}
            if not raw["patient"]:
                messagebox.showerror("Validation", "Patient is required.", parent=dlg); return
            if not raw["doctor"]:
                messagebox.showerror("Validation", "Doctor is required.", parent=dlg); return
            if not raw["appt_date"]:
                messagebox.showerror("Validation", "Date is required.", parent=dlg); return
            try:
                datetime.strptime(raw["appt_date"], "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Validation", "Date must be YYYY-MM-DD.", parent=dlg); return
            if not re.match(r"^\d{2}:\d{2}$", raw.get("appt_time","")):
                messagebox.showerror("Validation", "Time must be HH:MM.", parent=dlg); return

            data = {
                "patient_id": raw["patient"].split(" – ")[0],
                "doctor_id":  raw["doctor"].split(" – ")[0],
                "appt_date":  raw["appt_date"],
                "appt_time":  raw["appt_time"],
                "reason":     raw["reason"],
                "status":     raw["status"] or "Scheduled",
                "notes":      raw["notes"],
            }
            if existing:
                self.db.update_appointment(existing["appointment_id"], **data)
                messagebox.showinfo("Success", "Appointment updated.", parent=dlg)
            else:
                aid = self.db.add_appointment(**data)
                messagebox.showinfo("Success", f"Appointment booked! ID: {aid}", parent=dlg)
            dlg.destroy()
            self._refresh_appointments()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _appt_edit(self):
        sel = self.appt_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an appointment."); return
        aid = self.appt_tree.item(sel[0])["values"][0]
        rows = self.db.get_appointments(aid)
        appt = next((r for r in rows if r["appointment_id"] == aid), None)
        if appt:
            self._appt_form(existing=appt)

    def _appt_delete(self):
        sel = self.appt_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an appointment."); return
        aid = self.appt_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Delete", f"Delete appointment {aid}?"):
            self.db.delete_appointment(aid)
            messagebox.showinfo("Done", "Appointment removed.")
            self._refresh_appointments()

    # ─────────────────────────────────────────────────────────────────────────
    #  BILLING MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_billing(self):
        self._clear_content()
        self._switch_highlight("billing")
        self._page_header("💵  Billing & Invoices", "billing")

        tb = self._toolbar(self.content)
        self.bill_search = tk.StringVar()
        Widgets.entry(tb, textvariable=self.bill_search, width=30).pack(side="left", padx=4)
        Widgets.button(tb, "🔍 Search",    lambda: self._refresh_billing(), width=10).pack(side="left", padx=2)
        Widgets.button(tb, "➕ New Invoice", lambda: self._billing_form(),   width=14).pack(side="left", padx=2)
        Widgets.button(tb, "✏️ Update",     lambda: self._billing_edit(),    width=10).pack(side="left", padx=2)
        Widgets.button(tb, "🖨️ Print",      lambda: self._billing_print(),   width=10, bg=COLOR["success"]).pack(side="left", padx=2)
        Widgets.button(tb, "📤 Export",     lambda: self._export_csv("billing"), width=10, bg=COLOR["success"]).pack(side="left", padx=2)

        cols = ("Invoice ID", "Patient ID", "Patient Name", "Total ₹", "Paid ₹", "Discount", "Method", "Status", "Date")
        self.bill_tree, frame = Widgets.treeview(self.content, cols)
        widths = [110, 90, 150, 80, 80, 70, 80, 80, 110]
        for col, w in zip(cols, widths):
            self.bill_tree.heading(col, text=col)
            self.bill_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._refresh_billing()

    def _refresh_billing(self):
        q = self.bill_search.get() if hasattr(self, "bill_search") else ""
        for row in self.bill_tree.get_children():
            self.bill_tree.delete(row)
        for i, b in enumerate(self.db.get_invoices(q)):
            tag = "warn" if b["status"] == "Pending" else ("odd" if i % 2 else "even")
            self.bill_tree.insert("", "end", values=(
                b["invoice_id"], b["patient_id"], b.get("patient_name",""),
                f"{b['total_amount']:.2f}", f"{b['paid_amount']:.2f}",
                f"{b.get('discount',0):.0f}%",
                b.get("payment_method",""), b["status"], b["created_at"][:10],
            ), tags=(tag,))

    def _billing_form(self):
        dlg = self._dialog("New Invoice", 620, 520)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        patients = self.db.get_patients()
        pat_opts = [f"{p['patient_id']} – {p['full_name']}" for p in patients]

        tk.Label(frm, text="Patient *", font=FONT["small"],
                 bg=COLOR["bg_mid"], fg=COLOR["text_dim"]).grid(row=0, column=0, sticky="w", pady=4)
        pat_var = tk.StringVar()
        Widgets.combo(frm, pat_opts, textvariable=pat_var, width=40).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        # Line items
        tk.Label(frm, text="Service Items", font=FONT["subhead"],
                 bg=COLOR["bg_mid"], fg=COLOR["accent"]).grid(row=1, columnspan=2, pady=(12,4))

        items_frame = tk.Frame(frm, bg=COLOR["bg_card"])
        items_frame.grid(row=2, columnspan=2, sticky="ew", padx=4, pady=4)

        item_rows = []
        def add_item_row(desc="", qty="1", price="0"):
            r = len(item_rows)
            d = tk.StringVar(value=desc)
            q = tk.StringVar(value=qty)
            p = tk.StringVar(value=price)
            Widgets.entry(items_frame, textvariable=d, width=22).grid(row=r, column=0, padx=2, pady=2)
            Widgets.entry(items_frame, textvariable=q, width=6).grid(row=r, column=1, padx=2, pady=2)
            Widgets.entry(items_frame, textvariable=p, width=10).grid(row=r, column=2, padx=2, pady=2)
            item_rows.append((d, q, p))

        tk.Label(items_frame, text="Description", font=FONT["small"],
                 bg=COLOR["bg_card"], fg=COLOR["text_dim"]).grid(row=0, column=0, padx=2)
        # add header labels
        items_frame_hdr = tk.Frame(frm, bg=COLOR["bg_card"])
        # reuse add_item_row for initial rows
        for desc, qty, price in [("Consultation Fee","1","500"),("Lab Tests","1","300")]:
            add_item_row(desc, qty, price)
        Widgets.button(items_frame, "➕ Add Row", lambda: add_item_row(), width=12,
                       bg=COLOR["bg_mid"]).grid(row=20, column=0, columnspan=3, pady=4)

        row = 3
        other_vars = {}
        for label, key, default in [
            ("Discount %",      "discount",       "0"),
            ("Payment Method",  "payment_method", ""),
            ("Status",          "status",         ""),
        ]:
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"]).grid(row=row, column=0, sticky="w", pady=4)
            if key == "payment_method":
                v = tk.StringVar(value="Cash")
                Widgets.combo(frm, ["Cash","Card","UPI","Insurance","Other"],
                              textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            elif key == "status":
                v = tk.StringVar(value="Pending")
                Widgets.combo(frm, ["Pending","Paid","Partial","Cancelled"],
                              textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            else:
                v = tk.StringVar(value=default)
                Widgets.entry(frm, textvariable=v, width=35).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            other_vars[key] = v
            row += 1
        frm.columnconfigure(1, weight=1)

        def save():
            if not pat_var.get():
                messagebox.showerror("Validation", "Patient is required.", parent=dlg); return
            total = 0.0
            import json
            items_list = []
            for d_v, q_v, p_v in item_rows:
                desc = d_v.get().strip()
                if not desc:
                    continue
                try:
                    qty = float(q_v.get() or 1)
                    price = float(p_v.get() or 0)
                except ValueError:
                    messagebox.showerror("Validation", "Qty/Price must be numeric.", parent=dlg); return
                subtotal = qty * price
                total += subtotal
                items_list.append({"desc": desc, "qty": qty, "price": price, "subtotal": subtotal})

            try:
                disc_pct = float(other_vars["discount"].get() or 0)
            except ValueError:
                messagebox.showerror("Validation", "Discount must be numeric.", parent=dlg); return

            discounted = total * (1 - disc_pct / 100)
            pid = pat_var.get().split(" – ")[0]
            iid = self.db.add_invoice(
                patient_id=pid,
                total_amount=round(discounted, 2),
                paid_amount=round(discounted, 2) if other_vars["status"].get() == "Paid" else 0,
                discount=disc_pct,
                payment_method=other_vars["payment_method"].get(),
                status=other_vars["status"].get(),
                items_json=json.dumps(items_list),
            )
            messagebox.showinfo("Success", f"Invoice created! ID: {iid}\nTotal: ₹{discounted:.2f}", parent=dlg)
            dlg.destroy()
            self._refresh_billing()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _billing_edit(self):
        sel = self.bill_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an invoice."); return
        iid = self.bill_tree.item(sel[0])["values"][0]
        invoices = self.db.get_invoices(iid)
        inv = next((r for r in invoices if r["invoice_id"] == iid), None)
        if not inv:
            return
        dlg = self._dialog("Update Invoice", 400, 300)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        vars_ = {}
        for row, (label, key, opts) in enumerate([
            ("Paid Amount ₹", "paid_amount", "entry"),
            ("Payment Method", "payment_method", ["Cash","Card","UPI","Insurance","Other"]),
            ("Status", "status", ["Pending","Paid","Partial","Cancelled"]),
        ]):
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"]).grid(row=row, column=0, sticky="w", pady=6)
            v = tk.StringVar(value=str(inv.get(key,"")))
            vars_[key] = v
            if opts == "entry":
                Widgets.entry(frm, textvariable=v, width=25).grid(row=row, column=1, padx=6, pady=6)
            else:
                Widgets.combo(frm, opts, textvariable=v, width=23).grid(row=row, column=1, padx=6, pady=6)
        frm.columnconfigure(1, weight=1)

        def save():
            try:
                paid = float(vars_["paid_amount"].get() or 0)
            except ValueError:
                messagebox.showerror("Validation", "Paid amount must be numeric.", parent=dlg); return
            self.db.update_invoice(iid,
                paid_amount=paid,
                discount=inv.get("discount",0),
                payment_method=vars_["payment_method"].get(),
                status=vars_["status"].get())
            messagebox.showinfo("Updated", "Invoice updated.", parent=dlg)
            dlg.destroy()
            self._refresh_billing()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _billing_print(self):
        """Show a simple text invoice in a new window."""
        sel = self.bill_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an invoice."); return
        iid = self.bill_tree.item(sel[0])["values"][0]
        invoices = self.db.get_invoices(iid)
        inv = next((r for r in invoices if r["invoice_id"] == iid), None)
        if not inv:
            return
        import json

        dlg = self._dialog("Invoice Preview", 500, 520)
        dlg.configure(bg=COLOR["bg_dark"])
        txt = tk.Text(dlg, font=FONT["mono"], bg="#0A1520", fg=COLOR["text_light"],
                      padx=20, pady=16, relief="flat")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        lines = [
            "═" * 54,
            "          SMART HOSPITAL MANAGEMENT SYSTEM",
            "                    INVOICE",
            "═" * 54,
            f"  Invoice ID : {inv['invoice_id']}",
            f"  Patient ID : {inv['patient_id']}",
            f"  Patient    : {inv.get('patient_name','')}",
            f"  Date       : {inv['created_at'][:10]}",
            f"  Method     : {inv.get('payment_method','')}",
            "─" * 54,
            f"  {'Description':<28}{'Qty':>6}{'Price':>9}{'Total':>9}",
            "─" * 54,
        ]
        try:
            items = json.loads(inv.get("items_json","[]"))
        except Exception:
            items = []
        for it in items:
            lines.append(f"  {it['desc']:<28}{it['qty']:>6.0f}{it['price']:>9.2f}{it['subtotal']:>9.2f}")
        lines += [
            "─" * 54,
            f"  {'Discount':<40}{inv.get('discount',0):>8.0f}%",
            f"  {'TOTAL AMOUNT':<40}₹{inv['total_amount']:>8.2f}",
            f"  {'PAID':<40}₹{inv['paid_amount']:>8.2f}",
            f"  {'BALANCE':<40}₹{inv['total_amount']-inv['paid_amount']:>8.2f}",
            "═" * 54,
            f"  Status: {inv['status']}",
            "",
            "  Thank you for choosing Smart Hospital!",
            "═" * 54,
        ]
        txt.insert("1.0", "\n".join(lines))
        txt.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    #  MEDICINES MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_medicines(self):
        self._clear_content()
        self._switch_highlight("medicines")
        self._page_header("💊  Medicine Inventory", "medicines")

        tb = self._toolbar(self.content)
        self.med_search = tk.StringVar()
        Widgets.entry(tb, textvariable=self.med_search, width=30).pack(side="left", padx=4)
        Widgets.button(tb, "🔍 Search", lambda: self._refresh_medicines(), width=10).pack(side="left", padx=2)
        Widgets.button(tb, "➕ Add",    lambda: self._medicine_form(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "✏️ Edit",   lambda: self._medicine_edit(),     width=10).pack(side="left", padx=2)
        Widgets.button(tb, "🗑️ Delete", lambda: self._medicine_delete(),   width=10, bg=COLOR["danger"]).pack(side="left", padx=2)
        Widgets.button(tb, "📤 Export", lambda: self._export_csv("medicines"), width=10, bg=COLOR["success"]).pack(side="left", padx=2)

        cols = ("Med ID", "Name", "Category", "Manufacturer", "Unit", "Price ₹", "Stock", "Min Stock", "Expiry")
        self.med_tree, frame = Widgets.treeview(self.content, cols)
        widths = [80, 160, 120, 140, 60, 80, 70, 80, 100]
        for col, w in zip(cols, widths):
            self.med_tree.heading(col, text=col)
            self.med_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._refresh_medicines()

    def _refresh_medicines(self):
        q = self.med_search.get() if hasattr(self, "med_search") else ""
        for row in self.med_tree.get_children():
            self.med_tree.delete(row)
        for i, m in enumerate(self.db.get_medicines(q)):
            low = m.get("stock", 0) <= m.get("min_stock", 10)
            tag = "warn" if low else ("odd" if i % 2 else "even")
            self.med_tree.insert("", "end", values=(
                m["medicine_id"], m["name"], m.get("category",""),
                m.get("manufacturer",""), m.get("unit","pcs"),
                f"{m.get('price',0):.2f}", m.get("stock",0),
                m.get("min_stock",10), m.get("expiry_date",""),
            ), tags=(tag,))

    def _medicine_form(self, existing=None):
        dlg = self._dialog("Medicine Record", 560, 440)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        cats = ["Analgesic","Antibiotic","Antifungal","Antihistamine","Antiviral",
                "Cardiovascular","Dermatology","Diabetes","Gastrointestinal",
                "Neurological","Respiratory","Supplement","Vaccine","Other"]

        fields = [
            ("Name *",          "name",          "entry"),
            ("Category",        "category",      cats),
            ("Manufacturer",    "manufacturer",  "entry"),
            ("Unit",            "unit",          ["pcs","tablet","capsule","ml","mg","bottle","box"]),
            ("Price ₹",         "price",         "entry"),
            ("Stock Qty",       "stock",         "entry"),
            ("Min Stock Alert", "min_stock",     "entry"),
            ("Expiry Date",     "expiry_date",   "entry"),
        ]

        vars_ = {}
        for row, (label, key, ftype) in enumerate(fields):
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"], anchor="w"
                     ).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            v = tk.StringVar(value=str(existing.get(key,"")) if existing else "")
            vars_[key] = v
            if ftype == "entry":
                Widgets.entry(frm, textvariable=v, width=33).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            else:
                Widgets.combo(frm, ftype, textvariable=v, width=31).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        frm.columnconfigure(1, weight=1)

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            if not data.get("name"):
                messagebox.showerror("Validation", "Name is required.", parent=dlg); return
            for num_key in ("price", "stock", "min_stock"):
                try:
                    data[num_key] = float(data.get(num_key, 0) or 0)
                except ValueError:
                    messagebox.showerror("Validation", f"{num_key} must be numeric.", parent=dlg); return
            data["stock"] = int(data["stock"])
            data["min_stock"] = int(data["min_stock"])
            if existing:
                self.db.update_medicine(existing["medicine_id"], **data)
                messagebox.showinfo("Success", "Medicine updated.", parent=dlg)
            else:
                mid = self.db.add_medicine(**data)
                messagebox.showinfo("Success", f"Medicine added! ID: {mid}", parent=dlg)
            dlg.destroy()
            self._refresh_medicines()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    def _medicine_edit(self):
        sel = self.med_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a medicine."); return
        mid = self.med_tree.item(sel[0])["values"][0]
        meds = self.db.get_medicines(mid)
        med = next((m for m in meds if m["medicine_id"] == mid), None)
        if med:
            self._medicine_form(existing=med)

    def _medicine_delete(self):
        sel = self.med_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a medicine."); return
        mid = self.med_tree.item(sel[0])["values"][0]
        name = self.med_tree.item(sel[0])["values"][1]
        if messagebox.askyesno("Delete", f"Delete {name}?"):
            self.db.delete_medicine(mid)
            messagebox.showinfo("Done", "Medicine deleted.")
            self._refresh_medicines()

    # ─────────────────────────────────────────────────────────────────────────
    #  MEDICAL HISTORY MODULE
    # ─────────────────────────────────────────────────────────────────────────
    def _show_history(self):
        self._clear_content()
        self._switch_highlight("history")
        self._page_header("📋  Medical History", "history")

        # Patient search bar
        bar = tk.Frame(self.content, bg=COLOR["bg_dark"])
        bar.pack(fill="x", padx=14, pady=6)
        tk.Label(bar, text="Patient ID / Name:", font=FONT["body"],
                 bg=COLOR["bg_dark"], fg=COLOR["text_dim"]).pack(side="left", padx=4)
        self.hist_search = tk.StringVar()
        Widgets.entry(bar, textvariable=self.hist_search, width=30).pack(side="left", padx=4)
        Widgets.button(bar, "🔍 Load History", lambda: self._load_history(), width=14).pack(side="left", padx=4)
        Widgets.button(bar, "➕ Add Entry",    lambda: self._history_form(), width=12).pack(side="left", padx=4)

        cols = ("Visit Date", "Patient ID", "Doctor", "Diagnosis", "Symptoms", "Prescription", "Notes")
        self.hist_tree, frame = Widgets.treeview(self.content, cols, heights=18)
        widths = [100, 90, 140, 180, 160, 180, 140]
        for col, w in zip(cols, widths):
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._load_history()

    def _load_history(self):
        q = self.hist_search.get().strip() if hasattr(self, "hist_search") else ""
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)
        if q:
            patients = self.db.get_patients(q)
            pids = [p["patient_id"] for p in patients]
            if not pids:
                messagebox.showinfo("Not found", "No patient found.")
                return
        else:
            pids = [p["patient_id"] for p in self.db.get_patients()]

        i = 0
        for pid in pids:
            for rec in self.db.get_history(pid):
                tag = "odd" if i % 2 else "even"
                self.hist_tree.insert("", "end", values=(
                    rec["visit_date"], rec["patient_id"],
                    rec.get("doctor_name",""),
                    rec.get("diagnosis",""), rec.get("symptoms",""),
                    rec.get("prescription",""), rec.get("notes",""),
                ), tags=(tag,))
                i += 1

    def _history_form(self):
        dlg = self._dialog("Add Medical History Entry", 580, 460)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        patients = self.db.get_patients()
        doctors  = self.db.get_doctors()
        pat_opts = [f"{p['patient_id']} – {p['full_name']}" for p in patients]
        doc_opts = [""] + [f"{d['doctor_id']} – Dr. {d['full_name']}" for d in doctors]

        fields = [
            ("Patient *",     "patient",      pat_opts),
            ("Visit Date *",  "visit_date",   "entry"),
            ("Doctor",        "doctor",       doc_opts),
            ("Diagnosis",     "diagnosis",    "entry"),
            ("Symptoms",      "symptoms",     "text"),
            ("Prescription",  "prescription", "text"),
            ("Notes",         "notes",        "entry"),
        ]

        vars_ = {}
        text_ws = {}
        for row, (label, key, ftype) in enumerate(fields):
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"], anchor="w"
                     ).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            if ftype == "entry":
                v = tk.StringVar()
                vars_[key] = v
                w = Widgets.entry(frm, textvariable=v, width=38)
                w.grid(row=row, column=1, sticky="ew", padx=4, pady=3)
                if key == "visit_date":
                    v.set(date.today().isoformat())
            elif ftype == "text":
                t = tk.Text(frm, font=FONT["body"], bg=COLOR["bg_dark"],
                            fg=COLOR["text_light"], width=38, height=3,
                            insertbackground=COLOR["accent"])
                t.grid(row=row, column=1, sticky="ew", padx=4, pady=3)
                text_ws[key] = t
            elif isinstance(ftype, list):
                v = tk.StringVar()
                vars_[key] = v
                Widgets.combo(frm, ftype, textvariable=v, width=36).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
        frm.columnconfigure(1, weight=1)

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            for k, t in text_ws.items():
                data[k] = t.get("1.0","end-1c").strip()
            if not data.get("patient"):
                messagebox.showerror("Validation", "Patient is required.", parent=dlg); return
            if not data.get("visit_date"):
                messagebox.showerror("Validation", "Visit date is required.", parent=dlg); return
            try:
                datetime.strptime(data["visit_date"], "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Validation", "Date must be YYYY-MM-DD.", parent=dlg); return

            pid = data["patient"].split(" – ")[0]
            doc_raw = data.get("doctor","")
            did = doc_raw.split(" – ")[0] if doc_raw else ""
            self.db.add_history(
                patient_id=pid, visit_date=data["visit_date"],
                doctor_id=did, diagnosis=data.get("diagnosis",""),
                symptoms=data.get("symptoms",""),
                prescription=data.get("prescription",""),
                notes=data.get("notes",""),
            )
            messagebox.showinfo("Success", "History entry added.", parent=dlg)
            dlg.destroy()
            self._load_history()

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Save", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────────────────────────
    #  USER MANAGEMENT (Admin only)
    # ─────────────────────────────────────────────────────────────────────────
    def _show_users(self):
        if self.user["role"] != "Admin":
            messagebox.showerror("Access Denied", "Only admins can manage users.")
            return
        self._clear_content()
        self._switch_highlight("users")
        self._page_header("⚙️  User Management", "users")

        tb = self._toolbar(self.content)
        Widgets.button(tb, "➕ Add User", lambda: self._user_form(), width=12).pack(side="left", padx=2)
        Widgets.button(tb, "🔄 Refresh",  lambda: self._refresh_users(), width=12, bg=COLOR["bg_card"]).pack(side="right", padx=2)

        cols = ("ID", "Username", "Role", "Full Name", "Email", "Phone", "Active", "Created")
        self.user_tree, frame = Widgets.treeview(self.content, cols)
        widths = [40, 120, 110, 160, 160, 110, 60, 120]
        for col, w in zip(cols, widths):
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=w, anchor="center")
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._refresh_users()

    def _refresh_users(self):
        for row in self.user_tree.get_children():
            self.user_tree.delete(row)
        for i, u in enumerate(self.db.get_all_users()):
            tag = "odd" if i % 2 else "even"
            self.user_tree.insert("", "end", values=(
                u["id"], u["username"], u["role"], u["full_name"],
                u.get("email",""), u.get("phone",""),
                "Yes" if u["active"] else "No", u["created_at"][:10],
            ), tags=(tag,))

    def _user_form(self):
        dlg = self._dialog("Create User", 480, 380)
        frm = tk.Frame(dlg, bg=COLOR["bg_mid"], padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        fields = [
            ("Username *",  "username",  "entry"),
            ("Password *",  "password",  "pass"),
            ("Full Name *", "full_name", "entry"),
            ("Role *",      "role",      ["Admin","Doctor","Receptionist"]),
            ("Email",       "email",     "entry"),
            ("Phone",       "phone",     "entry"),
        ]

        vars_ = {}
        for row, (label, key, ftype) in enumerate(fields):
            tk.Label(frm, text=label, font=FONT["small"],
                     bg=COLOR["bg_mid"], fg=COLOR["text_dim"], anchor="w"
                     ).grid(row=row, column=0, sticky="w", padx=4, pady=5)
            v = tk.StringVar()
            vars_[key] = v
            if ftype == "pass":
                Widgets.entry(frm, textvariable=v, width=30, show="●").grid(row=row, column=1, padx=4, pady=5)
            elif ftype == "entry":
                Widgets.entry(frm, textvariable=v, width=30).grid(row=row, column=1, padx=4, pady=5)
            else:
                Widgets.combo(frm, ftype, textvariable=v, width=28).grid(row=row, column=1, padx=4, pady=5)
        frm.columnconfigure(1, weight=1)

        def save():
            data = {k: v.get().strip() for k, v in vars_.items()}
            for req in ("username","password","full_name","role"):
                if not data.get(req):
                    messagebox.showerror("Validation", f"{req} is required.", parent=dlg); return
            if len(data["password"]) < 6:
                messagebox.showerror("Validation", "Password must be at least 6 characters.", parent=dlg); return
            ok = self.db.create_user(
                data["username"], data["password"], data["role"],
                data["full_name"], data.get("email",""), data.get("phone","")
            )
            if ok:
                messagebox.showinfo("Success", f"User '{data['username']}' created.", parent=dlg)
                dlg.destroy()
                self._refresh_users()
            else:
                messagebox.showerror("Error", "Username already exists.", parent=dlg)

        bf = tk.Frame(dlg, bg=COLOR["bg_mid"])
        bf.pack(pady=10)
        Widgets.button(bf, "💾 Create", save).pack(side="left", padx=8)
        Widgets.button(bf, "Cancel", dlg.destroy, bg=COLOR["bg_card"]).pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────────────────────────
    #  UTILITY METHODS
    # ─────────────────────────────────────────────────────────────────────────
    def _page_header(self, title, key):
        hdr = tk.Frame(self.content, bg=COLOR["bg_dark"])
        hdr.pack(fill="x", padx=14, pady=(14, 4))
        tk.Label(hdr, text=title, font=FONT["title"],
                 bg=COLOR["bg_dark"], fg=COLOR["accent"]).pack(side="left")
        tk.Frame(self.content, bg=COLOR["border"], height=1).pack(fill="x", padx=14, pady=4)

    def _toolbar(self, parent):
        tb = tk.Frame(parent, bg=COLOR["bg_card"], padx=8, pady=6)
        tb.pack(fill="x", padx=14, pady=4)
        return tb

    def _dialog(self, title, w=500, h=420):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=COLOR["bg_mid"])
        dlg.resizable(False, False)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        dlg.grab_set()
        return dlg

    def _export_csv(self, table: str):
        """Export the given table to a CSV file."""
        data_map = {
            "patients":     (self.db.get_patients,     ["patient_id","full_name","dob","gender","blood_group","phone","email","address","emergency_contact","created_at"]),
            "doctors":      (self.db.get_doctors,      ["doctor_id","full_name","specialization","qualification","phone","email","fee","available_days","created_at"]),
            "appointments": (self.db.get_appointments, ["appointment_id","patient_id","patient_name","doctor_id","doctor_name","appt_date","appt_time","reason","status","notes"]),
            "billing":      (self.db.get_invoices,     ["invoice_id","patient_id","patient_name","total_amount","paid_amount","discount","payment_method","status","created_at"]),
            "medicines":    (self.db.get_medicines,    ["medicine_id","name","category","manufacturer","unit","price","stock","min_stock","expiry_date"]),
        }
        if table not in data_map:
            return
        fn = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files","*.csv")],
            initialfile=f"{table}_{date.today().isoformat()}.csv"
        )
        if not fn:
            return
        get_fn, headers = data_map[table]
        rows = get_fn()
        try:
            with open(fn, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            messagebox.showinfo("Export Success", f"Data exported to:\n{fn}")
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION BOOTSTRAP
# ─────────────────────────────────────────────────────────────────────────────
class App:
    """Entry point – wires together the DB, Login, and Main windows."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.db = Database()
        self._show_login()

    def _show_login(self):
        for w in self.root.winfo_children():
            w.destroy()
        LoginWindow(self.root, self.db, self._on_login_success)

    def _on_login_success(self, user: dict):
        for w in self.root.winfo_children():
            w.destroy()
        MainApp(self.root, self.db, user)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
