"""Android storage and event temporal invariant hardening."""

import os
import sys
import types
from pathlib import Path

from engine.cli import build_session
from engine.core.invariants import InvariantError, check_invariants
from engine.core.state import EventState
from engine.core.validation import apply_effects
from engine.persistence.saves import default_save_dir
from engine.rules.base import Effect


def test_event_cannot_resolve_before_start():
    session = build_session()
    session.state.world.events["e"] = EventState(
        id="e", type="test", status="active", start_turn=10
    )
    report = apply_effects([Effect("event", "e", "resolve", 9)], session.state)
    assert report.rejected
    assert session.state.world.events["e"].status == "active"


def test_event_invariant_rejects_terminal_before_start():
    session = build_session()
    session.state.world.events["e"] = EventState(
        id="e", type="test", status="resolved", start_turn=10, resolved_turn=9
    )
    try:
        check_invariants(session.state)
        raised = False
    except InvariantError:
        raised = True
    assert raised


def test_event_invariant_rejects_empty_type():
    session = build_session()
    session.state.world.events["e"] = EventState(id="e", type="")
    try:
        check_invariants(session.state)
        raised = False
    except InvariantError:
        raised = True
    assert raised


def test_android_default_save_dir_uses_app_private_storage():
    android = types.ModuleType("android")
    storage = types.ModuleType("android.storage")
    storage.app_storage_path = lambda: "/data/user/0/example/files"
    android.storage = storage
    old_android = sys.modules.get("android")
    old_storage = sys.modules.get("android.storage")
    old_argument = os.environ.get("ANDROID_ARGUMENT")
    try:
        sys.modules["android"] = android
        sys.modules["android.storage"] = storage
        os.environ["ANDROID_ARGUMENT"] = "1"
        assert default_save_dir() == Path("/data/user/0/example/files/saves")
    finally:
        if old_android is None:
            sys.modules.pop("android", None)
        else:
            sys.modules["android"] = old_android
        if old_storage is None:
            sys.modules.pop("android.storage", None)
        else:
            sys.modules["android.storage"] = old_storage
        if old_argument is None:
            os.environ.pop("ANDROID_ARGUMENT", None)
        else:
            os.environ["ANDROID_ARGUMENT"] = old_argument


def test_desktop_default_save_dir_does_not_require_android():
    old_argument = os.environ.pop("ANDROID_ARGUMENT", None)
    try:
        assert default_save_dir().name == "saves"
    finally:
        if old_argument is not None:
            os.environ["ANDROID_ARGUMENT"] = old_argument


def test_android_autosave_is_dirty_aware_and_not_silent():
    source = Path(__file__).resolve().parent.parent / "rpg_android_app.py"
    text = source.read_text(encoding="utf-8")
    assert "if not self.controller.dirty:" in text
    assert "autosave_error.log" in text
    assert "except Exception as exc:" in text[text.index("    def _autosave(self, reason):"):]
