import asyncio
import io
import json
import socket
import threading
import time
from typing import Dict, Any, Optional, Callable
import cv2
import numpy as np
try:
    from aiohttp import web, WSMsgType
    AIOHTTP_AVAILABLE = True
except ImportError:
    web = None
    WSMsgType = None
    AIOHTTP_AVAILABLE = False

from app.core.motion_detector import MotionDetector

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Plantilla HTML5 Mobile Web App para el dispositivo móvil (Sin Apps de terceros)
MOBILE_CAMERA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0">
    <title>Sentinel Mobile Cam</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0A111E;
            color: #FFFFFF;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        #video-container {
            position: relative;
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #050B14;
        }
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        #hud {
            position: absolute;
            top: 15px;
            left: 15px;
            right: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }
        .badge {
            background: rgba(16, 194, 120, 0.9);
            color: #ffffff;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }
        .dot { width: 8px; height: 8px; background: #fff; border-radius: 50%; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .controls {
            position: absolute;
            bottom: 25px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            gap: 12px;
            padding: 0 15px;
            z-index: 10;
        }
        .btn {
            background: rgba(22, 38, 62, 0.9);
            border: 1px solid rgba(0, 132, 255, 0.4);
            color: #FFFFFF;
            padding: 12px 18px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            backdrop-filter: blur(10px);
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: all 0.2s ease;
        }
        .btn:active { background: #0084FF; border-color: #0084FF; }
        #powersave-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: #02060D;
            z-index: 999;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: #9EB2CA;
            font-size: 14px;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div id="video-container">
        <div id="hud">
            <div class="badge"><div class="dot"></div> EN VIVO</div>
            <div id="fps" style="background: rgba(0,0,0,0.6); padding: 4px 8px; border-radius: 6px; font-size: 12px;">0 FPS</div>
        </div>
        <video id="webcam" autoplay playsinline muted></video>
        <canvas id="captureCanvas" style="display:none;"></canvas>

        <div class="controls">
            <button class="btn" id="btnSwitch">🔄 Lente</button>
            <button class="btn" id="btnTorch">🔦 Linterna</button>
            <button class="btn" id="btnSaver">🌙 Pantalla Negra</button>
        </div>
    </div>

    <div id="powersave-overlay">
        <p style="font-size: 24px; color: #666; margin-bottom: 10px;">🔒 MODO AHORRO ACTIVO</p>
        <p>Vigilancia en segundo plano.<br>Toca dos veces la pantalla para desbloquear.</p>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('captureCanvas');
        const ctx = canvas.getContext('2d');
        const fpsLabel = document.getElementById('fps');
        const btnSwitch = document.getElementById('btnSwitch');
        const btnTorch = document.getElementById('btnTorch');
        const btnSaver = document.getElementById('btnSaver');
        const overlay = document.getElementById('powersave-overlay');

        let currentStream = null;
        let currentFacingMode = 'environment'; // trasera por defecto
        let torchActive = false;
        let ws = null;
        let frameCount = 0;
        let lastFpsCheck = performance.now();
        let wakeLock = null;

        // Mantener pantalla encendida
        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            } catch (err) {
                console.warn('Wake Lock no disponible:', err);
            }
        }

        async function initCamera() {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }

            try {
                const constraints = {
                    video: {
                        facingMode: { ideal: currentFacingMode },
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    },
                    audio: false
                };
                currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = currentStream;
                await video.play();
                requestWakeLock();
            } catch (e) {
                alert('Error accediendo a la cámara: ' + e.message + '\\nAsegúrate de otorgar permisos de cámara.');
            }
        }

        // Conectar WebSocket con el servidor Sentinel en el PC
        function connectWebSocket() {
            const loc = window.location;
            const wsUri = (loc.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + loc.host + '/ws/camera';
            ws = new WebSocket(wsUri);

            ws.onopen = () => {
                console.log('Conectado a Sentinel Server');
                startStreaming();
            };

            ws.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleRemoteCommand(data);
                } catch(e) {}
            };

            ws.onclose = () => {
                if (!window.isDisconnectedByServer) {
                    setTimeout(connectWebSocket, 2000);
                }
            };
        }

        // Ejecutar comandos remotos enviados desde el Monitor Central
        async function handleRemoteCommand(data) {
            if (data.cmd === 'disconnect') {
                window.isDisconnectedByServer = true;
                if (currentStream) {
                    currentStream.getTracks().forEach(track => track.stop());
                }
                if (ws) {
                    ws.close();
                }
                document.body.innerHTML = `
                    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:25px;text-align:center;background:#121212;">
                        <div style="font-size:48px;margin-bottom:15px;">🔌</div>
                        <h2 style="color:#e53935;margin-bottom:12px;font-size:22px;">Dispositivo Desvinculado</h2>
                        <p style="color:#aaa;margin-bottom:25px;font-size:15px;line-height:1.5;">Esta cámara ha sido desvinculada desde el monitor central.<br>La captura de video y linterna se han apagado.</p>
                        <button onclick="location.reload()" style="background:#1e88e5;color:#fff;border:none;padding:12px 28px;border-radius:25px;font-size:15px;font-weight:bold;cursor:pointer;">Volver a Conectar</button>
                    </div>
                `;
            } else if (data.cmd === 'toggle_torch') {
                toggleTorch();
            } else if (data.cmd === 'switch_cam') {
                currentFacingMode = (currentFacingMode === 'environment' ? 'user' : 'environment');
                await initCamera();
            } else if (data.cmd === 'siren') {
                playSirenAlarm(data.duration || 5);
            }
        }

        // Sirena disuasoria generada en el móvil
        function playSirenAlarm(durationSec = 5) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctxAudio = new AudioCtx();
            const osc = ctxAudio.createOscillator();
            const gain = ctxAudio.createGain();
            osc.type = 'sawtooth';
            osc.connect(gain);
            gain.connect(ctxAudio.destination);
            gain.gain.value = 0.8;
            osc.start();

            const start = ctxAudio.currentTime;
            for (let i = 0; i < durationSec * 2; i++) {
                osc.frequency.setValueAtTime(650, start + i * 0.5);
                osc.frequency.linearRampToValueAtTime(1400, start + (i + 1) * 0.5);
            }
            setTimeout(() => {
                osc.stop();
                ctxAudio.close();
            }, durationSec * 1000);
        }

        async function toggleTorch() {
            if (!currentStream) return;
            const track = currentStream.getVideoTracks()[0];
            const caps = track.getCapabilities ? track.getCapabilities() : {};
            if (caps.torch) {
                torchActive = !torchActive;
                await track.applyConstraints({ advanced: [{ torch: torchActive }] });
            } else {
                console.warn('La linterna no está disponible en este lente.');
            }
        }

        function startStreaming() {
            const sendFrame = () => {
                if (video.videoWidth > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    canvas.width = 640;
                    canvas.height = 480;
                    ctx.drawImage(video, 0, 0, 640, 480);
                    
                    canvas.toBlob((blob) => {
                        if (blob && ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(blob);
                            frameCount++;
                            const now = performance.now();
                            if (now - lastFpsCheck >= 1000) {
                                fpsLabel.innerText = frameCount + ' FPS';
                                frameCount = 0;
                                lastFpsCheck = now;
                            }
                        }
                    }, 'image/jpeg', 0.65);
                }
                setTimeout(sendFrame, 40); // ~25 FPS
            };
            sendFrame();
        }

        btnSwitch.onclick = async () => {
            currentFacingMode = (currentFacingMode === 'environment' ? 'user' : 'environment');
            await initCamera();
        };
        btnTorch.onclick = toggleTorch;

        btnSaver.onclick = () => { overlay.style.display = 'flex'; };
        let lastTap = 0;
        overlay.onclick = () => {
            const now = new Date().getTime();
            if (now - lastTap < 400) {
                overlay.style.display = 'none';
            }
            lastTap = now;
        };

        window.onload = async () => {
            await initCamera();
            connectWebSocket();
        };
    </script>
