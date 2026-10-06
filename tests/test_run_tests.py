"""Tests for tools/run_tests.py, exercised as a real subprocess (exit codes).

The runner is pointed at throwaway test directories, never at this suite, so
there is no recursion. Stays pytest-optional (CONVENTIONS §4).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "tools" / "run_tests.py"

# Same optional-pytest wrapping pattern as tests/conftest.py.
_CONFTEST = '''
def demo_state():
    return 42

try:
    import pytest
except ImportError:
    pytest = None
else:
    demo_state = pytest.fixture(demo_state)
'''

# Stand-in for pytest whose fixtures refuse direct calls, like the real one.
_STUB_PYTEST = '''
class _Fixture:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, *a, **k):
        raise RuntimeError("Fixture called directly")

def fixture(fn):
    return _Fixture(fn)
'''


def _run(tests_dir, extra_env=None):
    env = dict(os.environ)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(RUNNER), str(tests_dir)],
        capture_output=True, text=True, env=env, timeout=60,
    )


def _make_dir(files):
    d = Path(tempfile.mkdtemp())
    for name, body in files.items():
        (d / name).write_text(body)
    return d


def test_runner_exit_0_when_all_pass():
    d = _make_dir({"test_ok.py": "def test_a():\n    assert 1 + 1 == 2\n"})
    try:
        r = _run(d)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "1 passed, 0 failed" in r.stdout
    finally:
        shutil.rmtree(d)


def test_runner_exit_1_when_a_test_fails():
    d = _make_dir({"test_bad.py": "def test_a():\n    assert False\n"
                                  "def test_b():\n    assert True\n"})
    try:
        r = _run(d)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "FAIL test_bad::test_a" in r.stdout
        assert "1 passed, 1 failed" in r.stdout
    finally:
        shutil.rmtree(d)


def test_runner_exit_1_on_import_error_and_on_empty_dir():
    d = _make_dir({"test_broken.py": "import does_not_exist_xyz\n"})
    e = _make_dir({})
    try:
        assert _run(d).returncode == 1
        assert _run(e).returncode == 1  # nothing collected is not success
    finally:
        shutil.rmtree(d)
        shutil.rmtree(e)


def test_runner_exit_1_on_unknown_fixture():
    d = _make_dir({"test_fx.py": "def test_a(nope):\n    pass\n"})
    try:
        r = _run(d)
        assert r.returncode == 1
        assert "FAIL test_fx::test_a" in r.stdout
    finally:
        shutil.rmtree(d)


def test_runner_resolves_fixture_when_pytest_is_importable():
    """Original bug: with pytest importable, conftest fixtures were wrapped and
    calling them directly raised. The runner must still execute them."""
    stub = _make_dir({"pytest.py": _STUB_PYTEST})
    d = _make_dir({
        "conftest.py": _CONFTEST,  # defines fixture 'demo_state' (runner resolves *_state)
        "test_fx.py": "def test_uses_fixture(demo_state):\n    assert demo_state == 42\n",
    })
    try:
        r = _run(d, {"PYTHONPATH": str(stub)})
        assert r.returncode == 0, r.stdout + r.stderr
        assert "1 passed, 0 failed" in r.stdout
    finally:
        shutil.rmtree(d)
        shutil.rmtree(stub)


def test_runner_rejects_async_tests():
    d = _make_dir({"test_async.py": "async def test_a():\n    return None\n"})
    try:
        r = _run(d)
        assert r.returncode == 1
        assert "async tests are not supported" in r.stdout
    finally:
        shutil.rmtree(d)


def test_runner_rejects_returning_test_values():
    d = _make_dir({"test_return.py": "def test_a():\n    return True\n"})
    try:
        r = _run(d)
        assert r.returncode == 1
        assert "test functions must not return a value" in r.stdout
    finally:
        shutil.rmtree(d)
