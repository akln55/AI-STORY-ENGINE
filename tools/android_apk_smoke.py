#!/usr/bin/env python3
"""Install, launch, and smoke-test the Android APK through ADB."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import time

PACKAGE = "org.rpgengine"
LAUNCH_COMPONENT = "org.kivy.android.PythonActivity"


def run_adb(adb: Path, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(adb), *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--adb", type=Path, default=Path("adb"))
    parser.add_argument("--serial")
    parser.add_argument("--wait", type=float, default=12.0)
    parser.add_argument("--log", type=Path, default=Path(".ci/android-startup-logcat.txt"))
    args = parser.parse_args()

    if not args.apk.is_file():
        print(f"ANDROID DEVICE SMOKE: FAIL\n- APK not found: {args.apk}")
        return 1

    prefix = ["-s", args.serial] if args.serial else []

    def adb(*parts: str, timeout: float = 30.0):
        return run_adb(args.adb, *prefix, *parts, timeout=timeout)

    if adb("version").returncode:
        print("ANDROID DEVICE SMOKE: FAIL\n- adb is unavailable")
        return 1

    state = adb("get-state")
    if state.returncode or state.stdout.strip() != "device":
        print("ANDROID DEVICE SMOKE: FAIL\n- no ready Android device found")
        print((state.stdout + state.stderr).strip())
        return 1

    args.log.parent.mkdir(parents=True, exist_ok=True)
    adb("logcat", "-c", timeout=10)

    install = adb("install", "-r", str(args.apk.resolve()), timeout=120)
    if install.returncode:
        print("ANDROID DEVICE SMOKE: FAIL\n- APK installation failed")
        print((install.stdout + install.stderr).strip())
        return 1

    launch = adb("shell", "am", "start", "-n", f"{PACKAGE}/{LAUNCH_COMPONENT}", timeout=30)
    launch_output = (launch.stdout + "\n" + launch.stderr).strip()
    if launch.returncode or "Error type 3" in launch_output or (
        "Activity class" in launch_output and "does not exist" in launch_output
    ):
        print("ANDROID DEVICE SMOKE: FAIL\n- activity launch failed")
        print(launch_output)
        return 1

    deadline = time.monotonic() + args.wait
    package_running = False
    while time.monotonic() < deadline:
        pid = adb("shell", "pidof", PACKAGE, timeout=10)
        if pid.returncode == 0 and pid.stdout.strip():
            package_running = True
            break
        time.sleep(0.5)

    logs = adb("logcat", "-d", "-v", "threadtime", timeout=30)
    log_text = logs.stdout + ("\n" + logs.stderr if logs.stderr else "")
    args.log.write_text(log_text, encoding="utf-8")

    fatal_markers = (
        "FATAL EXCEPTION",
        f"Process: {PACKAGE},",
        "AndroidRuntime",
        "java.lang.RuntimeException",
    )
    fatal = [line for line in log_text.splitlines() if any(marker in line for marker in fatal_markers)]

    if not package_running:
        print("ANDROID DEVICE SMOKE: FAIL")
        print("- app process did not remain alive during startup window")
        print(f"- logcat: {args.log}")
        return 1

    if fatal:
        print("ANDROID DEVICE SMOKE: FAIL")
        print("- Android reported a fatal startup exception")
        print(f"- logcat: {args.log}")
        for line in fatal[:8]:
            print(f"- {line}")
        return 1

    print("ANDROID DEVICE SMOKE: PASS")
    print(f"- package={PACKAGE}")
    print(f"- startup_window={args.wait:.1f}s")
    print(f"- logcat={args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
