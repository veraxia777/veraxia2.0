from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from ai_engine import generate_response
from memory import is_within_limit, get_daily_count, clear_context
from sheets import registrar_conversacion, registrar_usuario, registrar_pago
from database import cursor, conn
from config import FREE_DAILY_LIMIT
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
import os
import mercadopago

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
CORS(app)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "veraxia777520@gmail.com")

# ─── HELPERS ───────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def crear_token(email):
    token = secrets.token_hex(32)
    expira = datetime.now() + timedelta(days=30)
    cursor.execute("INSERT INTO sesiones (token, email, expira) VALUES (%s, %s, %s)",
                   (token, email, expira.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return token

def verificar_token(token):
    if not token:
        return None
    cursor.execute("SELECT email, expira FROM sesiones WHERE token=%s", (token,))
    row = cursor.fetchone()
    if not row:
        return None
    email, expira = row
    if isinstance(expira, str):
        expira = datetime.strptime(expira, "%Y-%m-%d %H:%M:%S")
    if expira < datetime.now():
        cursor.execute("DELETE FROM sesiones WHERE token=%s", (token,))
        conn.commit()
        return None
    return email

def get_plan_db(email):
    cursor.execute("SELECT plan FROM usuarios WHERE email=%s", (email,))
    row = cursor.fetchone()
    return row[0] if row else "libre"

def get_email_from_request():
    token = request.cookies.get("vx_token") or request.headers.get("X-Token")
    return verificar_token(token)

# ─── RUTAS PÚBLICAS ────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/privacidad", methods=["GET"])
def privacidad():
    return render_template("privacidad.html")

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "VeraxIA activa 🤍", "version": "2.1"})

# ─── REGISTRO Y LOGIN ──────────────────────────────────────

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("registro.html")

    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email y contraseña requeridos"}), 400

    try:
        cursor.execute(
            "INSERT INTO usuarios (email, password_hash) VALUES (%s, %s)",
            (email, hash_password(password))
        )
        conn.commit()
        token = crear_token(email)
        try:
            registrar_usuario(email, email)
        except:
            pass
        resp = jsonify({"ok": True, "plan": "libre", "email": email})
        resp.set_cookie("vx_token", token, max_age=30*24*3600, httponly=True, samesite="Lax")
        return resp
    except Exception as e:
        conn.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return jsonify({"error": "Este email ya está registrado"}), 409
        return jsonify({"error": str(e)}), 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.is_json:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
    else:
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

    cursor.execute(
        "SELECT email, plan FROM usuarios WHERE email=%s AND password_hash=%s",
        (email, hash_password(password))
    )
    row = cursor.fetchone()

    if not row:
        if request.is_json:
            return jsonify({"error": "Email o contraseña incorrectos"}), 401
        return render_template("login.html", error="Email o contraseña incorrectos")

    cursor.execute("UPDATE usuarios SET ultimo_acceso=%s WHERE email=%s",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email))
    conn.commit()
    token = crear_token(email)

    if request.is_json:
        resp = jsonify({"ok": True, "plan": row[1], "email": email})
    else:
        resp = make_response(redirect("/admin"))
    resp.set_cookie("vx_token", token, max_age=30*24*3600, httponly=True, samesite="Lax")
    return resp

@app.route("/logout", methods=["POST"])
def logout():
    token = request.cookies.get("vx_token")
    if token:
        cursor.execute("DELETE FROM sesiones WHERE token=%s", (token,))
        conn.commit()
    resp = jsonify({"ok": True})
    resp.delete_cookie("vx_token")
    return resp

@app.route("/yo", methods=["GET"])
def yo():
    email = get_email_from_request()
    if not email:
        return jsonify({"autenticado": False}), 200
    plan = get_plan_db(email)
    return jsonify({"autenticado": True, "email": email, "plan": plan})

