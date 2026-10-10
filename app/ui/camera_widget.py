import cv2
from typing import Optional, Any
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty

class KivyCameraWidget(BoxLayout):
    """
    Widget de visualización de cámara para Kivy.
    Compatible tanto con receptores RTSP/ONVIF/USB (StreamReceiver)
    como con teléfonos conectados vía web (WebCameraDevice).
    """
    camera_name = StringProperty("Cámara")
    fps_text = StringProperty("0 FPS")
    is_recording = BooleanProperty(False)
    has_motion = BooleanProperty(False)
    is_connected = BooleanProperty(False)

    def __init__(self, device: Any, is_web_device: bool = False, on_remove_callback: Optional[Any] = None, **kwargs):
        super().__init__(orientation="vertical", spacing=2, **kwargs)
        self.device = device
        self.is_web_device = is_web_device
        self.on_remove_callback = on_remove_callback
        self.camera_name = getattr(device, "name", "Cámara")

        # 1. Visor de Video
        self.image_widget = Image(allow_stretch=True, keep_ratio=True)
        self.add_widget(self.image_widget)

        # 2. Barra de información y desvinculación superior/inferior
        self.status_bar = BoxLayout(size_hint_y=None, height=28, padding=[6, 2], spacing=6)
        self.lbl_info = Label(
            text=f"{self.camera_name} - Esperando señal...",
            font_size="12sp",
            halign="left",
            valign="middle"
        )
        self.lbl_info.bind(size=self.lbl_info.setter('text_size'))
        self.status_bar.add_widget(self.lbl_info)

        # Botón Desvincular / Quitar Dispositivo
        self.btn_unpair = Button(
            text="🔌 Desvincular" if self.is_web_device else "✕ Quitar",
            size_hint_x=None,
            width=92,
            font_size="11sp",
            background_normal="",
            background_color=(0.55, 0.2, 0.2, 1)
        )
        self.btn_unpair.bind(on_release=self._on_unpair_clicked)
        self.status_bar.add_widget(self.btn_unpair)
        self.add_widget(self.status_bar)

        # 3. Barra de Controles Remotos (Estilo AlfredCamera)
        self.controls_bar = BoxLayout(size_hint_y=None, height=32, spacing=4, padding=[4, 2])

        # Botón Grabar
        self.btn_rec = Button(
            text="🔴 REC",
            size_hint_x=0.25,
            font_size="11sp",
            background_normal="",
            background_color=(0.7, 0.2, 0.2, 1)
        )
        self.btn_rec.bind(on_release=self.toggle_recording)
        self.controls_bar.add_widget(self.btn_rec)

        if self.is_web_device:
            # Botón Linterna Remota
            btn_torch = Button(
                text="🔦 Flash",
                size_hint_x=0.25,
                font_size="11sp",
                background_normal="",
                background_color=(0.3, 0.3, 0.35, 1)
            )
            btn_torch.bind(on_release=lambda *a: self.device.send_remote_command({"cmd": "toggle_torch"}))
            self.controls_bar.add_widget(btn_torch)

            # Botón Cambiar Lente
            btn_switch = Button(
                text="🔄 Lente",
                size_hint_x=0.25,
                font_size="11sp",
                background_normal="",
                background_color=(0.25, 0.4, 0.55, 1)
            )
            btn_switch.bind(on_release=lambda *a: self.device.send_remote_command({"cmd": "switch_cam"}))
            self.controls_bar.add_widget(btn_switch)

            # Botón Sirena Disuasoria (Alarma en el teléfono)
            btn_siren = Button(
                text="🚨 Sirena",
                size_hint_x=0.25,
                font_size="11sp",
                background_normal="",
                background_color=(0.8, 0.4, 0.1, 1)
            )
            btn_siren.bind(on_release=lambda *a: self.device.send_remote_command({"cmd": "siren", "duration": 5}))
            self.controls_bar.add_widget(btn_siren)

        self.add_widget(self.controls_bar)
        self._update_event = None

    def start_feed(self, fps: int = 25) -> None:
        if hasattr(self.device, "start"):
            self.device.start()
        if self._update_event is None:
            self._update_event = Clock.schedule_interval(self._render_frame, 1.0 / fps)

    def stop_feed(self) -> None:
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None
        if hasattr(self.device, "stop"):
            self.device.stop()

    def toggle_recording(self, *args):
        if not self.device.is_recording:
            self.device.start_recording()
            self.btn_rec.text = "⏹ STOP"
            self.btn_rec.background_color = (0.9, 0.3, 0.1, 1)
        else:
            self.device.stop_recording()
            self.btn_rec.text = "🔴 REC"
            self.btn_rec.background_color = (0.7, 0.2, 0.2, 1)

    def _render_frame(self, dt: float) -> None:
        frame = self.device.get_frame(draw_annotations=True)
        self.is_connected = getattr(self.device, "connected", False)
        self.has_motion = getattr(self.device, "motion_active", False)
        self.is_recording = getattr(self.device, "is_recording", False)
        self.fps_text = f"{getattr(self.device, 'fps', 0)} FPS"

        if frame is None:
            self.lbl_info.text = f"🔴 {self.camera_name} [Sin señal / Reconectando...]"
            return

        rec_badge = "🔴 REC " if self.is_recording else ""
        motion_badge = "⚠️ MOVIMIENTO " if self.has_motion else ""
        self.lbl_info.text = f"{rec_badge}{motion_badge}{self.camera_name} | {self.fps_text}"

        # Normalizar canal de color a BGR
        if len(frame.shape) == 2:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif len(frame.shape) == 3 and frame.shape[2] == 1:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif len(frame.shape) == 3 and frame.shape[2] == 4:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        else:
            frame_bgr = frame

        # Voltear verticalmente para textura OpenGL Kivy
        flipped = cv2.flip(frame_bgr, 0)
        h, w = flipped.shape[:2]

        texture = Texture.create(size=(w, h), colorfmt='bgr')
        texture.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
        self.image_widget.texture = texture

    def _on_unpair_clicked(self, *args):
        if self.on_remove_callback:
            self.on_remove_callback(self)
