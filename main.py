import sys
import os

# Configurar backend de ventana y logger antes de importar Kivy
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.utils import platform

from app.ui.screens.role_selector_screen import RoleSelectorScreen
from app.ui.screens.camera_node_screen import CameraNodeScreen
from app.ui.screens.monitor_screen import MonitorScreen

class KivySentinelApp(App):
    """Aplicación principal Kivy Sentinel."""

    def build(self):
        self.title = "Kivy Sentinel - Videovigilancia Multiplataforma"

        # Configurar tamaño de ventana cómodo si se ejecuta en escritorio
        if platform not in ("android", "ios"):
            Window.size = (960, 640)
            Window.minimum_width, Window.minimum_height = (640, 480)

        # Gestor de Pantallas con transiciones suaves
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(RoleSelectorScreen(name="role_selector"))
        sm.add_widget(CameraNodeScreen(name="camera_node"))
        sm.add_widget(MonitorScreen(name="monitor"))

        # Solicitar permisos en Android si se está ejecutando en el móvil
        if platform == "android":
            self._request_android_permissions()

        return sm

    def _request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.WAKE_LOCK
            ])
        except Exception as e:
            print(f"[Android Permissions] Advertencia: {e}")

    def on_stop(self):
        """Limpieza al cerrar la aplicación."""
        print("[Kivy Sentinel] Cerrando aplicación y liberando recursos...")
        # Asegurarse de detener hilos y cámaras activas
        if hasattr(self.root, "current_screen"):
            screen = self.root.current_screen
            if hasattr(screen, "on_leave"):
                screen.on_leave()

if __name__ == "__main__":
    KivySentinelApp().run()
