[app]
title = La Fuga
package.name = lafuga
package.domain = org.lafuga
source.dir = .
source.include_exts = py,png,jpg,jpeg,wav,ogg,txt,json,ttf
source.exclude_exts = spec
source.exclude_dirs = tests, bin, .buildozer, __pycache__
version = 1.0
requirements = python3,kivy==2.3.1,pillow,python-socketio,websocket-client,requests,certifi
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
