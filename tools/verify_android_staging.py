#!/usr/bin/env python3
"""Verify that the built Android APK contains the intended application source.

This guards against the historical failure where a stale Buildozer tree
packaged an obsolete entrypoint after the source tree had already migrated.
The verification is performed against the final APK so it does not depend on
Buildozer's internal staging-directory layout.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

try:
    from tools.android_apk_contents import (
        VERIFIER_SCRIPTS, find_forbidden_imports, load_apk_private_files,
    )
except ModuleNotFoundError:  # Direct execution as: python tools/verify_android_staging.py
    from android_apk_contents import (
        VERIFIER_SCRIPTS, find_forbidden_imports, load_apk_private_files,
    )

CRITICAL_FILES = (
    "main.py",
    "rpg_android_app.py",
    "rpg_android_file_picker.py",
)
FORBIDDEN_IMPORTS = (
    "android.main",
    "android.file_picker",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_staging(source_dir: Path, staging_dir: Path) -> list[str]:
    """Legacy helper retained for local diagnostics of a known staging tree."""
    errors: list[str] = []
    source_dir = source_dir.resolve()
    staging_dir = staging_dir.resolve()

    if not staging_dir.is_dir():
        return [f"staging directory not found: {staging_dir}"]

    for rel in CRITICAL_FILES:
        source = source_dir / rel
        staged = staging_dir / rel
        if not source.is_file():
            errors.append(f"source critical file missing: {rel}")
            continue
        if not staged.is_file():
            errors.append(f"staged critical file missing: {rel}")
            continue
        source_hash = sha256(source)
        staged_hash = sha256(staged)
        if source_hash != staged_hash:
            errors.append(
                f"staged/source hash mismatch for {rel}: "
                f"source={source_hash} staged={staged_hash}"
            )

    main = staging_dir / "main.py"
    if main.is_file():
        main_text = main.read_text(encoding="utf-8")
        if "from rpg_android_app import RPGEngineApp" not in main_text:
            errors.append("staged main.py does not import rpg_android_app.RPGEngineApp")

    for path in staging_dir.rglob("*.py"):
        relative = path.relative_to(staging_dir).as_posix()
        if relative in VERIFIER_SCRIPTS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"staged Python file is not valid UTF-8: {relative}")
            continue
        try:
            forbidden_modules = find_forbidden_imports(text, FORBIDDEN_IMPORTS)
        except SyntaxError as exc:
            errors.append(f"staged Python file has invalid syntax: {relative}: {exc.msg}")
            continue
        for forbidden in forbidden_modules:
            errors.append(f"obsolete Android module import '{forbidden}' in {relative}")

    return errors


def verify_apk(source_dir: Path, apk_path: Path) -> list[str]:
    """Verify critical Python sources in the final APK."""
    errors: list[str] = []
    source_dir = source_dir.resolve()
    apk_path = apk_path.resolve()

    if not apk_path.is_file():
        return [f"APK not found: {apk_path}"]

    try:
        with zipfile.ZipFile(apk_path) as apk:
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

                source_hash = sha256(source)
                packaged_hash = hashlib.sha256(packaged_data).hexdigest()
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
                        errors.append(
                            "APK main.py does not import rpg_android_app.RPGEngineApp"
                        )

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
                        f"obsolete Android module import '{forbidden}' in {name}"
                    )
    except (zipfile.BadZipFile, OSError) as exc:
        errors.append(f"cannot read APK/ZIP: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("."))
    parser.add_argument("--build-dir", type=Path, default=Path(".buildozer"))
    parser.add_argument("--apk", type=Path, help="verify the final APK instead of Buildozer staging")
    args = parser.parse_args()

    if args.apk:
        errors = verify_apk(args.source_dir, args.apk)
        if errors:
            print("ANDROID APK CONTENT: FAIL")
            for error in errors:
                print(f"- {error}")
            return 1
        print(f"ANDROID APK CONTENT: PASS ({args.apk.resolve()})")
        for rel in CRITICAL_FILES:
            print(f"- {rel}: verified against APK private payload")
        return 0

    staging = args.build_dir / "android" / "app"
    errors = verify_staging(args.source_dir, staging)
    if errors:
        print("ANDROID STAGING: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"ANDROID STAGING: PASS ({staging.resolve()})")
    for rel in CRITICAL_FILES:
        print(f"- {rel}: {sha256(staging / rel)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
