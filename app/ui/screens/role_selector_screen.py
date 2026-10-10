from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

class RoleSelectorScreen(Screen):
    """Pantalla inicial para seleccionar el rol del dispositivo."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=[30, 40, 30, 40],
            spacing=20
        )

        # Encabezado con ajuste de texto responsivo
        title = Label(
            text="[b]KIVY SENTINEL[/b]\nSistema de Videovigilancia",
            markup=True,
            font_size="22sp",
            halign="center",
            valign="middle",
            size_hint_y=0.22
        )
        title.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 20, None)))
        layout.add_widget(title)

        subtitle = Label(
            text="Selecciona el modo de operación para este dispositivo:",
            font_size="14sp",
            color=(0.8, 0.8, 0.8, 1),
            halign="center",
            valign="middle",
            size_hint_y=0.1
        )
        subtitle.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 20, None)))
        layout.add_widget(subtitle)

        # Botones de selección de rol
        btn_box = BoxLayout(orientation="vertical", spacing=20, size_hint_y=0.58)

        # Opción 1: Modo Cámara Transmisora (Teléfono / Tablet)
        btn_cam = Button(
            text="[ MODO CÁMARA / TRANSMISOR ]\nTransformar este móvil en una cámara de seguridad",
            font_size="15sp",
            background_normal="",
            background_color=(0.15, 0.5, 0.85, 1),
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_cam.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 30, None)))
        btn_cam.bind(on_release=self.go_to_camera_mode)
        btn_box.add_widget(btn_cam)

        # Opción 2: Modo Monitor Central / NVR
        btn_mon = Button(
            text="[ MODO MONITOR / NVR ]\nMonitorear múltiples cámaras y detectar ONVIF en la red",
            font_size="15sp",
            background_normal="",
            background_color=(0.18, 0.65, 0.35, 1),
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_mon.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 30, None)))
        btn_mon.bind(on_release=self.go_to_monitor_mode)
        btn_box.add_widget(btn_mon)

        layout.add_widget(btn_box)

        # Pie
        footer = Label(
            text="Compatible con ONVIF Profile S, RTSP, MJPEG y Webcams",
            font_size="11sp",
            color=(0.5, 0.5, 0.5, 1),
            halign="center",
            size_hint_y=0.1
        )
        footer.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 20, None)))
        layout.add_widget(footer)

        self.add_widget(layout)

    def go_to_camera_mode(self, *args):
        try:
            if not self.manager.has_screen("camera_node"):
                from app.ui.screens.camera_node_screen import CameraNodeScreen
                self.manager.add_widget(CameraNodeScreen(name="camera_node"))
            self.manager.current = "camera_node"
        except Exception as e:
            import traceback
            self._show_error_popup("Error al cargar Modo Cámara", traceback.format_exc())

    def go_to_monitor_mode(self, *args):
        try:
            if not self.manager.has_screen("monitor"):
                from app.ui.screens.monitor_screen import MonitorScreen
                self.manager.add_widget(MonitorScreen(name="monitor"))
            self.manager.current = "monitor"
        except Exception as e:
            import traceback
            self._show_error_popup("Error al cargar Modo Monitor", traceback.format_exc())

    def _show_error_popup(self, title: str, error_text: str):
        from kivy.uix.popup import Popup
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label
        sv = ScrollView()
        lbl = Label(
            text=f"[b][color=ff3333]{title}[/color][/b]\n\n{error_text}",
            markup=True,
            size_hint_y=None,
            font_size="13sp",
            padding=(15, 15)
        )
        lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(val[1], 300)))
        sv.add_widget(lbl)
        popup = Popup(title="Detalle del Error", content=sv, size_hint=(0.9, 0.8))
        popup.open()
