import asyncio
import json
import random
import socket
from typing import Dict, List, Any
from aiohttp import web, WSMsgType

PORT = 8765

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

class CameraSession:
    def __init__(self, pair_code: str, name: str, camera_ws: web.WebSocketResponse):
        self.pair_code = pair_code
        self.name = name
        self.camera_ws = camera_ws
        self.viewers: List[web.WebSocketResponse] = []

class RelayServer:
    """
    Servidor de Relevo y Señalización tipo AlfredCamera.
    Permite emparejar cámaras y reproductores sin importar en qué red se encuentren.
    """

    def __init__(self, port: int = PORT):
        self.port = port
        self.sessions: Dict[str, CameraSession] = {}  # pair_code -> CameraSession
        self.ws_to_code: Dict[web.WebSocketResponse, str] = {}
        self.ws_roles: Dict[web.WebSocketResponse, str] = {}  # ws -> "camera" / "viewer"

    def _generate_pair_code(self) -> str:
        while True:
            code = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
            if code not in self.sessions:
                return code

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        current_code = None
        role = None

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    if msg_type == "register_camera":
                        role = "camera"
                        name = data.get("name", "Cámara Móvil")
                        current_code = self._generate_pair_code()
                        session = CameraSession(pair_code=current_code, name=name, camera_ws=ws)
                        self.sessions[current_code] = session
                        self.ws_to_code[ws] = current_code
                        self.ws_roles[ws] = "camera"

                        print(f"[Relay] [CAMARA] Registrada '{name}' con Codigo: {current_code}")
                        await ws.send_str(json.dumps({
                            "type": "registered",
                            "pair_code": current_code
                        }))

                    elif msg_type == "join_camera":
                        role = "viewer"
                        code = data.get("pair_code", "").strip()
                        session = self.sessions.get(code)
                        if session and not session.camera_ws.closed:
                            current_code = code
                            session.viewers.append(ws)
                            self.ws_to_code[ws] = code
                            self.ws_roles[ws] = "viewer"

                            print(f"[Relay] [VISOR] Conectado a la camara {code}")
                            await ws.send_str(json.dumps({
                                "type": "joined_success",
                                "name": session.name
                            }))
                            # Notificar a la cámara
                            await session.camera_ws.send_str(json.dumps({
                                "type": "viewer_connected"
                            }))
                        else:
                            await ws.send_str(json.dumps({
                                "type": "join_error",
                                "message": f"Código {code} no encontrado o cámara desconectada"
                            }))

                    elif msg_type == "command":
                        # Reenviar comando del visor a la cámara
                        if role == "viewer" and current_code in self.sessions:
                            session = self.sessions[current_code]
                            if not session.camera_ws.closed:
                                await session.camera_ws.send_str(json.dumps(data))

                elif msg.type == WSMsgType.BINARY:
                    # Fotograma binario proveniente de la cámara -> Reenviar a todos sus visores
                    if role == "camera" and current_code in self.sessions:
                        session = self.sessions[current_code]
                        for v_ws in list(session.viewers):
                            if not v_ws.closed:
                                try:
                                    await v_ws.send_bytes(msg.data)
                                except Exception:
                                    session.viewers.remove(v_ws)

        finally:
            # Limpieza al desconectarse
            if ws in self.ws_roles:
                r = self.ws_roles[ws]
                code = self.ws_to_code.get(ws)

                if r == "camera" and code in self.sessions:
                    session = self.sessions[code]
                    print(f"[Relay] [AVISO] Camara {code} desconectada.")
                    for v_ws in session.viewers:
                        if not v_ws.closed:
                            await v_ws.send_str(json.dumps({
                                "type": "join_error",
                                "message": "La cámara remota se ha desconectado."
                            }))
                    del self.sessions[code]

                elif r == "viewer" and code in self.sessions:
                    session = self.sessions[code]
                    if ws in session.viewers:
                        session.viewers.remove(ws)
                    print(f"[Relay] [AVISO] Visor desconectado de {code}")
                    if not session.camera_ws.closed:
                        await session.camera_ws.send_str(json.dumps({
                            "type": "viewer_disconnected"
                        }))

                if ws in self.ws_roles:
                    del self.ws_roles[ws]
                if ws in self.ws_to_code:
                    del self.ws_to_code[ws]

        return ws

    async def handle_status(self, request):
        return web.Response(
            text=f"""<html><body style="font-family:sans-serif;background:#111;color:#eee;padding:30px;">
            <h2>Kivy Sentinel - Servidor de Relevo Activo</h2>
            <p>IP Local: <b>{get_local_ip()}:{self.port}</b></p>
            <p>Cámaras activas enlazadas: <b>{len(self.sessions)}</b></p>
            <ul>
            {"".join([f"<li>Código: <b>{code}</b> ({s.name}) - {len(s.viewers)} visores conectados</li>" for code, s in self.sessions.items()])}
            </ul>
            </body></html>""",
            content_type="text/html"
        )

def main():
    server = RelayServer(port=PORT)
    app = web.Application()
    app.router.add_get('/ws/signaling', server.handle_ws)
    app.router.add_get('/', server.handle_status)

    local_ip = get_local_ip()
    print("=====================================================")
    print("  KIVY SENTINEL - SERVIDOR DE SEÑALIZACIÓN & RELEVO  ")
    print("=====================================================")
    print(f" Servidor iniciado en: http://{local_ip}:{PORT}")
    print(f" Endpoint WebSocket:   ws://{local_ip}:{PORT}/ws/signaling")
    print(" Compatible con conexiones 4G/5G y WiFi cruzadas.")
    print("=====================================================\n")

    web.run_app(app, host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
