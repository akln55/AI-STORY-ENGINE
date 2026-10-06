"""Minimal Android entrypoint with first-launch failure diagnostics."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import traceback


def _runtime_log_dir() -> Path:
    try:
        from android.storage import app_storage_path  # type: ignore
    except Exception:
        root = Path.cwd()
    else:
        try:
            root = Path(app_storage_path())
        except Exception:
            root = Path.cwd()
    path = root / "diagnostics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_startup_failure(stage: str, exc: BaseException) -> Path | None:
    try:
        log_path = _runtime_log_dir() / "startup_error.log"
        payload = (
            f"timestamp={datetime.now(timezone.utc).isoformat()}\n"
            f"stage={stage}\n"
            f"python={sys.version}\n"
            f"platform={sys.platform}\n\n"
            f"{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}"
        )
        log_path.write_text(payload, encoding="utf-8")
        return log_path
    except Exception:
        return None


def _show_fallback_failure(stage: str, exc: BaseException, log_path: Path | None) -> None:
    """Try to keep the app visible long enough to expose the first-launch error."""
    try:
        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.metrics import dp

        location = str(log_path) if log_path else "diagnostics/startup_error.log"

        class StartupFailureApp(App):
            title = "RPG Engine"

            def build(self):
                root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(18))
                root.add_widget(Label(
                    text="RPG Engine başlatılamadı",
                    font_size=dp(24),
                    halign="left",
                    valign="middle",
                    size_hint_y=None,
                    height=dp(52),
                ))
                detail = (
                    f"Açılış aşaması: {stage}\n\n"
                    f"Hata: {type(exc).__name__}: {exc}\n\n"
                    f"Tanı kaydı:\n{location}\n\n"
                    "Bu ekran yalnızca hata teşhisi içindir."
                )
                message = Label(text=detail, halign="left", valign="top")
                message.bind(size=lambda *_: setattr(message, "text_size", message.size))
                root.add_widget(message)
                return root

        StartupFailureApp().run()
    except Exception as fallback_exc:
        sys.stderr.write(
            "RPG Engine startup failure; fallback UI unavailable.\n"
            f"primary={type(exc).__name__}: {exc}\n"
            f"fallback={type(fallback_exc).__name__}: {fallback_exc}\n"
        )


def _boot() -> int:
    try:
        from rpg_android_app import RPGEngineApp
    except Exception as exc:
        log_path = _write_startup_failure("android_entrypoint_import", exc)
        _show_fallback_failure("android_entrypoint_import", exc, log_path)
        return 1

    try:
        app = RPGEngineApp()
        app.run()
    except Exception as exc:
        log_path = _write_startup_failure("application_runtime", exc)
        # Re-raise after logging so the process exit code remains non-zero in CI/debug.
        if log_path:
            sys.stderr.write(f"RPG Engine startup log: {log_path}\n")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(_boot())
