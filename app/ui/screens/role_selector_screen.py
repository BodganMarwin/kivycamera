from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from app.ui.theme import (
    BG_DARK, CARD_BG, CARD_BG_ELEVATED, PRIMARY_BLUE, NAVY_BUTTON,
    WHITE, WHITE_SOFT, WHITE_MUTED, CYAN_ACCENT,
    HEX_WHITE, HEX_WHITE_SOFT, HEX_CYAN, HEX_MUTED,
    RoundedButton, CardLayout, apply_screen_background
)

class RoleSelectorScreen(Screen):
    """
    Pantalla inicial de selección de rol estilo AlfredCamera.
    Diseño refinado en Azul Marino y Blanco con tarjetas independientes.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_DARK)

        main_layout = BoxLayout(
            orientation="vertical",
            padding=[24, 30, 24, 25],
            spacing=16
        )

        # 1. ENCABEZADO Y LOGOTIPO DE MARCA (Estilo AlfredCamera)
        header_box = BoxLayout(orientation="vertical", size_hint_y=0.22, spacing=4)

        lbl_brand = Label(
            text=f"[b][color={HEX_CYAN}]● SENTINEL CAM[/color][/b]",
            markup=True,
            font_size="13sp",
            halign="center",
            valign="middle",
            size_hint_y=0.3
        )
        lbl_brand.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        header_box.add_widget(lbl_brand)

        lbl_title = Label(
            text=f"[b][size=23sp][color={HEX_WHITE}]Seguridad Inteligente[/color][/size][/b]",
            markup=True,
            font_size="23sp",
            halign="center",
            valign="middle",
            size_hint_y=0.42
        )
        lbl_title.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        header_box.add_widget(lbl_title)

        lbl_subtitle = Label(
            text=f"[color={HEX_MUTED}]¿Cómo deseas utilizar este dispositivo?[/color]",
            markup=True,
            font_size="13sp",
            halign="center",
            valign="middle",
            size_hint_y=0.28
        )
        lbl_subtitle.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        header_box.add_widget(lbl_subtitle)

        main_layout.add_widget(header_box)

        # 2. CONTENEDOR DE TARJETAS DE SELECCIÓN
        cards_container = BoxLayout(orientation="vertical", spacing=14, size_hint_y=0.68)

        # TARJETA 1: MODO CÁMARA (TRANSMISOR)
        card_cam = CardLayout(
            orientation="vertical",
            padding=[20, 16, 20, 16],
            spacing=10,
            bg_color=CARD_BG_ELEVATED
        )

        lbl_cam_title = Label(
            text=f"[b][size=16sp][color={HEX_CYAN}]● Dispositivo Cámara[/color][/size][/b]",
            markup=True,
            halign="left",
            size_hint_y=None,
            height=26
        )
        lbl_cam_title.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        card_cam.add_widget(lbl_cam_title)

        lbl_cam_desc = Label(
            text=f"[color={HEX_WHITE_SOFT}]Transforma este teléfono en una cámara de seguridad en vivo. Genera un código de 6 dígitos para monitorear en 4G o WiFi.[/color]",
            markup=True,
            font_size="12sp",
            halign="left",
            valign="top"
        )
        lbl_cam_desc.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        card_cam.add_widget(lbl_cam_desc)

        btn_cam = RoundedButton(
            text="INICIAR MODO CÁMARA",
            font_size="13sp",
            bold=True,
            size_hint_y=None,
            height=46,
            bg_color=PRIMARY_BLUE,
            radius=[12, 12, 12, 12]
        )
        btn_cam.bind(on_release=self.go_to_camera_mode)
        card_cam.add_widget(btn_cam)
        cards_container.add_widget(card_cam)

        # TARJETA 2: MODO VISOR / MONITOR (NVR)
        card_mon = CardLayout(
            orientation="vertical",
            padding=[20, 16, 20, 16],
            spacing=10,
            bg_color=CARD_BG
        )

        lbl_mon_title = Label(
            text=f"[b][size=16sp][color={HEX_WHITE}]● Dispositivo Visor / NVR[/color][/size][/b]",
            markup=True,
            halign="left",
            size_hint_y=None,
            height=26
        )
        lbl_mon_title.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        card_mon.add_widget(lbl_mon_title)

        lbl_mon_desc = Label(
            text=f"[color={HEX_WHITE_SOFT}]Visualiza transmisiones simultáneas, vincula teléfonos por código Alfred o Web QR y detecta cámaras IP ONVIF.[/color]",
            markup=True,
            font_size="12sp",
            halign="left",
            valign="top"
        )
        lbl_mon_desc.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        card_mon.add_widget(lbl_mon_desc)

        btn_mon = RoundedButton(
            text="ABRIR MONITOR DE CÁMARAS",
            font_size="13sp",
            bold=True,
            size_hint_y=None,
            height=46,
            bg_color=NAVY_BUTTON,
            radius=[12, 12, 12, 12]
        )
        btn_mon.bind(on_release=self.go_to_monitor_mode)
        card_mon.add_widget(btn_mon)
        cards_container.add_widget(card_mon)

        main_layout.add_widget(cards_container)

        # 3. PIE DE PÁGINA
        footer = Label(
            text=f"[color={HEX_MUTED}]P2P 4G/5G/WiFi • ONVIF Profile S • RTSP • WebRTC[/color]",
            markup=True,
            font_size="10sp",
            halign="center",
            size_hint_y=0.1
        )
        footer.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        main_layout.add_widget(footer)

        self.add_widget(main_layout)

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
        content = BoxLayout(orientation="vertical", padding=15, spacing=10)
        sv = ScrollView(size_hint=(1, 0.8))
        lbl = Label(
            text=f"[b][color={HEX_WHITE}]{title}[/color][/b]\n\n{error_text}",
            markup=True,
            size_hint_y=None,
            font_size="12sp",
            padding=(10, 10),
            color=WHITE_SOFT
        )
        lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(val[1], 300)))
        sv.add_widget(lbl)
        content.add_widget(sv)

        btn_close = RoundedButton(
            text="Cerrar",
            size_hint_y=None,
            height=40,
            bg_color=PRIMARY_BLUE
        )
        content.add_widget(btn_close)

        popup = Popup(
            title="Aviso del Sistema",
            title_color=WHITE,
            content=content,
            size_hint=(0.9, 0.8),
            background_color=CARD_BG_ELEVATED
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()
