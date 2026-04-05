import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1tNgf-6mPY3Yj0DSzjhlXOdZw6a5SBbuQeK4s_JKwdNk")

def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def registrar_usuario(user_id, email=""):
    try:
        sh = get_sheet()
        hoja = sh.worksheet("usuarios")
        hoja.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id, email, "", 0, "activo", "free"
        ])
    except Exception as e:
        print(f"Error registrar_usuario: {e}")

def registrar_conversacion(user_id, mensaje, respuesta, emocion=""):
    try:
        sh = get_sheet()
        hoja = sh.worksheet("conversaciones")
        hoja.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id, mensaje, respuesta, emocion
        ])
    except Exception as e:
        print(f"Error registrar_conversacion: {e}")

def registrar_pago(user_id, email, plan, metodo, notas=""):
    try:
        sh = get_sheet()
        hoja = sh.worksheet("pagos")
        hoja.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id, email, plan, "activo", metodo, notas
        ])
    except Exception as e:
        print(f"Error registrar_pago: {e}")