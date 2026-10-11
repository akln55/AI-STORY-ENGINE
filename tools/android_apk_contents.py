#!/usr/bin/env python3
"""Read Python app sources and the native server from a python-for-android APK.

Recent python-for-android builds store private application files inside
assets/private.tar instead of exposing them as individual ZIP members. Older
builds may still expose assets/private/<path>, so both layouts are supported.
"""
from __future__ import annotations

import ast
from io import BytesIO
import tarfile
import zipfile

PRIVATE_BUNDLES = (
    "assets/private.tar",
    "assets/private.mp3",
    "assets/private.tar.gz",
)
NATIVE_BINARY_PATH = "android_native/arm64-v8a/llama-server.bin"
VERIFIER_SCRIPTS = {
    "tools/verify_android_staging.py",
    "tools/verify_android_apk.py",
}


def _normalise_private_path(name: str) -> str | None:
    """Return a safe relative private path, or None for path traversal."""
    name = name.replace("\\", "/")
    if name.startswith("/"):
        return None
    parts: list[str] = []
    for part in name.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            return None
        parts.append(part)
    if parts[:2] == ["assets", "private"]:
        parts = parts[2:]
    elif parts[:1] == ["private"]:
        parts = parts[1:]
    return "/".join(parts)


def _is_relevant_private_file(path: str) -> bool:
    return path.endswith(".py") or path == NATIVE_BINARY_PATH


def load_apk_private_files(apk: zipfile.ZipFile, errors: list[str]) -> dict[str, bytes]:
    """Load relevant app files from direct APK entries and p4a private tarballs.

    Only Python sources and the pinned native llama-server are retained in
    memory. Tar members are never extracted to disk, and path traversal,
    symlinks, and conflicting duplicate payloads are rejected.
    """
    files: dict[str, bytes] = {}
    names = set(apk.namelist())

    def record(path: str, data: bytes, origin: str) -> None:
        relative = _normalise_private_path(path)
        if relative is None:
            errors.append(f"unsafe path in APK private payload: {path}")
            return
        if not relative or not _is_relevant_private_file(relative):
            return
        previous = files.get(relative)
        if previous is not None and previous != data:
            errors.append(f"conflicting APK private payload copies for {relative} ({origin})")
            return
        files[relative] = data

    # Legacy layout: each private file is a separate APK ZIP member.
    for name in sorted(names):
        prefix = "assets/private/"
        if not name.startswith(prefix) or name in PRIVATE_BUNDLES or name.endswith("/"):
            continue
        relative = name[len(prefix):]
        if not _is_relevant_private_file(relative):
            continue
        try:
            record(relative, apk.read(name), name)
        except (KeyError, OSError, zipfile.BadZipFile) as exc:
            errors.append(f"cannot read APK private file {name}: {exc}")

    # Current p4a layout: app-private files are bundled in a tar archive.
    for bundle in PRIVATE_BUNDLES:
        if bundle not in names:
            continue
        try:
            with tarfile.open(fileobj=BytesIO(apk.read(bundle)), mode="r:*") as payload:
                for member in payload.getmembers():
                    if member.isdir():
                        continue
                    relative = _normalise_private_path(member.name)
                    if relative is None:
                        errors.append(f"unsafe path in APK private bundle {bundle}: {member.name}")
                        continue
                    if not relative or not _is_relevant_private_file(relative):
                        continue
                    if not member.isfile():
                        errors.append(f"non-regular app file in APK private bundle {bundle}: {member.name}")
                        continue
                    stream = payload.extractfile(member)
                    if stream is None:
                        errors.append(f"cannot read APK private bundle member: {member.name}")
                        continue
                    with stream:
                        record(relative, stream.read(), f"{bundle}:{member.name}")
        except (KeyError, OSError, tarfile.TarError, EOFError) as exc:
            errors.append(f"cannot read APK private bundle {bundle}: {exc}")

    return files


def find_forbidden_imports(source: str, forbidden_imports: tuple[str, ...]) -> list[str]:
    """Find actual Python import statements, not comments or string literals."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        imported_modules: list[str] = []
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_modules.append(module)
            if module == "android":
                imported_modules.extend(f"android.{alias.name}" for alias in node.names)
        for module in imported_modules:
            for forbidden in forbidden_imports:
                if module == forbidden or module.startswith(forbidden + "."):
                    if forbidden not in found:
                        found.append(forbidden)
    return found
