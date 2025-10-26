from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2, json, os, time
from pyzbar.pyzbar import decode

app = FastAPI()

# Cámara
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Drawers (usa claves en mayúsculas)
drawer_capacity = {"DRW_001": 2, "DRW_002": 2, "DRW_003": 10, "DRW_004": 12, "DRAW_005": 8}

# Contadores globales
conteo_vuelos = {} 

# Vuelos disponibles y vuelo seleccionado
vuelos_disponibles = ["LAK345", "DL045", "AF123", "BA678", "EK088", "BA713"]
vuelo_actual = None  # será una cadena en MAYÚSCULAS

# Último estado mostrado al frontend
# --- Determinar valores actuales del drawer
current = 0
capacidad = 0
if vuelo_actual and drawer_id:
    capacidad = drawer_capacity.get(drawer_id, 0)
    current = conteo_vuelos.get(vuelo_actual, {}).get(drawer_id, 0)

# --- Guardar la información más reciente
ultimo_qr_info.update({
    "qr_data": qr_info,
    "message": mensaje,
    "status": estado,
    "drawer": drawer_id or "",
    "current": current,
    "capacity": capacidad,
    "vuelo_actual": vuelo_actual
})

ultimo_qr_leido = {"data": None, "timestamp": 0}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Helper: obtener número de vuelo desde diferentes claves posibles
def obtener_vuelo_desde_qr(qr_info: dict):
    posibles = ["flight_number", "flight", "flight_no", "flightNumber", "flight_id", "vuelo", "vuelo_id"]
    for k in posibles:
        if k in qr_info and qr_info[k] not in (None, ""):
            return str(qr_info[k]).strip().upper()
    return None


def gen_frames():
    global ultimo_qr_info, ultimo_qr_leido, vuelo_actual, conteo_vuelos

    while True:
        success, frame = cap.read()
        if not success:
            continue

        codigos = decode(frame)

        for codigo in codigos:
            datos = codigo.data.decode("utf-8")
            now = time.time()

            # Evitar duplicados recientes
            if datos == ultimo_qr_leido["data"] and now - ultimo_qr_leido["timestamp"] < 2:
                continue
            ultimo_qr_leido = {"data": datos, "timestamp": now}

            mensaje = "Esperando QR..."
            estado = "waiting"
            qr_info = None
            drawer_id = None
            vuelo_qr = None

            try:
                qr_info = json.loads(datos)
            except Exception:
                qr_info = None

            if qr_info is None:
                mensaje = "QR no contiene JSON válido."
                estado = "error"

            else:
                drawer_id = (qr_info.get("drawer_id") or qr_info.get("drawer") or "").strip().upper()
                vuelo_qr = obtener_vuelo_desde_qr(qr_info)

                if drawer_id == "" or drawer_id not in drawer_capacity:
                    mensaje = f"Drawer inválido: {drawer_id or 'N/A'}"
                    estado = "error"

                elif vuelo_actual is None:
                    mensaje = "Selecciona un vuelo primero."
                    estado = "error"

                elif vuelo_qr is None:
                    mensaje = "El QR no contiene número de vuelo válido."
                    estado = "error"

                elif vuelo_qr and vuelo_qr.strip().upper() == vuelo_actual.strip().upper():
                    capacidad = drawer_capacity.get(drawer_id, 0)

                    # Asegurar estructura
                    if vuelo_actual not in conteo_vuelos:
                        conteo_vuelos[vuelo_actual] = {}
                    if drawer_id not in conteo_vuelos[vuelo_actual]:
                        conteo_vuelos[vuelo_actual][drawer_id] = 0

                    # Incrementar si hay espacio
                    if conteo_vuelos[vuelo_actual][drawer_id] < capacidad:
                        conteo_vuelos[vuelo_actual][drawer_id] += 1
                        mensaje = f"Producto agregado a {drawer_id} ({conteo_vuelos[vuelo_actual][drawer_id]}/{capacidad})"
                        estado = "ok"
                    else:
                        mensaje = f"{drawer_id} lleno ({conteo_vuelos[vuelo_actual][drawer_id]}/{capacidad})"
                        estado = "full"

                else:
                    mensaje = f"Vuelo incorrecto: {vuelo_qr or 'N/A'} ≠ {vuelo_actual}"
                    estado = "flight_error"

            # ✅ Obtener los valores actuales del drawer aunque no se haya leído nuevo QR
            current = 0
            capacidad = 0
            if vuelo_actual and drawer_id in drawer_capacity:
                capacidad = drawer_capacity[drawer_id]
                if vuelo_actual in conteo_vuelos and drawer_id in conteo_vuelos[vuelo_actual]:
                    current = conteo_vuelos[vuelo_actual][drawer_id]

            ultimo_qr_info.update({
                "qr_data": qr_info,
                "message": mensaje,
                "status": estado,
                "drawer": drawer_id or "",
                "current": current,
                "capacity": capacidad,
                "vuelo_actual": vuelo_actual
            })

            # Dibujar recuadro
            x, y, w, h = codigo.rect
            color = (0, 255, 0) if estado == "ok" else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)

        ret, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/scanner")
def scanner():
    return FileResponse(os.path.join(os.getcwd(), "scanner.html"))


@app.get("/ultimo_qr")
def obtener_qr(clear: bool = False):
    global ultimo_qr_info
    if clear:
        ultimo_qr_info.update({
            "qr_data": None,
            "message": "Esperando QR...",
            "status": "waiting",
            "drawer": "",
            "current": 0,
            "capacity": 0,
            "vuelo_actual": vuelo_actual
        })
    return JSONResponse(content=ultimo_qr_info)


@app.get("/seleccionar_vuelo")
def seleccionar_vuelo(vuelo: str = Query(...)):
    global vuelo_actual
    vuelo_actual = str(vuelo).strip().upper()
    print(f"✅ Vuelo seleccionado: {vuelo_actual}")
    return JSONResponse(content={
        "status": "ok",
        "vuelo_actual": vuelo_actual,
        "message": f"Vuelo {vuelo_actual} seleccionado"
    })

@app.get("/vuelos_disponibles")
def vuelos():
    return JSONResponse(content={"vuelos": vuelos_disponibles})

@app.get("/conteo")
def obtener_conteo():
    return JSONResponse(content=conteo_vuelos)

