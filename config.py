import os
import json
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_CONTEXT = 10
TEMPERATURE = 0.7
FREE_DAILY_LIMIT = 7   # mensajes gratis por día (escasez estratégica)
MAX_TOKENS_RESPUESTA = 500   # tokens máx por respuesta
MAX_INPUT_CHARS = 800        # chars máx por mensaje del usuario
RATE_LIMIT_MENSAJES = 20     # mensajes por IP cada 10 min
RATE_LIMIT_VENTANA = 600     # segundos

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No se encontró OPENAI_API_KEY en .env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_CREDS_DICT = json.loads(GOOGLE_CREDENTIALS) if GOOGLE_CREDENTIALS else None
