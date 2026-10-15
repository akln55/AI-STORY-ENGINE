from __future__ import annotations

import os
from pathlib import Path

import pytest

from engine.ai.llama_native_runtime import (
    NativeLlamaRuntimeConfig,
    NativeLlamaRuntimeConfigError,
    NativeLlamaRuntimeStartError,
    NativeLlamaServer,
    packaged_llama_server_path,
    pick_free_local_port,
    validate_runtime_binary,
)


def _write_elf(path: Path, *, machine: int = 183, elf_type: int = 3, executable: bool = True) -> None:
    header = bytearray(2048)
    header[:4] = bytes((0x7F, 0x45, 0x4C, 0x46))
    header[4] = 2  # ELF64
    header[5] = 1  # little-endian
    header[16:18] = elf_type.to_bytes(2, "little")  # ET_DYN PIE executable
    header[18:20] = machine.to_bytes(2, "little")  # EM_AARCH64
    path.write_bytes(header)
    os.chmod(path, 0o755 if executable else 0o644)


def _assert_raises(exc_type, func):
    try:
        func()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_packaged_runtime_path_is_arm64_native_library():
    path = packaged_llama_server_path(Path("/repo"))
    assert path.as_posix().endswith("android_native/arm64-v8a/libllama-server.so")


def test_packaged_runtime_resolves_android_native_library_dir(monkeypatch):
    import sys
    import types

    class FakeActivity:
        def getApplicationInfo(self):
            return types.SimpleNamespace(nativeLibraryDir="/data/app/example/lib/arm64")

    fake_kivy = types.ModuleType("kivy")
    fake_kivy.__path__ = []
    fake_utils = types.ModuleType("kivy.utils")
    fake_utils.platform = "android"
    fake_jnius = types.ModuleType("jnius")
    fake_jnius.autoclass = lambda name: types.SimpleNamespace(mActivity=FakeActivity())
    monkeypatch.setitem(sys.modules, "kivy", fake_kivy)
    monkeypatch.setitem(sys.modules, "kivy.utils", fake_utils)
    monkeypatch.setitem(sys.modules, "jnius", fake_jnius)

    assert packaged_llama_server_path() == Path("/data/app/example/lib/arm64/libllama-server.so")


def test_runtime_requires_loopback_host():
    config = NativeLlamaRuntimeConfig("runtime.so", "runtime", "model.gguf", host="0.0.0.0")
    _assert_raises(NativeLlamaRuntimeConfigError, config.validate)


def test_command_is_local_only_and_explicit(tmp_path: Path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF-test")
    config = NativeLlamaRuntimeConfig(
        "runtime.so", "runtime", model, port=8123, ctx_size=4096, max_tokens=256, threads=6
    )
    server = NativeLlamaServer(config)
    command = server.build_command(Path("/native/libllama-server.so"))
    assert command == [
        "/native/libllama-server.so",
        "--model", str(model.resolve()),
        "--host", "127.0.0.1",
        "--port", "8123",
        "--ctx-size", "4096",
        "--n-predict", "256",
        "--threads", "6",
    ]


def test_runtime_validation_returns_packaged_executable_without_copy(tmp_path: Path):
    source = tmp_path / "libllama-server.so"
    _write_elf(source)
    validated = validate_runtime_binary(source)
    assert validated == source.resolve()
    assert not (tmp_path / "native_runtime" / "llama-server").exists()


def test_runtime_binary_must_exist(tmp_path: Path):
    with pytest.raises(NativeLlamaRuntimeStartError, match="not found"):
        validate_runtime_binary(tmp_path / "missing.so")


def test_runtime_binary_rejects_wrong_elf_type(tmp_path: Path):
    source = tmp_path / "libllama-server.so"
    _write_elf(source, elf_type=2)
    with pytest.raises(NativeLlamaRuntimeStartError, match="PIE executable"):
        validate_runtime_binary(source)


def test_runtime_binary_rejects_wrong_architecture(tmp_path: Path):
    source = tmp_path / "libllama-server.so"
    _write_elf(source, machine=62)
    with pytest.raises(NativeLlamaRuntimeStartError, match="not ARM64"):
        validate_runtime_binary(source)


def test_runtime_binary_must_be_executable(tmp_path: Path):
    source = tmp_path / "libllama-server.so"
    _write_elf(source, executable=False)
    with pytest.raises(NativeLlamaRuntimeStartError, match="not executable"):
        validate_runtime_binary(source)


def test_server_launches_native_library_in_place(tmp_path: Path, monkeypatch):
    source = tmp_path / "libllama-server.so"
    _write_elf(source)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF-test")
    runtime_dir = tmp_path / "native_runtime"
    config = NativeLlamaRuntimeConfig(source, runtime_dir, model, port=8124)
    server = NativeLlamaServer(config)

    class FakeProcess:
        pid = 2147483000
        returncode = None

        def poll(self):
            return None

        def terminate(self):
            self.returncode = 0

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr("engine.ai.llama_native_runtime.subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(server, "health_check", lambda timeout=1.0: True)
    assert server.start() == "http://127.0.0.1:8124"
    assert server.binary_path == source.resolve()
    assert not (runtime_dir / "llama-server").exists()


def test_permission_denied_diagnostic_identifies_packaged_path(tmp_path: Path, monkeypatch):
    source = tmp_path / "libllama-server.so"
    _write_elf(source)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF-test")
    runtime_dir = tmp_path / "native_runtime"
    config = NativeLlamaRuntimeConfig(source, runtime_dir, model, port=8125)
    server = NativeLlamaServer(config)

    def denied(*args, **kwargs):
        raise PermissionError(13, "Permission denied", str(source))

    monkeypatch.setattr("engine.ai.llama_native_runtime.subprocess.Popen", denied)
    with pytest.raises(NativeLlamaRuntimeStartError, match="Permission denied") as error:
        server.start()
    assert str(source) in str(error.value)
    assert not (runtime_dir / "llama-server").exists()


def test_pick_free_local_port_returns_loopback_port():
    port = pick_free_local_port()
    assert 1024 <= port <= 65535
