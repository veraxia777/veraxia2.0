"""analisis.py — Motor de aprendizaje veraxIA"""
import json, logging, os
from datetime import datetime

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _conn():
    import psycopg2
    c = psycopg2.connect(os.getenv("DATABASE_URL"))
    c.autocommit = True
    return c


def _crear_tablas(c):
    """Crear tablas si no existen — llamado antes de cada operación."""
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


def _ia(prompt, max_tokens=500):
    try:
        import urllib.request as ur
        data = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }).encode()
        req = ur.Request("https://api.openai.com/v1/chat/completions", data=data,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"})
        with ur.urlopen(req, timeout=30) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"IA error: {e}")
        return ""


def _analizar(mensajes):
    if len(mensajes) < 2:
        return {}
    texto = "\n".join([
        f"{'U' if m['role']=='user' else 'V'}: {m['content'][:200]}"
        for m in mensajes[:16]
    ])
    raw = _ia(f"""Analiza esta conversacion con una IA filosofica.
{texto}

Responde SOLO JSON sin markdown:
{{"intencion_real":"que busca esta persona","emocion":"estado emocional","filosofia":"corriente filosofica afin","calidad":0.7,"tipo_respuesta":"que tipo de respuesta funciona","temas":"temas recurrentes"}}""")
    try:
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except:
        return {"intencion_real":"conversacion general","emocion":"neutral",
                "filosofia":"general","calidad":0.5,"tipo_respuesta":"reflexiva","temas":"varios"}


def analizar_todo_el_historico():
    # 1. Obtener usuarios
    try:
        c = _conn()
        _crear_tablas(c)  # asegurar tablas antes de todo
        cur = c.cursor()
        cur.execute("SELECT DISTINCT user_id FROM messages WHERE role='user' AND content!=''")
        usuarios = [r[0] for r in cur.fetchall()]
        c.close()
    except Exception as e:
        logger.error(f"Error obteniendo usuarios: {e}")
        return {"procesados": 0, "total": 0}

    logger.info(f"📊 Analizando {len(usuarios)} usuarios...")
    procesados = 0

    for uid in usuarios:
        try:
            # Obtener mensajes
            c = _conn()
            cur = c.cursor()
            cur.execute("SELECT role,content FROM messages WHERE user_id=%s ORDER BY id LIMIT 40", (uid,))
            msgs = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
            c.close()

            if len(msgs) < 2:
                continue

            ins = _analizar(msgs)
            if not ins:
                continue

            # Guardar resultados
            c2 = _conn()
            _crear_tablas(c2)  # asegurar tablas en esta conexión también
            cur2 = c2.cursor()

            cur2.execute("""INSERT INTO conversation_insights
                (user_id, fecha, intencion_real, emocion_detectada, conexion_filosofica, calidad_estimada)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (uid, datetime.now().strftime("%Y-%m-%d"),
                 str(ins.get("intencion_real",""))[:300],
                 str(ins.get("emocion",""))[:100],
                 str(ins.get("filosofia",""))[:200],
                 float(ins.get("calidad", 0.5))))

            cur2.execute("""INSERT INTO user_profiles
                (user_id, busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos,
                 temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
                ON CONFLICT (user_id) DO UPDATE SET
                    busqueda_profunda = EXCLUDED.busqueda_profunda,
                    estado_emocional_frecuente = EXCLUDED.estado_emocional_frecuente,
                    marcos_filosoficos = EXCLUDED.marcos_filosoficos,
                    temas_recurrentes = EXCLUDED.temas_recurrentes,
                    tipo_respuesta_que_funciona = EXCLUDED.tipo_respuesta_que_funciona,
                    total_sesiones = user_profiles.total_sesiones + 1,
                    ultima_actualizacion = CURRENT_TIMESTAMP""",
                (uid,
                 str(ins.get("intencion_real",""))[:300],
                 str(ins.get("emocion",""))[:100],
                 str(ins.get("filosofia",""))[:200],
                 str(ins.get("temas",""))[:300],
                 str(ins.get("tipo_respuesta",""))[:300]))

            c2.close()
            procesados += 1
            logger.info(f"✅ {uid}: {str(ins.get('intencion_real',''))[:50]}")

        except Exception as e:
            logger.error(f"❌ Error {uid}: {e}")
            try: c2.close()
            except: pass
            continue

    logger.info(f"✅ Completado: {procesados}/{len(usuarios)}")
    return {"procesados": procesados, "total": len(usuarios)}


def get_contexto_usuario(user_id):
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user_id,))
        p = cur.fetchone()
        c.close()
        if not p or not p[1]:
            return ""
        return f"""[MEMORIA — {p[6]} sesiones previas]
Lo que busca: {p[1]}
Emocion frecuente: {p[2]}
Filosofia afin: {p[3]}
Temas recurrentes: {p[4]}
Tipo de respuesta que funciona: {p[5]}
Usa este contexto sin mencionarlo."""
    except:
        return ""


def analizar_post_sesion(user_id):
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT role,content FROM messages WHERE user_id=%s ORDER BY id DESC LIMIT 20", (user_id,))
        msgs = list(reversed([{"role": r[0], "content": r[1]} for r in cur.fetchall()]))
        c.close()

        if len(msgs) < 4:
            return

        ins = _analizar(msgs)
        if not ins:
            return

        c2 = _conn()
        _crear_tablas(c2)
        cur2 = c2.cursor()
        cur2.execute("""INSERT INTO user_profiles
            (user_id, busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos,
             temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE SET
                busqueda_profunda = EXCLUDED.busqueda_profunda,
                estado_emocional_frecuente = EXCLUDED.estado_emocional_frecuente,
                marcos_filosoficos = EXCLUDED.marcos_filosoficos,
                temas_recurrentes = EXCLUDED.temas_recurrentes,
                tipo_respuesta_que_funciona = EXCLUDED.tipo_respuesta_que_funciona,
                total_sesiones = user_profiles.total_sesiones + 1,
                ultima_actualizacion = CURRENT_TIMESTAMP""",
            (user_id,
             str(ins.get("intencion_real",""))[:300],
             str(ins.get("emocion",""))[:100],
             str(ins.get("filosofia",""))[:200],
             str(ins.get("temas",""))[:300],
             str(ins.get("tipo_respuesta",""))[:300]))
        c2.close()
        logger.info(f"✅ Post-sesion actualizado: {user_id}")
    except Exception as e:
        logger.error(f"❌ Post-sesion {user_id}: {e}")
