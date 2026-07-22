import datetime
import ccxt
import pandas as pd
import requests

WEBHOOK_URL = "https://risaac-quant.onrender.com/webhook"
exchange = ccxt.binance()

def fetch_candles(symbol="BTC/USDT", timeframe="15m", limit=100):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def check_ny_session():
    now_ny = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-4)))
    return 8 <= now_ny.hour < 12

def analyze_and_send():
    try:
        df = fetch_candles("BTC/USDT", "15m", 50)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close_price = float(latest['close'])
        df['tr'] = df['high'] - df['low']
        atr = df['tr'].rolling(14).mean().iloc[-1]
        
        ob_top = float(prev['high'])
        ob_bot = float(prev['low'])
        
        in_ny = check_ny_session()
        has_displacement = abs(latest['close'] - latest['open']) > (df['close'] - df['open']).abs().rolling(20).mean().iloc[-1] * 1.3
        
        is_bull = latest['close'] > latest['open']
        signal_type = "BUY" if is_bull else "SELL"
        
        entry = ob_top if is_bull else ob_bot
        sl = ob_bot - (atr * 0.1) if is_bull else ob_top + (atr * 0.3)
        risk = abs(entry - sl)
        rr = 2.5 if in_ny else 2.1
        tp = entry + (risk * rr) if is_bull else entry - (risk * rr)
        
        payload = {
            "symbol": "BTCUSD",
            "type": signal_type,
            "entry": str(round(entry, 2)),
            "sl": str(round(sl, 2)),
            "tp": str(round(tp, 2)),
            "setup_type": "GOLDEN_NY" if in_ny else "STANDARD"
        }
        
        response = requests.post(WEBHOOK_URL, json=payload)
        print(f"Estado del envio: {response.status_code}")
        print(f"Payload enviado: {payload}")
        
    except Exception as e:
        print(f"Error procesando mercado: {e}")

if __name__ == "__main__":
    analyze_and_send()
