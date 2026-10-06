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
import sys
import zipfile

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
        if path.relative_to(staging_dir).as_posix() == "tools/verify_android_staging.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"staged Python file is not valid UTF-8: {path.relative_to(staging_dir)}")
            continue
        for forbidden in FORBIDDEN_IMPORTS:
            if forbidden in text:
                errors.append(
                    f"obsolete Android module reference '{forbidden}' in "
                    f"{path.relative_to(staging_dir)}"
                )

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
            names = set(apk.namelist())

            for rel in CRITICAL_FILES:
                source = source_dir / rel
                packaged = f"assets/private/{rel}"

                if not source.is_file():
                    errors.append(f"source critical file missing: {rel}")
                    continue
                if packaged not in names:
                    errors.append(f"APK critical file missing: {packaged}")
                    continue

                source_hash = sha256(source)
                packaged_hash = hashlib.sha256(apk.read(packaged)).hexdigest()
                if source_hash != packaged_hash:
                    errors.append(
                        f"APK/source hash mismatch for {rel}: "
                        f"source={source_hash} apk={packaged_hash}"
                    )

            main = "assets/private/main.py"
            if main in names:
                main_text = apk.read(main).decode("utf-8")
                if "from rpg_android_app import RPGEngineApp" not in main_text:
                    errors.append(
                        "APK main.py does not import rpg_android_app.RPGEngineApp"
                    )

            for name in names:
                if not name.endswith(".py") or not name.startswith("assets/private/"):
                    continue
                try:
                    text = apk.read(name).decode("utf-8")
                except UnicodeDecodeError:
                    errors.append(f"APK Python file is not valid UTF-8: {name}")
                    continue
                for forbidden in FORBIDDEN_IMPORTS:
                    if forbidden in text:
                        errors.append(
                            f"obsolete Android module reference '{forbidden}' in {name}"
                        )
    except zipfile.BadZipFile as exc:
        errors.append(f"invalid APK/ZIP: {exc}")
    except OSError as exc:
        errors.append(f"cannot read APK: {exc}")

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
            print(f"- {rel}: verified against assets/private/{rel}")
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
