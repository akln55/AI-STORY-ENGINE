"""Shared test fixtures. Plain factories by default so the stdlib runner
(tools/run_tests.py) works without pytest; wrapped for pytest when present."""

from engine.cli import build_session
from engine.demo import build_demo_state


def demo_state():
    return build_demo_state()


def session():
    """CLI-equivalent session without AI adapter (deterministic tests)."""
    return build_session()


try:
    import pytest
except ImportError:  # bare-python environments (Android/Termux)
    pytest = None
else:
    demo_state = pytest.fixture(demo_state)
    session = pytest.fixture(session)
