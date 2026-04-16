from database import cursor, conn
from config import MAX_CONTEXT, GOOGLE_CREDS_DICT, FREE_DAILY_LIMIT
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Google Sheets — opcional
hoja_conversaciones = None
hoja_usuarios = None

if GOOGLE_CREDS_DICT:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        CREDS = Credentials.from_service_account_info(GOOGLE_CREDS_DICT, scopes=SCOPES)
        gc = gspread.authorize(CREDS)
        sh = gc.open("veraxia_data")
        hoja_conversaciones = sh.worksheet("conversaciones")
        hoja_usuarios = sh.worksheet("usuarios")
        logger.info("✅ Google Sheets conectado")
    except Exception as e:
        logger.warning(f"⚠️ Google Sheets no disponible: {e}")


def get_daily_count(user_id: str) -> int:
    hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT count FROM daily_usage WHERE user_id=%s AND date=%s", (user_id, hoy))
    row = cursor.fetchone()
    return row[0] if row else 0


def increment_daily_count(user_id: str):
    hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO daily_usage (user_id, date, count) VALUES (%s, %s, 1)
        ON CONFLICT(user_id, date) DO UPDATE SET count = daily_usage.count + 1
    """, (user_id, hoy))
    conn.commit()


def is_within_limit(user_id: str) -> bool:
    return get_daily_count(user_id) < FREE_DAILY_LIMIT


def save_message(user_id: str, user_input: str, reply: str, emocion: str = ""):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        cursor.execute("INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)", (user_id, "user", user_input))
        cursor.execute("INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)", (user_id, "assistant", reply))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ PostgreSQL: {e}")
        conn.rollback()

    if hoja_conversaciones:
        try:
            hoja_conversaciones.append_row([ahora, str(user_id), user_input, reply, emocion])
            if hoja_usuarios:
                usuarios = hoja_usuarios.col_values(2)
                if str(user_id) not in usuarios:
                    hoja_usuarios.append_row([ahora, str(user_id), "", ahora, 1, "activo"])
                else:
                    fila = usuarios.index(str(user_id)) + 1
                    hoja_usuarios.update_cell(fila, 4, ahora)
                    total = hoja_usuarios.cell(fila, 5).value or 0
                    hoja_usuarios.update_cell(fila, 5, int(total) + 1)
        except Exception as e:
            logger.warning(f"⚠️ Sheets (no crítico): {e}")


def get_context(user_id: str) -> list:
    try:
        cursor.execute(
            "SELECT role, content FROM messages WHERE user_id=%s ORDER BY id DESC LIMIT %s",
            (user_id, MAX_CONTEXT)
        )
        rows = cursor.fetchall()
        rows.reverse()
        return [{"role": r, "content": c} for r, c in rows]
    except Exception as e:
        logger.error(f"❌ Contexto: {e}")
        return []


def clear_context(user_id: str):
    try:
        cursor.execute("DELETE FROM messages WHERE user_id=%s", (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Reset: {e}")
