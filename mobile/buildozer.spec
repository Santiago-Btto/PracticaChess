[app]
title = PracticaChess
package.name = practicachess
package.domain = com.santiagobtto
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf
version = 0.1.0
requirements = python3,kivy,python-chess
orientation = portrait
fullscreen = 0
android.permissions =
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
# Python-for-Android 2024.01.21 usa Python 3.11.5 y evita la rueda cp314
# incompatible de charset-normalizer al construir para arm64.
p4a.branch = master
p4a.commit = 957a3e5f8c270f7aa648ba185e5a68c1077a798d
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
