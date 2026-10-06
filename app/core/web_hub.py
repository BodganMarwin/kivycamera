import asyncio
import io
import json
import socket
import threading
import time
from typing import Dict, Any, Optional, Callable
import cv2
import numpy as np
try:
    from aiohttp import web, WSMsgType
    AIOHTTP_AVAILABLE = True
except ImportError:
    web = None
    WSMsgType = None
    AIOHTTP_AVAILABLE = False

from app.core.motion_detector import MotionDetector

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Plantilla HTML5 Mobile Web App para el dispositivo móvil (Sin Apps de terceros)
MOBILE_CAMERA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0">
    <title>Sentinel Mobile Cam</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000;
            color: #fff;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        #video-container {
            position: relative;
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #111;
        }
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        #hud {
            position: absolute;
            top: 15px;
            left: 15px;
            right: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }
        .badge {
            background: rgba(229, 57, 53, 0.85);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .dot { width: 8px; height: 8px; background: #fff; border-radius: 50%; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .controls {
            position: absolute;
            bottom: 20px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            gap: 15px;
            padding: 0 15px;
            z-index: 10;
        }
        .btn {
            background: rgba(30, 30, 30, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            padding: 12px 18px;
            border-radius: 50px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            backdrop-filter: blur(8px);
            cursor: pointer;
        }
        .btn:active { background: rgba(80, 80, 80, 0.9); }
        #powersave-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: #000;
            z-index: 999;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: #444;
            font-size: 14px;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div id="video-container">
        <div id="hud">
            <div class="badge"><div class="dot"></div> EN VIVO</div>
            <div id="fps" style="background: rgba(0,0,0,0.6); padding: 4px 8px; border-radius: 6px; font-size: 12px;">0 FPS</div>
        </div>
        <video id="webcam" autoplay playsinline muted></video>
        <canvas id="captureCanvas" style="display:none;"></canvas>

        <div class="controls">
            <button class="btn" id="btnSwitch">🔄 Lente</button>
            <button class="btn" id="btnTorch">🔦 Linterna</button>
            <button class="btn" id="btnSaver">🌙 Pantalla Negra</button>
        </div>
    </div>

    <div id="powersave-overlay">
        <p style="font-size: 24px; color: #666; margin-bottom: 10px;">🔒 MODO AHORRO ACTIVO</p>
        <p>Vigilancia en segundo plano.<br>Toca dos veces la pantalla para desbloquear.</p>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('captureCanvas');
        const ctx = canvas.getContext('2d');
        const fpsLabel = document.getElementById('fps');
        const btnSwitch = document.getElementById('btnSwitch');
        const btnTorch = document.getElementById('btnTorch');
        const btnSaver = document.getElementById('btnSaver');
        const overlay = document.getElementById('powersave-overlay');

        let currentStream = null;
        let currentFacingMode = 'environment'; // trasera por defecto
        let torchActive = false;
        let ws = null;
        let frameCount = 0;
        let lastFpsCheck = performance.now();
        let wakeLock = null;

        // Mantener pantalla encendida
        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            } catch (err) {
                console.warn('Wake Lock no disponible:', err);
            }
        }

        async function initCamera() {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }

            try {
                const constraints = {
                    video: {
                        facingMode: { ideal: currentFacingMode },
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    },
                    audio: false
                };
                currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = currentStream;
                await video.play();
                requestWakeLock();
            } catch (e) {
                alert('Error accediendo a la cámara: ' + e.message + '\\nAsegúrate de otorgar permisos de cámara.');
            }
        }

        // Conectar WebSocket con el servidor Sentinel en el PC
        function connectWebSocket() {
            const loc = window.location;
            const wsUri = (loc.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + loc.host + '/ws/camera';
            ws = new WebSocket(wsUri);

            ws.onopen = () => {
                console.log('Conectado a Sentinel Server');
                startStreaming();
            };

            ws.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleRemoteCommand(data);
                } catch(e) {}
            };

            ws.onclose = () => {
                if (!window.isDisconnectedByServer) {
                    setTimeout(connectWebSocket, 2000);
                }
            };
        }

        // Ejecutar comandos remotos enviados desde el Monitor Central
        async function handleRemoteCommand(data) {
            if (data.cmd === 'disconnect') {
                window.isDisconnectedByServer = true;
                if (currentStream) {
                    currentStream.getTracks().forEach(track => track.stop());
                }
                if (ws) {
                    ws.close();
                }
                document.body.innerHTML = `
                    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:25px;text-align:center;background:#121212;">
                        <div style="font-size:48px;margin-bottom:15px;">🔌</div>
                        <h2 style="color:#e53935;margin-bottom:12px;font-size:22px;">Dispositivo Desvinculado</h2>
                        <p style="color:#aaa;margin-bottom:25px;font-size:15px;line-height:1.5;">Esta cámara ha sido desvinculada desde el monitor central.<br>La captura de video y linterna se han apagado.</p>
                        <button onclick="location.reload()" style="background:#1e88e5;color:#fff;border:none;padding:12px 28px;border-radius:25px;font-size:15px;font-weight:bold;cursor:pointer;">Volver a Conectar</button>
                    </div>
                `;
            } else if (data.cmd === 'toggle_torch') {
                toggleTorch();
            } else if (data.cmd === 'switch_cam') {
                currentFacingMode = (currentFacingMode === 'environment' ? 'user' : 'environment');
                await initCamera();
            } else if (data.cmd === 'siren') {
                playSirenAlarm(data.duration || 5);
            }
        }

        // Sirena disuasoria generada en el móvil
        function playSirenAlarm(durationSec = 5) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctxAudio = new AudioCtx();
            const osc = ctxAudio.createOscillator();
            const gain = ctxAudio.createGain();
            osc.type = 'sawtooth';
            osc.connect(gain);
            gain.connect(ctxAudio.destination);
            gain.gain.value = 0.8;
            osc.start();

            const start = ctxAudio.currentTime;
            for (let i = 0; i < durationSec * 2; i++) {
                osc.frequency.setValueAtTime(650, start + i * 0.5);
                osc.frequency.linearRampToValueAtTime(1400, start + (i + 1) * 0.5);
            }
            setTimeout(() => {
                osc.stop();
                ctxAudio.close();
            }, durationSec * 1000);
        }

        async function toggleTorch() {
            if (!currentStream) return;
            const track = currentStream.getVideoTracks()[0];
            const caps = track.getCapabilities ? track.getCapabilities() : {};
            if (caps.torch) {
                torchActive = !torchActive;
                await track.applyConstraints({ advanced: [{ torch: torchActive }] });
            } else {
                console.warn('La linterna no está disponible en este lente.');
            }
        }

        function startStreaming() {
            const sendFrame = () => {
                if (video.videoWidth > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    canvas.width = 640;
                    canvas.height = 480;
                    ctx.drawImage(video, 0, 0, 640, 480);
                    
                    canvas.toBlob((blob) => {
                        if (blob && ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(blob);
                            frameCount++;
                            const now = performance.now();
                            if (now - lastFpsCheck >= 1000) {
                                fpsLabel.innerText = frameCount + ' FPS';
                                frameCount = 0;
                                lastFpsCheck = now;
                            }
                        }
                    }, 'image/jpeg', 0.65);
                }
                setTimeout(sendFrame, 40); // ~25 FPS
            };
            sendFrame();
        }

        btnSwitch.onclick = async () => {
            currentFacingMode = (currentFacingMode === 'environment' ? 'user' : 'environment');
            await initCamera();
        };
        btnTorch.onclick = toggleTorch;

        btnSaver.onclick = () => { overlay.style.display = 'flex'; };
        let lastTap = 0;
        overlay.onclick = () => {
            const now = new Date().getTime();
            if (now - lastTap < 400) {
                overlay.style.display = 'none';
            }
            lastTap = now;
        };

        window.onload = async () => {
            await initCamera();
            connectWebSocket();
        };
    </script>
