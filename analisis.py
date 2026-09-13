"""analisis.py — Motor de aprendizaje veraxIA"""
import json, logging, os
from datetime import datetime

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _conn():
    """Conexión PostgreSQL con autocommit — sin manejo de transacciones."""
    import psycopg2
    c = psycopg2.connect(os.getenv("DATABASE_URL"))
    c.autocommit = True
    return c


def _ia(prompt, max_tokens=600):
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


def init_tablas_analisis():
    try:
        c = _conn()
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
        c.close()
        logger.info("✅ Tablas analisis OK")
    except Exception as e:
        logger.warning(f"Tablas analisis: {e}")


def _analizar(mensajes):
    if len(mensajes) < 2:
        return {}
    texto = "\n".join([
        f"{'U' if m['role']=='user' else 'V'}: {m['content'][:200]}"
        for m in mensajes[:16]
    ])
    raw = _ia(f"""Analiza esta conversación con una IA filosófica.
{texto}

Responde SOLO JSON:
{{"intencion_real":"...","emocion":"...","filosofia":"...","calidad":0.7,"tipo_respuesta":"...","temas":"..."}}""")
    try:
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except:
        return {"intencion_real":"conversación","emocion":"neutral","filosofia":"general",
                "calidad":0.5,"tipo_respuesta":"reflexiva","temas":"varios"}


def analizar_todo_el_historico():
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT DISTINCT user_id FROM messages WHERE role='user' AND content!=''")
        usuarios = [r[0] for r in cur.fetchall()]
        c.close()
    except Exception as e:
        logger.error(f"Error obteniendo usuarios: {e}")
        return {"procesados": 0, "total": 0}

    procesados = 0
    for uid in usuarios:
        try:
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

            c2 = _conn()
            cur2 = c2.cursor()
            cur2.execute("""INSERT INTO conversation_insights
                (user_id,fecha,intencion_real,emocion_detectada,conexion_filosofica,calidad_estimada)
                VALUES (%s,%s,%s,%s,%s,%s)""",
                (uid, datetime.now().strftime("%Y-%m-%d"),
                 ins.get("intencion_real","")[:300], ins.get("emocion","")[:100],
                 ins.get("filosofia","")[:200], float(ins.get("calidad",0.5))))

            cur2.execute("""INSERT INTO user_profiles
                (user_id,busqueda_profunda,estado_emocional_frecuente,marcos_filosoficos,
                 temas_recurrentes,tipo_respuesta_que_funciona,total_sesiones)
                VALUES (%s,%s,%s,%s,%s,%s,1)
                ON CONFLICT (user_id) DO UPDATE SET
                    busqueda_profunda=EXCLUDED.busqueda_profunda,
                    estado_emocional_frecuente=EXCLUDED.estado_emocional_frecuente,
                    marcos_filosoficos=EXCLUDED.marcos_filosoficos,
                    temas_recurrentes=EXCLUDED.temas_recurrentes,
                    tipo_respuesta_que_funciona=EXCLUDED.tipo_respuesta_que_funciona,
                    total_sesiones=user_profiles.total_sesiones+1,
                    ultima_actualizacion=CURRENT_TIMESTAMP""",
                (uid, ins.get("intencion_real","")[:300], ins.get("emocion","")[:100],
                 ins.get("filosofia","")[:200], ins.get("temas","")[:300],
                 ins.get("tipo_respuesta","")[:300]))
            c2.close()
            procesados += 1
            logger.info(f"✅ {uid}: {ins.get('intencion_real','')[:40]}")

        except Exception as e:
            logger.error(f"❌ Error {uid}: {e}")
            try: c2.close()
            except: pass
            continue

    logger.info(f"✅ {procesados}/{len(usuarios)} procesados")
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
Busca: {p[1]}
Emoción frecuente: {p[2]}
Filosofía afín: {p[3]}
Temas recurrentes: {p[4]}
Responde de forma: {p[5]}
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
        if len(msgs) >= 4:
            ins = _analizar(msgs)
            if ins:
                c2 = _conn()
                cur2 = c2.cursor()
                cur2.execute("""INSERT INTO user_profiles
                    (user_id,busqueda_profunda,estado_emocional_frecuente,marcos_filosoficos,
                     temas_recurrentes,tipo_respuesta_que_funciona,total_sesiones)
                    VALUES (%s,%s,%s,%s,%s,%s,1)
                    ON CONFLICT (user_id) DO UPDATE SET
                        busqueda_profunda=EXCLUDED.busqueda_profunda,
                        estado_emocional_frecuente=EXCLUDED.estado_emocional_frecuente,
                        marcos_filosoficos=EXCLUDED.marcos_filosoficos,
                        temas_recurrentes=EXCLUDED.temas_recurrentes,
                        tipo_respuesta_que_funciona=EXCLUDED.tipo_respuesta_que_funciona,
                        total_sesiones=user_profiles.total_sesiones+1,
                        ultima_actualizacion=CURRENT_TIMESTAMP""",
                    (user_id, ins.get("intencion_real","")[:300], ins.get("emocion","")[:100],
                     ins.get("filosofia","")[:200], ins.get("temas","")[:300],
                     ins.get("tipo_respuesta","")[:300]))
                c2.close()
                logger.info(f"✅ Post-sesión: {user_id}")
    except Exception as e:
        logger.error(f"❌ Post-sesión {user_id}: {e}")
