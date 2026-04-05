import sqlite3

conn = sqlite3.connect("veraxia.db", check_same_thread=False)
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

conn.commit()
