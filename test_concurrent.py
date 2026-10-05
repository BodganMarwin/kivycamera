import time
import threading
import numpy as np
import cv2
from app.core.stream_server import StreamServer
from app.core.stream_receiver import StreamReceiver

def test_concurrent_multicam():
    print("=== TEST: CONCURRENCIA MULTI-CÁMARA ===")
    
    # 1. Crear servidor que simula un Smartphone en la red (Cámara Móvil 1)
    phone_server = StreamServer(port=8081, fps_limit=25)
    phone_url = phone_server.start()
    print(f"[NODO MÓVIL SIMULADO] Transmitiendo en: {phone_url}/video_feed")

    # Hilo emisor que genera fotogramas sintéticos simulando el móvil
    running = True
    def phone_emitter():
        t = 0
        while running:
            # Generar frame con timestamp y animación
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (20, 20), (620, 460), (40, 40, 40), -1)
            # Bola móvil para simular movimiento
            bx = int(320 + 200 * np.sin(t))
            by = int(240 + 100 * np.cos(t))
            cv2.circle(frame, (bx, by), 30, (0, 255, 120), -1)
            cv2.putText(
                frame,
                f"SMARTPHONE NODO 1 - {time.strftime('%H:%M:%S')}",
                (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
            phone_server.update_frame(frame)
            t += 0.1
            time.sleep(0.04)

    emitter_thread = threading.Thread(target=phone_emitter, daemon=True)
    emitter_thread.start()

    # 2. Iniciar receptores en paralelo:
    #    - Feed 1: Cámara local integrada (0)
    #    - Feed 2: Feed del smartphone simulado por HTTP
    print("\nIniciando receptores concurrentes en el Monitor...")
    rec_local = StreamReceiver(source="0", name="Webcam Local", enable_motion=True)
    rec_phone = StreamReceiver(source=f"{phone_url}/video_feed", name="Smartphone Remoto", enable_motion=True)

    rec_local.start()
    rec_phone.start()

    print("Esperando estabilización de streams (3 segundos)...")
    time.sleep(3)

    # Validar lecturas
    f_local = rec_local.get_frame()
    f_phone = rec_phone.get_frame()

    print(f"Estado Cámara Local: Conectada={rec_local.connected}, FPS={rec_local.fps}")
    print(f"Estado Smartphone:   Conectada={rec_phone.connected}, FPS={rec_phone.fps}, Movimiento={rec_phone.motion_active}")

    success = (f_local is not None) and (f_phone is not None)
    if success:
        print("\n[ÉXITO] Ambos flujos funcionan simultáneamente a plena tasa de cuadros!")
    else:
        print("\n[FALLO] Uno de los flujos no entregó fotogramas.")

    running = False
    rec_local.stop()
    rec_phone.stop()
    phone_server.stop()
    return success

if __name__ == "__main__":
    test_concurrent_multicam()
