from openai import OpenAI
from config import MODEL, TEMPERATURE, OPENAI_API_KEY, WEBHOOK_URL
from identity import SYSTEM_IDENTITY
from memory import save_message, get_context, increment_daily_count
import requests
import logging

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


def generate_response(user_id: str, user_input: str) -> str:
    context = get_context(user_id)

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
