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

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions =
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
