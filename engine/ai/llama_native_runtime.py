"""Android-native llama.cpp server lifecycle.

This module is the bridge between the Python engine and a packaged
``llama-server`` ARM64 Android executable. The executable is built separately
and injected into the Android source tree during the Android build; this
module never downloads or executes arbitrary native code.

The server executable is loaded from Android's package-managed native-library
folder. It must not be copied into writable app-private storage: Android 10+
blocks executing files from that location for apps targeting API 29+.
Only logs and mutable runtime state belong in app-private storage. The server
remains local-only (127.0.0.1).
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request


class NativeLlamaRuntimeError(Exception):
    """Base error for the Android-native llama runtime."""


class NativeLlamaRuntimeConfigError(NativeLlamaRuntimeError):
    """Raised when runtime configuration is invalid."""


class NativeLlamaRuntimeStartError(NativeLlamaRuntimeError):
    """Raised when llama-server cannot be started or become healthy."""


@dataclass(frozen=True)
class NativeLlamaRuntimeConfig:
    binary_source: Path | str
    runtime_dir: Path | str
    model_path: Path | str
    host: str = "127.0.0.1"
    port: int = 8080
    ctx_size: int = 2048
    max_tokens: int = 192
    threads: int | None = 4
    batch_size: int = 256
    ubatch_size: int = 128
    health_timeout: float = 45.0

    def validate(self) -> None:
        if self.host != "127.0.0.1":
            raise NativeLlamaRuntimeConfigError("native local runtime must bind to 127.0.0.1")
        if not 1024 <= self.port <= 65535:
            raise NativeLlamaRuntimeConfigError("port must be in the unprivileged TCP range")
        if self.ctx_size <= 0 or self.max_tokens <= 0:
            raise NativeLlamaRuntimeConfigError("ctx_size and max_tokens must be positive")
        if self.threads is not None and self.threads <= 0:
            raise NativeLlamaRuntimeConfigError("threads must be positive when set")
        if self.batch_size <= 0 or self.ubatch_size <= 0 or self.ubatch_size > self.batch_size:
            raise NativeLlamaRuntimeConfigError("batch sizes must be positive and ubatch_size cannot exceed batch_size")
        if self.health_timeout <= 0:
            raise NativeLlamaRuntimeConfigError("health_timeout must be positive")


def default_runtime_dir(root: Path | str | None = None) -> Path:
    """Return/create the app-private directory used for native runtime state."""
    if root is None:
        try:
            from android.storage import app_storage_path  # type: ignore
        except ImportError:
            root = Path.home() / ".rpgengine"
        else:
            root = Path(app_storage_path())
    directory = Path(root).expanduser().resolve() / "native_runtime"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


NATIVE_SERVER_FILENAME = "libllama-server.so"
NATIVE_SERVER_SOURCE = Path("android_native") / "arm64-v8a" / NATIVE_SERVER_FILENAME


def packaged_llama_server_path(project_root: Path | str | None = None) -> Path:
    """Resolve the server path from Android nativeLibraryDir or source tree.

    Android's PackageManager extracts lib-prefixed shared-library entries from
    the APK to ApplicationInfo.nativeLibraryDir with executable permissions.
    Passing project_root explicitly returns the build/source artifact path.
    On Android, resolution failure is reported rather than falling back to an
    executable copy in writable app-private storage.
    """
    if project_root is not None:
        return Path(project_root).resolve() / NATIVE_SERVER_SOURCE

    try:
        from kivy.utils import platform
    except ImportError:
        platform = "unknown"

    if platform == "android":
        try:
            from jnius import autoclass
            python_activity = autoclass("org.kivy.android.PythonActivity")
            activity = python_activity.mActivity
            native_library_dir = str(activity.getApplicationInfo().nativeLibraryDir)
            if not native_library_dir:
                raise RuntimeError("Android returned an empty nativeLibraryDir")
            return Path(native_library_dir) / NATIVE_SERVER_FILENAME
        except Exception as exc:
            raise NativeLlamaRuntimeStartError(
                "could not resolve Android's package-managed native library directory for llama-server"
            ) from exc

    return Path(__file__).resolve().parents[2] / NATIVE_SERVER_SOURCE


def validate_runtime_binary(source: Path | str) -> Path:
    """Validate the already-installed, package-managed native server executable.

    Android 10+ blocks execution of binaries copied into writable app data for
    modern target SDKs. This function never copies or chmods the binary;
    Android must install it into nativeLibraryDir from the APK's lib directory.
    """
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        raise NativeLlamaRuntimeStartError(f"packaged native runtime not found: {src}")
    if src.stat().st_size < 1024:
        raise NativeLlamaRuntimeStartError("packaged native runtime appears invalid or truncated")
    with src.open("rb") as input_file:
        header = input_file.read(20)
    # ELF64 AArch64 PIE: magic + class=2 + little-endian=1 + ET_DYN + EM_AARCH64=183.
    if len(header) < 20 or header[:4] != b"\x7fELF" or header[4] != 2 or header[5] != 1:
        raise NativeLlamaRuntimeStartError("packaged native runtime is not a valid ELF64 binary")
    elf_type = int.from_bytes(header[16:18], "little")
    if elf_type != 3:
        raise NativeLlamaRuntimeStartError(f"packaged native runtime is not a PIE executable (ELF type={elf_type})")
    machine = int.from_bytes(header[18:20], "little")
    if machine != 183:
        raise NativeLlamaRuntimeStartError(f"packaged native runtime is not ARM64 (ELF machine={machine})")
    if not os.access(src, os.X_OK):
        raise NativeLlamaRuntimeStartError(
            f"packaged native runtime is not executable: {src}; ensure it is packaged as lib/arm64-v8a/libllama-server.so"
        )
    return src


def pick_free_local_port() -> int:
    """Reserve a free loopback TCP port for one local llama-server instance."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class NativeLlamaServer:
    """Own one app-private llama-server process."""

    def __init__(self, config: NativeLlamaRuntimeConfig):
        config.validate()
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None
        self.binary_path: Path | None = None
        self.log_path: Path | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def build_command(self, binary_path: Path) -> list[str]:
        model = Path(self.config.model_path).expanduser().resolve()
        if not model.is_file():
            raise NativeLlamaRuntimeConfigError(f"model file not found: {model}")
        command = [
            str(binary_path),
            "--model", str(model),
            "--host", self.config.host,
            "--port", str(self.config.port),
            "--ctx-size", str(self.config.ctx_size),
            "--n-predict", str(self.config.max_tokens),
            "--batch-size", str(self.config.batch_size),
            "--ubatch-size", str(self.config.ubatch_size),
        ]
        if self.config.threads is not None:
            command.extend(["--threads", str(self.config.threads)])
        return command

    def start(self) -> str:
        if self.running:
            return self.base_url
        runtime_dir = Path(self.config.runtime_dir).expanduser().resolve()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self.binary_path = validate_runtime_binary(self.config.binary_source)
        command = self.build_command(self.binary_path)
        self.log_path = runtime_dir / "llama-server.log"
        log_handle = self.log_path.open("ab")
        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(runtime_dir),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                close_fds=True,
                start_new_session=True,
            )
            log_handle.close()
        except OSError as exc:
            log_handle.close()
            raise NativeLlamaRuntimeStartError(
                f"could not start packaged llama-server at {self.binary_path}: {exc}"
            ) from exc

        deadline = time.monotonic() + self.config.health_timeout
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise NativeLlamaRuntimeStartError(
                        f"llama-server exited early with code {self.process.returncode}; see {self.log_path}"
                    )
                if self.health_check():
                    return self.base_url
                time.sleep(0.25)
        except Exception:
            self.stop()
            raise

        self.stop()
        raise NativeLlamaRuntimeStartError(
            f"llama-server did not become healthy within {self.config.health_timeout:.0f}s"
        )

    def health_check(self, timeout: float = 1.0) -> bool:
        try:
            with urllib.request.urlopen(self.base_url + "/health", timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def stop(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                try:
                    process.terminate()
                except OSError:
                    pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    try:
                        process.kill()
                    except OSError:
                        pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
