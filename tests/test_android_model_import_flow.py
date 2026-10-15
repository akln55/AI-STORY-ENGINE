from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import rpg_android_file_picker as picker


class FakeCursor:
    def __init__(self, display_name: str | None):
        self.display_name = display_name
        self.closed = False

    def moveToFirst(self):
        return self.display_name is not None

    def getColumnIndex(self, _column):
        return 0 if self.display_name is not None else -1

    def getString(self, _index):
        return self.display_name

    def close(self):
        self.closed = True


class FakeJavaInputStream:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.closed = False

    def read(self, target):
        if self.offset >= len(self.data):
            return -1
        count = min(len(target), len(self.data) - self.offset)
        target[:count] = self.data[self.offset:self.offset + count]
        self.offset += count
        return count

    def close(self):
        self.closed = True


class FakeResolver:
    def __init__(self, display_name="tiny.gguf", data=b"model bytes", error=None):
        self.display_name = display_name
        self.data = data
        self.error = error
        self.stream = None

    def query(self, *_args):
        return FakeCursor(self.display_name)

    def openInputStream(self, _uri):
        if self.error is not None:
            raise self.error
        self.stream = FakeJavaInputStream(self.data)
        return self.stream


class FakeActivity:
    def __init__(self, resolver):
        self.resolver = resolver
        self.callbacks = {}
        self.unbound = set()
        self.started = None

    def getContentResolver(self):
        return self.resolver

    def startActivityForResult(self, intent, request_code):
        self.started = (intent, request_code)


class FakeIntent:
    ACTION_OPEN_DOCUMENT = "open-document"
    CATEGORY_OPENABLE = "openable"
    EXTRA_ALLOW_MULTIPLE = "allow-multiple"

    def __init__(self, action):
        self.action = action
        self.category = None
        self.mime_type = None
        self.extras = {}

    def addCategory(self, category):
        self.category = category

    def setType(self, mime_type):
        self.mime_type = mime_type

    def putExtra(self, name, value):
        self.extras[name] = value


class FakeResultIntent:
    def __init__(self, uri="content://provider/document/1"):
        self.uri = uri

    def getData(self):
        return self.uri


class ImmediateThread:
    def __init__(self, *, target, name=None, daemon=None):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


def _install_android_mocks(monkeypatch, tmp_path, *, display_name="tiny.gguf", data=b"model bytes", error=None):
    resolver = FakeResolver(display_name=display_name, data=data, error=error)
    fake_activity = FakeActivity(resolver)
    event_activity = types.SimpleNamespace()

    def bind(**kwargs):
        fake_activity.callbacks.update(kwargs)

    def unbind(**kwargs):
        for callback in kwargs.values():
            fake_activity.unbound.add(callback)
            for name, current in list(fake_activity.callbacks.items()):
                if current is callback:
                    del fake_activity.callbacks[name]

    event_activity.bind = bind
    event_activity.unbind = unbind

    android_module = types.ModuleType("android")
    android_module.__path__ = []
    android_module.activity = event_activity

    storage_module = types.ModuleType("android.storage")
    storage_module.app_storage_path = lambda: str(tmp_path / "app-private")

    jnius_module = types.ModuleType("jnius")
    openable_columns = types.SimpleNamespace(DISPLAY_NAME="display-name")
    jnius_module.autoclass = lambda name: (
        FakeIntent if name == "android.content.Intent"
        else types.SimpleNamespace(mActivity=fake_activity)
        if name == "org.kivy.android.PythonActivity"
        else openable_columns
    )

    monkeypatch.setitem(sys.modules, "android", android_module)
    monkeypatch.setitem(sys.modules, "android.storage", storage_module)
    monkeypatch.setitem(sys.modules, "jnius", jnius_module)
    monkeypatch.setattr(picker, "Thread", ImmediateThread)
    return fake_activity, resolver


