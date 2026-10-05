import time
import threading
import unittest
import numpy as np
from aiohttp import web

from relay_server import RelayServer
from app.core.signaling_client import SentinelSignalingClient

TEST_PORT = 8799

class TestRelaySystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Iniciar RelayServer en puerto de prueba
        cls.server = RelayServer(port=TEST_PORT)
        cls.app = web.Application()
        cls.app.router.add_get('/ws/signaling', cls.server.handle_ws)

        cls.runner = web.AppRunner(cls.app)
        cls.loop = None

        def run_srv():
            import asyncio
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)
            cls.loop.run_until_complete(cls.runner.setup())
            site = web.TCPSite(cls.runner, '127.0.0.1', TEST_PORT)
            cls.loop.run_until_complete(site.start())
            cls.loop.run_forever()

        cls.thread = threading.Thread(target=run_srv, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    def test_cross_network_pair_and_stream(self):
        relay_url = f"http://127.0.0.1:{TEST_PORT}"

        cam_client = SentinelSignalingClient(relay_url=relay_url)
        viewer_client = SentinelSignalingClient(relay_url=relay_url)

        received_code = []
        code_ready_event = threading.Event()

        def on_code(code):
            received_code.append(code)
            code_ready_event.set()

        # 1. Cámara se registra
        cam_client.start_as_camera(device_name="Teléfono Cámara 1", on_code_ready=on_code)
        self.assertTrue(code_ready_event.wait(timeout=3.0), "La cámara no obtuvo código de emparejamiento")
        pair_code = received_code[0]
        self.assertTrue(len(pair_code) >= 6)
        print(f"\n[Test] Código asignado a la cámara: {pair_code}")

        # 2. Visor se conecta usando ese código
        viewer_frames = []
        frame_event = threading.Event()

        def on_viewer_frame(frame):
            viewer_frames.append(frame)
            frame_event.set()

        viewer_client.on_frame_received = on_viewer_frame
        viewer_client.start_as_viewer(pair_code=pair_code)

        time.sleep(1.0)
        self.assertTrue(cam_client.is_connected)
        self.assertTrue(viewer_client.is_connected)

        # 3. Cámara envía un fotograma simulado
        test_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        test_frame[:, :] = (0, 255, 100) # color verde
        cam_client.send_frame(test_frame)

        self.assertTrue(frame_event.wait(timeout=3.0), "El visor no recibió el fotograma a través del relay")
        self.assertGreater(len(viewer_frames), 0)
        h, w = viewer_frames[0].shape[:2]
        self.assertEqual((h, w), (240, 320))
        print("[Test] Fotograma transmitido y recibido con éxito a través del túnel!")

        # 4. Visor envía comando remoto (Linterna)
        cam_commands = []
        cmd_event = threading.Event()

        def on_cam_cmd(cmd):
            cam_commands.append(cmd)
            cmd_event.set()

        cam_client.on_command_received = on_cam_cmd
        viewer_client.send_command({"cmd": "toggle_torch"})

        self.assertTrue(cmd_event.wait(timeout=3.0), "La cámara no recibió el comando remoto del visor")
        self.assertEqual(cam_commands[0].get("cmd"), "toggle_torch")
        print("[Test] Comando remoto 'toggle_torch' recibido con éxito!")

        cam_client.stop()
        viewer_client.stop()

if __name__ == "__main__":
    unittest.main()
