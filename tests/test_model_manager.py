from __future__ import annotations

from pathlib import Path
import struct

from engine.ai.model_manager import (
    BYTES_PER_GIB,
    HARD_MAX_MODEL_BYTES,
    ModelFormatError,
    ModelIntegrityError,
    ModelSpec,
    ModelSpecError,
    ModelSizeError,
    download_huggingface_model,
    install_imported_model,
    list_installed_models,
    model_storage_dir,
    validate_model_file,
)


def test_model_storage_dir_is_scoped_to_models(tmp_path):
    directory = model_storage_dir(tmp_path)
    assert directory == (tmp_path / "models").resolve()
    assert directory.is_dir()


def test_model_spec_builds_safe_huggingface_url():
    spec = ModelSpec("org/example-model", "example.Q4_K_M.gguf", expected_size_bytes=1234)
    assert spec.resolved_url == (
        "https://huggingface.co/org/example-model/resolve/main/"
        "example.Q4_K_M.gguf?download=true"
    )
    assert spec.destination_name == "org__example-model--example.Q4_K_M.gguf"


def test_model_spec_rejects_path_traversal_and_non_gguf():
    for filename in ("../bad.gguf", "folder/bad.gguf", "bad.bin"):
        try:
            ModelSpec("org/model", filename).validate()
        except ModelSpecError:
            pass
        else:
            raise AssertionError(f"expected ModelSpecError for {filename!r}")


def test_model_spec_rejects_size_above_hard_ceiling():
    try:
        ModelSpec(
            "org/model", "big.gguf", expected_size_bytes=HARD_MAX_MODEL_BYTES + 1
        ).validate()
    except ModelSizeError:
        pass
    else:
        raise AssertionError("expected ModelSizeError")


def _gguf_payload(body: bytes = b"DEMO-MODEL") -> bytes:
    return b"GGUF" + struct.pack("<I", 3) + struct.pack("<QQ", 0, 0) + body


def test_import_is_atomic_and_hashes_file(tmp_path):
    source = tmp_path / "source.gguf"
    source.write_bytes(_gguf_payload())
    installed = install_imported_model(source, tmp_path / "app")
    assert installed.path.exists()
    assert installed.path.read_bytes() == source.read_bytes()
    assert not list((tmp_path / "app").glob("*.part"))
    assert validate_model_file(installed.path).sha256 == installed.sha256


def test_import_rejects_wrong_hash_and_cleans_partial(tmp_path):
    source = tmp_path / "source.gguf"
    source.write_bytes(_gguf_payload())
    try:
        install_imported_model(source, tmp_path / "app", expected_sha256="0" * 64)
    except ModelIntegrityError:
        pass
    else:
        raise AssertionError("expected ModelIntegrityError")
    assert not list((tmp_path / "app").glob("*.part"))
    assert not list((tmp_path / "app").glob("*.gguf"))


def test_list_installed_models_ignores_invalid_files(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "good.gguf").write_bytes(_gguf_payload())
    (models / "notes.txt").write_text("not a model")
    result = list_installed_models(models)
    assert [item.name for item in result] == ["good.gguf"]


def test_model_header_validation_rejects_fake_gguf(tmp_path):
    source = tmp_path / "fake.gguf"
    source.write_bytes(b"GGUF" + struct.pack("<I", 99) + b"x" * 16)
    try:
        validate_model_file(source)
    except ModelFormatError:
        pass
    else:
        raise AssertionError("expected ModelFormatError")


def test_fast_model_listing_does_not_require_sha256(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "good.gguf").write_bytes(_gguf_payload())

    import engine.ai.model_manager as module
    original = module._sha256_file
    module._sha256_file = lambda _path: (_ for _ in ()).throw(AssertionError("hash should not run"))
    try:
        result = list_installed_models(models, verify_integrity=False)
    finally:
        module._sha256_file = original
    assert result[0].sha256 == ""



def test_download_uses_expected_size_and_hash(tmp_path):
    payload = _gguf_payload(b"REMOTE")
    sha = __import__("hashlib").sha256(payload).hexdigest()

    class FakeResponse:
        def __init__(self):
            self.headers = {"Content-Length": str(len(payload))}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            nonlocal payload
            if not payload:
                return b""
            chunk, payload = payload[:size], payload[size:]
            return chunk

    def opener(_request, timeout):
        assert timeout == 60
        return FakeResponse()

    spec = ModelSpec(
        "org/model", "model.Q4_K_M.gguf", expected_size_bytes=len(payload), expected_sha256=sha
    )
    installed = download_huggingface_model(spec, tmp_path / "models", opener=opener)
    assert installed.path.exists()
    assert installed.sha256 == sha
