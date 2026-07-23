import datetime
import os
import time
import pytz
import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# CONFIGURACIÓN Y CREDENCIALES
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEBHOOK_URL = "https://risaac-quant.onrender.com/webhook"
PING_URL = "https://risaac-quant.onrender.com/ping"


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Faltan credenciales de Telegram.")
        return

    token_limpio = TELEGRAM_TOKEN.strip().replace('"', '').replace("'", "")
    if token_limpio.lower().startswith("bot"):
        token_limpio = token_limpio[3:]

    chat_id_limpio = TELEGRAM_CHAT_ID.strip().replace('"', '').replace("'", "")

    try:
        url = f"https://api.telegram.org/bot{token_limpio}/sendMessage"
        payload = {"chat_id": chat_id_limpio, "text": mensaje}
        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            print("📲 ¡Mensaje enviado a Telegram con éxito!")
        else:
            print(f"❌ Telegram rechazó el mensaje: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")


def wake_up_render():
    print("⏰ Despertando servidor en Render...")
    try:
        requests.get(PING_URL, timeout=10)
        time.sleep(2)
    except Exception as e:
        print(f"Servidor Render: {e}")


# ---------------------------------------------------------------------------
# MOTOR QUANT (LÓGICA RISAAC ENGINE V32.0)
# ---------------------------------------------------------------------------
def evaluar_estrategia_risaac():
    # 1. Obtención de Datos (Oro 15m y 4h, y DXY)
    gold_15m = yf.download("GC=F", period="5d", interval="15m", progress=False)
    gold_4h = yf.download("GC=F", period="15d", interval="1h", progress=False) # Aproximación H4
    dxy_data = yf.download("DX-Y.NYB", period="5d", interval="15m", progress=False)

    if gold_15m.empty or dxy_data.empty:
        print("❌ Error: No se obtuvieron datos de Yahoo Finance.")
        return None

    # Normalizar columnas
    if isinstance(gold_15m.columns, pd.MultiIndex):
        gold_15m.columns = gold_15m.columns.get_level_values(0)
    if isinstance(gold_4h.columns, pd.MultiIndex):
        gold_4h.columns = gold_4h.columns.get_level_values(0)
    if isinstance(dxy_data.columns, pd.MultiIndex):
        dxy_data.columns = dxy_data.columns.get_level_values(0)

    # 2. Verificar Sesión NY (08:00 a 12:00 EST)
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.datetime.now(ny_tz)
    in_ny_session = 8 <= now_ny.hour < 12

    # 3. Tendencia HTF (H4)
    gold_4h['SMA_20'] = gold_4h['Close'].rolling(20).mean()
    h4_bullish = gold_4h['Close'].iloc[-1] > gold_4h['SMA_20'].iloc[-1]

    # 4. Tendencia y Correlación DXY
    dxy_close = dxy_data['Close'].iloc[-1]
    dxy_high_10 = dxy_data['High'].tail(10).max()
    dxy_low_10 = dxy_data['Low'].tail(10).min()
    dxy_bullish = dxy_close >= ((dxy_high_10 + dxy_low_10) / 2.0)

    # 5. Detección de Fair Value Gap (FVG) en 15m
    fvg_bull = (gold_15m['Low'].iloc[-1] > gold_15m['High'].iloc[-3]) and (gold_15m['Close'].iloc[-2] > gold_15m['High'].iloc[-3])
    fvg_bear = (gold_15m['High'].iloc[-1] < gold_15m['Low'].iloc[-3]) and (gold_15m['Close'].iloc[-2] < gold_15m['Low'].iloc[-3])

    # 6. Detección de Sweeps (Toma de Liquidez)
    last_high = gold_15m['High'].tail(10).iloc[:-1].max()
    last_low = gold_15m['Low'].tail(10).iloc[:-1].min()

    latest = gold_15m.iloc[-1]
    sweep_sell = (latest['Low'] < last_low) and (latest['Close'] > last_low)
    sweep_buy = (latest['High'] > last_high) and (latest['Close'] < last_high)

    # 7. Evaluación de Gatillo / Matriz RISAAC
    local_bull = h4_bullish  # Mantiene alineación con estructura local

    # Regla: Si la tendencia es Bullish, DXY debe ser Bearish (Correlación Inversa)
    valid_dxy = (local_bull and not dxy_bullish) or (not local_bull and dxy_bullish)

    # Clasificación de Setups
    has_ob_and_fvg = fvg_bull or fvg_bear
    is_setup_71 = in_ny_session and (sweep_sell or sweep_buy) and has_ob_and_fvg and valid_dxy
    is_setup_62 = has_ob_and_fvg and valid_dxy

    if not (is_setup_71 or is_setup_62):
        print("⏳ El mercado actual no cumple con las confluencias cuantitativas. No se envía señal.")
        return None

    # Configuración de Métricas
    if is_setup_71:
        setup_type = "GOLD SNIPE ⚡ (71.3%)"
        rr = 2.5
    else:
        setup_type = "STANDARD 🟢 (62.4%)"
        rr = 2.1

    signal_type = "BUY" if local_bull else "SELL"
    entry = round(float(latest['Close']), 2)
    atr = (gold_15m['High'] - gold_15m['Low']).rolling(14).mean().iloc[-1]

    # Cálculos dinámicos de Stop Loss y Take Profit
    if signal_type == "BUY":
        sl = round(entry - (atr * 1.5), 2)
        risk = entry - sl
        tp = round(entry + (risk * rr), 2)
    else:
        sl = round(entry + (atr * 1.5), 2)
        risk = sl - entry
        tp = round(entry - (risk * rr), 2)

    return {
        "symbol": "XAUUSD",
        "signal_type": signal_type,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "setup_type": setup_type,
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    }


# ---------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------------------------------------------------------
def analyze_and_send():
    wake_up_render()

    signal = evaluar_estrategia_risaac()
    if not signal:
        return

    # 1. Enviar a Webhook de Render
    try:
        requests.post(WEBHOOK_URL, json=signal, timeout=10)
    except Exception as e:
        print(f"❌ Error al enviar a Render: {e}")

    # 2. Formatear y Enviar a Telegram
    mensaje = (
        f"🚀 NUEVA SEÑAL DETECTADA - {signal['setup_type']}\n"
        "--------------------------------\n"
        f"📈 Símbolo: {signal['symbol']}\n"
        f"🟢 Tipo: {signal['signal_type']}\n"
        f"🎯 Entrada: ${signal['entry']}\n"
        f"🛑 Stop Loss: ${signal['sl']}\n"
        f"💰 Take Profit: ${signal['tp']}\n"
        "--------------------------------\n"
        f"⏰ Hora: {signal['fecha']}"
    )

    enviar_telegram(mensaje)


if __name__ == "__main__":
    analyze_and_send()
