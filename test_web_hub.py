import unittest
from pathlib import Path
from app.core.qr_helper import generate_qr_image
from app.core.web_hub import SentinelWebHub

class TestWebHub(unittest.TestCase):

    def test_qr_generator(self):
        url = "http://192.168.1.16:8080/camera"
        img_path = generate_qr_image(url, output_path="test_qr.png")
        self.assertTrue(Path(img_path).exists())
        self.assertGreater(Path(img_path).stat().st_size, 100)

    def test_web_hub_lifecycle(self):
        hub = SentinelWebHub(port=8998)
        url = hub.start()
        self.assertTrue(hub.is_running)
        self.assertIn("8998", url)
        self.assertIn("/camera", url)
        hub.stop()

if __name__ == "__main__":
    unittest.main()
