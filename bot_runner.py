import datetime
import os
import time
import pandas as pd
import requests
import yfinance as yf

# CREDENCIALES DE TELEGRAM (Leídas desde GitHub Secrets)
TELEGRAM_TOKEN = "8621364550:AAGssZEKKgJUfBWRHNPsbute0-xbGLki4g"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEBHOOK_URL = "https://risaac-quant.onrender.com/webhook"
PING_URL = "https://risaac-quant.onrender.com/ping"


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Faltan credenciales de Telegram en las variables de entorno.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
            # Sin parse_mode para garantizar que ningún carácter especial bloquee el envío
        }
        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            print("📲 ¡Mensaje enviado a Telegram con éxito!")
        else:
            print(f"❌ Telegram rechazó el mensaje: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error de red conectando con Telegram: {e}")


def wake_up_render():
    print("⏰ Despertando servidor en Render...")
    try:
        requests.get(PING_URL, timeout=10)
        time.sleep(5)
    except Exception as e:
        print(f"Servidor despertando: {e}")


def analyze_and_send():
    # 1. Despertar servidor Render
    wake_up_render()

    # 2. Descargar datos del Oro (GC=F)
    ticker = yf.Ticker("GC=F")
    df = ticker.history(period="5d", interval="15m")

    if df.empty:
        print("❌ No se pudieron obtener datos del mercado desde Yahoo Finance.")
        return

    latest = df.iloc[-1]
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # 3. Construir datos de la señal
    symbol = "XAUUSD"
    signal_type = "BUY"  # Ajustarás esta lógica según tus indicadores
    entry = round(float(latest["Close"]), 2)
    sl = round(entry - 5.0, 2)
    tp = round(entry + 10.0, 2)
    setup_type = "GOLDEN_NY"

    # 4. Enviar Webhook a Render
    payload = {
        "symbol": symbol,
        "signal_type": signal_type,
        "entry": str(entry),
        "sl": str(sl),
        "tp": str(tp),
        "setup_type": setup_type,
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"✅ Estado del envio a Render: {response.status_code}")
    except Exception as e:
        print(f"❌ Error procesando en Render: {e}")

    # 5. Formatear y Enviar Alerta a Telegram
    mensaje_telegram = (
        "🚀 NUEVA SEÑAL DETECTADA\n"
        "--------------------------------\n"
        f"📈 Símbolo: {symbol}\n"
        f"🟢 Tipo: {signal_type}\n"
        f"🎯 Entrada: ${entry}\n"
        f"🛑 Stop Loss: ${sl}\n"
        f"💰 Take Profit: ${tp}\n"
        f"⚡ Setup: {setup_type}\n"
        "--------------------------------\n"
        f"⏰ Hora: {fecha_actual}"
    )

    enviar_telegram(mensaje_telegram)


if __name__ == "__main__":
    analyze_and_send()
