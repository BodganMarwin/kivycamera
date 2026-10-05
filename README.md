# Kivy Sentinel - Sistema Multiplataforma de Videovigilancia

Sistema de videovigilancia híbrido desarrollado con **Python** y **Kivy**. Permite reutilizar dispositivos móviles (teléfonos inteligentes y tabletas) como cámaras de vigilancia inalámbricas, al tiempo que centraliza la visualización y grabación de cámaras de seguridad tradicionales (RTSP / ONVIF / Webcams).

---

## 🚀 Características Principales

1. **Modo Dual:**
   - **📱 Nodo Transmisor (Cámara):** Convierte el smartphone o tablet en una cámara IP inalámbrica con servidor HTTP-MJPEG embebido, soporte para cambio de cámara (frontal/trasera), detector de movimiento y modo de ahorro de pantalla (Black Screen / OLED Protection).
   - **🖥️ Monitor Central / NVR:** Panel de visualización multivista en tiempo real (1x1, 2x2, 3x3), compatible con cámaras RTSP de marcas tradicionales (Hikvision, Dahua, etc.), cámaras locales USB y nodos móviles Sentinel.

2. **Descubridor Automático ONVIF:**
   - Implementación de **WS-Discovery (UDP Multicast 3702)** en Python puro para escanear y encontrar automáticamente cámaras IP en tu red local sin configurar direcciones IP manualmente.

3. **Arquitectura de Alto Rendimiento:**
   - Hilos dedicados de ingesta de video que **nunca congelan la interfaz gráfica** de Kivy.
   - Decodificación y mapeo directo a texturas **OpenGL ES**.
   - Detección de movimiento liviana con delimitación de áreas sospechosas.
   - Grabación de video en bucle local (`.mp4`).

---

## 🛠️ Instalación y Uso en Escritorio (Windows / Linux / macOS)

### 1. Activar entorno virtual
```powershell
.venv\Scripts\Activate.ps1
```

### 2. Ejecutar la aplicación
```powershell
python main.py
```

---

## 📱 Compilación para Android (Smartphones y Tabletas)

La aplicación incluye un archivo [`buildozer.spec`](buildozer.spec) optimizado para Android (API 34) con todos los permisos requeridos (Cámara, Micrófono, Wakelock y Red).

Para compilar el APK en Linux o WSL:
```bash
# 1. Instalar buildozer
pip install buildozer cython

# 2. Compilar APK en modo debug
buildozer -v android debug
```
El archivo `.apk` resultante se encontrará en la carpeta `bin/`.
