#!/usr/bin/env python3
"""Report whether the host has the tools needed for an Android debug build."""
from __future__ import annotations
import importlib.util
import shutil
import sys

checks = {
    "python": sys.version.split()[0],
    "buildozer": shutil.which("buildozer") or "MISSING",
    "adb": shutil.which("adb") or "MISSING",
    "java": shutil.which("java") or "MISSING",
    "kivy": "installed" if importlib.util.find_spec("kivy") else "MISSING",
}
for key, value in checks.items():
    print(f"{key}: {value}")
missing = [k for k in ("buildozer", "java", "kivy") if checks[k] == "MISSING"]
if missing:
    print("ANDROID BUILD ENVIRONMENT: INCOMPLETE")
    print("Missing:", ", ".join(missing))
    sys.exit(2)
print("ANDROID BUILD ENVIRONMENT: READY")
