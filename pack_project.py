import zipfile
from pathlib import Path

def package_project():
    output_zip = Path("kivy_sentinel_project.zip")
    base_dir = Path(".")
    
    exclude_dirs = {".venv", ".git", "__pycache__", ".buildozer", "bin", "recordings"}
    exclude_exts = {".pyc", ".log"}

    print(f"Empaquetando proyecto en {output_zip.name}...")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in base_dir.rglob("*"):
            if file_path.is_file():
                # Comprobar exclusiones
                parts = set(file_path.parts)
                if any(ex in parts for ex in exclude_dirs):
                    continue
                if file_path.suffix in exclude_exts:
                    continue
                if file_path == output_zip:
                    continue

                rel_path = file_path.relative_to(base_dir)
                zf.write(file_path, arcname=str(rel_path))

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"Proyecto empaquetado con éxito: {output_zip.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    package_project()