</body>
</html>
"""

class WebCameraDevice:
    """Representa un dispositivo móvil conectado a través del navegador web."""

    def __init__(self, device_id: str, ws: Any = None):
        self.device_id = device_id
        self.name = f"Móvil {device_id[:4]}"
        self.ws = ws
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.motion_active = False
        self.fps = 0.0
        self.connected = True
        self.detector = MotionDetector(min_area=1000)
        self._lock = threading.Lock()
        self._frame_count = 0
        self._start_time = time.time()

        # Grabación local
        self._recording = False
        self._video_writer = None

    def update_raw_image(self, image_bytes: bytes) -> None:
        """Decodifica el JPEG recibido por WebSocket desde el navegador del móvil."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        has_motion, boxes, annotated = self.detector.process_frame(frame)

        with self._lock:
            self.latest_frame = frame
            self.latest_annotated_frame = annotated
            self.motion_active = has_motion

            if self._recording and self._video_writer:
                try:
                    self._video_writer.write(frame)
                except Exception:
                    pass

        self._frame_count += 1
        elapsed = time.time() - self._start_time
        if elapsed >= 1.0:
            self.fps = round(self._frame_count / elapsed, 1)
            self._frame_count = 0
            self._start_time = time.time()

    def get_frame(self, draw_annotations: bool = True) -> Optional[np.ndarray]:
        with self._lock:
            if draw_annotations and self.latest_annotated_frame is not None:
                return self.latest_annotated_frame.copy()
            elif self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def send_remote_command(self, cmd_dict: Dict[str, Any]) -> None:
        """Envía un comando al teléfono (ej: linterna, sirena, cambiar cámara)."""
        if self.ws and not self.ws.closed:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_str(json.dumps(cmd_dict)),
                self.ws._loop
            )

    def start_recording(self, output_dir: str = "recordings") -> None:
        with self._lock:
            if self._recording or self.latest_frame is None:
                return
            h, w = self.latest_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"{output_dir}/rec_{self.name}_{ts}.mp4"
            self._video_writer = cv2.VideoWriter(path, fourcc, 20, (w, h))
            self._recording = True

    def stop_recording(self) -> None:
        with self._lock:
            self._recording = False
            if self._video_writer:
                self._video_writer.release()
                self._video_writer = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def disconnect(self) -> None:
        """Desvincula y apaga la cámara remota del teléfono."""
        self.send_remote_command({"cmd": "disconnect"})
        self.stop_recording()
        self.connected = False
        if self.ws and not self.ws.closed:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.ws._loop)


