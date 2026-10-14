"""
Módulo de tema visual para Kivy Sentinel (Estilo AlfredCamera).
Paleta elegante en Azul Marino y Blanco con contrastes de alta visibilidad.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import ListProperty

# ==========================================
# PALETA DE COLORES (RGBA 0.0 - 1.0)
# ==========================================

# Fondos principales (Azul Marino Profundo)
BG_DARK = (0.039, 0.067, 0.118, 1.0)        # #0A111E - Fondo oscuro principal
BG_NAVY = (0.055, 0.098, 0.165, 1.0)        # #0E192A - Barra superior / Menú
BG_OVERLAY = (0.02, 0.04, 0.08, 0.95)       # Fondo translúcido / Ahorro

# Superficies y Tarjetas (Mid Navy)
CARD_BG = (0.086, 0.149, 0.243, 1.0)        # #16263E - Fondo de tarjetas
CARD_BG_ELEVATED = (0.118, 0.196, 0.314, 1.0) # #1E3250 - Tarjetas destacadas / Modales
CARD_BORDER = (0.173, 0.278, 0.431, 1.0)    # #2C476E - Bordes sutiles

# Acentos primarios (Azul Eléctrico / Cyan Alfred)
PRIMARY_BLUE = (0.0, 0.518, 1.0, 1.0)       # #0084FF - Botones de acción principales
PRIMARY_BLUE_DARK = (0.0, 0.392, 0.784, 1.0)# #0064C8 - Estado presionado
CYAN_ACCENT = (0.0, 0.851, 1.0, 1.0)        # #00D9FF - Códigos, badges y detalles

# Blanco y Neutros (Tipografía y Contrastes)
WHITE = (1.0, 1.0, 1.0, 1.0)                # #FFFFFF - Títulos y textos principales
WHITE_SOFT = (0.922, 0.941, 0.969, 1.0)     # #EBF0F7 - Textos secundarios
WHITE_MUTED = (0.620, 0.698, 0.792, 1.0)    # #9EB2CA - Textos sutiles, notas
NAVY_BUTTON = (0.118, 0.204, 0.337, 1.0)    # #1E3456 - Botones secundarios azul marino

# Estados y Alertas
GREEN_LIVE = (0.063, 0.761, 0.471, 1.0)     # #10C278 - EN VIVO / Online
RED_ALERT = (0.937, 0.259, 0.259, 1.0)      # #EF4242 - REC / Desvincular / Peligro
AMBER_WARN = (0.961, 0.620, 0.051, 1.0)     # #F59E0D - Movimiento / Conectando
PURPLE_SIREN = (0.545, 0.361, 0.965, 1.0)   # #8B5CF6 - Sirena disuasoria

# ==========================================
# CÓDIGOS HEX PARA MARKUP [color=HEX]...[/color]
# ==========================================
HEX_WHITE = "ffffff"
HEX_WHITE_SOFT = "ebf0f7"
HEX_MUTED = "9eb2ca"
HEX_BLUE = "0084ff"
HEX_CYAN = "00d9ff"
HEX_GREEN = "10c278"
HEX_RED = "ef4242"
HEX_AMBER = "f59e0d"
HEX_PURPLE = "8b5cf6"


# ==========================================
# COMPONENTES VISUALES REUTILIZABLES
# ==========================================

class RoundedButton(Button):
    """Botón moderno con esquinas redondeadas y feedback visual al pulsar."""
    bg_color = ListProperty([0.0, 0.518, 1.0, 1.0])
    radius = ListProperty([10, 10, 10, 10])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = WHITE
        self.font_size = kwargs.get("font_size", "14sp")

        with self.canvas.before:
            self._color_instr = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

        self.bind(pos=self._update_rect, size=self._update_rect, state=self._update_state)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_state(self, *args):
        if self.state == "down":
            self._color_instr.rgba = [
                max(0.0, c * 0.78) for c in self.bg_color[:3]
            ] + [self.bg_color[3] if len(self.bg_color) > 3 else 1.0]
        else:
            self._color_instr.rgba = self.bg_color

    def on_bg_color(self, inst, val):
        if hasattr(self, "_color_instr"):
            self._color_instr.rgba = val


class CardLayout(BoxLayout):
    """Contenedor estilo tarjeta redondeada en azul marino."""
    bg_color = ListProperty([0.086, 0.149, 0.243, 1.0])
    radius = ListProperty([14, 14, 14, 14])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color_instr = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def on_bg_color(self, inst, val):
        if hasattr(self, "_color_instr"):
            self._color_instr.rgba = val


def apply_screen_background(screen, bg_color=BG_DARK):
    """Aplica un fondo sólido de pantalla completa a cualquier Screen."""
    with screen.canvas.before:
        Color(*bg_color)
        rect = Rectangle(pos=screen.pos, size=screen.size)

    def _update(inst, val):
        rect.pos = inst.pos
        rect.size = inst.size

    screen.bind(pos=_update, size=_update)
