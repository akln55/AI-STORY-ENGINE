"""Minimal stdlib test runner for environments without pytest.

Runs isolated pytest-style smoke directories with a minimal stdlib fixture resolver.
For the project test suite, it delegates to pytest when installed and refuses to
misrepresent a partial stdlib run as the complete project suite when pytest is missing.
Use the project-wide command:
    python -m pytest -q tests
For standalone fixture-free/supported smoke directories, the stdlib runner remains useful.

Usage:
    python tools/run_tests.py [TESTS_DIR]     # default: <project>/tests

Exit code: 0 if every test passed (and at least one ran), 1 otherwise.

Project-wide test execution must use pytest. The stdlib smoke mode intentionally hides
pytest only after it has selected a non-project test directory.
"""

from __future__ import annotations

import importlib.util
import inspect
import asyncio
import sys
import tempfile
import subprocess
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTS_DIR = PROJECT_ROOT / "tests"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hide_pytest() -> None:
    """Make ``import pytest`` raise ImportError for everything loaded below."""
    sys.modules["pytest"] = None  # type: ignore[assignment]


def _build_fixtures(tests_dir: Path) -> dict:
    conftest_path = tests_dir / "conftest.py"
    if not conftest_path.exists():
        return {}
    conftest = _load_module(conftest_path, "conftest")
    fixtures = {}
    for fname in dir(conftest):
        obj = getattr(conftest, fname)
        if fname.endswith("_state") or fname == "session":
            fixtures[fname] = obj
    return fixtures


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    tests_dir = Path(args[0]).resolve() if args else DEFAULT_TESTS_DIR
    if not tests_dir.is_dir():
        print(f"error: tests directory not found: {tests_dir}")
        return 1

    if tests_dir == DEFAULT_TESTS_DIR:
        try:
            pytest_available = importlib.util.find_spec("pytest") is not None
        except (ImportError, ValueError):
            pytest_available = False
        if not pytest_available:
            print("error: the full project suite requires pytest.")
            print("Install pytest, then run: python -m pytest -q tests")
            print("The stdlib helper supports isolated smoke directories only; it is not a full-suite substitute.")
            return 2
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(tests_dir)],
            check=False,
        ).returncode

    _hide_pytest()
    sys.path.insert(0, str(PROJECT_ROOT))
    fixtures = _build_fixtures(tests_dir)
    passed = failed = 0
    failures: list[str] = []
    for path in sorted(tests_dir.glob("test_*.py")):
        label_prefix = path.stem
        try:
            module = _load_module(path, path.stem)
        except Exception:  # import/collection error counts as a failure
            failed += 1
            failures.append(f"{label_prefix} (import)\n{traceback.format_exc()}")
            print(f"FAIL {label_prefix} (import)")
            continue
        for fname in sorted(dir(module)):
            if not fname.startswith("test_"):
                continue
            fn = getattr(module, fname)
            if not callable(fn):
                continue
            label = f"{label_prefix}::{fname}"
            try:
                if inspect.iscoroutinefunction(fn):
                    raise TypeError("async tests are not supported by the stdlib runner; use synchronous tests")
                kwargs = {}
                for p in inspect.signature(fn).parameters:
                    if p == "tmp_path":  # pytest-compatible: fresh temp dir per test
                        kwargs[p] = Path(tempfile.mkdtemp())
                    elif p in fixtures:
                        kwargs[p] = fixtures[p]()
                    else:
                        raise TypeError(f"unknown fixture '{p}'")
                result = fn(**kwargs)
                if result is not None:
                    raise AssertionError("test functions must not return a value; use assert")
                passed += 1
                print(f"PASS {label}")
            except Exception:
                failed += 1
                failures.append(f"{label}\n{traceback.format_exc()}")
                print(f"FAIL {label}")
    print(f"\n{passed} passed, {failed} failed")
    for f in failures:
        print("\n" + f)
    if passed == 0 and failed == 0:
        print("error: no tests collected")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
