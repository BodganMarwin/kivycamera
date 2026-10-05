[app]
# (str) Title of your application
title = Kivy Sentinel

# (str) Package name
package.name = kivysentinel

# (str) Package domain (needed for android/ios packaging)
package.domain = org.sentinel

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,opencv,numpy,aiohttp,requests,qrcode

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = all

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (list) Permissions
android.permissions = CAMERA,RECORD_AUDIO,INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (bool) Android logcat filters to use
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
