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
    list_huggingface_gguf_files,
    search_huggingface_models,
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


def test_huggingface_search_returns_validated_repository_metadata():
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps([
                {"id": "Qwen/Qwen3-1.7B-GGUF", "downloads": 1234, "likes": 56},
                {"id": "../unsafe", "downloads": 999},
                {"id": "invalid"},
            ]).encode()

    def opener(request, timeout):
        assert request.full_url.startswith("https://huggingface.co/api/models?")
        assert "filter=gguf" in request.full_url
        assert timeout == 20
        return FakeResponse()

    results = search_huggingface_models("Qwen GGUF", opener=opener)
    assert len(results) == 1
    assert results[0].repo_id == "Qwen/Qwen3-1.7B-GGUF"
    assert results[0].downloads == 1234
    assert results[0].likes == 56


def test_huggingface_search_falls_back_when_gguf_filter_returns_empty():
    import json

    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    def opener(request, timeout):
        calls.append(request.full_url)
        if "filter=gguf" in request.full_url:
            return FakeResponse([])
        return FakeResponse([
            {"id": "Qwen/Qwen3-1.7B-GGUF", "downloads": "42", "likes": "3"},
            {"id": "Qwen/Qwen3-1.7B", "downloads": 9999, "tags": ["text-generation"]},
            {"id": "../unsafe-GGUF", "downloads": 5},
        ])

    results = search_huggingface_models("Qwen", opener=opener)
    assert len(calls) == 2
    assert len(results) == 1
    assert results[0].repo_id == "Qwen/Qwen3-1.7B-GGUF"
    assert results[0].downloads == 42
    assert results[0].likes == 3


def test_huggingface_file_listing_only_returns_safe_gguf_under_size_limit():
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "siblings": [
                    {"rfilename": "model.Q4_K_M.gguf", "size": 1024},
                    {"rfilename": "folder/nested.gguf", "size": 1024},
                    {"rfilename": "too-big.gguf", "size": HARD_MAX_MODEL_BYTES + 1},
                    {"rfilename": "readme.md", "size": 50},
                    {"rfilename": "unknown-size.gguf"},
                ]
            }).encode()

    def opener(request, timeout):
        assert request.full_url == "https://huggingface.co/api/models/Qwen/model?blobs=true"
        assert timeout == 20
        return FakeResponse()

    files = list_huggingface_gguf_files("Qwen/model", opener=opener)
    assert [item.filename for item in files] == ["model.Q4_K_M.gguf", "unknown-size.gguf"]
    assert files[0].size_bytes == 1024
    assert files[1].size_bytes is None


def test_model_spec_rejects_traversal_like_repository_ids():
    for repo_id in ("../unsafe", "org/../model", "./model"):
        try:
            ModelSpec(repo_id, "model.gguf").validate()
        except ModelSpecError:
            pass
        else:
            raise AssertionError(f"expected ModelSpecError for {repo_id!r}")



def test_huggingface_connectivity_probe_uses_public_endpoint_without_download():
    import json
    from engine.ai.model_manager import check_huggingface_connection

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, _size=-1):
            return json.dumps([{"id": "Qwen/Qwen3-1.7B-GGUF"}]).encode()

    def opener(request, timeout):
        assert request.full_url == "https://huggingface.co/api/models?limit=1"
        assert request.get_header("Authorization") is None
        assert timeout == 8.0
        return FakeResponse()

    assert check_huggingface_connection(opener=opener) is None


def test_huggingface_connectivity_probe_reports_dns_failure_without_url_or_secrets():
    import urllib.error
    from engine.ai.model_manager import ModelDiscoveryError, check_huggingface_connection

    def opener(_request, timeout):
        raise urllib.error.URLError(OSError("No address associated with hostname"))

    try:
        check_huggingface_connection(opener=opener)
    except ModelDiscoveryError as exc:
        assert str(exc) == "DNS resolution failed for huggingface.co"
        assert "https://" not in str(exc)
    else:
        raise AssertionError("expected ModelDiscoveryError for DNS failure")