def test_model_picker_copies_gguf_and_returns_local_path_off_ui_callback(monkeypatch, tmp_path):
    activity, resolver = _install_android_mocks(monkeypatch, tmp_path, data=b"GGUF-demo-model")
    selected = []
    errors = []
    cancelled = []

    assert picker.open_model_document(selected.append, on_error=errors.append, on_cancel=lambda: cancelled.append(True))
    intent, request_code = activity.started
    assert intent.action == FakeIntent.ACTION_OPEN_DOCUMENT
    assert intent.mime_type == "*/*"
    assert request_code == 18428

    callback = activity.callbacks["on_activity_result"]
    callback(request_code, -1, FakeResultIntent())

    destination = tmp_path / "app-private" / "imports" / "tiny.gguf"
    assert selected == [str(destination)]
    assert destination.read_bytes() == b"GGUF-demo-model"
    assert resolver.stream.closed
    assert errors == []
    assert cancelled == []
    assert callback in activity.unbound


def test_model_picker_cancel_calls_cancel_callback_and_releases_callback(monkeypatch, tmp_path):
    activity, _resolver = _install_android_mocks(monkeypatch, tmp_path)
    selected, errors, cancelled = [], [], []

    assert picker.open_model_document(selected.append, on_error=errors.append, on_cancel=lambda: cancelled.append(True))
    callback = activity.callbacks["on_activity_result"]
    callback(18428, 0, None)

    assert selected == []
    assert errors == []
    assert cancelled == [True]
    assert callback in activity.unbound


def test_model_picker_rejects_non_gguf_without_uncaught_activity_exception(monkeypatch, tmp_path):
    activity, _resolver = _install_android_mocks(monkeypatch, tmp_path, display_name="notes.txt")
    selected, errors, cancelled = [], [], []

    assert picker.open_model_document(selected.append, on_error=errors.append, on_cancel=lambda: cancelled.append(True))
    callback = activity.callbacks["on_activity_result"]
    callback(18428, -1, FakeResultIntent())

    assert selected == []
    assert errors == ["Yalnızca .gguf model dosyaları destekleniyor"]
    assert cancelled == []


def test_model_picker_reports_uri_copy_error_and_cleans_busy_flow(monkeypatch, tmp_path):
    activity, _resolver = _install_android_mocks(
        monkeypatch, tmp_path, error=OSError("provider-specific path details")
    )
    selected, errors, cancelled = [], [], []

    assert picker.open_model_document(selected.append, on_error=errors.append, on_cancel=lambda: cancelled.append(True))
    callback = activity.callbacks["on_activity_result"]
    callback(18428, -1, FakeResultIntent())

    assert selected == []
    assert errors == [
        "Dosya okunamadı. Depolama alanını ve dosya erişimini kontrol edip tekrar dene."
    ]
    assert cancelled == []


def test_model_picker_uses_gguf_fallback_when_provider_omits_display_name(monkeypatch, tmp_path):
    activity, resolver = _install_android_mocks(monkeypatch, tmp_path, display_name=None, data=b"not parsed by picker")
    selected, errors = [], []

    assert picker.open_model_document(selected.append, on_error=errors.append)
    callback = activity.callbacks["on_activity_result"]
    callback(18428, -1, FakeResultIntent())

    assert selected == [str(tmp_path / "app-private" / "imports" / "model.gguf")]
    assert errors == []


def test_model_picker_enforces_copy_size_limit_and_does_not_leave_partial_file(monkeypatch, tmp_path):
    activity, _resolver = _install_android_mocks(monkeypatch, tmp_path, data=b"0123456789")
    selected, errors = [], []
    monkeypatch.setattr(
        picker,
        "_copy_uri_to_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("Model dosyası izin verilen boyuttan büyük")),
    )

    assert picker.open_model_document(selected.append, on_error=errors.append)
    callback = activity.callbacks["on_activity_result"]
    callback(18428, -1, FakeResultIntent())

    assert selected == []
    assert errors == ["Model dosyası izin verilen boyuttan büyük"]
    assert not list((tmp_path / "app-private").rglob("*.part")) if (tmp_path / "app-private").exists() else True


def test_model_copy_reports_final_progress(monkeypatch, tmp_path):
    _activity, resolver = _install_android_mocks(monkeypatch, tmp_path, data=b"small model bytes")
    reports = []
    target = picker._copy_uri_to_cache(
        resolver, "content://provider/document/1", "tiny.gguf",
        on_progress=lambda written, total: reports.append((written, total)),
    )
    assert target.read_bytes() == b"small model bytes"
    assert reports[-1] == (len(b"small model bytes"), len(b"small model bytes"))
