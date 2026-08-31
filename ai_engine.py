from openai import OpenAI
from config import MODEL, TEMPERATURE, OPENAI_API_KEY, MAX_TOKENS_RESPUESTA, MAX_INPUT_CHARS, WEBHOOK_URL
from identity import SYSTEM_IDENTITY
from memory import save_message, get_context, increment_daily_count
import requests
import logging
import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = "6325653174"

def _alerta_telegram(user_id: str, mensaje: str):
    if not TELEGRAM_TOKEN:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🚨 CRISIS veraxIA\n👤 {user_id}\n💬 {mensaje[:300]}"},
            timeout=5)
    except:
        pass

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)


def detectar_emocion(texto: str) -> str:
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"En una sola palabra, ¿qué emoción expresa este mensaje? Solo la emoción: '{texto}'"}],
            temperature=0,
            max_tokens=10
        )
        return r.choices[0].message.content.strip()
    except:
        return ""



import re

# ── Detección básica de crisis ──────────────────────────────
_CRISIS_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\b(suicid|quiero morir|me quiero morir|matarme|acabar con mi vida|no quiero vivir|hacerme daño)\b",
    r"\b(kill myself|end my life|want to die|hurt myself|harm myself)\b",
    r"\b(quero morrer|me matar|acabar com minha vida|me machucar)\b",
]]

CRISIS_MSG = (
    "Antes de continuar, quiero que sepas algo importante: no tienes que pasar por esto solo/a.\n\n"
    "Si estás pensando en hacerte daño, por favor habla ahora con alguien preparado:\n"
    "• Chile: *4141 (Línea Prevención Suicidio, gratis 24/7)\n"
    "• EE.UU.: 988 (llama o textea, 24/7)\n"
    "• Cualquier país: findahelpline.com\n\n"
    "Estoy aquí contigo. ¿Quieres contarme qué está pasando?"
)

def is_crisis(text):
    return any(rx.search(text or "") for rx in _CRISIS_RE)
# ────────────────────────────────────────────────────────────

def generate_response(user_id: str, user_input: str) -> str:
    context = get_context(user_id)

    # Límite de input
    if len(user_input) > MAX_INPUT_CHARS:
        user_input = user_input[:MAX_INPUT_CHARS]

    # Detección de crisis
    if is_crisis(user_input):
        save_message(user_id, user_input, CRISIS_MSG, "Crisis")
        increment_daily_count(user_id)
        _alerta_telegram(user_id, user_input)
        return CRISIS_MSG

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_IDENTITY},
            *context,
            {"role": "user", "content": user_input}
        ],
        temperature=TEMPERATURE,
        max_tokens=800
    )

    reply = response.choices[0].message.content
    emocion = detectar_emocion(user_input)

    save_message(user_id, user_input, reply, emocion)
    increment_daily_count(user_id)

    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={
                "user_id": str(user_id),
                "mensaje": user_input,
                "respuesta": reply,
                "emocion": emocion
            }, timeout=5)
        except:
            pass

    return reply
