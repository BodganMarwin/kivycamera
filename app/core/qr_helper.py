import qrcode
from pathlib import Path

def generate_qr_image(url: str, output_path: str = "qr_camera.png") -> str:
    """
    Genera una imagen QR de alta resolución con la URL del nodo cámara.
    Retorna la ruta absoluta del archivo generado.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    out_p = Path(output_path).resolve()
    img.save(str(out_p))
    return str(out_p)
