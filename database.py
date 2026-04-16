import sqlite3 
import os
DB_PATH = os.getenv("DB_PATH", "/data/veraxia.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_usage (
    user_id TEXT,
    date TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT DEFAULT 'libre',
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_mensajes INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'activo'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    creada DATETIME DEFAULT CURRENT_TIMESTAMP,
    expira DATETIME NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    plan TEXT NOT NULL,
    monto_usd REAL,
    metodo TEXT,
    estado TEXT DEFAULT 'activo',
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    vencimiento DATE,
    notas TEXT
)
""")
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "veraxia777520@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "veraxia2024")

cursor.execute("""
    INSERT OR IGNORE INTO usuarios (email, password_hash, plan, estado)
    VALUES (?, ?, 'admin', 'activo')
""", (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD)))

conn.commit()
conn.commit()
