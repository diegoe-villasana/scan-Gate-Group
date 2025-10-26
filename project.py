from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2, json, os, time
from pyzbar.pyzbar import decode

app = FastAPI()
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

drawer_capacity = {"DRW_001": 15, "DRW_002": 12, "DRW_003": 10, "DRW_004": 12, "DRAW_005": 8}
drawer_current = {"DRW_001": 0, "DRW_002": 0, "DRW_003": 0}
drawer_flight = {"DRW_001": "LAK345", "DRW_002": "DL045", "DRW_003": "AF123", "DRW_004": "BA678", "DRAW_005": "EK088", "DRW_005_2": "LAK345", "DRW_001": "BA713"}

ultimo_qr_info = {
    "qr_data": None,
    "message": "Esperando QR...",
    "status": "waiting",
    "drawer": "",
    "current": 0,
    "capacity": 0
}

ultimo_qr_leido = {"data": None, "timestamp": 0}

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

def gen_frames():
    global ultimo_qr_info, ultimo_qr_leido
    while True:
        success, frame = cap.read()
        if not success:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codigos = decode(gray)

        for codigo in codigos:
            datos = codigo.data.decode("utf-8")

            now = time.time()
            if datos == ultimo_qr_leido["data"] and now - ultimo_qr_leido["timestamp"] < 3:
                continue
            ultimo_qr_leido = {"data": datos, "timestamp": now}

            try:
                qr_info = json.loads(datos)
                drawer = qr_info.get("drawer_id", "N/A")
                vuelo = qr_info.get("flight_id", "N/A")
                ultimo_qr_info["qr_data"] = qr_info

                if drawer not in drawer_current:
                    ultimo_qr_info.update({
                        "message": f"El drawer '{drawer}' no existe.",
                        "status": "error",
                        "drawer": drawer,
                        "current": 0,
                        "capacity": 0
                    })
                    print(f"[ERROR] Drawer inexistente: {drawer}")
                    continue 

                if drawer in drawer_flight:
                    if drawer_flight[drawer] != vuelo:
                        ultimo_qr_info.update({
                            "message": f"Vuelo incorrecto: {vuelo} ≠ {drawer_flight[drawer]} asignado a {drawer}.",
                            "status": "error",
                            "drawer": drawer,
                            "current": drawer_current[drawer],
                            "capacity": drawer_capacity[drawer]
                        })
                        print(f"[ERROR] Vuelo incorrecto para {drawer}. Esperado: {drawer_flight[drawer]}, recibido: {vuelo}")
                        continue 
                else:
                    drawer_flight[drawer] = vuelo
                    print(f"[INFO] Drawer {drawer} asignado al vuelo {vuelo}")

                if drawer_current[drawer] >= drawer_capacity[drawer]:
                    ultimo_qr_info.update({
                        "message": f"{drawer} está lleno ({drawer_current[drawer]}/{drawer_capacity[drawer]}).",
                        "status": "full",
                        "drawer": drawer,
                        "current": drawer_current[drawer],
                        "capacity": drawer_capacity[drawer]
                    })
                    print(f"[FULL] {drawer} lleno.")
                    continue 

                drawer_current[drawer] += 1
                ultimo_qr_info.update({
                    "message": f"Producto agregado a {drawer} (Vuelo: {vuelo}). Total: {drawer_current[drawer]}/{drawer_capacity[drawer]}",
                    "status": "ok",
                    "drawer": drawer,
                    "current": drawer_current[drawer],
                    "capacity": drawer_capacity[drawer]
                })
                print(f"[OK] {drawer}: {drawer_current[drawer]}/{drawer_capacity[drawer]} (Vuelo {vuelo})")

            except json.JSONDecodeError:
                ultimo_qr_info.update({
                    "qr_data": None,
                    "message": "El QR no trae un JSON válido.",
                    "status": "error",
                    "drawer": "",
                    "current": 0,
                    "capacity": 0
                })
                print("[ERROR] QR inválido: no es JSON.")

            x, y, w, h = codigo.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

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
            "capacity": 0
        })
        print("[INFO] Escáner reseteado.")
    return JSONResponse(content=ultimo_qr_info)

