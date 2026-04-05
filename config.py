import os
import json
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_CONTEXT = 10
TEMPERATURE = 0.7
FREE_DAILY_LIMIT = 15  # mensajes gratis por día

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No se encontró OPENAI_API_KEY en .env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_CREDS_DICT = json.loads(GOOGLE_CREDENTIALS) if GOOGLE_CREDENTIALS else None