def test_default_https_opener_uses_verified_ssl_context(monkeypatch):
    import ssl
    import engine.ai.model_manager as module

    captured = {}

    def fake_urlopen(request, *, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return object()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    result = module._open_url(
        module.urllib.request.Request("https://huggingface.co/api/models?limit=1"),
        timeout=3.5,
    )
    assert result is not None
    assert captured["timeout"] == 3.5
    assert captured["request"].full_url.startswith("https://huggingface.co/")
    assert isinstance(captured["context"], ssl.SSLContext)
    assert captured["context"].check_hostname is True
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED


def test_injected_https_opener_remains_usable_without_network():
    import engine.ai.model_manager as module

    seen = {}

    def fake_opener(request, *, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return "fixture-response"

    result = module._open_url(
        module.urllib.request.Request("https://huggingface.co/api/models"),
        timeout=2,
        opener=fake_opener,
    )
    assert result == "fixture-response"
    assert seen["timeout"] == 2
    assert seen["url"] == "https://huggingface.co/api/models"



def test_huggingface_file_listing_uses_shared_verified_transport(monkeypatch):
    import json
    import engine.ai.model_manager as module

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "siblings": [{"rfilename": "model.Q4_K_M.gguf", "size": 1024}]
            }).encode()

    seen = {}

    def fake_open_url(request, *, timeout, opener=None):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["opener"] = opener
        return FakeResponse()

    monkeypatch.setattr(module, "_open_url", fake_open_url)
    files = module.list_huggingface_gguf_files("org/model")
    assert [item.filename for item in files] == ["model.Q4_K_M.gguf"]
    assert seen["url"] == "https://huggingface.co/api/models/org/model?blobs=true"
    assert seen["timeout"] == 20
    assert seen["opener"] is None



def test_huggingface_connectivity_probe_sanitizes_tls_certificate_failure():
    import ssl
    from engine.ai.model_manager import ModelDiscoveryError, check_huggingface_connection

    def opener(_request, timeout):
        raise ssl.SSLCertVerificationError("certificate verify failed: private-path-detail")

    try:
        check_huggingface_connection(opener=opener)
    except ModelDiscoveryError as exc:
        assert str(exc) == "TLS certificate/handshake failed"
        assert "private-path-detail" not in str(exc)
        assert "https://" not in str(exc)
    else:
        raise AssertionError("expected ModelDiscoveryError for TLS failure")


def test_huggingface_connectivity_probe_sanitizes_timeout():
    import socket
    from engine.ai.model_manager import ModelDiscoveryError, check_huggingface_connection

    def opener(_request, timeout):
        raise socket.timeout("internal socket detail")

    try:
        check_huggingface_connection(opener=opener)
    except ModelDiscoveryError as exc:
        assert str(exc) == "Hugging Face connection timed out"
        assert "internal socket detail" not in str(exc)
    else:
        raise AssertionError("expected ModelDiscoveryError for timeout")



def test_huggingface_search_sanitizes_network_failure():
    import socket
    from engine.ai.model_manager import ModelDiscoveryError

    def opener(_request, timeout):
        raise socket.timeout("private socket path and internal socket detail")

    try:
        search_huggingface_models("Qwen", opener=opener)
    except ModelDiscoveryError as exc:
        assert str(exc) == "Hugging Face connection timed out"
        assert "private socket path" not in str(exc)
    else:
        raise AssertionError("expected sanitized model search error")


def test_huggingface_file_listing_sanitizes_tls_failure():
    import ssl
    from engine.ai.model_manager import ModelDiscoveryError

    def opener(_request, timeout):
        raise ssl.SSLCertVerificationError("private certificate store path")

    try:
        list_huggingface_gguf_files("org/model", opener=opener)
    except ModelDiscoveryError as exc:
        assert str(exc) == "TLS certificate/handshake failed"
        assert "private certificate store path" not in str(exc)
    else:
        raise AssertionError("expected sanitized repository listing error")


