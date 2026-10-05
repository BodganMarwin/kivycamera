import time
import requests
import cv2
from app.core.stream_receiver import StreamReceiver
from app.core.stream_server import StreamServer, get_local_ip

def test_full_pipeline():
    print("Iniciando prueba de transmisión en vivo...")
    receiver = StreamReceiver(source="0", name="Camara-Test", enable_motion=True)
    server = StreamServer(port=8080, fps_limit=20)
    
    receiver.start()
    stream_url = server.start()
    print(f"Servidor HTTP activo en: {stream_url}")
    
    # Esperar a que la cámara caliente y entregue frames
    frame_ready = False
    for _ in range(30):
        frame = receiver.get_frame(draw_annotations=True)
        if frame is not None:
            server.update_frame(frame)
            frame_ready = True
            break
        time.sleep(0.1)

    if not frame_ready:
        print("[ERROR] No se pudo capturar frame de la cámara 0.")
        receiver.stop()
        server.stop()
        return False

    print("[OK] Primer frame capturado y enviado al servidor de streaming.")

    # Simular cliente HTTP consumiendo snapshot
    try:
        resp = requests.get("http://127.0.0.1:8080/snapshot.jpg", timeout=3)
        if resp.status_code == 200 and len(resp.content) > 1000:
            print(f"[OK] Endpoint /snapshot.jpg respondiendo correctamente ({len(resp.content)} bytes)")
            with open("test_snapshot.jpg", "wb") as f:
                f.write(resp.content)
            print("     -> Guardado 'test_snapshot.jpg' con éxito.")
        else:
            print(f"[FALLO] Endpoint /snapshot.jpg respondió con código {resp.status_code}")
    except Exception as e:
        print(f"[FALLO] Error solicitando snapshot: {e}")

    # Simular lectura de stream MJPEG
    try:
        resp = requests.get("http://127.0.0.1:8080/video_feed", stream=True, timeout=3)
        if resp.status_code == 200:
            chunk = next(resp.iter_content(chunk_size=1024))
            print(f"[OK] Endpoint /video_feed transmitiendo flujo MJPEG ({len(chunk)} bytes recibidos)")
    except Exception as e:
        print(f"[FALLO] Error leyendo video_feed: {e}")

    receiver.stop()
    server.stop()
    print("Prueba de transmisión completada con éxito.")
    return True

if __name__ == "__main__":
    test_full_pipeline()
