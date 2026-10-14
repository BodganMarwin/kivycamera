"""
Lanzador del Servidor Web Sentinel (AlfredCamera Web Hub).
Despliega la aplicación completa en el navegador local y red WiFi.
"""

import sys
import time
import webbrowser

# Asegurar codificación utf-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.web_hub import SentinelWebHub, get_local_ip

def main():
    port = 8080
    print("=" * 60)
    print("[*] KIVY SENTINEL - ALFRED CAMERA WEB HUB")
    print("=" * 60)
    print("Iniciando servidor web y centro de streaming...")

    hub = SentinelWebHub(port=port)
    url = hub.start()

    if not url:
        print("[ERROR] No se pudo iniciar el servidor web (aiohttp no disponible).")
        sys.exit(1)

    local_ip = get_local_ip()
    dashboard_url = f"http://localhost:{port}/"
    mobile_url = f"http://{local_ip}:{port}/camera"

    print("\n[OK] Servidor Web Desplegado con Exito!")
    print("-" * 60)
    print(f"[PC]     Monitor Central (Navegador):       {dashboard_url}")
    print(f"[MOVIL]  Transmisor Camara (Red WiFi / LAN): {mobile_url}")
    print("-" * 60)
    print("Abriendo el navegador automaticamente...")

    # Abrir navegador automáticamente
    try:
        webbrowser.open(dashboard_url)
    except Exception as e:
        print(f"Aviso al abrir navegador: {e}")

    print("\nPresiona Ctrl+C en esta terminal para detener el servidor web.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        hub.stop()
        print("Servidor detenido correctamente.")

if __name__ == "__main__":
    main()
