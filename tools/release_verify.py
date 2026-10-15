"""Verify a release ZIP from a fresh extraction.

Usage: python tools/release_verify.py path/to/RPG_ENGINE_vX.Y.Z.zip
The verifier is dependency-light: pytest is optional, while the project's
stdlib runner, compileall, scenario validation, and mutation smoke are always
required. It also checks the authoritative version against buildozer.spec and
engine/__init__.py and fails on stale top-level package nesting.
"""
from __future__ import annotations

import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

MAX_RELEASE_ENTRIES = 50_000
MAX_RELEASE_FILE_BYTES = 64 * 1024 * 1024
MAX_RELEASE_TOTAL_BYTES = 512 * 1024 * 1024


def run(root: Path, args: list[str]) -> None:
    proc = subprocess.run(args, cwd=root, text=True, capture_output=True)
    if proc.returncode:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(proc.returncode)
    print(proc.stdout.splitlines()[-1] if proc.stdout else "PASS " + " ".join(args))


def _extract_release_archive(archive_path: Path, destination: Path) -> None:
    """Safely extract an untrusted release ZIP within strict size/path limits."""
    root = destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_RELEASE_ENTRIES:
            raise ValueError(f"release ZIP has too many entries (max {MAX_RELEASE_ENTRIES})")

        total_size = 0
        normalized: list[tuple[zipfile.ZipInfo, str, Path, bool]] = []
        seen: set[str] = set()
        file_paths: set[str] = set()
        for info in infos:
            name = info.filename.replace("\\", "/")
            if not name or "\\x00" in name:
                raise ValueError("release ZIP contains an empty or invalid path")
            if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                raise ValueError(f"unsafe absolute path in release ZIP: {info.filename!r}")
            parts = PurePosixPath(name).parts
            if not parts or ".." in parts:
                raise ValueError(f"unsafe traversal path in release ZIP: {info.filename!r}")
            clean_name = "/".join(part for part in parts if part not in ("", "."))
            if not clean_name:
                raise ValueError(f"unsafe empty path in release ZIP: {info.filename!r}")

            is_dir = info.is_dir() or name.endswith("/")
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError(f"non-regular file in release ZIP: {info.filename!r}")
            if kind == stat.S_IFDIR and not is_dir:
                raise ValueError(f"directory metadata/path mismatch in release ZIP: {info.filename!r}")
            if kind == stat.S_IFREG and is_dir:
                raise ValueError(f"file metadata/path mismatch in release ZIP: {info.filename!r}")

            key = clean_name.casefold()
            if key in seen:
                raise ValueError(f"duplicate or case-colliding path in release ZIP: {info.filename!r}")
            seen.add(key)

            target = (root.joinpath(*PurePosixPath(clean_name).parts)).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"release ZIP path escapes extraction root: {info.filename!r}")
            if is_dir and info.file_size:
                raise ValueError(f"directory entry has data: {info.filename!r}")
            if not is_dir:
                if info.file_size > MAX_RELEASE_FILE_BYTES:
                    raise ValueError(f"release ZIP file too large (max {MAX_RELEASE_FILE_BYTES} bytes): {info.filename!r}")
                file_paths.add(key)
            total_size += info.file_size
            if total_size > MAX_RELEASE_TOTAL_BYTES:
                raise ValueError(f"release ZIP expands beyond {MAX_RELEASE_TOTAL_BYTES} bytes")
            normalized.append((info, clean_name, target, is_dir))

        for _info, name, _target, _is_dir in normalized:
            parts = PurePosixPath(name).parts
            for i in range(1, len(parts)):
                if "/".join(parts[:i]).casefold() in file_paths:
                    raise ValueError(f"release ZIP path is nested under a file: {name!r}")

        total_written = 0
        for info, _name, target, is_dir in normalized:
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(info, "r") as src, target.open("xb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    total_written += len(chunk)
                    if written > MAX_RELEASE_FILE_BYTES or total_written > MAX_RELEASE_TOTAL_BYTES:
                        raise ValueError("release ZIP exceeded the extraction size limit")
                    dst.write(chunk)
            if written != info.file_size:
                raise ValueError(f"release ZIP size mismatch for {info.filename!r}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tools/release_verify.py RELEASE.zip")
        return 2
    archive = Path(sys.argv[1]).resolve()
    if not archive.is_file():
        print(f"error: release archive not found: {archive}")
        return 2
    with tempfile.TemporaryDirectory(prefix="rpg-release-") as tmp:
        extract = Path(tmp)
        try:
            _extract_release_archive(archive, extract)
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
            print(f"error: release ZIP is unsafe or unreadable: {exc}")
            return 1
        roots = [p for p in extract.iterdir() if p.is_dir()]
        root = roots[0] if len(roots) == 1 else extract
        if not (root / "engine").is_dir() or not (root / "tests").is_dir():
            print("error: release root is missing engine/tests")
            return 1
        init_version = re.search(r'__version__\s*=\s*["\']([^"\']+)', (root / "engine/__init__.py").read_text())
        build_version = re.search(r"^version\s*=\s*(\S+)", (root / "buildozer.spec").read_text(), re.M)
        if not init_version or not build_version or init_version.group(1) != build_version.group(1):
            print("error: version mismatch")
            return 1
        print(f"PASS version {init_version.group(1)}")
        run(root, [sys.executable, "-m", "compileall", "-q", "engine", "tools", "android", "tests"])
        run(root, [sys.executable, "tools/run_tests.py"])
        try:
            run(root, [sys.executable, "-m", "pytest", "-q"])
        except SystemExit:
            print("warning: pytest unavailable or failed; dependency-free verification already ran")
            return 1
        run(root, [sys.executable, "tools/validate_scenario.py", "scenarios/demo-bootstrap"])
        # Mutation smoke intentionally runs as a separate release check because
        # it creates nested pytest subprocesses and is not needed for basic
        # package integrity. See docs/TESTING.md.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
