# VeraxIA — Inteligencia cognitiva y ontológica
**veraxIA SpA · Villa Alegre, Región del Maule, Chile**

---

## Estructura del proyecto

```
veraxia/
├── app.py              # Servidor Flask (web + API)
├── ai_engine.py        # Motor de respuestas (OpenAI GPT-4o mini)
├── identity.py         # Sistema de identidad ontológica
├── memory.py           # Memoria SQLite + Google Sheets
├── database.py         # Base de datos local
├── config.py           # Configuración y variables
├── templates/
│   └── index.html      # Landing page + chat
├── Procfile            # Para Railway
├── requirements.txt
└── .env.example
```

---

## Instalación local

```bash
pip install -r requirements.txt
cp .env.example .env
# Completa tu OPENAI_API_KEY en .env
python app.py
```

Abre: http://localhost:8080

---

## Deploy en Railway

1. Crea proyecto nuevo en railway.app
2. Conecta tu repositorio GitHub (o sube los archivos)
3. En Variables de entorno agrega:
   - `OPENAI_API_KEY` = tu clave
   - (opcional) `TELEGRAM_TOKEN`, `WEBHOOK_URL`, `GOOGLE_CREDENTIALS`
4. Railway detecta el Procfile automáticamente
5. Tu URL pública queda lista al instante

---

## Modelo de negocio

| Plan | Precio | Límite |
|------|--------|--------|
| Libre | $0 | 15 mensajes/día |
| Alma | $7 USD/mes | Ilimitado |
| Alma Pro | $15 USD/mes | Ilimitado + prioridad |

El límite diario se controla desde `config.py` → `FREE_DAILY_LIMIT`

---

## Costos de operación estimados (GPT-4o mini)

| Usuarios/día | Mensajes/usuario | Costo mensual |
|-------------|-----------------|---------------|
| 100 | 5 | ~$3 USD |
| 500 | 5 | ~$15 USD |
| 1000 | 5 | ~$30 USD |

---

*Creado por Daniela Brito · veraxIA SpA*