</body>
</html>
"""

# Plantilla HTML5 para el Monitor Central / Dashboard Web (Estilo AlfredCamera en Azul Marino y Blanco)
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kivy Sentinel - AlfredCamera Web Hub</title>
    <style>
        :root {
            --bg-dark: #0A111E;
            --bg-nav: #0E1A2D;
            --bg-card: #15253D;
            --border: #223B5F;
            --primary: #0084FF;
            --primary-hover: #006CD6;
            --cyan: #00D9FF;
            --text-main: #FFFFFF;
            --text-soft: #EBF0F7;
            --text-muted: #9EB2CA;
            --green: #10C278;
            --red: #EF4242;
            --amber: #F59E0D;
            --purple: #8B5CF6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: var(--bg-nav);
            border-bottom: 1px solid var(--border);
            padding: 14px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-icon {
            font-size: 26px;
        }
        .brand-title h1 {
            font-size: 19px;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.3px;
        }
        .brand-title p {
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 500;
        }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-live {
            background: rgba(16, 194, 120, 0.15);
            color: var(--green);
            border: 1px solid rgba(16, 194, 120, 0.35);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .pulse-dot {
            width: 7px;
            height: 7px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.3); } }
        .btn {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 9px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            text-decoration: none;
        }
        .btn:hover { background: var(--primary-hover); }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border);
            color: var(--text-soft);
        }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.14); }
        .btn-red { background: var(--red); }
        .btn-red:hover { background: #d32f2f; }
        
        main {
            flex: 1;
            padding: 24px;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .toolbar-stats {
            display: flex;
            gap: 18px;
            font-size: 13px;
            color: var(--text-muted);
        }
        .toolbar-stats strong { color: var(--text-main); }
        
        .camera-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
        }
        .cam-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease, border-color 0.2s ease;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }
        .cam-card:hover {
            border-color: rgba(0, 132, 255, 0.5);
        }
        .cam-card.motion-active {
            border-color: var(--amber);
            box-shadow: 0 0 16px rgba(245, 158, 13, 0.3);
        }
        .cam-header {
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .cam-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cam-fps {
            font-size: 12px;
            color: var(--text-muted);
            background: rgba(0, 0, 0, 0.35);
            padding: 3px 8px;
            border-radius: 6px;
        }
        .motion-pill {
            background: var(--amber);
            color: #000;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
            animation: pulse 1s infinite;
        }
        .video-box {
            position: relative;
            background: #02060D;
            width: 100%;
            height: 280px;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        .video-box img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .cam-controls {
            padding: 10px 14px;
            display: flex;
            gap: 8px;
            background: rgba(0, 0, 0, 0.2);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            flex-wrap: wrap;
        }
        .cam-controls .btn {
            font-size: 12px;
            padding: 7px 11px;
            border-radius: 6px;
        }

        /* Empty state */
        .empty-hero {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 40px 24px;
            text-align: center;
            max-width: 620px;
            margin: 40px auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        .empty-hero h2 {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 12px;
        }
        .empty-hero p {
            font-size: 14px;
            color: var(--text-soft);
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .qr-card {
            background: #fff;
            padding: 14px;
            border-radius: 12px;
            display: inline-block;
            margin-bottom: 20px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3);
        }
        .qr-card img {
            width: 200px;
            height: 200px;
            display: block;
        }
        .url-box {
            background: rgba(0,0,0,0.35);
            border: 1px solid var(--border);
            padding: 10px 16px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            color: var(--cyan);
            margin-bottom: 24px;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(4, 8, 15, 0.85);
            backdrop-filter: blur(8px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 999;
        }
        .modal {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            max-width: 480px;
            width: 90%;
            text-align: center;
            box-shadow: 0 16px 48px rgba(0,0,0,0.6);
        }
        .modal h3 { font-size: 18px; margin-bottom: 8px; color: var(--text-main); }
        .modal p { font-size: 13px; color: var(--text-muted); margin-bottom: 18px; }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--primary);
            color: #fff;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5);
            display: none;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span class="brand-icon">🛡️</span>
            <div class="brand-title">
                <h1>KIVY SENTINEL</h1>
                <p>AlfredCamera Web Hub</p>
            </div>
        </div>
        <div class="header-actions">
            <div class="badge-live"><div class="pulse-dot"></div> EN LÍNEA</div>
            <button class="btn btn-secondary" onclick="openQrModal()">📱 Vincular Móvil</button>
            <a href="/camera" target="_blank" class="btn">📷 Transmisor Web</a>
        </div>
    </header>

    <main>
        <div class="toolbar">
            <div class="toolbar-stats">
                <div>Cámaras en vivo: <strong id="cam-count">0</strong></div>
                <div>IP Local: <strong id="local-ip">--</strong></div>
                <div>Puerto: <strong id="local-port">--</strong></div>
            </div>
            <div>
                <button class="btn btn-secondary" onclick="loadDevices()">🔄 Actualizar</button>
            </div>
        </div>

        <div id="camera-container"></div>
    </main>

    <div class="modal-overlay" id="qr-modal" onclick="closeQrModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <h3>Vincular Teléfono o Tablet</h3>
            <p>Escanea este código QR con la cámara de tu smartphone para transmitir video en vivo sin instalar nada.</p>
            <div class="qr-card">
                <img src="/qr" alt="Código QR">
            </div>
            <div class="url-box" id="modal-url">http://...</div>
            <div style="display:flex; justify-content:center; gap:10px;">
                <button class="btn" onclick="copyUrl()">Copiar Enlace</button>
                <button class="btn btn-secondary" onclick="closeQrModal()">Cerrar</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const container = document.getElementById('camera-container');
        const camCountEl = document.getElementById('cam-count');
        const localIpEl = document.getElementById('local-ip');
        const localPortEl = document.getElementById('local-port');
        const modalUrlEl = document.getElementById('modal-url');

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2500);
        }

        function openQrModal() {
            document.getElementById('qr-modal').style.display = 'flex';
        }
        function closeQrModal() {
            document.getElementById('qr-modal').style.display = 'none';
        }
        function copyUrl() {
            const url = modalUrlEl.innerText;
            navigator.clipboard.writeText(url).then(() => showToast('¡Enlace copiado al portapapeles!'));
        }

        async function triggerAction(action, devId) {
            try {
                const res = await fetch(`/api/${action}/${devId}`);
                const data = await res.json();
                showToast(data.message || 'Comando enviado');
            } catch (e) {
                showToast('Error ejecutando comando');
            }
        }

        async function loadDevices() {
            try {
                const res = await fetch('/api/devices');
                const data = await res.json();
                
                localIpEl.innerText = data.local_ip;
                localPortEl.innerText = data.port;
                modalUrlEl.innerText = `http://${data.local_ip}:${data.port}/camera`;
                camCountEl.innerText = data.devices.length;

                renderDevices(data.devices, data.local_ip, data.port);
            } catch (e) {
                console.error('Error cargando dispositivos:', e);
            }
        }

        function renderDevices(devices, ip, port) {
            if (devices.length === 0) {
                container.innerHTML = `
                    <div class="empty-hero">
                        <h2>No hay cámaras conectadas actualmente</h2>
                        <p>Convierte cualquier smartphone (Android / iPhone) o tablet en una cámara de vigilancia en segundos sin instalar ninguna aplicación:</p>
                        <div class="qr-card">
                            <img src="/qr" alt="QR Cámara">
                        </div>
                        <div style="margin-bottom: 20px;">
                            <div class="url-box">http://${ip}:${port}/camera</div>
                        </div>
                        <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
                            <a href="/camera" target="_blank" class="btn">📷 Iniciar Transmisor en este Navegador</a>
                            <button class="btn btn-secondary" onclick="openQrModal()">📱 Instrucciones Móvil</button>
                        </div>
                    </div>
                `;
                return;
            }

            let html = '<div class="camera-grid">';
            devices.forEach(dev => {
                const motionClass = dev.motion ? 'motion-active' : '';
                const motionPill = dev.motion ? '<span class="motion-pill">⚠️ MOVIMIENTO</span>' : '';
                html += `
                    <div class="cam-card ${motionClass}">
                        <div class="cam-header">
                            <div class="cam-title">
                                <span>📹</span>
                                <span>${dev.name}</span>
                                ${motionPill}
                            </div>
                            <div class="cam-fps">${dev.fps} FPS</div>
                        </div>
                        <div class="video-box">
                            <img src="/stream/${dev.id}" alt="${dev.name}">
                        </div>
                        <div class="cam-controls">
                            <button class="btn btn-secondary" onclick="triggerAction('torch', '${dev.id}')">🔦 Linterna</button>
                            <button class="btn btn-secondary" onclick="triggerAction('switch', '${dev.id}')">🔄 Lente</button>
                            <button class="btn btn-secondary" onclick="triggerAction('siren', '${dev.id}')">🚨 Sirena</button>
                            <a href="/api/snapshot/${dev.id}" target="_blank" class="btn btn-secondary">📸 Captura</a>
                            <button class="btn btn-red" onclick="triggerAction('disconnect', '${dev.id}')">🔌 Desvincular</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }

        loadDevices();
        setInterval(loadDevices, 2500);
    </script>
</body>
</html>
"""

