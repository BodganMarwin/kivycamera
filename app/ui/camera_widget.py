import cv2
from typing import Optional, Any
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty

from app.ui.theme import (
    CARD_BG, CARD_BG_ELEVATED, PRIMARY_BLUE, NAVY_BUTTON,
    WHITE, WHITE_SOFT, WHITE_MUTED, GREEN_LIVE, RED_ALERT, AMBER_WARN, PURPLE_SIREN,
    HEX_WHITE, HEX_WHITE_SOFT, HEX_CYAN, HEX_GREEN, HEX_RED, HEX_AMBER, HEX_MUTED,
    RoundedButton, CardLayout
)

class KivyCameraWidget(CardLayout):
    """
    Widget de visualización de cámara estilo AlfredCamera.
    Presentado como una tarjeta elegante en Azul Marino y Blanco con controles
    remotos integrados (Linterna, Lente, Sirena, REC y Desvinculación).
    """
    camera_name = StringProperty("Cámara")
    fps_text = StringProperty("0 FPS")
    is_recording = BooleanProperty(False)
    has_motion = BooleanProperty(False)
    is_connected = BooleanProperty(False)

    def __init__(self, device: Any, is_web_device: bool = False, on_remove_callback: Optional[Any] = None, **kwargs):
        super().__init__(
            orientation="vertical",
            spacing=5,
            padding=[8, 8, 8, 8],
            bg_color=CARD_BG,
            radius=[12, 12, 12, 12],
            **kwargs
        )
        self.device = device
        self.is_web_device = is_web_device
        self.on_remove_callback = on_remove_callback
        self.camera_name = getattr(device, "name", "Cámara")

        # 1. BARRA SUPERIOR DE INFORMACIÓN Y ESTADO
        self.status_bar = BoxLayout(size_hint_y=None, height=30, padding=[4, 0], spacing=6)
        
        self.lbl_info = Label(
            text=f"[b][color={HEX_WHITE}]{self.camera_name}[/color][/b] [color={HEX_AMBER}]• Conectando...[/color]",
            markup=True,
            font_size="12sp",
            halign="left",
            valign="middle"
        )
        self.lbl_info.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        self.status_bar.add_widget(self.lbl_info)

        # Botón Desvincular / Quitar Dispositivo
        self.btn_unpair = RoundedButton(
            text="Desvincular" if self.is_web_device else "Quitar",
            size_hint_x=None,
            width=90,
            font_size="11sp",
            bold=True,
            bg_color=RED_ALERT,
            radius=[6, 6, 6, 6]
        )
        self.btn_unpair.bind(on_release=self._on_unpair_clicked)
        self.status_bar.add_widget(self.btn_unpair)
        self.add_widget(self.status_bar)

        # 2. CONTENEDOR DEL VISOR DE VIDEO (Pantalla oscura con placeholder)
        self.video_box = FloatLayout(size_hint=(1, 1))

        # Fondo oscuro del monitor
        monitor_bg = CardLayout(
            pos_hint={'x': 0, 'y': 0},
            size_hint=(1, 1),
            bg_color=(0.02, 0.04, 0.08, 1.0),
            radius=[8, 8, 8, 8]
        )
        self.video_box.add_widget(monitor_bg)

        # Etiqueta de espera / sin señal
        self.lbl_placeholder = Label(
            text=f"[b][color={HEX_MUTED}]Esperando transmisión...[/color][/b]\n"
                 f"[size=11sp][color={HEX_MUTED}]Conectando con {self.camera_name}[/size][/color]",
            markup=True,
            halign="center",
            valign="middle",
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.video_box.add_widget(self.lbl_placeholder)

        # Imagen de video de la cámara
        self.image_widget = Image(
            allow_stretch=True,
            keep_ratio=True,
            opacity=0.0,
            pos_hint={'x': 0, 'y': 0},
            size_hint=(1, 1)
        )
        self.video_box.add_widget(self.image_widget)
        self.add_widget(self.video_box)

        # 3. BARRA DE CONTROLES REMOTOS (Estilo AlfredCamera)
        self.controls_bar = BoxLayout(size_hint_y=None, height=36, spacing=6, padding=[2, 2])

        # Botón Grabar Localmente
        self.btn_rec = RoundedButton(
            text="● REC",
            size_hint_x=0.25,
            font_size="11sp",
            bold=True,
            bg_color=RED_ALERT,
            radius=[6, 6, 6, 6]
        )
        self.btn_rec.bind(on_release=self.toggle_recording)
        self.controls_bar.add_widget(self.btn_rec)

        if self.is_web_device:
            # Botón Linterna Remota
            btn_torch = RoundedButton(
                text="Flash",
                size_hint_x=0.25,
                font_size="11sp",
                bg_color=NAVY_BUTTON,
                radius=[6, 6, 6, 6]
            )
            btn_torch.bind(on_release=lambda *a: self.device.send_remote_command({"cmd": "toggle_torch"}))
            self.controls_bar.add_widget(btn_torch)

            # Botón Conmutar Lente Frontal / Trasera
            btn_switch = RoundedButton(
                text="Lente",
                size_hint_x=0.25,
                font_size="11sp",
                bg_color=PRIMARY_BLUE,
                radius=[6, 6, 6, 6]
            )
            btn_switch.bind(on_release=lambda *a: self.device.send_remote_command({"cmd": "switch_cam"}))
            self.controls_bar.add_widget(btn_switch)

            # Botón Sirena Disuasoria (Alarma acústica remota)
            btn_siren = RoundedButton(
                text="Sirena",
                size_hint_x=0.25,
                font_size="11sp",
                bold=True,
                bg_color=PURPLE_SIREN,
                radius=[6, 6, 6, 6]
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
            self.btn_rec.bg_color = (0.9, 0.4, 0.1, 1.0)
        else:
            self.device.stop_recording()
            self.btn_rec.text = "● REC"
            self.btn_rec.bg_color = RED_ALERT

    def _render_frame(self, dt: float) -> None:
        frame = self.device.get_frame(draw_annotations=True)
        self.is_connected = getattr(self.device, "connected", False)
        self.has_motion = getattr(self.device, "motion_active", False)
        self.is_recording = getattr(self.device, "is_recording", False)
        self.fps_text = f"{getattr(self.device, 'fps', 0)} FPS"

        if frame is None:
            self.image_widget.opacity = 0.0
            self.lbl_placeholder.opacity = 1.0
            self.lbl_info.text = f"[b][color={HEX_WHITE}]{self.camera_name}[/color][/b] [color={HEX_RED}]● Sin señal[/color]"
            return

        self.lbl_placeholder.opacity = 0.0
        self.image_widget.opacity = 1.0

        rec_badge = f"[b][color={HEX_RED}]● REC [/color][/b]" if self.is_recording else ""
        motion_badge = f"[b][color={HEX_AMBER}]• MOV [/color][/b]" if self.has_motion else ""
        status_dot = f"[color={HEX_GREEN}]● [/color]"
        self.lbl_info.text = f"{rec_badge}{motion_badge}{status_dot}[b][color={HEX_WHITE}]{self.camera_name}[/color][/b] [color={HEX_MUTED}]| {self.fps_text}[/color]"

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
