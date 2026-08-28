import psycopg2
import os
from psycopg2.extras import RealDictCursor
import hashlib

DATABASE_URL = os.getenv("DATABASE_URL")

_conn = None
_cursor = None

def get_conn():
    """
    Retorna (conn, cursor) reconectando si la conexión está cerrada.
    USA UN CURSOR SEPARADO para el health check — no corrompe resultados pendientes.
    """
    global _conn, _cursor
    try:
        if _conn is None or _conn.closed != 0:
            raise Exception("Sin conexión")
        # Health check con cursor SEPARADO para no afectar _cursor
        _hc = _conn.cursor()
        _hc.execute("SELECT 1")
        _hc.close()
    except Exception:
        try:
            if _conn:
                _conn.close()
        except:
            pass
        _conn = psycopg2.connect(DATABASE_URL)
        _conn.autocommit = False
        _cursor = _conn.cursor()
    return _conn, _cursor

class _ProxyCursor:
    def __getattr__(self, name):
        _, cur = get_conn()
        return getattr(cur, name)

class _ProxyConn:
    def __getattr__(self, name):
        con, _ = get_conn()
        return getattr(con, name)

conn = _ProxyConn()
cursor = _ProxyCursor()

def init_db():
    con, cur = get_conn()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_usage (
        user_id TEXT,
        date TEXT,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        plan TEXT DEFAULT 'libre',
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ultimo_acceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_mensajes INTEGER DEFAULT 0,
        estado TEXT DEFAULT 'activo'
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sesiones (
        token TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        creada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expira TIMESTAMP NOT NULL
    )""")
    cur.execute("""
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
    )""")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "veraxia777520@gmail.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "veraxia2024")

    cur.execute("""
        INSERT INTO usuarios (email, password_hash, plan, estado)
        VALUES (%s, %s, 'admin', 'activo')
        ON CONFLICT (email) DO NOTHING
    """, (ADMIN_EMAIL, hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()))
    con.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_db()
