"""Android Storage Access Framework helper with desktop-safe fallback."""
from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import Callable
import logging
from uuid import uuid4


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
        name = _display_name(resolver, uri, default="scenario.rpgscenario.zip")
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


def _display_name(resolver, uri, *, default: str = "document") -> str:
    """Read a SAF display name, using a caller-specific safe fallback if unavailable."""
    from jnius import autoclass
    OpenableColumns = autoclass("android.provider.OpenableColumns")
    cursor = resolver.query(uri, [OpenableColumns.DISPLAY_NAME], None, None, None)
    if cursor is None:
        return default
    try:
        if cursor.moveToFirst():
            idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if idx >= 0:
                value = cursor.getString(idx)
                if value:
                    return str(value)
    finally:
        cursor.close()
    return default


def _copy_uri_to_cache(resolver, uri, name: str, subdir: str = "imports", max_bytes: int | None = None, on_progress: Callable[[int, int | None], None] | None = None) -> Path:
    """Copy a SAF document atomically so failed imports never leave partial targets."""
    from android.storage import app_storage_path
    cache = Path(app_storage_path()) / subdir
    cache.mkdir(parents=True, exist_ok=True)
    safe_name = Path(name).name.replace("/", "_").replace("\\", "_")
    if safe_name in {"", ".", ".."}:
        raise ValueError("Seçilen dosyanın adı geçersiz")
    target = cache / safe_name
    temporary = cache / ("." + safe_name + "." + uuid4().hex + ".part")
    stream = resolver.openInputStream(uri)
    if stream is None:
        raise OSError("Seçilen dosya açılamadı")
    try:
        written = 0
        next_progress = 8 * 1024 * 1024
        try:
            with temporary.open("wb") as output:
                buffer = bytearray(64 * 1024)
                while True:
                    count = stream.read(buffer)
                    if count <= 0:
                        break
                    written += count
                    if max_bytes is not None and written > max_bytes:
                        raise ValueError("Model dosyası izin verilen boyuttan büyük")
                    output.write(buffer[:count])
                    if on_progress is not None and written >= next_progress:
                        on_progress(written, None)
                        next_progress = written + 8 * 1024 * 1024
        finally:
            stream.close()
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if on_progress is not None:
        try:
            on_progress(written, written)
        except Exception:
            logging.getLogger(__name__).debug("GGUF progress callback failed", exc_info=True)
    return target


def _model_picker_error_message(exc: BaseException) -> str:
    """Expose a safe, actionable import error without leaking raw provider paths."""
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, OSError):
        return "Dosya okunamadı. Depolama alanını ve dosya erişimini kontrol edip tekrar dene."
    logging.getLogger(__name__).warning("GGUF picker failed (%s)", type(exc).__name__)
    return "GGUF dosyası içe aktarılamadı. Dosyanın geçerli ve erişilebilir olduğundan emin ol."


def save_scenario_document(
    source_path: str | Path,
    suggested_name: str,
    on_saved: Callable[[str], None],
    on_error: Callable[[str], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
) -> bool:
    """Use Android SAF to save a generated scenario ZIP to user-selected storage."""
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return False

    source = Path(source_path)
    if not source.is_file() or not source.name.lower().endswith(".rpgscenario.zip"):
        raise ValueError("Kaydedilecek dosya geçerli bir .rpgscenario.zip olmalı")

    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    request_code = 18430

    def on_result(request, result, intent):
        if request != request_code:
            return
        try:
            activity.unbind(on_activity_result=on_result)
        except Exception:
            pass
        if result != -1 or intent is None:
            if on_cancel is not None:
                on_cancel()
            return
        uri = intent.getData()
        if uri is None:
            if on_cancel is not None:
                on_cancel()
            return
        stream = None
        try:
            resolver = PythonActivity.mActivity.getContentResolver()
            stream = resolver.openOutputStream(uri)
            if stream is None:
                raise OSError("Seçilen konum yazılabilir değil")
            with source.open("rb") as input_file:
                while True:
                    chunk = input_file.read(64 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)
            stream.flush()
            stream.close()
            stream = None
            on_saved(str(uri.toString()))
        except Exception as exc:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            if on_error is not None:
                on_error(type(exc).__name__)
            else:
                raise

    activity.bind(on_activity_result=on_result)
    intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("application/zip")
    intent.putExtra(Intent.EXTRA_TITLE, Path(suggested_name).name)
    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, False)
    PythonActivity.mActivity.startActivityForResult(intent, request_code)
    return True


def open_source_document(on_path: Callable[[str], None]) -> bool:
    """Open Android SAF for a UTF-8 source text file (.txt or .md)."""
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return False

    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    request_code = 18429

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
        name = _display_name(resolver, uri, default="source.md")
        if Path(name).suffix.casefold() not in {".txt", ".md"}:
            raise ValueError("Yalnızca .txt ve .md kaynak dosyaları destekleniyor")
        destination = _copy_uri_to_cache(
            resolver, uri, name, subdir="source_imports", max_bytes=32 * 1024 * 1024,
        )
        on_path(str(destination))

    activity.bind(on_activity_result=on_result)
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")
    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, False)
    PythonActivity.mActivity.startActivityForResult(intent, request_code)
    return True


def open_model_document(
    on_path: Callable[[str], None],
    *,
    on_error: Callable[[str], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> bool:
    """Pick a GGUF document; copy it off-thread so large files cannot freeze the UI.

    The temporary copy is atomic and errors/cancellation have explicit callbacks,
    allowing the app to clear its busy state instead of leaving a black screen.
    """
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return False

    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    request_code = 18428

    def report_error(exc: BaseException) -> None:
        message = _model_picker_error_message(exc)
        if on_error is not None:
            try:
                on_error(message)
            except Exception:
                logging.getLogger(__name__).exception("GGUF import error callback failed")
        else:
            logging.getLogger(__name__).warning("GGUF import failed: %s", message)

    def on_result(request, result, intent):
        if request != request_code:
            return
        try:
            activity.unbind(on_activity_result=on_result)
        except Exception:
            pass
        if result != -1 or intent is None:
            if on_cancel is not None:
                on_cancel()
            return

        try:
            uri = intent.getData()
            if uri is None:
                if on_cancel is not None:
                    on_cancel()
                return
            resolver = PythonActivity.mActivity.getContentResolver()
            name = _display_name(resolver, uri, default="model.gguf")
            if not name.casefold().endswith(".gguf"):
                raise ValueError("Yalnızca .gguf model dosyaları destekleniyor")
        except Exception as exc:
            report_error(exc)
            return

        def copy_worker():
            try:
                destination = _copy_uri_to_cache(
                    resolver, uri, name, subdir="imports",
                    max_bytes=3 * 1024 * 1024 * 1024,
                    on_progress=on_progress,
                )
                on_path(str(destination))
            except Exception as exc:
                report_error(exc)

        try:
            Thread(target=copy_worker, name="gguf-import-copy", daemon=True).start()
        except Exception as exc:
            report_error(exc)

    activity.bind(on_activity_result=on_result)
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    # GGUF has no universal Android MIME type; filter by extension after selection.
    intent.setType("*/*")
    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, False)
    PythonActivity.mActivity.startActivityForResult(intent, request_code)
    return True
