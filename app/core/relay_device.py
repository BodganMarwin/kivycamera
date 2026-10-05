import threading
import time
from typing import Optional, Dict, Any
import cv2
import numpy as np

from app.core.signaling_client import SentinelSignalingClient
from app.core.motion_detector import MotionDetector

class RelayCameraDevice:
    """
    Representa una cámara remota enlazada por código de 6 dígitos
    a través del servidor de relevo (funciona en diferentes redes, WiFi y 4G/5G).
    """

    def __init__(self, pair_code: str, name: str = "Cámara Remota"):
        self.pair_code = pair_code
        self.name = f"{name} [{pair_code}]"
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.motion_active = False
        self.fps = 0.0
        self.connected = False

        self.detector = MotionDetector(min_area=1000)
        self._lock = threading.Lock()
        self._frame_count = 0
        self._start_time = time.time()

        # Grabación local
        self._recording = False
        self._video_writer = None

        # Cliente de señalización
        self.signaling = SentinelSignalingClient()
        self.signaling.on_frame_received = self._on_frame
        self.signaling.on_status_changed = self._on_status

    def start(self):
        self.signaling.start_as_viewer(self.pair_code)

    def _on_frame(self, frame: np.ndarray):
        self.connected = True
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

    def _on_status(self, status: str):
        if "Conectado" in status:
            self.connected = True
        elif "desconectado" in status or "Error" in status:
            self.connected = False

    def get_frame(self, draw_annotations: bool = True) -> Optional[np.ndarray]:
        with self._lock:
            if draw_annotations and self.latest_annotated_frame is not None:
                return self.latest_annotated_frame.copy()
            elif self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def send_remote_command(self, cmd_dict: Dict[str, Any]):
        self.signaling.send_command(cmd_dict)

    def start_recording(self, output_dir: str = "recordings"):
        with self._lock:
            if self._recording or self.latest_frame is None:
                return
            h, w = self.latest_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"{output_dir}/rec_{self.pair_code}_{ts}.mp4"
            self._video_writer = cv2.VideoWriter(path, fourcc, 20, (w, h))
            self._recording = True

    def stop_recording(self):
        with self._lock:
            self._recording = False
            if self._video_writer:
                self._video_writer.release()
                self._video_writer = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def disconnect(self):
        self.stop_recording()
        self.connected = False
        self.signaling.stop()

    def stop(self):
        self.disconnect()
