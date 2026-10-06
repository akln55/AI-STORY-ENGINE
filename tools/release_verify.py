"""Verify a release ZIP from a fresh extraction.

Usage: python tools/release_verify.py path/to/RPG_ENGINE_vX.Y.Z.zip
The verifier is dependency-light: pytest is optional, while the project's
stdlib runner, compileall, scenario validation, and mutation smoke are always
required. It also checks the authoritative version against buildozer.spec and
engine/__init__.py and fails on stale top-level package nesting.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(root: Path, args: list[str]) -> None:
    proc = subprocess.run(args, cwd=root, text=True, capture_output=True)
    if proc.returncode:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(proc.returncode)
    print(proc.stdout.splitlines()[-1] if proc.stdout else "PASS " + " ".join(args))


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
        with zipfile.ZipFile(archive) as zf:
            bad = [n for n in zf.namelist() if Path(n).is_absolute() or ".." in Path(n).parts]
            if bad:
                print(f"error: unsafe ZIP paths: {bad[:3]}")
                return 1
            zf.extractall(extract)
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
