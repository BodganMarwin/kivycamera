import json
import os
from pathlib import Path
from typing import Dict, List, Any

DEFAULT_CONFIG_PATH = Path("camera_config.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "server": {
        "port": 8080,
        "fps_limit": 25,
        "width": 640,
        "height": 480,
        "camera_index": 0,
        "enable_motion": True
    },
    "cameras": [
        {
            "id": "cam_local",
            "name": "Cámara Local / USB",
            "url": "0",  # "0" for local webcam / camera index
            "type": "local",
            "enabled": True
        }
    ],
    "recordings_dir": "recordings"
}

class ConfigManager:
    """Administra la persistencia de configuraciones de cámaras y servidor."""

    def __init__(self, filepath: Path = DEFAULT_CONFIG_PATH):
        self.filepath = filepath
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Error leyendo {self.filepath}: {e}. Usando valores por defecto.")
                self.config = DEFAULT_SETTINGS.copy()
        else:
            self.config = DEFAULT_SETTINGS.copy()
            self.save()
        return self.config

    def save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error guardando {self.filepath}: {e}")

    def get_cameras(self) -> List[Dict[str, Any]]:
        return self.config.get("cameras", [])

    def add_camera(self, name: str, url: str, cam_type: str = "rtsp") -> Dict[str, Any]:
        cam_id = f"cam_{len(self.config.get('cameras', [])) + 1}"
        new_cam = {
            "id": cam_id,
            "name": name,
            "url": url,
            "type": cam_type,
            "enabled": True
        }
        self.config.setdefault("cameras", []).append(new_cam)
        self.save()
        return new_cam

    def remove_camera(self, cam_id: str) -> None:
        self.config["cameras"] = [c for c in self.config.get("cameras", []) if c.get("id") != cam_id]
        self.save()

    def get_server_config(self) -> Dict[str, Any]:
        return self.config.get("server", DEFAULT_SETTINGS["server"])

    def update_server_config(self, updates: Dict[str, Any]) -> None:
        self.config.setdefault("server", {}).update(updates)
        self.save()