# ─── CHAT ──────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Falta el campo 'message'"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    email = get_email_from_request()
    if email:
        user_id = f"user_{email}"
        plan = get_plan_db(email)
    else:
        user_id = data.get("user_id", f"web_{uuid.uuid4().hex[:8]}")
        plan = "libre"

    if plan == "libre" and not is_within_limit(user_id):
        return jsonify({
            "error": "limite",
            "message": f"Alcanzaste tus {FREE_DAILY_LIMIT} mensajes gratuitos de hoy 🌙 Regístrate gratis o activa tu plan Alma para continuar.",
            "user_id": user_id,
            "remaining": 0
        }), 429

    try:
        respuesta = generate_response(user_id, user_message)
        try:
            registrar_conversacion(user_id, user_message, respuesta)
        except:
            pass
        if email:
            cursor.execute("UPDATE usuarios SET total_mensajes = total_mensajes + 1 WHERE email=%s", (email,))
            conn.commit()
        remaining = 9999 if plan != "libre" else max(0, FREE_DAILY_LIMIT - get_daily_count(user_id))
        return jsonify({
            "reply": respuesta,
            "user_id": user_id,
            "plan": plan,
            "remaining": remaining
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json()
    user_id = data.get("user_id", "")
    if user_id:
        clear_context(user_id)
    return jsonify({"ok": True})

# ─── ADMIN DASHBOARD ───────────────────────────────────────

@app.route("/admin", methods=["GET"])
def admin():
    email = get_email_from_request()
    if email != ADMIN_EMAIL:
        return jsonify({"error": "No autorizado"}), 403
    return render_template("admin.html")

@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    email = get_email_from_request()
    if email != ADMIN_EMAIL:
        return jsonify({"error": "No autorizado"}), 403

    hoy = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE fecha_registro::date = %s", (hoy,))
    nuevos_hoy = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE plan != 'libre'")
    usuarios_pagos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp::date = %s", (hoy,))
    mensajes_hoy = cursor.fetchone()[0]

    cursor.execute("SELECT plan, COUNT(*) FROM usuarios GROUP BY plan")
    planes = dict(cursor.fetchall())

    cursor.execute("""
        SELECT email, plan, total_mensajes, ultimo_acceso, fecha_registro
        FROM usuarios ORDER BY ultimo_acceso DESC LIMIT 20
    """)
    ultimos = [{"email": r[0], "plan": r[1], "mensajes": r[2],
                "ultimo_acceso": str(r[3]), "registro": str(r[4])} for r in cursor.fetchall()]

    cursor.execute("SELECT SUM(monto_usd) FROM pagos WHERE estado='activo'")
    ingresos = cursor.fetchone()[0] or 0

    return jsonify({
        "total_usuarios": total_usuarios,
        "nuevos_hoy": nuevos_hoy,
        "usuarios_pagos": usuarios_pagos,
        "mensajes_hoy": mensajes_hoy,
        "planes": planes,
        "ultimos_usuarios": ultimos,
        "ingresos_total_usd": round(ingresos, 2)
    })

@app.route("/admin/upgrade", methods=["POST"])
def admin_upgrade():
    email_admin = get_email_from_request()
    if email_admin != ADMIN_EMAIL:
        return jsonify({"error": "No autorizado"}), 403

    data = request.get_json()
    email = data.get("email")
    plan = data.get("plan", "alma")
    monto = data.get("monto", 7)
    metodo = data.get("metodo", "manual")

    cursor.execute("UPDATE usuarios SET plan=%s WHERE email=%s", (plan, email))
    vencimiento = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO pagos (email, plan, monto_usd, metodo, estado, vencimiento)
        VALUES (%s, %s, %s, %s, 'activo', %s)
    """, (email, plan, monto, metodo, vencimiento))
    conn.commit()

    try:
        registrar_pago(email, email, plan, metodo)
    except:
        pass

    return jsonify({"ok": True, "email": email, "plan": plan})

MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")

@app.route("/crear_pago", methods=["POST"])
def crear_pago():
    email = get_email_from_request()
    if not email:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json()
    plan = data.get("plan")

    if plan == "alma":
        titulo = "VeraxIA Plan Alma"
        precio = 7
    elif plan == "alma_pro":
        titulo = "VeraxIA Plan Alma Pro"
        precio = 15
    else:
        return jsonify({"error": "Plan inválido"}), 400

    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
    BASE_URL = os.environ.get("BASE_URL", "https://web-production-5f0e2.up.railway.app")

    preference_data = {
        "items": [{"title": titulo, "quantity": 1, "unit_price": precio, "currency_id": "USD"}],
        "payer": {"email": email},
        "back_urls": {
            "success": f"{BASE_URL}/pago_exitoso",
            "failure": f"{BASE_URL}/pago_fallido",
            "pending": f"{BASE_URL}/pago_pendiente"
        },
        "auto_return": "approved",
        "notification_url": f"{BASE_URL}/webhook",
        "metadata": {"email": email, "plan": plan}
    }

    result = sdk.preference().create(preference_data)
    init_point = result["response"]["init_point"]
    return jsonify({"url": init_point})

@app.route("/pago_exitoso")
def pago_exitoso():
    return render_template("pago_exitoso.html")

@app.route("/pago_fallido")
def pago_fallido():
    return render_template("pago_fallido.html")

@app.route("/pago_pendiente")
def pago_pendiente():
    return render_template("pago_pendiente.html")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    if data.get("type") != "payment":
        return jsonify({"ok": True}), 200

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return jsonify({"ok": True}), 200

    try:
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        payment_info = sdk.payment().get(payment_id)
        payment = payment_info["response"]

        if payment.get("status") != "approved":
            return jsonify({"ok": True}), 200

        metadata = payment.get("metadata", {})
        email = metadata.get("email")
        plan = metadata.get("plan")

        if not email or not plan:
            return jsonify({"error": "Metadata incompleta"}), 400

        plan_nombre = "alma" if plan == "alma" else "alma_pro"
        cursor.execute("UPDATE usuarios SET plan=%s WHERE email=%s", (plan_nombre, email))
        conn.commit()

    except Exception as e:
        print(f"Error webhook: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
