"""
analisis.py — Motor de análisis y aprendizaje de veraxIA
Analiza todas las conversaciones existentes y construye perfiles de usuario.
Se ejecuta como endpoint /admin/analizar o automáticamente post-sesión.
"""

import json
import logging
import os
from datetime import datetime
from database import get_conn

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _llamar_ia(prompt: str, max_tokens: int = 800) -> str:
    """Llamada interna a OpenAI para análisis."""
    try:
        import urllib.request
        data = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.load(r)
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"❌ Error llamada IA análisis: {e}")
        return ""


def init_tablas_analisis():
    """Crea las tablas necesarias para el sistema de aprendizaje."""
    con, cur = get_conn()
    
    # Perfil acumulativo por usuario
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            busqueda_profunda TEXT,
            estado_emocional_frecuente TEXT,
            marcos_filosoficos TEXT,
            temas_recurrentes TEXT,
            tipo_respuesta_que_funciona TEXT,
            total_sesiones INTEGER DEFAULT 0,
            ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Análisis por conversación
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversation_insights (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            fecha TEXT,
            intencion_real TEXT,
            emocion_detectada TEXT,
            conexion_filosofica TEXT,
            respuestas_que_generaron_continuacion INTEGER DEFAULT 0,
            calidad_estimada REAL DEFAULT 0.5,
            analizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Síntesis global (patrones entre todos los usuarios)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sintesis_global (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            patrones_detectados TEXT,
            insight_principal TEXT,
            recomendacion_system_prompt TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    con.commit()
    logger.info("✅ Tablas de análisis creadas")


def analizar_conversacion(user_id: str, mensajes: list) -> dict:
    """
    Analiza una conversación completa y extrae insights.
    mensajes: lista de dicts {role, content}
    """
    if not mensajes or len(mensajes) < 2:
        return {}
    
    # Construir el texto de la conversación
    texto = "\n".join([
        f"{'Usuario' if m['role'] == 'user' else 'veraxIA'}: {m['content'][:300]}"
        for m in mensajes[:20]  # máximo 20 mensajes
    ])
    
    prompt = f"""Analiza esta conversación con veraxIA (IA filosófica para autoconocimiento).

CONVERSACIÓN:
{texto}

Responde en JSON con estas claves exactas:
{{
  "intencion_real": "qué buscaba realmente esta persona (no lo que preguntó literalmente)",
  "emocion_detectada": "estado emocional dominante",
  "conexion_filosofica": "qué corriente filosófica conecta con su situación",
  "calidad_dialogo": 0.0 a 1.0 (qué tan profunda fue la conversación),
  "respuestas_efectivas": "qué tipo de respuestas generaron más apertura",
  "temas_recurrentes": "temas que aparecieron más de una vez"
}}

Solo el JSON, sin explicación."""

    resultado_raw = _llamar_ia(prompt)
    
    try:
        # Limpiar posibles backticks
        resultado_raw = resultado_raw.replace("```json", "").replace("```", "").strip()
        resultado = json.loads(resultado_raw)
    except Exception:
        resultado = {
            "intencion_real": "no analizable",
            "emocion_detectada": "neutral",
            "conexion_filosofica": "general",
            "calidad_dialogo": 0.5,
            "respuestas_efectivas": "no determinado",
            "temas_recurrentes": "no determinado"
        }
    
    return resultado


def actualizar_perfil_usuario(user_id: str, nuevo_insight: dict):
    """Actualiza el perfil acumulativo del usuario con nuevo insight."""
    con, cur = get_conn()
    
    # Ver si existe perfil previo
    cur.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user_id,))
    perfil_existente = cur.fetchone()
    
    if perfil_existente:
        # Actualizar con nueva información
        prompt = f"""Tienes el perfil actual de un usuario de veraxIA:
Búsqueda profunda: {perfil_existente[1]}
Estado emocional frecuente: {perfil_existente[2]}
Marcos filosóficos: {perfil_existente[3]}
Temas recurrentes: {perfil_existente[4]}

Nueva conversación analizada:
{json.dumps(nuevo_insight, ensure_ascii=False)}

Genera un perfil ACTUALIZADO que integre lo nuevo con lo anterior.
Responde en JSON con las mismas claves: busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos, temas_recurrentes, tipo_respuesta_que_funciona.
Solo el JSON."""
        
        perfil_raw = _llamar_ia(prompt, max_tokens=500)
        try:
            perfil_raw = perfil_raw.replace("```json", "").replace("```", "").strip()
            perfil = json.loads(perfil_raw)
        except Exception:
            perfil = {}
        
        if perfil:
            cur.execute("""
                UPDATE user_profiles SET
                    busqueda_profunda=%s,
                    estado_emocional_frecuente=%s,
                    marcos_filosoficos=%s,
                    temas_recurrentes=%s,
                    tipo_respuesta_que_funciona=%s,
                    total_sesiones=total_sesiones+1,
                    ultima_actualizacion=CURRENT_TIMESTAMP
                WHERE user_id=%s
            """, (
                perfil.get("busqueda_profunda", ""),
                perfil.get("estado_emocional_frecuente", ""),
                perfil.get("marcos_filosoficos", ""),
                perfil.get("temas_recurrentes", ""),
                perfil.get("tipo_respuesta_que_funciona", ""),
                user_id
            ))
    else:
        # Crear nuevo perfil
        cur.execute("""
            INSERT INTO user_profiles 
            (user_id, busqueda_profunda, estado_emocional_frecuente, marcos_filosoficos, 
             temas_recurrentes, tipo_respuesta_que_funciona, total_sesiones)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """, (
            user_id,
            nuevo_insight.get("intencion_real", ""),
            nuevo_insight.get("emocion_detectada", ""),
            nuevo_insight.get("conexion_filosofica", ""),
            nuevo_insight.get("temas_recurrentes", ""),
            nuevo_insight.get("respuestas_efectivas", "")
        ))
    
    con.commit()


