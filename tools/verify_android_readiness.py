#!/usr/bin/env python3
"""Dependency-free Android packaging/readiness verifier."""
from pathlib import Path
import configparser
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = ROOT / "buildozer.spec"
main = ROOT / "main.py"
android_main = ROOT / "rpg_android_app.py"
picker = ROOT / "rpg_android_file_picker.py"
version_file = ROOT / "engine" / "__init__.py"

errors = []
text = spec.read_text()
version = re.search(r"^version\s*=\s*(\S+)$", text, re.M)
engine_version = re.search(r'__version__\s*=\s*["\']([^"\']+)', version_file.read_text())
if not version or not engine_version or version.group(1) != engine_version.group(1):
    errors.append("version mismatch")
if "android.api = 36" not in text:
    errors.append("android.api must be 36")
if "READ_EXTERNAL_STORAGE" in text or "WRITE_EXTERNAL_STORAGE" in text:
    errors.append("legacy external-storage permission present")
if "from rpg_android_app import RPGEngineApp" not in main.read_text():
    errors.append("root main.py is not the Android entrypoint")
if "open_scenario_document" not in android_main.read_text():
    errors.append("Android UI is not connected to SAF picker")
if "ACTION_OPEN_DOCUMENT" not in picker.read_text():
    errors.append("SAF ACTION_OPEN_DOCUMENT missing")
if "source.exclude_dirs =" not in text or "__pycache__" not in text:
    errors.append("buildozer source exclusion does not include cache directories")

if errors:
    print("ANDROID READINESS: FAIL")
    for error in errors:
        print("-", error)
    sys.exit(1)
print(f"ANDROID READINESS: PASS (version={version.group(1)}, target_api=36, SAF=enabled)")
