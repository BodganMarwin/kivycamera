import unittest
import numpy as np
from app.config import ConfigManager
from app.core.motion_detector import MotionDetector
from app.core.stream_server import get_local_ip, StreamServer

class TestSentinelCore(unittest.TestCase):

    def test_config_manager(self):
        mgr = ConfigManager()
        cams = mgr.get_cameras()
        self.assertIsInstance(cams, list)
        server_cfg = mgr.get_server_config()
        self.assertIn("port", server_cfg)

    def test_local_ip(self):
        ip = get_local_ip()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip.split('.')) == 4)

    def test_motion_detector(self):
        detector = MotionDetector(min_area=500)
        # Crear frame negro sintético
        frame1 = np.zeros((240, 320, 3), dtype=np.uint8)
        motion, boxes, annotated = detector.process_frame(frame1)
        self.assertFalse(motion)
        self.assertEqual(len(boxes), 0)

        # Crear frame con cambio notable (objeto blanco)
        frame2 = np.zeros((240, 320, 3), dtype=np.uint8)
        frame2[50:150, 50:150] = 255
        motion, boxes, annotated = detector.process_frame(frame2)
        # La diferencia debe gatillar la detección de movimiento
        self.assertTrue(motion)
        self.assertGreater(len(boxes), 0)

    def test_stream_server_lifecycle(self):
        server = StreamServer(port=8999)
        url = server.start()
        self.assertTrue(server.is_running)
        self.assertIn("8999", url)
        server.stop()
        self.assertFalse(server.is_running)

if __name__ == "__main__":
    unittest.main()
