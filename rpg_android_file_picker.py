"""Android Storage Access Framework helper with desktop-safe fallback."""
from __future__ import annotations

from pathlib import Path
from typing import Callable


def open_scenario_document(on_path: Callable[[str], None]) -> bool:
    """Open Android's document picker for scenario archives.

    Returns True when the native picker was launched. Returns False on
    non-Android runtimes or when the native bridge is unavailable.
    """
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return False

    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    request_code = 18427

    def on_result(request, result, intent):
        if request != request_code:
            return
        try:
            activity.unbind(on_activity_result=on_result)
        except Exception:
            pass
        if result != -1 or intent is None:
            return
        uri = intent.getData()
        if uri is None:
            return
        resolver = PythonActivity.mActivity.getContentResolver()
        name = _display_name(resolver, uri)
        if not name.lower().endswith((".zip", ".rpgscenario.zip")):
            raise ValueError("Seçilen dosya bir .rpgscenario.zip değil")
        destination = _copy_uri_to_cache(resolver, uri, name)
        on_path(str(destination))

    activity.bind(on_activity_result=on_result)
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("application/zip")
    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, False)
    PythonActivity.mActivity.startActivityForResult(intent, request_code)
    return True


def _display_name(resolver, uri) -> str:
    from jnius import autoclass
    OpenableColumns = autoclass("android.provider.OpenableColumns")
    cursor = resolver.query(uri, [OpenableColumns.DISPLAY_NAME], None, None, None)
    if cursor is None:
        return "scenario.rpgscenario.zip"
    try:
        if cursor.moveToFirst():
            idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if idx >= 0:
                return str(cursor.getString(idx))
    finally:
        cursor.close()
    return "scenario.rpgscenario.zip"


def _copy_uri_to_cache(resolver, uri, name: str, subdir: str = "imports", max_bytes: int | None = None) -> Path:
    from android.storage import app_storage_path
    cache = Path(app_storage_path()) / subdir
    cache.mkdir(parents=True, exist_ok=True)
    safe_name = Path(name).name.replace("/", "_").replace("\\", "_")
    target = cache / safe_name
    stream = resolver.openInputStream(uri)
    try:
        written = 0
        try:
            with target.open("wb") as output:
                buffer = bytearray(64 * 1024)
                while True:
                    count = stream.read(buffer)
                    if count <= 0:
                        break
                    written += count
                    if max_bytes is not None and written > max_bytes:
                        raise ValueError("Model dosyası izin verilen boyuttan büyük")
                    output.write(buffer[:count])
        except Exception:
            target.unlink(missing_ok=True)
            raise
    finally:
        stream.close()
    return target


def open_model_document(on_path: Callable[[str], None]) -> bool:
    """Open Android SAF for a local GGUF model and copy it to app-private storage."""
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return False

    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    request_code = 18428

    def on_result(request, result, intent):
        if request != request_code:
            return
        try:
            activity.unbind(on_activity_result=on_result)
        except Exception:
            pass
        if result != -1 or intent is None:
            return
        uri = intent.getData()
        if uri is None:
            return
        resolver = PythonActivity.mActivity.getContentResolver()
        name = _display_name(resolver, uri)
        if not name.lower().endswith(".gguf"):
            raise ValueError("Seçilen dosya bir .gguf model dosyası değil")
        destination = _copy_uri_to_cache(resolver, uri, name, subdir="imports", max_bytes=3 * 1024 * 1024 * 1024)
        on_path(str(destination))

    activity.bind(on_activity_result=on_result)
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("application/octet-stream")
    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, False)
    PythonActivity.mActivity.startActivityForResult(intent, request_code)
    return True
