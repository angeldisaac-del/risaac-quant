import datetime
from fastapi import BackgroundTasks, FastAPI
import requests

app = FastAPI()

# Base de datos simulada en memoria
base_de_datos = []


@app.get("/")
def home():
    return {"status": "Online", "bot": "RISAAC Engine v32.0"}


@app.post("/webhook")
def recibir_alerta(datos: dict):
    # Procesa la señal recibida
    registro = {
        "symbol": datos["symbol"],
        "type": datos["type"],
        "entry": datos["entry"],
        "sl": datos["sl"],
        "tp": datos["tp"],
        "setup_type": datos["setup_type"],
        "fecha": str(datetime.datetime.now()),
    }
    base_de_datos.append(registro)
    print(
        f"📩 [NUEVA SEÑAL REGISTRADA]: {registro['symbol']} {registro['type']} en {registro['entry']}"
    )

    return {"status": "OK", "message": "Guardado en Base de Datos", "total": len(base_de_datos)}


@app.get("/historial")
def ver_historial():
    return {"total_senales": len(base_de_datos), "registros": base_de_datos}
