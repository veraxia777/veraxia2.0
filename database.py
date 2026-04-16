import psycopg2
import os
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT DEFAULT 'libre',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_mensajes INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'activo'
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    creada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira TIMESTAMP NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    plan TEXT NOT NULL,
    monto_usd REAL,
    metodo TEXT,
    estado TEXT DEFAULT 'activo',
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    INSERT INTO usuarios (email, password_hash, plan, estado)
    VALUES (%s, %s, 'admin', 'activo')
    ON CONFLICT (email) DO NOTHING
""", (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD)))
conn.commit()