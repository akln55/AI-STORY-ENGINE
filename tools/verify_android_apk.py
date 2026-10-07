#!/usr/bin/env python3
"""Static validation for a built RPG Engine Android APK."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

CRITICAL_FILES = ("main.py", "rpg_android_app.py", "rpg_android_file_picker.py")
FORBIDDEN_IMPORTS = ("android.main", "android.file_picker")
EXPECTED_PACKAGE = "org.rpgengine"
EXPECTED_VERSION = "1.1.4"
NATIVE_BINARY = "assets/private/android_native/arm64-v8a/llama-server.bin"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_aapt(aapt: Path, apk: Path) -> str:
    proc = subprocess.run(
        [str(aapt), "dump", "badging", str(apk)],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "aapt dump badging failed")
    return proc.stdout


def verify_apk(source_dir: Path, apk_path: Path, *, aapt: Path | None = None) -> list[str]:
    errors: list[str] = []
    source_dir = source_dir.resolve()
    apk_path = apk_path.resolve()

    if not apk_path.is_file():
        return [f"APK not found: {apk_path}"]

    try:
        with zipfile.ZipFile(apk_path) as apk:
            names = set(apk.namelist())
            bad_paths = [n for n in names if Path(n).is_absolute() or ".." in Path(n).parts]
            if bad_paths:
                errors.append(f"APK contains unsafe paths: {bad_paths[:3]}")

            for rel in CRITICAL_FILES:
                source = source_dir / rel
                packaged = f"assets/private/{rel}"
                if not source.is_file():
                    errors.append(f"source critical file missing: {rel}")
                    continue
                if packaged not in names:
                    errors.append(f"APK critical file missing: {packaged}")
                    continue
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                packaged_hash = _sha256_bytes(apk.read(packaged))
                if source_hash != packaged_hash:
                    errors.append(f"APK/source hash mismatch for {rel}: source={source_hash} apk={packaged_hash}")

            main_name = "assets/private/main.py"
            if main_name in names:
                main_text = apk.read(main_name).decode("utf-8")
                if "from rpg_android_app import RPGEngineApp" not in main_text:
                    errors.append("APK main.py does not import rpg_android_app.RPGEngineApp")
            else:
                errors.append("APK main.py is missing")

            verifier_name = "assets/private/tools/verify_android_staging.py"
            for name in names:
                if name == verifier_name or not name.startswith("assets/private/") or not name.endswith(".py"):
                    continue
                try:
                    text = apk.read(name).decode("utf-8")
                except UnicodeDecodeError:
                    errors.append(f"APK Python file is not UTF-8: {name}")
                    continue
                for forbidden in FORBIDDEN_IMPORTS:
                    if forbidden in text:
                        errors.append(f"obsolete Android module reference {forbidden!r} in {name}")

            if NATIVE_BINARY not in names:
                errors.append(f"packaged llama-server missing: {NATIVE_BINARY}")
            else:
                native = apk.read(NATIVE_BINARY)
                if len(native) < 20 or native[:4] != b"\x7fELF" or native[4] != 2 or native[5] != 1:
                    errors.append("packaged llama-server is not an ELF64 little-endian binary")
                elif int.from_bytes(native[18:20], "little") != 183:
                    errors.append("packaged llama-server is not AArch64")

            if aapt is not None:
                try:
                    badging = _run_aapt(aapt, apk_path)
                except (OSError, RuntimeError) as exc:
                    errors.append(f"aapt verification failed: {exc}")
                else:
                    if f"package: name='{EXPECTED_PACKAGE}'" not in badging:
                        errors.append(f"APK package id is not {EXPECTED_PACKAGE}")
                    if f"versionName='{EXPECTED_VERSION}'" not in badging:
                        errors.append(f"APK versionName is not {EXPECTED_VERSION}")
                    if "sdkVersion:'26'" not in badging:
                        errors.append("APK min sdkVersion is not 26")
                    if "targetSdkVersion:'36'" not in badging:
                        errors.append("APK targetSdkVersion is not 36")
                    if "native-code: 'arm64-v8a'" not in badging:
                        errors.append("APK does not declare arm64-v8a native code")
    except (zipfile.BadZipFile, OSError) as exc:
        errors.append(f"cannot inspect APK: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--source-dir", type=Path, default=Path("."))
    parser.add_argument("--aapt", type=Path)
    args = parser.parse_args()

    if args.aapt is not None and not args.aapt.is_file():
        print(f"ANDROID APK STATIC CHECK: FAIL\n- aapt not found: {args.aapt}")
        return 1

    errors = verify_apk(args.source_dir, args.apk, aapt=args.aapt)
    if errors:
        print("ANDROID APK STATIC CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"ANDROID APK STATIC CHECK: PASS ({args.apk.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
