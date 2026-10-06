import qrcode
import numpy as np
import cv2
from pathlib import Path

def generate_qr_image(url: str, output_path: str = "qr_camera.png") -> str:
    """
    Genera una imagen QR de alta resolución con la URL del nodo cámara.
    Utiliza OpenCV y NumPy para evitar cualquier dependencia de Pillow en Android.
    Retorna la ruta absoluta del archivo generado.
    """
    out_p = Path(output_path).resolve()
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        matrix = np.array(qr.get_matrix(), dtype=np.uint8)
        img = np.where(matrix, 0, 255).astype(np.uint8)
        img = cv2.resize(img, (320, 320), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(out_p), img)
    except Exception as e:
        print(f"[QR] Error generando imagen QR: {e}")
    return str(out_p)
