#!/usr/bin/env python3
"""Static validation for a built RPG Engine Android APK.

This is deliberately separate from Android-device smoke testing. It answers:
"Does the APK contain the expected application and native payload?" It does
not claim that Android can successfully launch the application.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

try:
    from tools.android_apk_contents import (
        NATIVE_BINARY_PATH, NATIVE_LIBRARY_APK_PATH, VERIFIER_SCRIPTS, find_forbidden_imports,
        load_apk_private_files,
    )
except ModuleNotFoundError:  # Direct execution as: python tools/verify_android_apk.py
    from android_apk_contents import (
        NATIVE_BINARY_PATH, VERIFIER_SCRIPTS, find_forbidden_imports,
        load_apk_private_files,
    )

CRITICAL_FILES = (
    "main.py",
    "rpg_android_app.py",
    "rpg_android_file_picker.py",
)
FORBIDDEN_IMPORTS = ("android.main", "android.file_picker")

EXPECTED_PACKAGE = "org.rpgengine"
EXPECTED_VERSION = "1.1.4"
NATIVE_BINARY_SOURCE = NATIVE_BINARY_PATH
NATIVE_LIBRARY_ENTRY = NATIVE_LIBRARY_APK_PATH


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
            bad_paths = [
                name for name in names
                if name.startswith("/") or ".." in name.replace("\\", "/").split("/")
            ]
            if bad_paths:
                errors.append(f"APK contains unsafe paths: {bad_paths[:3]}")

            private_files = load_apk_private_files(apk, errors)
            if not private_files:
                errors.append(
                    "APK app-private payload is empty; expected assets/private.tar "
                    "or individual assets/private files"
                )

            for rel in CRITICAL_FILES:
                source = source_dir / rel
                if not source.is_file():
                    errors.append(f"source critical file missing: {rel}")
                    continue
                packaged_data = private_files.get(rel)
                if packaged_data is None:
                    errors.append(f"APK critical file missing from private payload: {rel}")
                    continue
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                packaged_hash = _sha256_bytes(packaged_data)
                if source_hash != packaged_hash:
                    errors.append(
                        f"APK/source hash mismatch for {rel}: "
                        f"source={source_hash} apk={packaged_hash}"
                    )

            main_data = private_files.get("main.py")
            if main_data is None:
                errors.append("APK main.py is missing")
            else:
                try:
                    main_text = main_data.decode("utf-8")
                except UnicodeDecodeError:
                    errors.append("APK main.py is not UTF-8")
                else:
                    if "from rpg_android_app import RPGEngineApp" not in main_text:
                        errors.append("APK main.py does not import rpg_android_app.RPGEngineApp")

            for name, data in private_files.items():
                if not name.endswith(".py") or name in VERIFIER_SCRIPTS:
                    continue
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    errors.append(f"APK Python file is not UTF-8: {name}")
                    continue
                try:
                    forbidden_modules = find_forbidden_imports(text, FORBIDDEN_IMPORTS)
                except SyntaxError as exc:
                    errors.append(f"APK Python file has invalid syntax: {name}: {exc.msg}")
                    continue
                for forbidden in forbidden_modules:
                    errors.append(
                        f"obsolete Android module import {forbidden!r} in {name}"
                    )

            if NATIVE_BINARY_SOURCE in private_files:
                errors.append(
                    "llama-server is incorrectly packaged in writable app-private payload; "
                    "it must be installed from the APK native-library directory"
                )

            native_source_path = source_dir / NATIVE_BINARY_SOURCE
            if not native_source_path.is_file():
                errors.append(f"native server source artifact missing: {NATIVE_BINARY_SOURCE}")
            if NATIVE_LIBRARY_ENTRY not in names:
                errors.append(
                    f"packaged llama-server missing from Android native library directory: {NATIVE_LIBRARY_ENTRY}"
                )
            else:
                native = apk.read(NATIVE_LIBRARY_ENTRY)
                if len(native) < 20 or native[:4] != b"\x7fELF" or native[4] != 2 or native[5] != 1:
                    errors.append("packaged llama-server is not an ELF64 little-endian binary")
                else:
                    elf_type = int.from_bytes(native[16:18], "little")
                    if elf_type != 3:
                        errors.append(f"packaged llama-server is not a PIE executable (ELF type={elf_type})")
                    if int.from_bytes(native[18:20], "little") != 183:
                        errors.append("packaged llama-server is not AArch64")
                    if native_source_path.is_file():
                        source_digest = hashlib.sha256(native_source_path.read_bytes()).hexdigest()
                        native_digest = hashlib.sha256(native).hexdigest()
                        if source_digest != native_digest:
                            errors.append("packaged llama-server differs from the verified native source artifact")

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

    aapt = args.aapt
    if aapt is not None and not aapt.is_file():
        print(f"ANDROID APK STATIC CHECK: FAIL\n- aapt not found: {aapt}")
        return 1

    errors = verify_apk(args.source_dir, args.apk, aapt=aapt)
    if errors:
        print("ANDROID APK STATIC CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"ANDROID APK STATIC CHECK: PASS ({args.apk.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
