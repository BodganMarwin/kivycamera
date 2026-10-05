import cv2
import numpy as np
from typing import Tuple, List, Optional

class MotionDetector:
    """
    Detector de movimiento liviano y optimizado para CPU basado en acumulación de fondo
    y diferenciación de contornos.
    """

    def __init__(self, min_area: int = 1200, threshold: int = 25, history_weight: float = 0.05):
        self.min_area = min_area
        self.threshold = threshold
        self.history_weight = history_weight
        self.avg_frame: Optional[np.ndarray] = None

    def reset(self) -> None:
        self.avg_frame = None

    def process_frame(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]], np.ndarray]:
        """
        Procesa un fotograma y detecta si hay movimiento.
        Retorna:
            (motion_detected, bounding_boxes [(x, y, w, h)], frame_con_marcas)
        """
        if frame is None:
            return False, [], frame

        # Redimensionar para análisis liviano si es muy grande
        h, w = frame.shape[:2]
        scale = 1.0
        if w > 480:
            scale = 480.0 / w
            proc_w = 480
            proc_h = int(h * scale)
            small_frame = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
        else:
            small_frame = frame

        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.avg_frame is None:
            self.avg_frame = gray.astype("float")
            return False, [], frame

        # Acumular media móvil del fondo
        cv2.accumulateWeighted(gray, self.avg_frame, self.history_weight)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg_frame))

        # Umbralización y dilatación
        thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        boxes = []
        annotated_frame = frame.copy()

        inv_scale = 1.0 / scale if scale != 1.0 else 1.0

        for c in contours:
            area = cv2.contourArea(c)
            # Ajustar área proporcional a la escala
            if area < (self.min_area * (scale * scale)):
                continue

            motion_detected = True
            (x, y, bw, bh) = cv2.boundingRect(c)
            
            # Escalar coordenadas a tamaño original del frame
            orig_x = int(x * inv_scale)
            orig_y = int(y * inv_scale)
            orig_w = int(bw * inv_scale)
            orig_h = int(bh * inv_scale)

            boxes.append((orig_x, orig_y, orig_w, orig_h))
            
            # Dibujar recuadro de alerta
            cv2.rectangle(annotated_frame, (orig_x, orig_y), (orig_x + orig_w, orig_y + orig_h), (0, 0, 255), 2)

        if motion_detected:
            cv2.putText(
                annotated_frame,
                "ALERTA: MOVIMIENTO",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        return motion_detected, boxes, annotated_frame
