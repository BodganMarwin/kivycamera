import sys
import os
import traceback

# Configurar backend de ventana y logger antes de importar Kivy
os.environ["KIVY_NO_ARGS"] = "1"

# Capturar cualquier excepción no controlada y escribirla a un archivo de diagnóstico
def _global_exception_handler(exctype, value, tb):
    err = "".join(traceback.format_exception(exctype, value, tb))
    print("[CRASH TRACEBACK]:", err)
    try:
        with open("kivy_crash.log", "w", encoding="utf-8") as f:
            f.write(err)
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = _global_exception_handler

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.utils import platform
from kivy.clock import Clock

class KivySentinelApp(App):
    """Aplicación principal Kivy Sentinel."""

    def build(self):
        try:
            self.title = "Kivy Sentinel - Videovigilancia Multiplataforma"

            # Configurar tamaño de ventana en escritorio
            if platform not in ("android", "ios"):
                Window.size = (960, 640)
                Window.minimum_width, Window.minimum_height = (640, 480)

            # Importar pantalla inicial de forma segura
            from app.ui.screens.role_selector_screen import RoleSelectorScreen

            # Gestor de Pantallas: cargamos inicialmente sólo el selector de roles
            # para arranque ultrarrápido y sin sobrecarga en el splash screen.
            sm = ScreenManager(transition=FadeTransition(duration=0.2))
            sm.add_widget(RoleSelectorScreen(name="role_selector"))

            # Solicitar permisos en Android de manera diferida, tras inicializar la ventana y OpenGL
            if platform == "android":
                Clock.schedule_once(self._request_android_permissions, 1.2)

            return sm

        except Exception:
            err = traceback.format_exc()
            print("[Kivy Sentinel] Error durante build():", err)
            try:
                with open("kivy_crash.log", "w", encoding="utf-8") as f:
                    f.write(err)
            except Exception:
                pass

            from kivy.uix.scrollview import ScrollView
            from kivy.uix.label import Label
            sv = ScrollView()
            lbl = Label(
                text=f"[b][color=ff3333]ERROR CRÍTICO AL INICIAR:[/color][/b]\n\n{err}",
                markup=True,
                size_hint_y=None,
                font_size="13sp",
                padding=(20, 20)
            )
            lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(val[1], 400)))
            sv.add_widget(lbl)
            return sv

    def _request_android_permissions(self, dt=None):
        try:
            from android.permissions import request_permissions, Permission
            # Solicitar permisos de tiempo de ejecución válidos (peligrosos)
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO
            ])
        except Exception as e:
            print(f"[Android Permissions] Advertencia: {e}")

    def on_stop(self):
        """Limpieza al cerrar la aplicación."""
        print("[Kivy Sentinel] Cerrando aplicación y liberando recursos...")
        if hasattr(self.root, "current_screen"):
            screen = self.root.current_screen
            if hasattr(screen, "on_leave"):
                screen.on_leave()

if __name__ == "__main__":
    KivySentinelApp().run()
