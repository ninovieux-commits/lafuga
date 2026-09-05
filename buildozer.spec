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
source.include_exts = py,png,jpg,jpeg,wav,ogg,txt,json,ttf,otf,ttc

# (list) Source files to exclude
source.exclude_exts = spec

# (list) List of directory to exclude
source.exclude_dirs = tests, bin, .buildozer, __pycache__

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# python-socketio + dependances pour le mode en ligne ; pillow pour les images.
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,pillow,python-socketio,websocket-client,requests,certifi

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png
# Icône ADAPTATIVE (Android 8+) : logo (icon_fg.png) sur fond gris (icon_bg.png)
icon.adaptive_foreground.filename = %(source.dir)s/icon_fg.png
icon.adaptive_background.filename = %(source.dir)s/icon_bg.png

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#
# Android specific
#

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# (int) Target Android API, should be as high as possible.
android.api = 35

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use.
android.ndk_api = 24

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
# UNE SEULE architecture pour un build plus rapide et leger (couvre tous les
# telephones modernes). On pourra rajouter armeabi-v7a plus tard si besoin.
android.archs = arm64-v8a

# (bool) enables Android auto backup feature
android.allow_backup = True

# ── Firebase Cloud Messaging (notifications push) ──
# androidx est requis par Firebase. La dépendance firebase-messaging sera
# utilisée aux étapes suivantes ; ici on teste juste que l'appli compile avec.
android.enable_androidx = True
android.gradle_dependencies = com.google.firebase:firebase-messaging:24.1.0
# Dossier de code Java à inclure (contient le service FCM qui référence Firebase,
# ce qui force l'inclusion des classes Firebase dans l'APK).
android.add_src = java

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

# (int) Display warning if buildozer is run as root
warn_on_root = 1
