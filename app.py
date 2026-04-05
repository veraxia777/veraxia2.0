from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from ai_engine import generate_response
from memory import is_within_limit, get_daily_count, clear_context 
from sheets import registrar_conversacion
from config import FREE_DAILY_LIMIT
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/privacidad", methods=["GET"])
def privacidad():
    return render_template("privacidad.html")
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Falta el campo 'message'"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    user_id = data.get("user_id", f"web_{uuid.uuid4().hex[:8]}")

    # Control freemium
    if not is_within_limit(user_id):
        remaining = 0
        return jsonify({
            "error": "limite",
            "message": f"Alcanzaste tus {FREE_DAILY_LIMIT} mensajes gratuitos de hoy 🌙 Vuelve mañana o activa tu plan Alma para continuar.",
            "user_id": user_id,
            "remaining": 0
        }), 429

    try:
        respuesta = generate_response(user_id, user_message) 
        registrar_conversacion(user_id, user_message, respuesta)
        used = get_daily_count(user_id)
        remaining = max(0, FREE_DAILY_LIMIT - used)
        return jsonify({
            "reply": respuesta,
            "user_id": user_id,
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


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "VeraxIA activa 🤍", "version": "1.0"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
