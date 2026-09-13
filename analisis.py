"""
analisis.py — Motor de análisis y aprendizaje de veraxIA
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _get_fresh_conn():
    """Obtiene una conexión fresca para operaciones de análisis."""
    import psycopg2
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn, conn.cursor()


def _llamar_ia(prompt: str, max_tokens: int = 800) -> str:
    try:
        import urllib.request as ur
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
            result = json.load(r)
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"❌ Error IA: {e}")
        return ""


def init_tablas_analisis():
    try:
        con, cur = _get_fresh_conn()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                busqueda_profunda TEXT DEFAULT '',
                estado_emocional_frecuente TEXT DEFAULT '',
                marcos_filosoficos TEXT DEFAULT '',
                temas_recurrentes TEXT DEFAULT '',
                tipo_respuesta_que_funciona TEXT DEFAULT '',
                total_sesiones INTEGER DEFAULT 0,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_insights (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                fecha TEXT,
                intencion_real TEXT DEFAULT '',
                emocion_detectada TEXT DEFAULT '',
                conexion_filosofica TEXT DEFAULT '',
                calidad_estimada REAL DEFAULT 0.5,
                analizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()
        con.close()
        logger.info("✅ Tablas análisis listas")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")


def analizar_conversacion(mensajes: list) -> dict:
    if not mensajes or len(mensajes) < 2:
        return {}

    texto = "\n".join([
        f"{'Usuario' if m['role'] == 'user' else 'veraxIA'}: {m['content'][:300]}"
        for m in mensajes[:20]
    ])

    prompt = f"""Analiza esta conversación con veraxIA (IA filosófica para autoconocimiento).

CONVERSACIÓN:
{texto}

Responde SOLO en JSON con estas claves:
{{
  "intencion_real": "qué buscaba realmente esta persona",
  "emocion_detectada": "estado emocional dominante en una palabra",
  "conexion_filosofica": "corriente filosófica más afín",
  "calidad_dialogo": 0.7,
  "respuestas_efectivas": "tipo de respuesta que generó apertura",
  "temas_recurrentes": "temas que aparecieron más de una vez"
}}"""

    raw = _llamar_ia(prompt)
    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return {
            "intencion_real": "conversación general",
            "emocion_detectada": "neutral",
            "conexion_filosofica": "general",
            "calidad_dialogo": 0.5,
            "respuestas_efectivas": "reflexivas",
            "temas_recurrentes": "varios"
        }


def analizar_todo_el_historico():
    try:
        con, cur = _get_fresh_conn()
        cur.execute("SELECT DISTINCT user_id FROM messages WHERE role='user' AND content != ''")
        usuarios = [row[0] for row in cur.fetchall()]
        con.close()
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuarios: {e}")
        return {"procesados": 0, "total": 0}

    logger.info(f"📊 Analizando {len(usuarios)} usuarios...")
    procesados = 0

    for user_id in usuarios:
        try:
            # Conexión fresca por cada usuario
            con, cur = _get_fresh_conn()

            cur.execute("""
                SELECT role, content FROM messages
                WHERE user_id=%s ORDER BY id ASC LIMIT 60
            """, (user_id,))
            mensajes = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
            con.close()

            if len(mensajes) < 2:
                continue

            insight = analizar_conversacion(mensajes)
            if not insight:
                continue

            # Guardar insight con conexión fresca
            con2, cur2 = _get_fresh_conn()
            try:
                cur2.execute("""
                    INSERT INTO conversation_insights
                    (user_id, fecha, intencion_real, emocion_detectada, conexion_filosofica, calidad_estimada)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    insight.get("intencion_real", "")[:300],
                    insight.get("emocion_detectada", "")[:100],
                    insight.get("conexion_filosofica", "")[:200],
                    float(insight.get("calidad_dialogo", 0.5))
                ))

                # Upsert perfil del usuario
                cur2.execute("""
                    INSERT INTO user_profiles
                    (user_id, busqueda_profunda, estado_emocional_frecuente,
                     marcos_filosoficos, temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                    ON CONFLICT (user_id) DO UPDATE SET
                        busqueda_profunda = EXCLUDED.busqueda_profunda,
                        estado_emocional_frecuente = EXCLUDED.estado_emocional_frecuente,
                        marcos_filosoficos = EXCLUDED.marcos_filosoficos,
                        temas_recurrentes = EXCLUDED.temas_recurrentes,
                        tipo_respuesta_que_funciona = EXCLUDED.tipo_respuesta_que_funciona,
                        total_sesiones = user_profiles.total_sesiones + 1,
                        ultima_actualizacion = CURRENT_TIMESTAMP
                """, (
                    user_id,
                    insight.get("intencion_real", "")[:300],
                    insight.get("emocion_detectada", "")[:100],
                    insight.get("conexion_filosofica", "")[:200],
                    insight.get("temas_recurrentes", "")[:300],
                    insight.get("respuestas_efectivas", "")[:300]
                ))

                con2.commit()
                procesados += 1
                logger.info(f"✅ {user_id}: {insight.get('intencion_real', 'N/A')[:50]}")

            except Exception as e:
                con2.rollback()
                logger.error(f"❌ Error guardando {user_id}: {e}")
            finally:
                con2.close()

        except Exception as e:
            logger.error(f"❌ Error analizando {user_id}: {e}")
            continue

    logger.info(f"✅ Completado: {procesados}/{len(usuarios)}")
    return {"procesados": procesados, "total": len(usuarios)}


