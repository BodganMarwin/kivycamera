import threading
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.clock import Clock

from app.config import ConfigManager
from app.core.stream_receiver import StreamReceiver
from app.core.onvif_discovery import discover_onvif_cameras
from app.core.web_hub import SentinelWebHub, get_local_ip
from app.core.qr_helper import generate_qr_image
from app.core.relay_device import RelayCameraDevice
from app.ui.camera_widget import KivyCameraWidget
from app.ui.theme import (
    BG_DARK, BG_NAVY, CARD_BG, CARD_BG_ELEVATED, PRIMARY_BLUE, NAVY_BUTTON,
    WHITE, WHITE_SOFT, WHITE_MUTED, CYAN_ACCENT, RED_ALERT, GREEN_LIVE,
    HEX_WHITE, HEX_WHITE_SOFT, HEX_CYAN, HEX_MUTED, HEX_GREEN, HEX_RED,
    RoundedButton, CardLayout, apply_screen_background
)

class MonitorScreen(Screen):
    """
    Pantalla del modo 'Monitor / NVR' estilo AlfredCamera.
    Diseño refinado en Azul Marino y Blanco.
    Visualiza simultáneamente múltiples cámaras tradicionales (RTSP/ONVIF),
    dispositivos web (QR) y celulares remotos vinculados por código Alfred P2P.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_DARK)

        self.config_mgr = ConfigManager()
        self.camera_widgets = []
        self.all_recording = False

        # Iniciar Servidor WebHub para vincular teléfonos vía navegador
        self.web_hub = SentinelWebHub(port=8080, on_device_connected=self._on_mobile_connected)

        self.root_layout = BoxLayout(orientation="vertical", spacing=8, padding=[8, 8, 8, 8])

        # 1. BARRA DE HERRAMIENTAS SUPERIOR (Deslizable horizontalmente)
        toolbar_scroll = ScrollView(
            size_hint=(1, None),
            height=48,
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0
        )

        toolbar_card = CardLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            width=540,
            spacing=6,
            padding=[6, 5, 6, 5],
            bg_color=CARD_BG_ELEVATED,
            radius=[10, 10, 10, 10]
        )

        btn_back = RoundedButton(
            text="< Menú",
            size_hint_x=None,
            width=72,
            font_size="12sp",
            bg_color=NAVY_BUTTON,
            radius=[8, 8, 8, 8]
        )
        btn_back.bind(on_release=self.on_back_pressed)
        toolbar_card.add_widget(btn_back)

        # Botón para vincular APK móvil por código (AlfredCamera P2P)
        btn_pair_code = RoundedButton(
            text="+ Código",
            size_hint_x=None,
            width=92,
            font_size="12sp",
            bold=True,
            bg_color=PRIMARY_BLUE,
            radius=[8, 8, 8, 8]
        )
        btn_pair_code.bind(on_release=self.show_pair_code_dialog)
        toolbar_card.add_widget(btn_pair_code)

        # Botón para vincular Smartphone sin instalar nada
        btn_qr = RoundedButton(
            text="Web QR",
            size_hint_x=None,
            width=84,
            font_size="12sp",
            bg_color=NAVY_BUTTON,
            radius=[8, 8, 8, 8]
        )
        btn_qr.bind(on_release=self.show_qr_dialog)
        toolbar_card.add_widget(btn_qr)

        btn_scan_onvif = RoundedButton(
            text="ONVIF",
            size_hint_x=None,
            width=80,
            font_size="12sp",
            bg_color=NAVY_BUTTON,
            radius=[8, 8, 8, 8]
        )
        btn_scan_onvif.bind(on_release=self.start_onvif_scan)
        toolbar_card.add_widget(btn_scan_onvif)

        btn_add_cam = RoundedButton(
            text="+ Añadir",
            size_hint_x=None,
            width=84,
            font_size="12sp",
            bg_color=NAVY_BUTTON,
            radius=[8, 8, 8, 8]
        )
        btn_add_cam.bind(on_release=self.show_add_camera_dialog)
        toolbar_card.add_widget(btn_add_cam)

        self.btn_rec_all = RoundedButton(
            text="● REC All",
            size_hint_x=None,
            width=94,
            font_size="12sp",
            bold=True,
            bg_color=RED_ALERT,
            radius=[8, 8, 8, 8]
        )
        self.btn_rec_all.bind(on_release=self.toggle_record_all)
        toolbar_card.add_widget(self.btn_rec_all)

        toolbar_scroll.add_widget(toolbar_card)
        self.root_layout.add_widget(toolbar_scroll)

        # 2. CUADRÍCULA DE CÁMARAS
        self.grid = GridLayout(spacing=8)
        self.root_layout.add_widget(self.grid)

        # Etiqueta de estado vacío
        self.lbl_empty = Label(
            text=f"[b][size=18sp][color={HEX_CYAN}]🛡️ Visor Central Alfred[/color][/size][/b]\n\n"
                 f"[color={HEX_WHITE}]No hay cámaras conectadas actualmente.[/color]\n\n"
                 f"[color={HEX_MUTED}]• Pulsa [b][color={HEX_CYAN}]🔗 Código[/color][/b] para vincular otro celular con el código de 6 dígitos.\n"
                 f"• Pulsa [b][color={HEX_WHITE}]📱 Web QR[/color][/b] para transmitir desde cualquier navegador sin apps.\n"
                 f"• O busca cámaras IP locales con [b][color={HEX_WHITE}]🔍 ONVIF[/color][/b].[/color]",
            markup=True,
            halign="center",
            valign="middle"
        )
        self.lbl_empty.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 40, None)))

        self.add_widget(self.root_layout)

    def on_enter(self, *args):
        """Inicia el servidor de móviles y carga las cámaras fijas."""
        self.web_hub.start()
        self.refresh_cameras()

    def on_leave(self, *args):
        """Detiene los feeds al salir para liberar recursos."""
        self.stop_all_feeds()

    def _on_mobile_connected(self, web_device):
        """Callback cuando un teléfono móvil abre la página web y empieza a transmitir."""
        Clock.schedule_once(lambda dt: self._add_mobile_widget(web_device), 0)

    def _add_mobile_widget(self, web_device):
        self._check_empty_state(remove=True)
        widget = KivyCameraWidget(
            device=web_device,
            is_web_device=True,
            on_remove_callback=self.confirm_unpair_camera
        )
        self.camera_widgets.append(widget)
        self.grid.add_widget(widget)
        widget.start_feed(fps=25)
        self._update_grid_columns()

    def _check_empty_state(self, remove=False):
        if remove:
            if self.lbl_empty in self.grid.children:
                self.grid.remove_widget(self.lbl_empty)
        else:
            if len(self.camera_widgets) == 0:
                self.grid.clear_widgets()
                self.grid.cols = 1
                self.grid.add_widget(self.lbl_empty)

    def _update_grid_columns(self):
        count = len(self.camera_widgets)
        if count == 0:
            self._check_empty_state(remove=False)
        else:
            self.grid.cols = 1 if count <= 1 else (2 if count <= 4 else 3)

    def stop_all_feeds(self):
        for w in self.camera_widgets:
            w.stop_feed()
        self.camera_widgets.clear()
        self.grid.clear_widgets()
        self._check_empty_state(remove=False)

    def refresh_cameras(self):
        self.stop_all_feeds()
        cameras = self.config_mgr.get_cameras()

        for cam in cameras:
            if not cam.get("enabled", True):
                continue
            self._check_empty_state(remove=True)
            receiver = StreamReceiver(
                source=cam.get("url", "0"),
                name=cam.get("name", "Cámara"),
                enable_motion=True
            )
            widget = KivyCameraWidget(
                device=receiver,
                is_web_device=False,
                on_remove_callback=self.confirm_unpair_camera
            )
            self.camera_widgets.append(widget)
            self.grid.add_widget(widget)
            widget.start_feed(fps=25)

        self._update_grid_columns()

    def confirm_unpair_camera(self, widget):
        """Muestra ventana modal de confirmación con estilo AlfredCamera."""
        cam_name = widget.camera_name
        is_web = widget.is_web_device

        content = BoxLayout(orientation="vertical", padding=15, spacing=14)
        if is_web:
            msg = (
                f"[b][color={HEX_WHITE}]¿Desvincular '{cam_name}'?[/color][/b]\n\n"
                f"[color={HEX_MUTED}]Se detendrá la transmisión en vivo, se apagará la cámara del "
                f"dispositivo y se liberará la conexión de red.[/color]"
            )
        else:
            msg = (
                f"[b][color={HEX_WHITE}]¿Quitar '{cam_name}'?[/color][/b]\n\n"
                f"[color={HEX_MUTED}]La cámara será desconectada y eliminada de tu configuración.[/color]"
            )

        lbl = Label(text=msg, markup=True, halign="center", font_size="13sp")
        content.add_widget(lbl)

        btn_box = BoxLayout(size_hint_y=None, height=44, spacing=10)
        btn_confirm = RoundedButton(
            text="Sí, Desvincular" if is_web else "Sí, Quitar",
            bg_color=RED_ALERT,
            font_size="13sp",
            radius=[8, 8, 8, 8]
        )
        btn_cancel = RoundedButton(
            text="Cancelar",
            bg_color=NAVY_BUTTON,
            font_size="13sp",
            radius=[8, 8, 8, 8]
        )
        btn_box.add_widget(btn_confirm)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Desvincular Dispositivo" if is_web else "Quitar Cámara",
            title_color=WHITE,
            content=content,
            size_hint=(0.75, 0.42),
            background_color=CARD_BG_ELEVATED
        )

        def do_unpair(*args):
            popup.dismiss()
            self.remove_camera(widget)

        btn_confirm.bind(on_release=do_unpair)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def remove_camera(self, widget):
        """Desvincula y limpia un dispositivo o cámara del sistema."""
        if widget.is_web_device and hasattr(widget.device, "device_id"):
            dev_id = widget.device.device_id
            self.web_hub.disconnect_device(dev_id)
        else:
            cams = self.config_mgr.get_cameras()
            for c in cams:
                if c.get("name") == widget.camera_name or c.get("url") == getattr(widget.device, "source", None):
                    self.config_mgr.remove_camera(c.get("id"))
                    break

        widget.stop_feed()
        if widget in self.camera_widgets:
            self.camera_widgets.remove(widget)
        self.grid.remove_widget(widget)
        self._update_grid_columns()

    def show_qr_dialog(self, *args):
        """Muestra ventana modal con código QR para conectar el teléfono sin instalar nada."""
        url = f"http://{get_local_ip()}:{self.web_hub.port}/camera"
        qr_path = generate_qr_image(url)

        content = BoxLayout(orientation="vertical", padding=14, spacing=10)

        info_lbl = Label(
            text=f"[b][color={HEX_CYAN}]Vincular Smartphone o Tablet[/color][/b]\n"
                 f"[color={HEX_WHITE_SOFT}]1. Abre la cámara nativa de tu teléfono.\n"
                 f"2. Escanea este código QR o abre en el navegador:[/color]\n"
                 f"[b][color={HEX_CYAN}]{url}[/color][/b]\n"
                 f"[color={HEX_MUTED}]3. Concede permiso de cámara. ¡Se conectará en vivo![/color]",
            markup=True,
            halign="center",
            font_size="12sp",
            size_hint_y=0.35
        )
        content.add_widget(info_lbl)

        qr_img = Image(source=qr_path, allow_stretch=True, keep_ratio=True, size_hint_y=0.53)
        content.add_widget(qr_img)

        btn_close = RoundedButton(
            text="Listo / Cerrar",
            size_hint_y=0.12,
            bg_color=PRIMARY_BLUE,
            radius=[8, 8, 8, 8]
        )
        content.add_widget(btn_close)

        popup = Popup(
            title="Conexión Instantánea Móvil (Web QR)",
            title_color=WHITE,
            content=content,
            size_hint=(0.82, 0.85),
            background_color=CARD_BG_ELEVATED
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()

    def toggle_record_all(self, *args):
        self.all_recording = not self.all_recording
        if self.all_recording:
            for w in self.camera_widgets:
                w.device.start_recording()
            self.btn_rec_all.text = "⏹ STOP"
            self.btn_rec_all.bg_color = (0.9, 0.4, 0.1, 1.0)
        else:
            for w in self.camera_widgets:
                w.device.stop_recording()
            self.btn_rec_all.text = "🔴 REC All"
            self.btn_rec_all.bg_color = RED_ALERT

    def start_onvif_scan(self, *args):
        popup_content = BoxLayout(orientation="vertical", padding=15, spacing=10)
        lbl = Label(
            text=f"[color={HEX_WHITE}]Buscando cámaras ONVIF en la red local...[/color]\n"
                 f"[color={HEX_MUTED}](Multicast UDP 3702)[/color]",
            markup=True,
            halign="center"
        )
        popup_content.add_widget(lbl)

        popup = Popup(
            title="Escáner ONVIF",
            title_color=WHITE,
            content=popup_content,
            size_hint=(0.8, 0.5),
            auto_dismiss=False,
            background_color=CARD_BG_ELEVATED
        )
        popup.open()

        def scan_worker():
            results = discover_onvif_cameras(timeout=3.0)
            Clock.schedule_once(lambda dt: self._display_onvif_results(results, popup), 0)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _display_onvif_results(self, results, popup):
        popup.dismiss()

        content = BoxLayout(orientation="vertical", padding=14, spacing=10)
        if not results:
            content.add_widget(Label(
                text=f"[color={HEX_WHITE_SOFT}]No se encontraron cámaras ONVIF automáticamente.\n"
                     f"Verifica que estén encendidas en la misma red WiFi.[/color]",
                markup=True,
                halign="center"
            ))
        else:
            for cam in results:
                row = BoxLayout(size_hint_y=None, height=40, spacing=8)
                row.add_widget(Label(text=f"{cam['name']} ({cam['ip']})", color=WHITE, size_hint_x=0.7))
                btn_add = RoundedButton(text="Añadir", size_hint_x=0.3, bg_color=PRIMARY_BLUE)
                btn_add.bind(on_release=lambda btn, c=cam: self._add_discovered_cam(c))
                content.add_widget(row)

        btn_close = RoundedButton(text="Cerrar", size_hint_y=None, height=40, bg_color=NAVY_BUTTON)
        content.add_widget(btn_close)

        res_popup = Popup(
            title="Cámaras ONVIF Encontradas",
            title_color=WHITE,
            content=content,
            size_hint=(0.85, 0.7),
            background_color=CARD_BG_ELEVATED
        )
        btn_close.bind(on_release=res_popup.dismiss)
        res_popup.open()

    def _add_discovered_cam(self, cam_info):
        self.config_mgr.add_camera(
            name=cam_info["name"],
            url=cam_info["default_rtsp"],
            cam_type="onvif"
        )
        self.refresh_cameras()

    def show_add_camera_dialog(self, *args):
        content = BoxLayout(orientation="vertical", padding=15, spacing=10)

        content.add_widget(Label(text="Nombre de la Cámara:", color=WHITE_SOFT, size_hint_y=None, height=22))
        txt_name = TextInput(
            text="Cámara Seguridad",
            multiline=False,
            size_hint_y=None,
            height=36,
            background_color=NAVY_BUTTON,
            foreground_color=WHITE
        )
        content.add_widget(txt_name)

        content.add_widget(Label(
            text="URL del Stream (RTSP, HTTP-MJPEG o número '0' para webcam):",
            color=WHITE_SOFT,
            size_hint_y=None,
            height=22
        ))
        txt_url = TextInput(
            text="rtsp://admin:password@192.168.1.50:554/stream1",
            multiline=False,
            size_hint_y=None,
            height=36,
            background_color=NAVY_BUTTON,
            foreground_color=WHITE
        )
        content.add_widget(txt_url)

        btn_box = BoxLayout(size_hint_y=None, height=44, spacing=10)
        btn_save = RoundedButton(text="Guardar", bg_color=PRIMARY_BLUE)
        btn_cancel = RoundedButton(text="Cancelar", bg_color=NAVY_BUTTON)
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Añadir Nueva Cámara",
            title_color=WHITE,
            content=content,
            size_hint=(0.85, 0.6),
            background_color=CARD_BG_ELEVATED
        )

        def on_save(instance):
            name = txt_name.text.strip() or "Cámara"
            url = txt_url.text.strip()
            if url:
                self.config_mgr.add_camera(name=name, url=url, cam_type="custom")
                self.refresh_cameras()
                popup.dismiss()

        btn_save.bind(on_release=on_save)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def show_pair_code_dialog(self, *args):
        """Muestra ventana para ingresar el código de 6 dígitos estilo AlfredCamera."""
        content = BoxLayout(orientation="vertical", padding=16, spacing=12)

        lbl_inst = Label(
            text=f"[b][color={HEX_CYAN}]Vincular Móvil Remoto (AlfredCamera)[/color][/b]\n"
                 f"[color={HEX_WHITE_SOFT}]Introduce el código de 6 dígitos que aparece en la pantalla\n"
                 f"del otro teléfono (funciona en 4G/5G y redes cruzadas):[/color]",
            markup=True,
            halign="center",
            font_size="13sp",
            size_hint_y=0.4
        )
        content.add_widget(lbl_inst)

        txt_code = TextInput(
            hint_text="Ejemplo: 749-218",
            multiline=False,
            halign="center",
            font_size="22sp",
            size_hint_y=None,
            height=48,
            background_color=NAVY_BUTTON,
            foreground_color=WHITE,
            cursor_color=CYAN_ACCENT
        )
        content.add_widget(txt_code)

        btn_box = BoxLayout(size_hint_y=None, height=46, spacing=10)
        btn_connect = RoundedButton(
            text="Conectar Cámara",
            bg_color=PRIMARY_BLUE,
            bold=True,
            font_size="13sp",
            radius=[8, 8, 8, 8]
        )
        btn_cancel = RoundedButton(
            text="Cancelar",
            bg_color=NAVY_BUTTON,
            font_size="13sp",
            radius=[8, 8, 8, 8]
        )
        btn_box.add_widget(btn_connect)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Vinculación AlfredCamera (Cross-Network)",
            title_color=WHITE,
            content=content,
            size_hint=(0.82, 0.56),
            background_color=CARD_BG_ELEVATED
        )

        def on_connect(instance):
            code = txt_code.text.strip()
            if code:
                popup.dismiss()
                self._check_empty_state(remove=True)
                relay_device = RelayCameraDevice(pair_code=code)
                widget = KivyCameraWidget(
                    device=relay_device,
                    is_web_device=True,
                    on_remove_callback=self.confirm_unpair_camera
                )
                self.camera_widgets.append(widget)
                self.grid.add_widget(widget)
                widget.start_feed(fps=25)
                relay_device.start()
                self._update_grid_columns()

        btn_connect.bind(on_release=on_connect)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def on_back_pressed(self, *args):
        self.manager.current = "role_selector"