class WebCameraDevice:
    """Representa un dispositivo móvil conectado a través del navegador web."""

    def __init__(self, device_id: str, ws: Any = None):
        self.device_id = device_id
        self.name = f"Móvil {device_id[:4]}"
        self.ws = ws
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.motion_active = False
        self.fps = 0.0
        self.connected = True
        self.detector = MotionDetector(min_area=1000)
        self._lock = threading.Lock()
        self._frame_count = 0
        self._start_time = time.time()

        # Grabación local
        self._recording = False
        self._video_writer = None

    def update_raw_image(self, image_bytes: bytes) -> None:
        """Decodifica el JPEG recibido por WebSocket desde el navegador del móvil."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        has_motion, boxes, annotated = self.detector.process_frame(frame)

        with self._lock:
            self.latest_frame = frame
            self.latest_annotated_frame = annotated
            self.motion_active = has_motion

            if self._recording and self._video_writer:
                try:
                    self._video_writer.write(frame)
                except Exception:
                    pass

        self._frame_count += 1
        elapsed = time.time() - self._start_time
        if elapsed >= 1.0:
            self.fps = round(self._frame_count / elapsed, 1)
            self._frame_count = 0
            self._start_time = time.time()

    def get_frame(self, draw_annotations: bool = True) -> Optional[np.ndarray]:
        with self._lock:
            if draw_annotations and self.latest_annotated_frame is not None:
                return self.latest_annotated_frame.copy()
            elif self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def send_remote_command(self, cmd_dict: Dict[str, Any]) -> None:
        """Envía un comando al teléfono (ej: linterna, sirena, cambiar cámara)."""
        if self.ws and not self.ws.closed:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_str(json.dumps(cmd_dict)),
                self.ws._loop
            )

    def start_recording(self, output_dir: str = "recordings") -> None:
        with self._lock:
            if self._recording or self.latest_frame is None:
                return
            h, w = self.latest_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"{output_dir}/rec_{self.name}_{ts}.mp4"
            self._video_writer = cv2.VideoWriter(path, fourcc, 20, (w, h))
            self._recording = True

    def stop_recording(self) -> None:
        with self._lock:
            self._recording = False
            if self._video_writer:
                self._video_writer.release()
                self._video_writer = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def disconnect(self) -> None:
        """Desvincula y apaga la cámara remota del teléfono."""
        self.send_remote_command({"cmd": "disconnect"})
        self.stop_recording()
        self.connected = False
        if self.ws and not self.ws.closed:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.ws._loop)


class SentinelWebHub:
    """
    Servidor Web y WebSocket centralizado para:
    1. Servir la aplicación web a los móviles (sin instalar apps).
    2. Recibir los fotogramas de video en tiempo real.
    3. Enviar comandos remotos (Linterna, Sirena, Cambio de Cámara).
    """

    def __init__(self, port: int = 8080, on_device_connected: Optional[Callable[[WebCameraDevice], None]] = None):
        self.port = port
        self.on_device_connected = on_device_connected
        self.devices: Dict[str, WebCameraDevice] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._runner: Optional[Any] = None
        self.is_running = False

    def start(self) -> str:
        if not AIOHTTP_AVAILABLE:
            print("[SentinelWebHub] aiohttp no está disponible en este entorno.")
            return ""

        if self.is_running:
            return f"http://{get_local_ip()}:{self.port}/"

        self.is_running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

        local_ip = get_local_ip()
        return f"http://{local_ip}:{self.port}/"

    def _run_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        app = web.Application()
        app.router.add_get('/', self._handle_dashboard_page)
        app.router.add_get('/monitor', self._handle_dashboard_page)
        app.router.add_get('/camera', self._handle_camera_page)
        app.router.add_get('/ws/camera', self._handle_camera_ws)
        app.router.add_get('/stream/{device_id}', self._handle_device_stream)
        app.router.add_get('/qr', self._handle_qr_code)
        app.router.add_get('/api/devices', self._handle_api_devices)
        app.router.add_get('/api/siren/{device_id}', self._handle_api_siren)
        app.router.add_get('/api/torch/{device_id}', self._handle_api_torch)
        app.router.add_get('/api/switch/{device_id}', self._handle_api_switch)
        app.router.add_get('/api/disconnect/{device_id}', self._handle_api_disconnect)
        app.router.add_get('/api/snapshot/{device_id}', self._handle_api_snapshot)

        self._runner = web.AppRunner(app)
        self._loop.run_until_complete(self._runner.setup())
        site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        self._loop.run_until_complete(site.start())
        print(f"[SentinelWebHub] Servidor activo en http://0.0.0.0:{self.port}")
        self._loop.run_forever()

    async def _handle_dashboard_page(self, request):
        return web.Response(text=DASHBOARD_HTML, content_type='text/html')

    async def _handle_qr_code(self, request):
        from app.core.qr_helper import generate_qr_image
        url = f"http://{get_local_ip()}:{self.port}/camera"
        qr_file = generate_qr_image(url)
        return web.FileResponse(qr_file)

    async def _handle_api_devices(self, request):
        dev_list = []
        for dev_id, dev in list(self.devices.items()):
            dev_list.append({
                "id": dev_id,
                "name": dev.name,
                "fps": dev.fps,
                "motion": dev.motion_active,
                "is_recording": dev.is_recording,
                "stream_url": f"/stream/{dev_id}"
            })
        return web.json_response({
            "devices": dev_list,
            "local_ip": get_local_ip(),
            "port": self.port
        })

    async def _handle_device_stream(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if not dev:
            return web.Response(text="Dispositivo no encontrado", status=404)

        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Connection': 'close',
            }
        )
        await response.prepare(request)

        try:
            while dev.connected and self.is_running:
                frame = dev.get_frame(draw_annotations=True)
                if frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                    if ret:
                        await response.write(
                            b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                        )
                await asyncio.sleep(0.04) # ~25 FPS
        except (asyncio.CancelledError, ConnectionResetError, Exception):
            pass

        return response

    async def _handle_camera_page(self, request):
        return web.Response(text=MOBILE_CAMERA_HTML, content_type='text/html')

    async def _handle_camera_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        import uuid
        device_id = str(uuid.uuid4())[:8]
        device = WebCameraDevice(device_id=device_id, ws=ws)
        self.devices[device_id] = device
        print(f"[SentinelWebHub] Nuevo dispositivo móvil conectado: {device.name} ({device_id})")

        if self.on_device_connected:
            self.on_device_connected(device)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    device.update_raw_image(msg.data)
                elif msg.type == WSMsgType.TEXT:
                    pass
                elif msg.type == WSMsgType.ERROR:
                    break
        finally:
            device.connected = False
            if device_id in self.devices:
                del self.devices[device_id]
            print(f"[SentinelWebHub] Dispositivo móvil desconectado: {device_id}")

        return ws

    async def _handle_api_siren(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "siren", "duration": 5})
            return web.json_response({"status": "ok", "message": "Sirena activada"})
        return web.json_response({"status": "error", "message": "Dispositivo no encontrado"}, status=404)

    async def _handle_api_torch(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "toggle_torch"})
            return web.json_response({"status": "ok", "message": "Linterna conmutada"})
        return web.json_response({"status": "error", "message": "Dispositivo no encontrado"}, status=404)

    async def _handle_api_switch(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "switch_cam"})
            return web.json_response({"status": "ok", "message": "Lente de cámara conmutado"})
        return web.json_response({"status": "error", "message": "Dispositivo no encontrado"}, status=404)

    async def _handle_api_disconnect(self, request):
        device_id = request.match_info.get('device_id')
        self.disconnect_device(device_id)
        return web.json_response({"status": "ok", "message": "Dispositivo desvinculado"})

    async def _handle_api_snapshot(self, request):
        device_id = request.match_info.get('device_id')
        dev = self.devices.get(device_id)
        if dev and dev.latest_frame is not None:
            ret, jpeg = cv2.imencode('.jpg', dev.latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if ret:
                return web.Response(
                    body=jpeg.tobytes(),
                    content_type='image/jpeg',
                    headers={'Content-Disposition': f'inline; filename="snapshot_{device_id}.jpg"'}
                )
        return web.Response(text="Sin fotograma disponible", status=404)

    def trigger_siren(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "siren", "duration": 5})

    def toggle_torch(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "toggle_torch"})

    def switch_camera(self, device_id: str):
        dev = self.devices.get(device_id)
        if dev:
            dev.send_remote_command({"cmd": "switch_cam"})

    def disconnect_device(self, device_id: str):
        """Desvincula un dispositivo móvil por su ID."""
        dev = self.devices.get(device_id)
        if dev:
            dev.disconnect()
            if device_id in self.devices:
                del self.devices[device_id]

    def stop(self):
        self.is_running = False
        if self._runner and self._loop:
            asyncio.run_coroutine_threadsafe(self._runner.cleanup(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)