class SentinelWebHub:
    """
    Servidor Web y WebSocket centralizado para:
    1. Servir la aplicación web a los móviles (sin instalar apps).
    2. Recibir los fotogramas de video en tiempo real.
    3. Enviar comandos remotos (Linterna, Sirena, Cambio de Cámara).
    """

    def __init__(self, port: int = 8080, on_device_connected: Optional[Callable[[WebCameraDevice], None]] = None):
        self.port = port
        self.on_device_connected = on_device_connected
        self.devices: Dict[str, WebCameraDevice] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._runner: Optional[Any] = None
        self.is_running = False

    def start(self) -> str:
        if not AIOHTTP_AVAILABLE:
            print("[SentinelWebHub] aiohttp no está disponible en este entorno.")
            return ""

        if self.is_running:
            return f"http://{get_local_ip()}:{self.port}/camera"

        self.is_running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

        local_ip = get_local_ip()
        return f"http://{local_ip}:{self.port}/camera"

    def _run_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        app = web.Application()
        app.router.add_get('/camera', self._handle_camera_page)
        app.router.add_get('/ws/camera', self._handle_camera_ws)
        app.router.add_get('/api/siren/{device_id}', self._handle_api_siren)
        app.router.add_get('/api/torch/{device_id}', self._handle_api_torch)

        self._runner = web.AppRunner(app)
        self._loop.run_until_complete(self._runner.setup())
        site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        self._loop.run_until_complete(site.start())
        print(f"[SentinelWebHub] Servidor activo en http://0.0.0.0:{self.port}")
        self._loop.run_forever()

    async def _handle_camera_page(self, request):
        return web.Response(text=MOBILE_CAMERA_HTML, content_type='text/html')

    async def _handle_camera_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        import uuid
        device_id = str(uuid.uuid4())[:8]
        device = WebCameraDevice(device_id=device_id, ws=ws)
        self.devices[device_id] = device
        print(f"[SentinelWebHub] Nuevo dispositivo móvil conectado: {device.name} ({device_id})")

        if self.on_device_connected:
            self.on_device_connected(device)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    device.update_raw_image(msg.data)
                elif msg.type == WSMsgType.TEXT:
                    pass
                elif msg.type == WSMsgType.ERROR:
                    break
        finally:
            device.connected = False
            if device_id in self.devices:
                del self.devices[device_id]
            print(f"[SentinelWebHub] Dispositivo móvil desconectado: {device_id}")

        return ws

    async def _handle_api_siren(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "siren", "duration": 5})
            return web.json_response({"status": "ok", "message": "Sirena activada"})
        return web.json_response({"status": "error", "message": "Dispositivo no encontrado"}, status=404)

    async def _handle_api_torch(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "toggle_torch"})
            return web.json_response({"status": "ok", "message": "Linterna conmutada"})
        return web.json_response({"status": "error", "message": "Dispositivo no encontrado"}, status=404)

    def trigger_siren(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "siren", "duration": 5})

    def toggle_torch(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "toggle_torch"})

    def switch_camera(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "switch_cam"})

    def disconnect_device(self, device_id: str):
        """Desvincula un dispositivo móvil por su ID."""
        dev = self.devices.get(device_id)
        if dev:
            dev.disconnect()
            if device_id in self.devices:
                del self.devices[device_id]

    def stop(self):
        self.is_running = False
        if self._runner and self._loop:
            asyncio.run_coroutine_threadsafe(self._runner.cleanup(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)
