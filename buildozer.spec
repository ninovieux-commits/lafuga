[app]

# (str) Title of your application
title = La Fuga

# (str) Package name
package.name = lafuga

# (str) Package domain (needed for android/ios packaging)
package.domain = org.lafuga

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,wav,ogg,txt,json,ttf

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, .buildozer, __pycache__

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# python-socketio + dépendances pour le mode en ligne ; pillow pour les images.
requirements = python3,kivy==2.3.1,pillow,python-socketio,websocket-client,requests,certifi

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (list) Supported orientations: portrait
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#
# Android specific
#

# (list) Permissions
# INTERNET nécessaire pour le mode en ligne (Socket.IO / HTTP vers le serveur).
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# (int) Target Android API, should be as high as possible.
# 35 = Android 15, exigé par Google Play pour les nouvelles apps.
android.api = 35

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use. This is the minimum API your app will support.
android.ndk_api = 24

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
# arm64-v8a couvre la quasi-totalité des téléphones modernes ;
# armeabi-v7a ajoute la compatibilité avec de vieux appareils.
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

#
# Python for android (p4a) specific
#

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

#
# Buildozer
#

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
