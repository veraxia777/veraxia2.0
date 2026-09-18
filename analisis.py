"""analisis.py — Motor de aprendizaje veraxIA (sin datos falsos)"""
import json, logging, os, time
from datetime import datetime

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Valores genéricos que NO deben guardarse — son placeholders de error
_VALORES_FALSOS = {
    "conversacion general", "conversación general",
    "neutral", "general", "reflexiva", "varios", "varias",
    "[que busca realmente esta persona]",
    "[estado emocional predominante]",
}


def _conn():
    import psycopg2
    c = psycopg2.connect(os.getenv("DATABASE_URL"))
    c.autocommit = True
    return c


def _crear_tablas(c):
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        busqueda_profunda TEXT DEFAULT '',
        estado_emocional_frecuente TEXT DEFAULT '',
        marcos_filosoficos TEXT DEFAULT '',
        temas_recurrentes TEXT DEFAULT '',
        tipo_respuesta_que_funciona TEXT DEFAULT '',
        total_sesiones INTEGER DEFAULT 0,
        ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS conversation_insights (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        fecha TEXT,
        intencion_real TEXT DEFAULT '',
        emocion_detectada TEXT DEFAULT '',
        conexion_filosofica TEXT DEFAULT '',
        calidad_estimada REAL DEFAULT 0.5,
        analizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")


def init_tablas_analisis():
    try:
        c = _conn()
        _crear_tablas(c)
        c.close()
        logger.info("✅ Tablas analisis OK")
    except Exception as e:
        logger.warning(f"Tablas analisis: {e}")


def _ia(prompt, max_tokens=600, intentos=3):
    """Llama a GPT con reintentos. Devuelve string o '' si todos fallan."""
    import urllib.request as ur
    for intento in range(intentos):
        try:
            data = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3
            }).encode()
            req = ur.Request(
                "https://api.openai.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            with ur.urlopen(req, timeout=30) as r:
                return json.load(r)["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"_ia intento {intento+1}/{intentos}: {e}")
            if intento < intentos - 1:
                time.sleep(2)
    return ""


def _parsear_json(raw):
    """Intenta parsear JSON limpiando posibles decoradores de markdown."""
    if not raw:
        return None
    raw = raw.strip()
    # Quitar bloques de código
    if "```" in raw:
        partes = raw.split("```")
        for p in partes:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            try:
                return json.loads(p)
            except:
                continue
    # Intentar directo
    try:
        return json.loads(raw)
    except:
        pass
    # Buscar primer { ... }
    try:
        inicio = raw.index("{")
        fin = raw.rindex("}") + 1
        return json.loads(raw[inicio:fin])
    except:
        return None


def _es_valido(resultado):
    """Verifica que el análisis tenga contenido real, no placeholders."""
    if not resultado:
        return False
    intencion = resultado.get("intencion_real", "").strip().lower()
    emocion = resultado.get("emocion", "").strip().lower()
    if not intencion or not emocion:
        return False
    if intencion in _VALORES_FALSOS or emocion in _VALORES_FALSOS:
        return False
    if len(intencion) < 10:  # demasiado corto para ser real
        return False
    return True


def _analizar(mensajes):
    """
    Analiza una conversación con GPT.
    Devuelve dict con datos reales, o {} si el análisis no es confiable.
    NUNCA devuelve datos genéricos/falsos.
    """
    mensajes_usuario = [m for m in mensajes if m["role"] == "user"]
    if len(mensajes_usuario) < 3:
        logger.info("Muy pocos mensajes para análisis confiable (mín. 3 del usuario)")
        return {}

    texto = "\n".join([
        f"{'Usuario' if m['role']=='user' else 'veraxIA'}: {m['content'][:250]}"
        for m in mensajes[:20]
    ])

    prompt = f"""Analiza esta conversación con una IA filosófica llamada veraxIA.
REGLA CRÍTICA: Responde ÚNICAMENTE con el JSON. Sin texto antes ni después. Sin bloques de código. Sin explicaciones.

Conversación:
{texto}

Completa este JSON con análisis real basado en la conversación (no inventes ni uses valores genéricos):
{{"intencion_real":"qué busca profundamente esta persona según sus mensajes","emocion":"emoción predominante observada en sus mensajes","filosofia":"corriente filosófica o enfoque mental que resuena con esta persona","calidad":0.8,"tipo_respuesta":"qué tipo de respuesta le funcionó mejor a esta persona","temas":"temas concretos que surgieron, separados por coma"}}"""

    for intento in range(2):
        raw = _ia(prompt)
        if not raw:
            continue
        resultado = _parsear_json(raw)
        if resultado and _es_valido(resultado):
            logger.info(f"✅ Análisis válido en intento {intento+1}")
            return resultado
        logger.warning(f"Intento {intento+1}: resultado inválido o genérico — reintentando")
        if intento == 0:
            time.sleep(1)

    logger.warning("❌ Análisis no confiable — no se guardará para evitar datos falsos")
    return {}


def analizar_todo_el_historico():
    try:
        c = _conn()
        _crear_tablas(c)
        cur = c.cursor()
        cur.execute("SELECT DISTINCT user_id FROM messages WHERE role='user' AND content!=''")
        usuarios = [r[0] for r in cur.fetchall()]
        c.close()
    except Exception as e:
        logger.error(f"Error obteniendo usuarios: {e}")
        return {"procesados": 0, "total": 0, "saltados": 0}

    logger.info(f"📊 Analizando {len(usuarios)} usuarios...")
    procesados = 0
    saltados = 0

    for uid in usuarios:
        try:
            c = _conn()
            cur = c.cursor()
            cur.execute(
                "SELECT role, content FROM messages WHERE user_id=%s ORDER BY id LIMIT 40",
                (uid,)
            )
            msgs = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
            c.close()

            ins = _analizar(msgs)
            if not ins:
                saltados += 1
                logger.info(f"⏭ {uid}: saltado (análisis no confiable)")
                continue

            c2 = _conn()
            _crear_tablas(c2)
            cur2 = c2.cursor()

            cur2.execute(
                """INSERT INTO conversation_insights
                   (user_id, fecha, intencion_real, emocion_detectada, conexion_filosofica, calidad_estimada)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (uid, datetime.now().strftime("%Y-%m-%d"),
                 str(ins.get("intencion_real", ""))[:300],
                 str(ins.get("emocion", ""))[:100],
                 str(ins.get("filosofia", ""))[:200],
                 float(ins.get("calidad", 0.5)))
            )

            cur2.execute(
                """INSERT INTO user_profiles
                   (user_id, busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos,
                    temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
                   VALUES (%s, %s, %s, %s, %s, %s, 1)
                   ON CONFLICT (user_id) DO UPDATE SET
                       busqueda_profunda            = EXCLUDED.busqueda_profunda,
                       estado_emocional_frecuente   = EXCLUDED.estado_emocional_frecuente,
                       marcos_filosoficos           = EXCLUDED.marcos_filosoficos,
                       temas_recurrentes            = EXCLUDED.temas_recurrentes,
                       tipo_respuesta_que_funciona  = EXCLUDED.tipo_respuesta_que_funciona,
                       total_sesiones               = user_profiles.total_sesiones + 1,
                       ultima_actualizacion         = CURRENT_TIMESTAMP""",
                (uid,
                 str(ins.get("intencion_real", ""))[:300],
                 str(ins.get("emocion", ""))[:100],
                 str(ins.get("filosofia", ""))[:200],
                 str(ins.get("temas", ""))[:300],
                 str(ins.get("tipo_respuesta", ""))[:300])
            )
            c2.close()
            procesados += 1
            logger.info(f"✅ {uid}: {str(ins.get('intencion_real',''))[:60]}")

        except Exception as e:
            logger.error(f"❌ Error {uid}: {e}")
            saltados += 1
            try: c2.close()
            except: pass
            continue

    logger.info(f"✅ Completado: {procesados} analizados, {saltados} saltados de {len(usuarios)}")
    return {"procesados": procesados, "total": len(usuarios), "saltados": saltados}


def get_contexto_usuario(user_id):
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            SELECT user_id, busqueda_profunda, estado_emocional_frecuente,
                   marcos_filosoficos, temas_recurrentes, tipo_respuesta_que_funciona,
                   total_sesiones,
                   estado_inicial, busqueda_principal, area_vida,
                   estilo_conversacion, frecuencia_estado, onboarding_completado
            FROM user_profiles WHERE user_id=%s
        """, (user_id,))
        p = cur.fetchone()
        c.close()
        if not p:
            return ""

        partes = []

        # Datos del onboarding (declarados por el usuario)
        ob_completado = p[12] if len(p) > 12 else False
        if ob_completado:
            ob_parts = []
            if p[7] and p[7] != 'omitido':
                ob_parts.append(f"Estado emocional al llegar: {p[7]}")
            if p[8] and p[8] != 'omitido':
                ob_parts.append(f"Lo que busca en veraxIA: {p[8]}")
            if p[9] and p[9] != 'omitido':
                ob_parts.append(f"Area de vida a explorar: {p[9]}")
            if p[10] and p[10] != 'omitido':
                ob_parts.append(f"Estilo de conversacion preferido: {p[10]}")
            if p[11] and p[11] != 'omitido':
                ob_parts.append(f"Frecuencia del estado: {p[11]}")
            if ob_parts:
                partes.append("[LO QUE ESTA PERSONA DECLARO AL LLEGAR]\n" + "\n".join(ob_parts))

        # Datos del RSI (aprendidos de conversaciones)
        if p[6] and int(p[6]) > 0:
            rsi_parts = []
            if p[1] and p[1].strip() not in _VALORES_FALSOS:
                rsi_parts.append(f"Busqueda profunda: {p[1]}")
            if p[2] and p[2].strip():
                rsi_parts.append(f"Emocion frecuente: {p[2]}")
            if p[3] and p[3].strip():
                rsi_parts.append(f"Marco filosofico afin: {p[3]}")
            if p[4] and p[4].strip():
                rsi_parts.append(f"Temas recurrentes: {p[4]}")
            if p[5] and p[5].strip():
                rsi_parts.append(f"Tipo de respuesta que funciona: {p[5]}")
            if rsi_parts:
                partes.append(f"[LO QUE VERAXIA APRENDIO — {p[6]} sesiones]\n" + "\n".join(rsi_parts))

        if not partes:
            return ""

        return "\n\n".join(partes) + "\n\nUsa este contexto para responder con mayor profundidad sin mencionarlo directamente."
    except Exception as e:
        logger.warning(f"[contexto] {e}")
        return ""


def analizar_post_sesion(user_id):
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute(
            "SELECT role, content FROM messages WHERE user_id=%s ORDER BY id DESC LIMIT 20",
            (user_id,)
        )
        msgs = list(reversed([{"role": r[0], "content": r[1]} for r in cur.fetchall()]))
        c.close()

        ins = _analizar(msgs)
        if not ins:
            logger.info(f"⏭ Post-sesion {user_id}: análisis no confiable, sin cambios")
            return

        c2 = _conn()
        _crear_tablas(c2)
        cur2 = c2.cursor()
        cur2.execute(
            """INSERT INTO user_profiles
               (user_id, busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos,
                temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
               VALUES (%s, %s, %s, %s, %s, %s, 1)
               ON CONFLICT (user_id) DO UPDATE SET
                   busqueda_profunda            = EXCLUDED.busqueda_profunda,
                   estado_emocional_frecuente   = EXCLUDED.estado_emocional_frecuente,
                   marcos_filosoficos           = EXCLUDED.marcos_filosoficos,
                   temas_recurrentes            = EXCLUDED.temas_recurrentes,
                   tipo_respuesta_que_funciona  = EXCLUDED.tipo_respuesta_que_funciona,
                   total_sesiones               = user_profiles.total_sesiones + 1,
                   ultima_actualizacion         = CURRENT_TIMESTAMP""",
            (user_id,
             str(ins.get("intencion_real", ""))[:300],
             str(ins.get("emocion", ""))[:100],
             str(ins.get("filosofia", ""))[:200],
             str(ins.get("temas", ""))[:300],
             str(ins.get("tipo_respuesta", ""))[:300])
        )
        c2.close()
        logger.info(f"✅ Post-sesion actualizado: {user_id} — {str(ins.get('intencion_real',''))[:50]}")
    except Exception as e:
        logger.error(f"❌ Post-sesion {user_id}: {e}")