def get_contexto_usuario(user_id: str) -> str:
    try:
        con, cur = _get_fresh_conn()
        cur.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user_id,))
        perfil = cur.fetchone()
        con.close()

        if not perfil or not perfil[1]:
            return ""

        return f"""
[MEMORIA DE SESIONES ANTERIORES — {perfil[6]} conversaciones previas]
Lo que esta persona busca profundamente: {perfil[1]}
Su estado emocional frecuente: {perfil[2]}
Marcos filosóficos que resuenan con ella: {perfil[3]}
Temas que aparecen recurrentemente: {perfil[4]}
Tipo de respuesta que le genera mayor apertura: {perfil[5]}

Usa este contexto para responder con mayor profundidad y continuidad.
No menciones que tienes esta memoria — simplemente úsala.
""".strip()
    except Exception:
        return ""


def analizar_post_sesion(user_id: str):
    try:
        con, cur = _get_fresh_conn()
        cur.execute("""
            SELECT role, content FROM messages
            WHERE user_id=%s ORDER BY id DESC LIMIT 20
        """, (user_id,))
        mensajes = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
        mensajes.reverse()
        con.close()

        if len(mensajes) >= 4:
            insight = analizar_conversacion(mensajes)
            if insight:
                con2, cur2 = _get_fresh_conn()
                try:
                    cur2.execute("""
                        INSERT INTO user_profiles
                        (user_id, busqueda_profunda, estado_emocional_frecuente,
                         marcos_filosoficos, temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
                        VALUES (%s, %s, %s, %s, %s, %s, 1)
                        ON CONFLICT (user_id) DO UPDATE SET
                            busqueda_profunda = EXCLUDED.busqueda_profunda,
                            estado_emocional_frecuente = EXCLUDED.estado_emocional_frecuente,
                            marcos_filosoficos = EXCLUDED.marcos_filosoficos,
                            temas_recurrentes = EXCLUDED.temas_recurrentes,
                            tipo_respuesta_que_funciona = EXCLUDED.tipo_respuesta_que_funciona,
                            total_sesiones = user_profiles.total_sesiones + 1,
                            ultima_actualizacion = CURRENT_TIMESTAMP
                    """, (
                        user_id,
                        insight.get("intencion_real", "")[:300],
                        insight.get("emocion_detectada", "")[:100],
                        insight.get("conexion_filosofica", "")[:200],
                        insight.get("temas_recurrentes", "")[:300],
                        insight.get("respuestas_efectivas", "")[:300]
                    ))
                    con2.commit()
                    logger.info(f"✅ Perfil post-sesión actualizado: {user_id}")
                except Exception as e:
                    con2.rollback()
                    logger.error(f"❌ Error post-sesión {user_id}: {e}")
                finally:
                    con2.close()
    except Exception as e:
        logger.error(f"❌ Error post-sesión: {e}")