def test_huggingface_download_sanitizes_network_failure(tmp_path):
    import socket
    from engine.ai.model_manager import ModelDownloadError

    def opener(_request, timeout):
        raise socket.timeout("private socket path and internal socket detail")

    try:
        download_huggingface_model(
            ModelSpec("org/model", "model.gguf"), tmp_path / "models", opener=opener
        )
    except ModelDownloadError as exc:
        assert str(exc) == "Hugging Face connection timed out"
        assert "private socket path" not in str(exc)
    else:
        raise AssertionError("expected sanitized model download error")



def test_huggingface_download_sanitizes_midstream_timeout_and_cleans_partial(tmp_path):
    import socket
    from engine.ai.model_manager import ModelDownloadError

    class BrokenResponse:
        headers = {"Content-Length": "100"}

        def __init__(self):
            self.read_count = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            self.read_count += 1
            if self.read_count == 1:
                return b"partial bytes"
            raise socket.timeout("private socket path and internal socket detail")

    response = BrokenResponse()

    def opener(_request, timeout):
        assert timeout == 60
        return response

    try:
        download_huggingface_model(
            ModelSpec("org/model", "model.gguf"),
            tmp_path / "models",
            opener=opener,
        )
    except ModelDownloadError as exc:
        assert str(exc) == "Hugging Face connection timed out"
        assert "private socket path" not in str(exc)
        assert "internal socket detail" not in str(exc)
    else:
        raise AssertionError("expected sanitized mid-stream download timeout")

    models_dir = tmp_path / "models"
    assert list(models_dir.glob("*.part"))
    assert not list(models_dir.glob("*.gguf"))



def test_huggingface_search_supports_validated_sort_modes():
    import json
    from engine.ai.model_manager import ModelSpecError

    seen = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps([
                {"id": "Qwen/Qwen3-1.7B-GGUF", "downloads": 42, "likes": 3}
            ]).encode()

    def opener(request, timeout):
        seen.append(request.full_url)
        return FakeResponse()

    search_huggingface_models("Qwen", sort_by="likes", opener=opener)
    assert all("sort=likes" in url for url in seen)
    seen.clear()
    search_huggingface_models("Qwen", sort_by="lastModified", opener=opener)
    assert all("sort=lastModified" in url for url in seen)

    try:
        search_huggingface_models("Qwen", sort_by="unsafe", opener=opener)
    except ModelSpecError:
        pass
    else:
        raise AssertionError("unsupported sort mode must be rejected")



def test_download_resumes_partial_file_with_http_range(tmp_path):
    import hashlib

    payload = _gguf_payload(b"RESUMED")
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    spec = ModelSpec("org/model", "model.Q4_K_M.gguf", expected_size_bytes=len(payload))
    part = models_dir / (spec.destination_name + ".part")
    offset = len(payload) // 2
    part.write_bytes(payload[:offset])
    calls = []

    class FakeResponse:
        status = 206

        def __init__(self):
            self.headers = {
                "Content-Length": str(len(payload) - offset),
                "Content-Range": f"bytes {offset}-{len(payload)-1}/{len(payload)}",
            }
            self.remaining = payload[offset:]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            chunk, self.remaining = self.remaining[:size], self.remaining[size:]
            return chunk

    def opener(request, timeout):
        calls.append(request.get_header("Range"))
        return FakeResponse()

    installed = download_huggingface_model(spec, models_dir, opener=opener)
    assert calls == [f"bytes={offset}-"]
    assert installed.path.read_bytes() == payload
    assert installed.sha256 == hashlib.sha256(payload).hexdigest()
    assert not part.exists()


def test_download_keeps_partial_file_when_stream_is_interrupted(tmp_path):
    import urllib.error

    payload = _gguf_payload(b"PARTIAL")

    class FakeResponse:
        status = 200
        headers = {"Content-Length": str(len(payload))}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            if hasattr(self, "sent"):
                raise urllib.error.URLError(TimeoutError("timed out"))
            self.sent = True
            return payload[:12]

    def opener(_request, timeout):
        return FakeResponse()

    spec = ModelSpec("org/model", "model.Q4_K_M.gguf")
    try:
        download_huggingface_model(spec, tmp_path / "models", opener=opener)
    except Exception:
        pass
    else:
        raise AssertionError("interrupted stream should fail")
    assert (tmp_path / "models" / (spec.destination_name + ".part")).exists()
