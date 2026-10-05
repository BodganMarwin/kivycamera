import asyncio
import base64
import json
import random
import threading
import time
from typing import Optional, Callable, Dict, Any
import cv2
import numpy as np
import aiohttp

DEFAULT_RELAY_URL = "http://192.168.1.16:8765"

class SentinelSignalingClient:
    """
    Cliente de señalización y túnel para vincular dispositivos entre redes distintas
    usando un código de emparejamiento de 6 dígitos estilo AlfredCamera.
    """

    def __init__(self, relay_url: str = DEFAULT_RELAY_URL):
        self.relay_url = relay_url.rstrip("/")
        self.pair_code: Optional[str] = None
        self.role: Optional[str] = None  # "camera" o "viewer"
        self.is_connected = False
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_frame_received: Optional[Callable[[np.ndarray], None]] = None
        self.on_command_received: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_status_changed: Optional[Callable[[str], None]] = None

    def start_as_camera(self, device_name: str = "Cámara Sentinel", on_code_ready: Optional[Callable[[str], None]] = None) -> None:
        """Inicia el cliente en rol de CÁMARA y genera un código de emparejamiento."""
        self.role = "camera"
        self._start_thread(on_code_ready=on_code_ready, device_name=device_name)

    def start_as_viewer(self, pair_code: str) -> None:
        """Inicia el cliente en rol de REPRODUCTOR y se conecta al código de la cámara."""
        self.role = "viewer"
        self.pair_code = pair_code.strip()
        self._start_thread()

    def _start_thread(self, **kwargs):
        self._thread = threading.Thread(target=self._run_event_loop, kwargs=kwargs, daemon=True)
        self._thread.start()

    def _run_event_loop(self, on_code_ready=None, device_name="Cámara"):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_listen(on_code_ready, device_name))

    async def _connect_and_listen(self, on_code_ready, device_name):
        ws_url = self.relay_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/signaling"
        
        while True:
            try:
                if self.on_status_changed:
                    self.on_status_changed("Conectando con servidor de relevo...")

                self._session = aiohttp.ClientSession()
                async with self._session.ws_connect(ws_url) as ws:
                    self._ws = ws
                    self.is_connected = True

                    if self.role == "camera":
                        # Registrarse como cámara
                        await ws.send_str(json.dumps({
                            "type": "register_camera",
                            "name": device_name
                        }))
                    elif self.role == "viewer":
                        # Conectarse a la cámara existente
                        await ws.send_str(json.dumps({
                            "type": "join_camera",
                            "pair_code": self.pair_code
                        }))

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self._handle_message(data, on_code_ready)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            self._handle_binary_frame(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

            except Exception as e:
                if self.on_status_changed:
                    self.on_status_changed(f"Reconectando... ({e})")
                await asyncio.sleep(3.0)
            finally:
                self.is_connected = False
                if self._session:
                    await self._session.close()

    async def _handle_message(self, data: Dict[str, Any], on_code_ready):
        msg_type = data.get("type")

        if msg_type == "registered":
            self.pair_code = data.get("pair_code")
            if on_code_ready and self.pair_code:
                on_code_ready(self.pair_code)
            if self.on_status_changed:
                self.on_status_changed(f"Esperando visor (Código: {self.pair_code})")

        elif msg_type == "viewer_connected":
            if self.on_status_changed:
                self.on_status_changed("🟢 Reproductor Conectado")

        elif msg_type == "viewer_disconnected":
            if self.on_status_changed:
                self.on_status_changed(f"Visor desconectado. Esperando (Código: {self.pair_code})")

        elif msg_type == "joined_success":
            if self.on_status_changed:
                self.on_status_changed("🟢 Conectado con la Cámara Remota")

        elif msg_type == "join_error":
            if self.on_status_changed:
                self.on_status_changed(f"❌ Error: {data.get('message', 'Código inválido')}")

        elif msg_type == "command":
            if self.on_command_received:
                self.on_command_received(data.get("command", {}))

    def _handle_binary_frame(self, frame_bytes: bytes):
        """Decodifica un fotograma JPEG binario recibido de la cámara."""
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is not None and self.on_frame_received:
            self.on_frame_received(frame)

    def send_frame(self, frame_bgr: np.ndarray, quality: int = 65):
        """Envía un fotograma desde la cámara hacia el visor a través del túnel."""
        if not self.is_connected or self._ws is None or self._ws.closed:
            return
        
        # Redimensionar y comprimir a JPEG para optimizar datos móviles
        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, encoded = cv2.imencode('.jpg', frame_bgr, params)
        if success and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._ws.send_bytes(encoded.tobytes()),
                self._loop
            )

    def send_command(self, cmd_dict: Dict[str, Any]):
        """Envía comando desde el visor hacia la cámara remota."""
        if not self.is_connected or self._ws is None or self._ws.closed:
            return
        msg = {
            "type": "command",
            "command": cmd_dict
        }
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._ws.send_str(json.dumps(msg)),
                self._loop
            )

    def stop(self):
        self.is_connected = False
        if self._ws and self._loop:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
