import cv2
import time
import threading
from typing import Optional, Tuple, Callable
import numpy as np
from pathlib import Path
from app.core.motion_detector import MotionDetector

class StreamReceiver:
    """
    Gestiona la ingesta de video multihilo desde RTSP, HTTP-MJPEG o webcam local.
    Diseñado para nunca bloquear el hilo de renderizado de Kivy.
    """

    def __init__(
        self,
        source: str,
        name: str = "Cámara",
        enable_motion: bool = True,
        on_motion_callback: Optional[Callable[[str], None]] = None
    ):
        self.source = source
        self.name = name
        self.enable_motion = enable_motion
        self.on_motion_callback = on_motion_callback

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.fps: float = 0.0
        self.motion_active: bool = False
        self.connected: bool = False
        
        # Detector de movimiento interno
        self.detector = MotionDetector()
        
        # Grabador
        self._recording = False
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._recording_path: Optional[Path] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"Stream-{self.name}")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self.stop_recording()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self.connected = False

    def _get_capture_source(self):
        # Si es un número entero en string ("0", "1"), convertir a int para webcam local
        if isinstance(self.source, str) and self.source.isdigit():
            return int(self.source)
        return self.source

    def _capture_loop(self) -> None:
        src = self._get_capture_source()
        cap = cv2.VideoCapture(src)

        # Optimizaciones de buffer de OpenCV para RTSP
        if isinstance(src, str) and src.startswith("rtsp://"):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_count = 0
        start_time = time.time()

        while self._running:
            if not cap.isOpened():
                self.connected = False
                time.sleep(2.0)
                cap.open(src)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                self.connected = False
                time.sleep(0.5)
                # Reintentar conexión si es stream de red
                if isinstance(src, str) and (src.startswith("rtsp") or src.startswith("http")):
                    cap.release()
                    time.sleep(1.0)
                    cap.open(src)
                continue

            self.connected = True
            
            # Procesar movimiento si está activado
            if self.enable_motion:
                has_motion, boxes, annotated = self.detector.process_frame(frame)
                self.motion_active = has_motion
                if has_motion and self.on_motion_callback:
                    self.on_motion_callback(self.name)
            else:
                annotated = frame
                self.motion_active = False

            # Manejar grabación si está activa
            with self._lock:
                self.latest_frame = frame
                self.latest_annotated_frame = annotated

                if self._recording and self._video_writer is not None:
                    try:
                        self._video_writer.write(frame)
                    except Exception as e:
                        print(f"[StreamReceiver] Error escribiendo frame en grabación: {e}")

            # Calcular FPS reales
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                self.fps = round(frame_count / elapsed, 1)
                frame_count = 0
                start_time = time.time()

            # Breve desahogo de CPU
            time.sleep(0.005)

        cap.release()
        self.connected = False

    def get_frame(self, draw_annotations: bool = True) -> Optional[np.ndarray]:
        """Obtiene el último fotograma de forma segura y libre de condición de carrera."""
        with self._lock:
            if draw_annotations and self.latest_annotated_frame is not None:
                return self.latest_annotated_frame.copy()
            elif self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def start_recording(self, output_dir: str = "recordings") -> Optional[str]:
        with self._lock:
            if self._recording:
                return str(self._recording_path)
            
            if self.latest_frame is None:
                return None

            path_dir = Path(output_dir)
            path_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_name = "".join([c if c.isalnum() else "_" for c in self.name])
            filename = path_dir / f"rec_{safe_name}_{timestamp}.mp4"

            h, w = self.latest_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = max(15, int(self.fps if self.fps > 0 else 20))
            
            self._video_writer = cv2.VideoWriter(str(filename), fourcc, fps, (w, h))
            self._recording_path = filename
            self._recording = True
            return str(filename)

    def stop_recording(self) -> None:
        with self._lock:
            if not self._recording:
                return
            self._recording = False
            if self._video_writer:
                self._video_writer.release()
                self._video_writer = None
            self._recording_path = None

    @property
    def is_recording(self) -> bool:
        return self._recording
