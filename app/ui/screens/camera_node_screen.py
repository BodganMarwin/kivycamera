from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import platform
import cv2

from app.core.stream_receiver import StreamReceiver
from app.core.stream_server import StreamServer, get_local_ip
from app.core.signaling_client import SentinelSignalingClient
from app.ui.theme import (
    BG_DARK, BG_NAVY, CARD_BG, CARD_BG_ELEVATED, PRIMARY_BLUE, NAVY_BUTTON,
    WHITE, WHITE_SOFT, WHITE_MUTED, GREEN_LIVE, AMBER_WARN, RED_ALERT,
    HEX_WHITE, HEX_WHITE_SOFT, HEX_CYAN, HEX_GREEN, HEX_AMBER, HEX_MUTED,
    RoundedButton, CardLayout, apply_screen_background
)

class CameraNodeScreen(Screen):
    """
    Pantalla del modo 'Cámara (Sensor)' estilo AlfredCamera.
    Diseño refinado en Azul Marino y Blanco. Muestra de forma destacada el
    código de 6 dígitos para vincular con el reproductor en cualquier red (WiFi/4G).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_DARK)

        self.current_cam_index = 0
        self.receiver = StreamReceiver(source=str(self.current_cam_index), name="Cámara Móvil", enable_motion=True)
        self.server = StreamServer(port=8080)
        self.signaling = SentinelSignalingClient()
        self.signaling.on_command_received = self._on_remote_command
        self.signaling.on_status_changed = self._on_signaling_status

        self.is_streaming = False
        self.powersave_mode = False
        self.torch_on = False

        self.main_layout = BoxLayout(orientation="vertical", spacing=10, padding=[12, 14, 12, 14])

        # 1. BARRA SUPERIOR (App Bar Azul Marino)
        top_bar = BoxLayout(size_hint_y=None, height=44, spacing=10)

        btn_back = RoundedButton(
            text="< Menú",
            size_hint_x=None,
            width=80,
            font_size="13sp",
            bg_color=NAVY_BUTTON,
            radius=[8, 8, 8, 8]
        )
        btn_back.bind(on_release=self.on_back_pressed)
        top_bar.add_widget(btn_back)

        self.lbl_title = Label(
            text=f"[b][color={HEX_WHITE}]MODO CÁMARA[/color][/b] [color={HEX_CYAN}]• EN VIVO[/color]",
            markup=True,
            font_size="14sp",
            halign="center",
            valign="middle"
        )
        top_bar.add_widget(self.lbl_title)

        self.lbl_live_badge = Label(
            text=f"[b][color={HEX_GREEN}][ ONLINE ][/color][/b]",
            markup=True,
            size_hint_x=None,
            width=85,
            font_size="12sp",
            halign="right"
        )
        top_bar.add_widget(self.lbl_live_badge)
        self.main_layout.add_widget(top_bar)

        # 2. TARJETA DESTACADA DEL CÓDIGO DE VINCULACIÓN (Estilo AlfredCamera)
        self.code_card = CardLayout(
            orientation="vertical",
            size_hint_y=None,
            height=86,
            padding=[14, 8, 14, 8],
            spacing=2,
            bg_color=CARD_BG_ELEVATED,
            radius=[12, 12, 12, 12]
        )

        self.lbl_code_title = Label(
            text=f"[b][color={HEX_MUTED}]CÓDIGO DE VINCULACIÓN PARA EL VISOR:[/color][/b]",
            markup=True,
            font_size="11sp",
            size_hint_y=None,
            height=18
        )
        self.code_card.add_widget(self.lbl_code_title)

        self.lbl_code = Label(
            text=f"[b][color={HEX_CYAN}]GENERANDO CÓDIGO...[/color][/b]",
            markup=True,
            font_size="28sp",
            size_hint_y=None,
            height=40
        )
        self.code_card.add_widget(self.lbl_code)

        self.lbl_status = Label(
            text=f"[color={HEX_AMBER}]Conectando con red de señalización...[/color]",
            markup=True,
            font_size="11sp",
            size_hint_y=None,
            height=18
        )
        self.code_card.add_widget(self.lbl_status)

        self.main_layout.add_widget(self.code_card)

        # 3. VISOR DE CÁMARA LOCAL (Card oscura con placeholder)
        self.preview_container = FloatLayout(size_hint=(1, 1))

        # Fondo oscuro del monitor
        monitor_bg = CardLayout(
            pos_hint={'x': 0, 'y': 0},
            size_hint=(1, 1),
            bg_color=(0.02, 0.04, 0.08, 1.0),
            radius=[10, 10, 10, 10]
        )
        self.preview_container.add_widget(monitor_bg)

        # Etiqueta placeholder mientras inicia la cámara
        self.lbl_placeholder = Label(
            text=f"[b][color={HEX_MUTED}]Iniciando cámara del dispositivo...[/color][/b]\n"
                 f"[size=11sp][color={HEX_MUTED}]Preparando sensor de video local[/size][/color]",
            markup=True,
            halign="center",
            valign="middle",
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.preview_container.add_widget(self.lbl_placeholder)

        self.preview_image = Image(
            allow_stretch=True,
            keep_ratio=True,
            opacity=0.0,
            pos_hint={'x': 0, 'y': 0},
            size_hint=(1, 1)
        )
        self.preview_container.add_widget(self.preview_image)
        self.main_layout.add_widget(self.preview_container)

        # 4. BARRA DE CONTROLES INFERIORES
        controls = BoxLayout(size_hint_y=None, height=46, spacing=8)

        self.btn_switch_cam = RoundedButton(
            text="Girar Cámara",
            bg_color=PRIMARY_BLUE,
            font_size="12sp",
            bold=True,
            radius=[10, 10, 10, 10]
        )
        self.btn_switch_cam.bind(on_release=self.switch_camera)
        controls.add_widget(self.btn_switch_cam)

        self.btn_torch = RoundedButton(
            text="Linterna",
            bg_color=NAVY_BUTTON,
            font_size="12sp",
            radius=[10, 10, 10, 10]
        )
        self.btn_torch.bind(on_release=self.toggle_local_torch)
        controls.add_widget(self.btn_torch)

        self.btn_powersave = RoundedButton(
            text="Modo Ahorro",
            bg_color=NAVY_BUTTON,
            font_size="12sp",
            radius=[10, 10, 10, 10]
        )
        self.btn_powersave.bind(on_release=self.toggle_powersave)
        controls.add_widget(self.btn_powersave)

        self.main_layout.add_widget(controls)
        self.add_widget(self.main_layout)

        self._render_clock = None

    def on_enter(self, *args):
        """Inicia la captura local y el enlace de señalización con la nube/relevo."""
        self.receiver.start()
        self.server.start()
        self.signaling.start_as_camera(
            device_name=f"Cámara {platform.capitalize()}",
            on_code_ready=self._on_pair_code_ready
        )
        self._render_clock = Clock.schedule_interval(self._render_loop, 1.0 / 25.0)

    def on_leave(self, *args):
        """Detiene todo al salir de la pantalla."""
        if self._render_clock:
            self._render_clock.cancel()
            self._render_clock = None
        self.receiver.stop()
        self.server.stop()
        self.signaling.stop()

    def _on_pair_code_ready(self, code: str):
        def update_ui(dt):
            self.lbl_code.text = f"[b][color={HEX_CYAN}]{code}[/color][/b]"
            self.lbl_status.text = f"[color={HEX_GREEN}][ Listo para transmitir en 4G/WiFi ][/color]"
        Clock.schedule_once(update_ui, 0)

    def _on_signaling_status(self, status: str):
        def update_ui(dt):
            self.lbl_status.text = f"[color={HEX_AMBER}]{status}[/color]"
        Clock.schedule_once(update_ui, 0)

    def _on_remote_command(self, cmd_dict: dict):
        cmd = cmd_dict.get("cmd")
        print(f"[Cámara] Comando remoto recibido: {cmd}")
        if cmd == "switch_cam":
            Clock.schedule_once(lambda dt: self.switch_camera(), 0)
        elif cmd == "toggle_torch":
            self.toggle_local_torch()
        elif cmd == "siren":
            self._trigger_siren_alarm()

    def toggle_local_torch(self, *args):
        self.torch_on = not self.torch_on
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                activity = PythonActivity.mActivity
                cam_mgr = activity.getSystemService(Context.CAMERA_SERVICE)
                cam_id = cam_mgr.getCameraIdList()[0]
                cam_mgr.setTorchMode(cam_id, self.torch_on)
            except Exception as e:
                print(f"[Linterna Android] Error: {e}")
        else:
            print(f"[Linterna Desktop] Estado linterna: {self.torch_on}")

        self.btn_torch.text = "Linterna [ON]" if self.torch_on else "Linterna"
        self.btn_torch.bg_color = PRIMARY_BLUE if self.torch_on else NAVY_BUTTON

    def _trigger_siren_alarm(self):
        print("🚨 [SIRENA ACTIVADA] Emitiendo sonido de alarma disuasoria...")

    def _render_loop(self, dt: float):
        frame = self.receiver.get_frame(draw_annotations=True)
        if frame is not None:
            # 1. Enviar fotograma al servidor de relevo
            self.signaling.send_frame(frame, quality=60)
            self.server.update_frame(frame)

            # 2. Renderizar previsualización en pantalla
            if not self.powersave_mode:
                self.lbl_placeholder.opacity = 0.0
                self.preview_image.opacity = 1.0

                if len(frame.shape) == 2:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                elif len(frame.shape) == 3 and frame.shape[2] == 1:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                elif len(frame.shape) == 3 and frame.shape[2] == 4:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                else:
                    frame_bgr = frame

                flipped = cv2.flip(frame_bgr, 0)
                h, w = flipped.shape[:2]
                texture = Texture.create(size=(w, h), colorfmt='bgr')
                texture.blit_buffer(flipped.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                self.preview_image.texture = texture

    def switch_camera(self, *args):
        self.current_cam_index = 1 if self.current_cam_index == 0 else 0
        self.receiver.stop()
        self.receiver = StreamReceiver(source=str(self.current_cam_index), name="Cámara Móvil", enable_motion=True)
        self.receiver.start()

    def toggle_powersave(self, *args):
        self.powersave_mode = not self.powersave_mode
        if self.powersave_mode:
            self.preview_image.opacity = 0.05
            self.btn_powersave.text = "Salir Ahorro"
            self.btn_powersave.bg_color = AMBER_WARN
        else:
            self.preview_image.opacity = 1.0
            self.btn_powersave.text = "Modo Ahorro"
            self.btn_powersave.bg_color = NAVY_BUTTON

    def on_back_pressed(self, *args):
        self.manager.current = "role_selector"