def analizar_todo_el_historico():
    """
    Analiza TODAS las conversaciones existentes en la base de datos.
    Se ejecuta una vez para procesar el histórico completo.
    """
    con, cur = get_conn()
    
    # Obtener todos los usuarios con conversaciones
    cur.execute("""
        SELECT DISTINCT user_id FROM messages 
        WHERE role='user' AND content != ''
        ORDER BY user_id
    """)
    usuarios = [row[0] for row in cur.fetchall()]
    
    logger.info(f"📊 Analizando {len(usuarios)} usuarios...")
    procesados = 0
    
    for user_id in usuarios:
        try:
            # Obtener conversaciones del usuario
            cur.execute("""
                SELECT role, content FROM messages 
                WHERE user_id=%s 
                ORDER BY id ASC
                LIMIT 100
            """, (user_id,))
            mensajes = [{"role": row[0], "content": row[1]} for row in cur.fetchall()]
            
            if len(mensajes) < 2:
                continue
            
            # Analizar
            insight = analizar_conversacion(user_id, mensajes)
            if insight:
                # Guardar insight de conversación
                cur.execute("""
                    INSERT INTO conversation_insights 
                    (user_id, fecha, intencion_real, emocion_detectada, 
                     conexion_filosofica, calidad_estimada)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    user_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    insight.get("intencion_real", ""),
                    insight.get("emocion_detectada", ""),
                    insight.get("conexion_filosofica", ""),
                    float(insight.get("calidad_dialogo", 0.5))
                ))
                con.commit()
                
                # Actualizar perfil del usuario
                actualizar_perfil_usuario(user_id, insight)
                procesados += 1
                logger.info(f"✅ Usuario {user_id}: {insight.get('intencion_real', 'N/A')[:50]}")
        
        except Exception as e:
            logger.error(f"❌ Error analizando {user_id}: {e}")
            continue
    
    logger.info(f"✅ Análisis completo: {procesados}/{len(usuarios)} usuarios procesados")
    return {"procesados": procesados, "total": len(usuarios)}


def get_contexto_usuario(user_id: str) -> str:
    """
    Retorna el contexto acumulado del usuario para inyectar en el system prompt.
    El corazón del aprendizaje — esto es lo que hace que veraxIA 'recuerde'.
    """
    con, cur = get_conn()
    
    try:
        cur.execute("SELECT * FROM user_profiles WHERE user_id=%s", (user_id,))
        perfil = cur.fetchone()
        
        if not perfil or perfil[6] < 1:  # total_sesiones
            return ""
        
        contexto = f"""
[PERFIL ACUMULADO DE ESTA PERSONA — {perfil[6]} sesiones anteriores]
Lo que realmente busca: {perfil[1]}
Estado emocional frecuente: {perfil[2]}
Marcos filosóficos que resuenan: {perfil[3]}
Temas que aparecen recurrentemente: {perfil[4]}
Tipo de respuesta que genera apertura en esta persona: {perfil[5]}

Usa este contexto para responder con mayor profundidad y coherencia con su historia.
No menciones que tienes este perfil — simplemente úsalo para responder mejor.
"""
        return contexto.strip()
    
    except Exception:
        return ""


def analizar_post_sesion(user_id: str):
    """
    Se llama automáticamente después de cada sesión para actualizar el perfil.
    Diseñado para ejecutarse en background sin bloquear al usuario.
    """
    try:
        con, cur = get_conn()
        
        # Obtener últimos 20 mensajes de esta sesión
        cur.execute("""
            SELECT role, content FROM messages 
            WHERE user_id=%s 
            ORDER BY id DESC LIMIT 20
        """, (user_id,))
        mensajes = [{"role": row[0], "content": row[1]} for row in cur.fetchall()]
        mensajes.reverse()
        
        if len(mensajes) >= 4:  # Solo analizar si hubo conversación real
            insight = analizar_conversacion(user_id, mensajes)
            if insight:
                actualizar_perfil_usuario(user_id, insight)
                logger.info(f"✅ Perfil actualizado post-sesión: {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Error análisis post-sesión: {e}")
