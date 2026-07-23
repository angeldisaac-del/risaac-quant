import datetime
import time
import pandas as pd
import requests
import yfinance as yf
import requests

import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")


WEBHOOK_URL = "https://risaac-quant.onrender.com/webhook"
PING_URL = "https://risaac-quant.onrender.com/"


def wake_up_render():
    """Despierta el servidor de Render si esta dormido."""
    print("⏰ Despertando servidor en Render...")
    try:
        requests.get(PING_URL, timeout=10)
        time.sleep(5)
    except Exception as e:
        print(f"Servidor despertando: {e}")


def fetch_gold_candles():
    """Descarga velas de 15m para el ORO (XAUUSD) desde Yahoo Finance."""
    gold = yf.Ticker("GC=F")  # Futuros continuos del Oro / XAUUSD
    df = gold.history(period="5d", interval="15m")
    df = df.reset_index()
    # Estandarizar nombres de columnas
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return df


def check_ny_session():
    now_ny = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=-4))
    )
    return 8 <= now_ny.hour < 12


def analyze_and_send():
    wake_up_render()
    try:
        df = fetch_gold_candles()
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        df["tr"] = df["high"] - df["low"]
        atr = df["tr"].rolling(14).mean().iloc[-1]

        ob_top = float(prev["high"])
        ob_bot = float(prev["low"])

        in_ny = check_ny_session()
        is_bull = latest["close"] > latest["open"]
        signal_type = "BUY" if is_bull else "SELL"

        entry = ob_top if is_bull else ob_bot
        sl = ob_bot - (atr * 0.2) if is_bull else ob_top + (atr * 0.2)
        risk = abs(entry - sl)
        rr = 2.5 if in_ny else 2.1
        tp = entry + (risk * rr) if is_bull else entry - (risk * rr)

        payload = {
            "symbol": "XAUUSD",
            "type": signal_type,
            "entry": str(round(entry, 2)),
            "sl": str(round(sl, 2)),
            "tp": str(round(tp, 2)),
            "setup_type": "GOLDEN_NY" if in_ny else "STANDARD",
        }

        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"✅ Estado del envio: {response.status_code}")
        print(f"📦 Payload enviado (ORO): {payload}")

    except Exception as e:
        print(f"❌ Error procesando mercado de Oro: {e}")


if __name__ == "__main__":
    analyze_and_send()
# ... (código previo de cálculo de indicadores/velas) ...

# 1. EVALUAR SI HAY ENTRADA
if tipo_senal in ["BUY", "SELL"]:
    print(f"🎯 ¡Señal encontrada!: {tipo_senal}")

    # 2. CONSTRUIR EL MENSAJE PARA TELEGRAM (AQUÍ VA TU BLOQUE)
    mensaje_telegram = (
        f"🚀 *NUEVA SEÑAL DETECTADA*\n"
        f"--------------------------------\n"
        f"📈 *Símbolo:* XAUUSD\n"
        f"🟢 *Tipo:* {tipo_senal}\n"
        f"🎯 *Entrada:* ${precio_entrada}\n"
        f"🛑 *Stop Loss:* ${stop_loss}\n"
        f"💰 *Take Profit:* ${take_profit}\n"
        f"--------------------------------\n"
        f"⏰ *Hora:* {fecha_actual}"
    )

    # 3. ENVIAR A TELEGRAM
    enviar_telegram(mensaje_telegram)

    # 4. (Opcional) Enviar también a Render
    # requests.post(WEBHOOK_URL, json=datos)
else:
    print("⏳ Sin señales operativas en este ciclo.")

