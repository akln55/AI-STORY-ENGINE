[app]
p4a.branch = master
p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831
title = RPG Engine
package.name = rpgengine
package.domain = org.rpgengine
source.dir = .
source.include_exts = py,md,json,txt,kv,db,rpgscenario,gguf,bin
source.exclude_dirs = .git,.venv,__pycache__,.pytest_cache,tests,saves,bin,.buildozer,dist,build
version = 1.1.4
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
android.api = 36
android.ndk = 29
android.minapi = 26
android.archs = arm64-v8a
android.allow_backup = 1
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
