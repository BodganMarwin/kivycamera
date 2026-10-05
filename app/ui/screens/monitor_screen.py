import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
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

class MonitorScreen(Screen):
    """
    Pantalla del modo 'Monitor / NVR'.
    Visualiza simultáneamente múltiples cámaras tradicionales (RTSP/ONVIF),
    dispositivos web (QR) y celulares remotos vinculados por código (AlfredCamera)
    en diferentes redes (WiFi y 4G/5G).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_mgr = ConfigManager()
        self.camera_widgets = []
        self.all_recording = False

        # Iniciar Servidor WebHub para vincular teléfonos vía navegador
        self.web_hub = SentinelWebHub(port=8080, on_device_connected=self._on_mobile_connected)

        self.root_layout = BoxLayout(orientation="vertical", spacing=8, padding=10)

        # Barra de herramientas superior
        toolbar = BoxLayout(size_hint_y=None, height=45, spacing=6)

        btn_back = Button(
            text="◀ Menú",
            size_hint_x=None,
            width=80,
            background_normal="",
            background_color=(0.3, 0.3, 0.3, 1)
        )
        btn_back.bind(on_release=self.on_back_pressed)
        toolbar.add_widget(btn_back)

        # Botón para vincular APK móvil por código (AlfredCamera P2P / 4G / WiFi)
        btn_pair_code = Button(
            text="🔗 Código (Alfred)",
            background_normal="",
            background_color=(0.12, 0.55, 0.75, 1)
        )
        btn_pair_code.bind(on_release=self.show_pair_code_dialog)
        toolbar.add_widget(btn_pair_code)

        # Botón para vincular Smartphone sin instalar nada
        btn_qr = Button(
            text="📱 Web QR",
            background_normal="",
            background_color=(0.15, 0.5, 0.85, 1)
        )
        btn_qr.bind(on_release=self.show_qr_dialog)
        toolbar.add_widget(btn_qr)

        btn_scan_onvif = Button(
            text="🔍 Escanear ONVIF",
            background_normal="",
            background_color=(0.18, 0.5, 0.7, 1)
        )
        btn_scan_onvif.bind(on_release=self.start_onvif_scan)
        toolbar.add_widget(btn_scan_onvif)

        btn_add_cam = Button(
            text="➕ Añadir Cámara",
            background_normal="",
            background_color=(0.2, 0.6, 0.3, 1)
        )
        btn_add_cam.bind(on_release=self.show_add_camera_dialog)
        toolbar.add_widget(btn_add_cam)

        self.btn_rec_all = Button(
            text="🔴 Grabar Todo",
            size_hint_x=0.25,
            background_normal="",
            background_color=(0.7, 0.2, 0.2, 1)
        )
        self.btn_rec_all.bind(on_release=self.toggle_record_all)
        toolbar.add_widget(self.btn_rec_all)

        self.root_layout.add_widget(toolbar)

        # Cuadrícula de cámaras
        self.grid = GridLayout(spacing=8)
        self.root_layout.add_widget(self.grid)

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
        widget = KivyCameraWidget(
            device=web_device,
            is_web_device=True,
            on_remove_callback=self.confirm_unpair_camera
        )
        self.camera_widgets.append(widget)
        self.grid.add_widget(widget)
        widget.start_feed(fps=25)
        self._update_grid_columns()

    def _update_grid_columns(self):
        count = len(self.camera_widgets)
        self.grid.cols = 1 if count <= 1 else (2 if count <= 4 else 3)

    def stop_all_feeds(self):
        for w in self.camera_widgets:
            w.stop_feed()
        self.camera_widgets.clear()
        self.grid.clear_widgets()

    def refresh_cameras(self):
        self.stop_all_feeds()
        cameras = self.config_mgr.get_cameras()

        for cam in cameras:
            if not cam.get("enabled", True):
                continue
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
        """Muestra ventana modal de confirmación para desvincular el dispositivo."""
        cam_name = widget.camera_name
        is_web = widget.is_web_device

        content = BoxLayout(orientation="vertical", padding=15, spacing=15)
        if is_web:
            msg = (
                f"[b]¿Desvincular '{cam_name}'?[/b]\n\n"
                f"Se detendrá la transmisión en vivo, se apagará la cámara del\n"
                f"teléfono y se liberarán los recursos de red."
            )
        else:
            msg = (
                f"[b]¿Quitar '{cam_name}' de la lista?[/b]\n\n"
                f"La cámara será desconectada y eliminada de tu configuración."
            )

        lbl = Label(text=msg, markup=True, halign="center", font_size="13sp")
        content.add_widget(lbl)

        btn_box = BoxLayout(size_hint_y=None, height=45, spacing=12)
        btn_confirm = Button(
            text="Sí, Desvincular" if is_web else "Sí, Quitar",
            background_normal="",
            background_color=(0.85, 0.2, 0.2, 1),
            font_size="13sp"
        )
        btn_cancel = Button(
            text="Cancelar",
            background_normal="",
            background_color=(0.4, 0.4, 0.4, 1),
            font_size="13sp"
        )
        btn_box.add_widget(btn_confirm)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Desvincular Dispositivo" if is_web else "Quitar Cámara",
            content=content,
            size_hint=(0.7, 0.45)
        )

        def do_unpair(*args):
            popup.dismiss()
            self.remove_camera(widget)

        btn_confirm.bind(on_release=do_unpair)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def remove_camera(self, widget):
        """Desvincula y limpia un dispositivo o cámara del sistema."""
        # 1. Si es un móvil web, enviar orden de desconexión y cerrar socket
        if widget.is_web_device and hasattr(widget.device, "device_id"):
            dev_id = widget.device.device_id
            self.web_hub.disconnect_device(dev_id)
        else:
            # 2. Si es una cámara guardada en config, eliminar de la persistencia
            cams = self.config_mgr.get_cameras()
            for c in cams:
                if c.get("name") == widget.camera_name or c.get("url") == getattr(widget.device, "source", None):
                    self.config_mgr.remove_camera(c.get("id"))
                    break

        # 3. Detener renderizado del widget y removerlo del grid
        widget.stop_feed()
        if widget in self.camera_widgets:
            self.camera_widgets.remove(widget)
        self.grid.remove_widget(widget)
        self._update_grid_columns()

    def show_qr_dialog(self, *args):
        """Muestra ventana modal con código QR para conectar el teléfono sin instalar nada."""
        url = f"http://{get_local_ip()}:{self.web_hub.port}/camera"
        qr_path = generate_qr_image(url)

        content = BoxLayout(orientation="vertical", padding=15, spacing=10)

        info_lbl = Label(
            text=f"[b]Vincular Smartphone o Tablet[/b]\n"
                 f"1. Abre la cámara nativa de tu teléfono.\n"
                 f"2. Escanea este código QR o abre en el navegador:\n[color=00ffaa]{url}[/color]\n"
                 f"3. Concede permiso de cámara. ¡Aparecerá aquí al instante!",
            markup=True,
            halign="center",
            font_size="13sp",
            size_hint_y=0.35
        )
        content.add_widget(info_lbl)

        # Imagen QR
        qr_img = Image(source=qr_path, allow_stretch=True, keep_ratio=True, size_hint_y=0.55)
        content.add_widget(qr_img)

        btn_close = Button(
            text="Listo / Cerrar",
            size_hint_y=0.1,
            background_normal="",
            background_color=(0.2, 0.6, 0.3, 1)
        )
        content.add_widget(btn_close)

        popup = Popup(
            title="Conexión Instantánea Móvil (Sin Apps)",
            content=content,
            size_hint=(0.8, 0.85)
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()

    def toggle_record_all(self, *args):
        self.all_recording = not self.all_recording
        if self.all_recording:
            for w in self.camera_widgets:
                w.device.start_recording()
            self.btn_rec_all.text = "⏹ STOP ALL"
            self.btn_rec_all.background_color = (0.9, 0.3, 0.1, 1)
        else:
            for w in self.camera_widgets:
                w.device.stop_recording()
            self.btn_rec_all.text = "🔴 Grabar Todo"
            self.btn_rec_all.background_color = (0.7, 0.2, 0.2, 1)

    def start_onvif_scan(self, *args):
        popup_content = BoxLayout(orientation="vertical", padding=15, spacing=10)
        lbl = Label(text="Buscando cámaras ONVIF en la red local...\n(Multicast UDP 3702)", halign="center")
        popup_content.add_widget(lbl)
        
        popup = Popup(
            title="Escáner ONVIF",
            content=popup_content,
            size_hint=(0.8, 0.6),
            auto_dismiss=False
        )
        popup.open()

        def scan_worker():
            results = discover_onvif_cameras(timeout=3.0)
            Clock.schedule_once(lambda dt: self._display_onvif_results(results, popup), 0)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _display_onvif_results(self, results, popup):
        popup.dismiss()

        content = BoxLayout(orientation="vertical", padding=12, spacing=10)
        if not results:
            content.add_widget(Label(
                text="No se encontraron cámaras ONVIF automáticamente.\nVerifica que estén encendidas en la misma red WiFi.",
                halign="center"
            ))
        else:
            for cam in results:
                row = BoxLayout(size_hint_y=None, height=40, spacing=8)
                row.add_widget(Label(text=f"{cam['name']} ({cam['ip']})", size_hint_x=0.7))
                btn_add = Button(text="Añadir", size_hint_x=0.3)
                btn_add.bind(on_release=lambda btn, c=cam: self._add_discovered_cam(c))
                content.add_widget(row)

        btn_close = Button(text="Cerrar", size_hint_y=None, height=40)
        content.add_widget(btn_close)

        res_popup = Popup(title="Cámaras ONVIF Encontradas", content=content, size_hint=(0.85, 0.7))
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

        content.add_widget(Label(text="Nombre de la Cámara:", size_hint_y=None, height=25))
        txt_name = TextInput(text="Cámara Seguridad", multiline=False, size_hint_y=None, height=35)
        content.add_widget(txt_name)

        content.add_widget(Label(
            text="URL del Stream (RTSP, HTTP-MJPEG o número '0' para webcam):",
            size_hint_y=None,
            height=25
        ))
        txt_url = TextInput(
            text="rtsp://admin:password@192.168.1.50:554/stream1",
            multiline=False,
            size_hint_y=None,
            height=35
        )
        content.add_widget(txt_url)

        btn_box = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_save = Button(text="Guardar", background_color=(0.2, 0.6, 0.3, 1))
        btn_cancel = Button(text="Cancelar", background_color=(0.5, 0.5, 0.5, 1))
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(title="Añadir Nueva Cámara", content=content, size_hint=(0.85, 0.6))

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
        content = BoxLayout(orientation="vertical", padding=15, spacing=12)

        lbl_inst = Label(
            text="[b]Vincular Dispositivo Celular (APK Remoto)[/b]\n"
                 "Introduce el código de 6 dígitos que aparece en la pantalla\n"
                 "del otro dispositivo (funciona en 4G/5G y WiFi cruzado):",
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
            height=45
        )
        content.add_widget(txt_code)

        btn_box = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_connect = Button(
            text="Conectar Cámara",
            background_normal="",
            background_color=(0.12, 0.55, 0.75, 1)
        )
        btn_cancel = Button(
            text="Cancelar",
            background_normal="",
            background_color=(0.4, 0.4, 0.4, 1)
        )
        btn_box.add_widget(btn_connect)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Vinculación AlfredCamera (Cross-Network)",
            content=content,
            size_hint=(0.8, 0.55)
        )

        def on_connect(instance):
            code = txt_code.text.strip()
            if code:
                popup.dismiss()
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
