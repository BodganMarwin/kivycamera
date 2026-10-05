#!/bin/bash
# Script de compilación automática para Google Colab (compatible con Ubuntu 22.04 y 24.04 Noble)
set -e

echo "=== 1. Instalando herramientas de compilación Linux ==="
sudo apt-get update -qq || true

# Instalar paquetes universales compatibles con Ubuntu 22.04 y 24.04 Noble
sudo apt-get install -y -qq \
  build-essential git ffmpeg libsm6 libxext6 \
  libncurses-dev libtinfo-dev \
  cmake libffi-dev libssl-dev zip unzip autoconf \
  libtool pkg-config zlib1g-dev ccache libltdl-dev openjdk-17-jdk

# Enlace simbólico de compatibilidad para herramientas que busquen libtinfo5
sudo ln -sf /usr/lib/x86_64-linux-gnu/libtinfo.so.6 /usr/lib/x86_64-linux-gnu/libtinfo.so.5 2>/dev/null || true
sudo ln -sf /usr/lib/x86_64-linux-gnu/libncurses.so.6 /usr/lib/x86_64-linux-gnu/libncurses.so.5 2>/dev/null || true

echo "=== 2. Instalando Buildozer y Cython compatible ==="
pip install --upgrade pip
pip install "cython<3.0" buildozer

echo "=== 3. Compilando APK Android ==="
# Compilar en modo debug
buildozer -v android debug

echo "=== ¡COMPILACIÓN COMPLETADA CON ÉXITO! ==="
ls -lh bin/*.apk
