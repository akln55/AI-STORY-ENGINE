from __future__ import annotations

from pathlib import Path

from engine.ai.llama_native_runtime import (
    NativeLlamaRuntimeConfig,
    NativeLlamaRuntimeConfigError,
    NativeLlamaRuntimeStartError,
    NativeLlamaServer,
    install_runtime_binary,
    packaged_llama_server_path,
    pick_free_local_port,
)


def _assert_raises(exc_type, func):
    try:
        func()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_packaged_runtime_path_is_arm64_specific():
    path = packaged_llama_server_path(Path("/repo"))
    assert path.as_posix().endswith("android_native/arm64-v8a/llama-server.bin")


def test_runtime_requires_loopback_host():
    config = NativeLlamaRuntimeConfig("runtime.bin", "runtime", "model.gguf", host="0.0.0.0")
    _assert_raises(NativeLlamaRuntimeConfigError, config.validate)


def test_command_is_local_only_and_explicit(tmp_path: Path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF-test")
    config = NativeLlamaRuntimeConfig(
        "runtime.bin", "runtime", model, port=8123, ctx_size=4096, max_tokens=256, threads=6
    )
    server = NativeLlamaServer(config)
    command = server.build_command(Path("/private/llama-server"))
    assert command == [
        "/private/llama-server",
        "--model", str(model.resolve()),
        "--host", "127.0.0.1",
        "--port", "8123",
        "--ctx-size", "4096",
        "--n-predict", "256",
        "--threads", "6",
    ]


def test_runtime_binary_install_is_atomic_and_executable(tmp_path: Path):
    source = tmp_path / "source.bin"
    header = bytearray(2048)
    header[:4] = b"\x7fELF"
    header[4] = 2  # ELF64
    header[5] = 1  # little-endian
    header[18:20] = (183).to_bytes(2, "little")  # AArch64
    source.write_bytes(header)
    runtime_dir = tmp_path / "runtime"
    installed = install_runtime_binary(source, runtime_dir)
    assert installed.exists()
    assert installed.read_bytes() == source.read_bytes()
    assert installed.stat().st_mode & 0o111
    assert not (runtime_dir / "llama-server.part").exists()


def test_runtime_binary_must_exist(tmp_path: Path):
    config = NativeLlamaRuntimeConfig(tmp_path / "missing.bin", tmp_path / "runtime", tmp_path / "model.gguf")
    _assert_raises(NativeLlamaRuntimeStartError, NativeLlamaServer(config).start)


def test_pick_free_local_port_returns_loopback_port():
    port = pick_free_local_port()
    assert 1024 <= port <= 65535
