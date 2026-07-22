import sqlite3
import requests
import time
import threading
from datetime import datetime
from fastapi import FastAPI, Request

app = FastAPI()

# ------------------------------------------------------------------------------
# 1. CREACIÓN DE LA BASE DE DATOS DINÁMICA
# ------------------------------------------------------------------------------
def iniciar_db():
    conn = sqlite3.connect("mismetricas.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registro_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            simbolo TEXT,
            tipo TEXT,
            entrada REAL,
            sl REAL,
            tp REAL,
            setup_tipo TEXT,
            estado TEXT DEFAULT 'ABIERTO',
            resultado TEXT DEFAULT 'PENDIENTE'
        )
    """)
    conn.commit()
    conn.close()

iniciar_db()

# ------------------------------------------------------------------------------
# 2. RECEPCIÓN DE LA SEÑAL (WEBHOOK O EMAIL PUENTE)
# ------------------------------------------------------------------------------
@app.post("/webhook")
async def recibir_alerta(request: Request):
    datos = await request.json()
    
    conn = sqlite3.connect("mismetricas.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO registro_setups (fecha, simbolo, tipo, entrada, sl, tp, setup_tipo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datos['symbol'], datos['type'], datos['entry'], 
        datos['sl'], datos['tp'], datos['setup_type']
    ))
    conn.commit()
    conn.close()
    
    print(f"📥 [NUEVA SEÑAL REGISTRADA]: {datos['symbol']} {datos['type']} en {datos['entry']}")
    return {"status": "OK", "message": "Guardado en Base de Datos VIVA"}

# ------------------------------------------------------------------------------
# 3. MOTOR EVALUADOR EN TIEMPO REAL (REVISA SI TOCÓ TP O SL)
# ------------------------------------------------------------------------------
def evaluador_en_vivo():
    """Este motor revisa el precio en vivo y determina si la orden ganó o perdió"""
    while True:
        conn = sqlite3.connect("mismetricas.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, simbolo, tipo, entrada, sl, tp FROM registro_setups WHERE estado = 'ABIERTO'")
        ordenes_abiertas = cursor.fetchall()
        
        for orden in ordenes_abiertas:
            o_id, simbolo, tipo, entrada, sl, tp = orden
            
            # Obtener precio actual (ejemplo con API de Binance/Yahoo Finance/Broker)
            precio_actual = obtener_precio_mercado(simbolo)
            if not precio_actual:
                continue

            # Verificación de Take Profit o Stop Loss
            if tipo == "BUY":
                if precio_actual >= tp:
                    cerrar_orden(o_id, "WIN", conn)
                elif precio_actual <= sl:
                    cerrar_orden(o_id, "LOSS", conn)
            elif tipo == "SELL":
                if precio_actual <= tp:
                    cerrar_orden(o_id, "WIN", conn)
                elif precio_actual >= sl:
                    cerrar_orden(o_id, "LOSS", conn)

        conn.close()
        time.sleep(3) # Chequea cada 3 segundos

def cerrar_orden(o_id, resultado, conn):
    cursor = conn.cursor()
    cursor.execute("UPDATE registro_setups SET estado = 'CERRADO', resultado = ? WHERE id = ?", (resultado, o_id))
    conn.commit()
    print(f"🎯 [ORDEN CERRADA]: ID {o_id} -> Resultado: {resultado}")

def obtener_precio_mercado(simbolo):
    try:
        # Petición rápida de precio (ejemplo crypto / adaptable a Forex con tu broker)
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}").json()
        return float(res['price'])
    except:
        return None

# Arrancar evaluador en hilo secundario
threading.Thread(target=evaluador_en_vivo, daemon=True).start()
