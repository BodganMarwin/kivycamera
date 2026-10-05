import cv2
import socket
import threading
import time
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import numpy as np

def get_local_ip() -> str:
    """Obtiene la dirección IP local del dispositivo en la red WiFi/LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No necesita ser alcanzable realmente
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class StreamServerHandler(BaseHTTPRequestHandler):
    """Maneja las solicitudes HTTP para servir stream MJPEG y fotos."""

    # Referencia a la instancia de CameraServer
    server_instance = None

    def log_message(self, format, *args):
        # Silenciar logs ruidosos de cada fotograma HTTP
        return

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f"""<!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Kivy Sentinel - Cámara Transmisora</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: #121212;
                        color: #ffffff;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 20px;
                        margin: 0;
                    }}
                    .container {{
                        max-width: 800px;
                        width: 100%;
                        background: #1e1e1e;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                    }}
                    .header {{
                        padding: 16px 20px;
                        background: #272727;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    .stream-box {{
                        width: 100%;
                        background: #000;
                        display: flex;
                        justify-content: center;
                    }}
                    img.video-stream {{
                        width: 100%;
                        height: auto;
                        max-height: 70vh;
                        object-fit: contain;
                    }}
                    .badge {{
                        background: #e53935;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                    .info {{
                        padding: 16px 20px;
                        font-size: 14px;
                        color: #aaaaaa;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Kivy Sentinel Camera</h2>
                        <span class="badge">EN VIVO</span>
                    </div>
                    <div class="stream-box">
                        <img class="video-stream" src="/video_feed" alt="Live Stream">
                    </div>
                    <div class="info">
                        <p>Stream MJPEG activo. Compatible con navegadores web, VLC y paneles Kivy Sentinel.</p>
                        <p>URL del Stream: <code>http://{get_local_ip()}:{self.server_instance.port}/video_feed</code></p>
                    </div>
                </div>
            </body>
            </html>"""
            self.wfile.write(html.encode('utf-8'))

        elif self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()

            while self.server_instance and self.server_instance.is_running:
                frame = self.server_instance.get_latest_jpeg()
                if frame is not None:
                    try:
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    except (BrokenPipeError, ConnectionResetError):
                        break
                time.sleep(1.0 / self.server_instance.fps_limit)

        elif self.path == '/snapshot.jpg':
            frame = self.server_instance.get_latest_jpeg()
            if frame is not None:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_response(503)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

class StreamServer:
    """
    Servidor HTTP embebido para convertir cualquier móvil o tablet en una cámara IP
    accesible desde la red local.
    """

    def __init__(self, port: int = 8080, fps_limit: int = 25, jpeg_quality: int = 75):
        self.port = port
        self.fps_limit = fps_limit
        self.jpeg_quality = jpeg_quality
        self.is_running = False
        
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._latest_jpeg: Optional[bytes] = None
        self._lock = threading.Lock()

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """Comprime el fotograma a JPEG y lo almacena para los clientes web conectados."""
        if frame_bgr is None:
            return
        
        params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        success, encoded = cv2.imencode('.jpg', frame_bgr, params)
        if success:
            with self._lock:
                self._latest_jpeg = encoded.tobytes()

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def start(self) -> str:
        if self.is_running:
            return f"http://{get_local_ip()}:{self.port}"

        StreamServerHandler.server_instance = self
        self._httpd = HTTPServer(('0.0.0.0', self.port), StreamServerHandler)
        self.is_running = True

        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

        local_ip = get_local_ip()
        return f"http://{local_ip}:{self.port}"

    def stop(self) -> None:
        self.is_running = False
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
