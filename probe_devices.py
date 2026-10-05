import cv2
import socket
from app.core.stream_server import get_local_ip
from app.core.onvif_discovery import discover_onvif_cameras

def run_diagnostics():
    print("==========================================")
    print("   DIAGNÓSTICO DE DISPOSITIVOS Y RED      ")
    print("==========================================")
    
    # 1. IP local
    ip = get_local_ip()
    print(f"\n[1] IP Local detectada: {ip}")

    # 2. Cámaras locales
    print("\n[2] Buscando cámaras locales / integradas (DirectShow)...")
    found_cams = []
    for idx in range(3):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"    -> [ENCONTRADA] Cámara #{idx}: {w}x{h} px")
                found_cams.append(idx)
            cap.release()
        else:
            cap.release()

    if not found_cams:
        print("    -> No se detectaron webcams físicas directas en los índices 0-2.")

    # 3. Cámaras ONVIF en red
    print("\n[3] Enviando sonda WS-Discovery (UDP 3702) a la red local...")
    try:
        onvif_cams = discover_onvif_cameras(timeout=3.0)
        if onvif_cams:
            for c in onvif_cams:
                print(f"    -> [ONVIF ENCONTRADA] {c['name']} @ {c['ip']}")
                print(f"       RTSP sugerido: {c['default_rtsp']}")
                print(f"       Endpoint: {c['xaddrs']}")
        else:
            print("    -> No se encontraron cámaras ONVIF automáticamente en la subred.")
    except Exception as e:
        print(f"    -> Error en escaneo ONVIF: {e}")

    print("\n==========================================")

if __name__ == "__main__":
    run_diagnostics()
