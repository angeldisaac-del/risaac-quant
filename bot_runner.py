import datetime
import os
import time
import pandas as pd
import requests
import yfinance as yf

# CREDENTCIALES DE TELEGRAM (Cargadas desde GitHub Secrets)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEBHOOK_URL = "https://risaac-quant.onrender.com/webhook"
PING_URL = "https://risaac-quant.onrender.com/ping"


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Faltan credenciales de Telegram.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown",
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")


def wake_up_render():
    print("⏰ Despertando servidor en Render...")
    try:
        requests.get(PING_URL, timeout=10)
        time.sleep(5)
    except Exception as e:
        print(f"Servidor despertando: {e}")


def analyze_and_send():
    wake_up_render()

    # Descarga datos de Oro (GC=F)
    ticker = yf.Ticker("GC=F")
    df = ticker.history(period="5d", interval="15m")

    if df.empty:
        print("❌ No se pudieron obtener datos del mercado.")
        return

    # Lógica simplificada de prueba de señal
    # (Tu bot evaluará las condiciones reales aquí)
    latest = df.iloc[-1]
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Ejemplo de datos procesados
    symbol = "XAUUSD"
    signal_type = "BUY"  # Cambiará a BUY/SELL según tu estrategia
    entry = round(latest["Close"], 2)
    sl = round(entry - 5.0, 2)
    tp = round(entry + 10.0, 2)
    setup_type = "GOLDEN_NY"

    # 1. Crear Payload para Render
    payload = {
        "symbol": symbol,
        "signal_type": signal_type,
        "entry": str(entry),
        "sl": str(sl),
        "tp": str(tp),
        "setup_type": setup_type,
    }

    # 2. Enviar a Render
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"✅ Estado del envio a Render: {response.status_code}")
    except Exception as e:
        print(f"❌ Error procesando en Render: {e}")

    # 3. CONSTRUIR Y ENVIAR ALERTA A TELEGRAM
    mensaje_telegram = (
        f"🚀 *NUEVA SEÑAL DETECTADA*\n"
        f"--------------------------------\n"
        f"📈 *Símbolo:* {symbol}\n"
        f"🟢 *Tipo:* {signal_type}\n"
        f"🎯 *Entrada:* ${entry}\n"
        f"🛑 *Stop Loss:* ${sl}\n"
        f"💰 *Take Profit:* ${tp}\n"
        f"⚡ *Setup:* {setup_type}\n"
        f"--------------------------------\n"
        f"⏰ *Hora:* {fecha_actual}"
    )

    enviar_telegram(mensaje_telegram)


if __name__ == "__main__":
    analyze_and_send()
