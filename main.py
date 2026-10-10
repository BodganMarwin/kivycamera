import sys
import os
import traceback

# Configurar backend de ventana y logger antes de importar Kivy
os.environ["KIVY_NO_ARGS"] = "1"

# Capturar y registrar diagnóstico en múltiples rutas de almacenamiento accesibles en Android
def log_diagnostic(msg: str):
    print(f"[SENTINEL DIAG]: {msg}", flush=True)
    paths = [
        "/storage/emulated/0/Download/kivy_crash.log",
        "/sdcard/Download/kivy_crash.log",
        "/storage/emulated/0/Android/data/org.sentinel.kivysentinel/files/kivy_crash.log",
        "kivy_crash.log"
    ]
    for p in paths:
        try:
            d = os.path.dirname(p)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

log_diagnostic("=== KIVY SENTINEL: INICIO DE MAIN.PY ===")

def _global_exception_handler(exctype, value, tb):
    err = "".join(traceback.format_exception(exctype, value, tb))
    log_diagnostic(f"[CRASH TRACEBACK NO CONTROLADO]:\n{err}")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = _global_exception_handler

try:
    log_diagnostic("Importando modulos base de Kivy...")
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager, FadeTransition
    from kivy.utils import platform
    from kivy.clock import Clock
    log_diagnostic("Modulos base de Kivy importados correctamente.")
except Exception:
    err = traceback.format_exc()
    log_diagnostic(f"ERROR CRITICO AL IMPORTAR KIVY:\n{err}")
    raise

class KivySentinelApp(App):
    """Aplicación principal Kivy Sentinel."""

    def build(self):
        log_diagnostic("Iniciando KivySentinelApp.build()...")
        try:
            self.title = "Kivy Sentinel - Videovigilancia Multiplataforma"

            # Configurar tamaño de ventana en escritorio de forma diferida
            if platform not in ("android", "ios"):
                from kivy.core.window import Window
                Window.size = (960, 640)
                Window.minimum_width, Window.minimum_height = (640, 480)

            # Importar pantalla inicial de forma segura
            log_diagnostic("Cargando RoleSelectorScreen...")
            from app.ui.screens.role_selector_screen import RoleSelectorScreen

            # Gestor de Pantallas: cargamos inicialmente sólo el selector de roles
            # para arranque ultrarrápido y sin sobrecarga en el splash screen.
            sm = ScreenManager(transition=FadeTransition(duration=0.2))
            sm.add_widget(RoleSelectorScreen(name="role_selector"))
            log_diagnostic("RoleSelectorScreen anadido al ScreenManager.")

            # Solicitar permisos en Android de manera diferida, tras inicializar la ventana y OpenGL
            if platform == "android":
                Clock.schedule_once(self._request_android_permissions, 1.5)

            log_diagnostic("KivySentinelApp.build() completado con exito.")
            return sm

        except Exception:
            err = traceback.format_exc()
            log_diagnostic(f"ERROR DURANTE build():\n{err}")

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
    try:
        log_diagnostic("Llamando a KivySentinelApp().run()...")
        KivySentinelApp().run()
        log_diagnostic("KivySentinelApp ha finalizado normalmente.")
    except Exception:
        err = traceback.format_exc()
        log_diagnostic(f"CRASH FATAL EN App.run():\n{err}")
        raise
