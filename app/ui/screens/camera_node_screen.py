from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import platform
import cv2

from app.core.stream_receiver import StreamReceiver
from app.core.stream_server import StreamServer, get_local_ip
from app.core.signaling_client import SentinelSignalingClient

class CameraNodeScreen(Screen):
    """
    Pantalla del modo 'Cámara (Sensor)'.
    Convierte el smartphone o tablet en una cámara de vigilancia vinculable
    por código de 6 dígitos tipo AlfredCamera, funcionando en cualquier red.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.current_cam_index = 0
        self.receiver = StreamReceiver(source=str(self.current_cam_index), name="Cámara Móvil", enable_motion=True)
        self.server = StreamServer(port=8080)
        self.signaling = SentinelSignalingClient()
        self.signaling.on_command_received = self._on_remote_command
        self.signaling.on_status_changed = self._on_signaling_status

        self.is_streaming = False
        self.powersave_mode = False

        self.main_layout = BoxLayout(orientation="vertical", spacing=8, padding=12)

        # 1. Barra superior
        top_bar = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_back = Button(
            text="◀ Menú",
            size_hint_x=None,
            width=90,
            background_normal="",
            background_color=(0.3, 0.3, 0.3, 1)
        )
        btn_back.bind(on_release=self.on_back_pressed)
        top_bar.add_widget(btn_back)

        self.lbl_title = Label(
            text="[b]DISPOSITIVO CÁMARA (TRANSMISOR)[/b]",
            markup=True,
            font_size="15sp"
        )
        top_bar.add_widget(self.lbl_title)
        self.main_layout.add_widget(top_bar)

        # 2. Caja destacada del Código de Vinculación (Estilo AlfredCamera)
        self.code_box = BoxLayout(orientation="vertical", size_hint_y=None, height=70, spacing=2)
        self.lbl_code_title = Label(
            text="CÓDIGO DE VINCULACIÓN PARA EL REPRODUCTOR:",
            font_size="12sp",
            color=(0.8, 0.8, 0.8, 1)
        )
        self.lbl_code = Label(
            text="[b][color=00ffaa]GENERANDO CÓDIGO...[/color][/b]",
            markup=True,
            font_size="28sp"
        )
        self.code_box.add_widget(self.lbl_code_title)
        self.code_box.add_widget(self.lbl_code)
        self.main_layout.add_widget(self.code_box)

        # 3. Estado de conexión
        self.lbl_status = Label(
            text="Conectando con red de relevo...",
            size_hint_y=None,
            height=25,
            font_size="13sp",
            color=(0.9, 0.7, 0.2, 1)
        )
        self.main_layout.add_widget(self.lbl_status)

        # 4. Visor de cámara local
        self.preview_image = Image(allow_stretch=True, keep_ratio=True)
        self.main_layout.add_widget(self.preview_image)

        # 5. Barra de controles inferiores
        controls = BoxLayout(size_hint_y=None, height=48, spacing=8)

        self.btn_switch_cam = Button(
            text="🔄 Cambiar Lente",
            background_normal="",
            background_color=(0.25, 0.45, 0.7, 1),
            font_size="13sp"
        )
        self.btn_switch_cam.bind(on_release=self.switch_camera)
        controls.add_widget(self.btn_switch_cam)

        self.btn_powersave = Button(
            text="🌙 Pantalla Negra (Ahorro)",
            background_normal="",
            background_color=(0.2, 0.2, 0.25, 1),
            font_size="13sp"
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
            self.lbl_code.text = f"[b][color=00ff88]{code}[/color][/b]"
            self.lbl_status.text = f"🟢 Listo para transmitir en cualquier red (WiFi / 4G / 5G)"
            self.lbl_status.color = (0.2, 0.9, 0.4, 1)
        Clock.schedule_once(update_ui, 0)

    def _on_signaling_status(self, status: str):
        def update_ui(dt):
            self.lbl_status.text = status
        Clock.schedule_once(update_ui, 0)

    def _on_remote_command(self, cmd_dict: dict):
        cmd = cmd_dict.get("cmd")
        print(f"[Cámara] Comando remoto recibido desde el visor: {cmd}")
        if cmd == "switch_cam":
            Clock.schedule_once(lambda dt: self.switch_camera(), 0)
        elif cmd == "toggle_torch":
            self._toggle_hardware_torch()
        elif cmd == "siren":
            self._trigger_siren_alarm()

    def _toggle_hardware_torch(self):
        # En Android activar CameraManager torchMode
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                activity = PythonActivity.mActivity
                cam_mgr = activity.getSystemService(Context.CAMERA_SERVICE)
                cam_id = cam_mgr.getCameraIdList()[0]
                # Conmutar modo linterna
                cam_mgr.setTorchMode(cam_id, True)
            except Exception as e:
                print(f"[Linterna Android] Error: {e}")
        else:
            print("[Linterna] Comando recibido (Simulado en Escritorio)")

    def _trigger_siren_alarm(self):
        print("🚨 [SIRENA ACTIVADA] Emitiendo sonido de alarma disuasoria...")
        # En Android o Desktop reproducir tono de alerta
        try:
            from kivy.core.audio import SoundLoader
            # Si hay un archivo de sonido, cargarlo o emitir beep
        except Exception:
            pass

    def _render_loop(self, dt: float):
        frame = self.receiver.get_frame(draw_annotations=True)
        if frame is not None:
            # 1. Enviar fotograma al servidor de relevo (hacia el reproductor remoto)
            self.signaling.send_frame(frame, quality=60)
            self.server.update_frame(frame)

            # 2. Renderizar previsualización en pantalla si no está en ahorro
            if not self.powersave_mode:
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
            self.btn_powersave.text = "☀️ Salir del Ahorro"
            self.btn_powersave.background_color = (0.7, 0.5, 0.1, 1)
        else:
            self.preview_image.opacity = 1.0
            self.btn_powersave.text = "🌙 Pantalla Negra (Ahorro)"
            self.btn_powersave.background_color = (0.2, 0.2, 0.25, 1)

    def on_back_pressed(self, *args):
        self.manager.current = "role_selector"
