#!/usr/bin/env python3
"""Verify that Buildozer staged the intended Android application source.

This specifically guards against the historical failure where a stale
.buildozer/app tree packaged an obsolete entrypoint after the source tree had
already been migrated.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

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

    # Only inspect textual Python sources. Binary/native assets are intentionally
    # ignored so a model or executable cannot trigger a false positive.
    for path in staging_dir.rglob("*.py"):
        # This verifier is itself part of the source tree and contains the
        # forbidden module names as validation patterns; do not self-scan it.
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("."))
    parser.add_argument("--build-dir", type=Path, default=Path(".buildozer"))
    args = parser.parse_args()

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
