"""Safe lifecycle management for local GGUF models.

This module intentionally owns *model files*, not inference.  It provides the
first product layer needed by the hybrid Local-AI path:

- validate GGUF imports;
- keep models in an app-private directory supplied by the caller;
- download an explicitly selected file from Hugging Face;
- enforce conservative model-size limits;
- verify optional SHA-256 integrity;
- write atomically through a temporary ``.part`` file;
- enumerate installed models without exposing filesystem access to the AI.

The module does not discover arbitrary models, execute them, or start llama.cpp.
Those are separate responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re
import ssl
import urllib.parse
from typing import Callable, Iterable
import urllib.error
import urllib.request

GGUF_SUFFIX = ".gguf"
GGUF_MAGIC = b"GGUF"
GGUF_MIN_VERSION = 1
GGUF_MAX_VERSION = 3
BYTES_PER_GIB = 1024 ** 3
PREFERRED_MAX_MODEL_BYTES = 2 * BYTES_PER_GIB
HARD_MAX_MODEL_BYTES = 3 * BYTES_PER_GIB
_IO_CHUNK_SIZE = 1024 * 1024

_REPO_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_HEX_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _safe_huggingface_error(exc: BaseException, *, operation: str) -> str:
    """Return a stable user-facing network diagnostic without raw exception data."""
    reason = getattr(exc, "reason", exc)
    if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
        return "Hugging Face connection timed out"
    raw = str(reason).lower()
    if any(term in raw for term in (
        "no address associated", "name or service not known",
        "temporary failure in name resolution", "nodename nor servname",
        "getaddrinfo failed",
    )):
        return "DNS resolution failed for huggingface.co"
    if "network is unreachable" in raw or "no route to host" in raw:
        return "Network is unreachable"
    if any(term in raw for term in ("ssl", "certificate", "tls")):
        return "TLS certificate/handshake failed"
    return {
        "search": "Could not search Hugging Face models",
        "listing": "Could not read Hugging Face repository",
        "download": "Could not download model from Hugging Face",
        "connection": "Could not reach Hugging Face",
    }.get(operation, "Could not reach Hugging Face")


def _open_url(request, *, timeout: float, opener=None):
    """Open HTTPS with an explicit CA bundle on Android and desktop.

    python-for-android does not always expose the host OS CA paths to Python's
    ssl module. Prefer certifi's maintained bundle when installed; never disable
    certificate verification. The injectable opener keeps network tests offline.
    """
    if opener is not None:
        return opener(request, timeout=timeout)
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


class ModelManagerError(Exception):
    """Base exception for model lifecycle failures."""


class ModelSpecError(ModelManagerError):
    """Raised when a requested model specification is unsafe or malformed."""


class ModelSizeError(ModelManagerError):
    """Raised when a model exceeds the product's safe size ceiling."""


class ModelIntegrityError(ModelManagerError):
    """Raised when a model fails integrity verification."""


class ModelFormatError(ModelManagerError):
    """Raised when a file does not contain a supported GGUF header."""


class ModelDownloadError(ModelManagerError):
    """Raised for network/download failures."""


class ModelDiscoveryError(ModelManagerError):
    """Raised when Hugging Face model discovery fails."""


@dataclass(frozen=True)
class HuggingFaceModel:
    repo_id: str
    downloads: int = 0
    likes: int = 0


@dataclass(frozen=True)
class HuggingFaceGGUFFile:
    filename: str
    size_bytes: int | None = None

    @property
    def size_gib(self) -> float | None:
        return None if self.size_bytes is None else self.size_bytes / BYTES_PER_GIB


@dataclass(frozen=True)
class ModelSpec:
    """An explicitly selected public model file.

    ``repo_id`` and ``filename`` are intentionally explicit.  The application
    must never turn an arbitrary model URL supplied by the model itself into a
    download request.
    """

    repo_id: str
    filename: str
    revision: str = "main"
    expected_size_bytes: int | None = None
    expected_sha256: str | None = None
    display_name: str = ""

    def validate(self, *, hard_max_bytes: int = HARD_MAX_MODEL_BYTES) -> None:
        if (not _REPO_ID_RE.fullmatch(self.repo_id)
                or any(part in {".", ".."} for part in self.repo_id.split("/"))):
            raise ModelSpecError(f"invalid Hugging Face repo id: {self.repo_id!r}")
        if not self.revision or self.revision.startswith(("/", "\\")):
            raise ModelSpecError("invalid model revision")
        path = Path(self.filename)
        if not path.name or path.name != self.filename or ".." in path.parts:
            raise ModelSpecError("model filename must be a single safe filename")
        if not self.filename.lower().endswith(GGUF_SUFFIX):
            raise ModelSpecError("only GGUF model files are supported")
        if self.expected_size_bytes is not None:
            if self.expected_size_bytes <= 0:
                raise ModelSpecError("expected_size_bytes must be positive")
            if self.expected_size_bytes > hard_max_bytes:
                raise ModelSizeError("model exceeds the hard size ceiling")
        if self.expected_sha256 is not None and not _HEX_SHA256_RE.fullmatch(self.expected_sha256):
            raise ModelSpecError("expected_sha256 must be a 64-character hex digest")

    @property
    def resolved_url(self) -> str:
        self.validate()
        revision = urllib.parse.quote(self.revision, safe="")
        repo = "/".join(urllib.parse.quote(part, safe="") for part in self.repo_id.split("/"))
        filename = urllib.parse.quote(self.filename, safe="")
        return f"https://huggingface.co/{repo}/resolve/{revision}/{filename}?download=true"

    @property
    def destination_name(self) -> str:
        self.validate()
        prefix = self.repo_id.replace("/", "__")
        return f"{prefix}--{self.filename}"


@dataclass(frozen=True)
class InstalledModel:
    path: Path
    size_bytes: int
    sha256: str = ""

    @property
    def integrity_verified(self) -> bool:
        """Whether this instance includes a full-file SHA-256 verification."""
        return bool(self.sha256)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def size_gib(self) -> float:
        return self.size_bytes / BYTES_PER_GIB




def default_model_storage_dir() -> Path:
    """Return the product's app-private model directory when available."""
    try:
        from android.storage import app_storage_path  # type: ignore
    except ImportError:
        root = Path.home() / ".rpgengine"
    else:
        root = Path(app_storage_path())
    return model_storage_dir(root)

def model_storage_dir(root: Path | str) -> Path:
    """Return/create the app-owned local model directory."""
    directory = Path(root).expanduser().resolve() / "models"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def validate_model_file(path: Path | str, *, max_bytes: int = HARD_MAX_MODEL_BYTES) -> InstalledModel:
    """Validate a complete GGUF file and calculate its SHA-256.

    This is intentionally the expensive integrity path. UI listings should use
    ``list_installed_models(..., verify_integrity=False)`` instead so multi-GB
    models are not re-hashed on the Kivy UI thread.
    """
    candidate = Path(path).expanduser().resolve()
    _inspect_model_file(candidate, max_bytes=max_bytes)
    return InstalledModel(candidate, candidate.stat().st_size, _sha256_file(candidate))


def install_imported_model(
    source: Path | str,
    models_dir: Path | str,
    *,
    expected_sha256: str | None = None,
    max_bytes: int = HARD_MAX_MODEL_BYTES,
) -> InstalledModel:
    """Copy an imported model into app-private storage atomically."""
    src = Path(source).expanduser().resolve()
    _inspect_model_file(src, max_bytes=max_bytes)
    if expected_sha256 is not None and not _HEX_SHA256_RE.fullmatch(expected_sha256):
        raise ModelSpecError("expected_sha256 must be a 64-character hex digest")

    destination_dir = Path(models_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / src.name
    part = destination.with_name(destination.name + ".part")
    try:
        _copy_stream(src, part, max_bytes=max_bytes)
        _inspect_model_file(part, max_bytes=max_bytes)
        digest = _sha256_file(part)
        if expected_sha256 and digest.lower() != expected_sha256.lower():
            raise ModelIntegrityError("imported model SHA-256 does not match the expected digest")
        part.replace(destination)
        return InstalledModel(destination, destination.stat().st_size, digest)
    except Exception:
        part.unlink(missing_ok=True)
        raise


def search_huggingface_models(
    query: str, *, limit: int = 12, sort_by: str = "downloads",
    opener: Callable[..., object] | None = None
) -> list[HuggingFaceModel]:
    """Search public Hugging Face repositories for GGUF models.

    Prefer the GGUF-filtered endpoint. Some search/index responses may return an
    empty filtered collection even when matching GGUF repositories exist, so a
    second unfiltered query is used as a compatibility fallback. Fallback
    results are kept only when the repository id or model tags identify GGUF.
    Search results are metadata only; downloads still require explicit file
    selection and confirmation.
    """
    cleaned = query.strip()
    if not cleaned:
        raise ModelSpecError("enter a model name or search term")
    if not 1 <= limit <= 30:
        raise ModelSpecError("model search limit must be between 1 and 30")
    if sort_by not in {"downloads", "likes", "lastModified"}:
        raise ModelSpecError("unsupported Hugging Face sort order")


    def request_models(*, filter_gguf: bool) -> list[dict]:
        params = {
            "search": cleaned,
            "sort": sort_by,
            "direction": "-1",
            "limit": str(limit),
        }
        if filter_gguf:
            params["filter"] = "gguf"
        url = "https://huggingface.co/api/models?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url, headers={
                "User-Agent": "RPG-Engine/1.1",
                "Accept": "application/json",
            }
        )
        try:
            with _open_url(request, timeout=20, opener=opener) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelDiscoveryError(_safe_huggingface_error(exc, operation="search")) from None
        except (UnicodeDecodeError, ValueError):
            raise ModelDiscoveryError("Hugging Face returned invalid model data") from None
        if not isinstance(payload, list):
            raise ModelDiscoveryError("Hugging Face returned an unexpected model list")
        return [item for item in payload if isinstance(item, dict)]

    raw_results = request_models(filter_gguf=True)
    if not raw_results:
        # Compatibility fallback for API/index deployments where filter=gguf
        # produces false-empty results. It never triggers a model download.
        raw_results = request_models(filter_gguf=False)
        raw_results = [
            item for item in raw_results
            if (
                "gguf" in str(item.get("id", "")).lower()
                or (
                    isinstance(item.get("tags"), list)
                    and any(str(tag).lower() == "gguf" for tag in item["tags"])
                )
            )
        ]

    results: list[HuggingFaceModel] = []
    seen: set[str] = set()
    for item in raw_results:
        repo_id = item.get("id")
        if (
            not isinstance(repo_id, str)
            or not _REPO_ID_RE.fullmatch(repo_id)
            or any(part in {".", ".."} for part in repo_id.split("/"))
            or repo_id in seen
        ):
            continue
        seen.add(repo_id)
        try:
            downloads = max(0, int(item.get("downloads") or 0))
        except (TypeError, ValueError):
            downloads = 0
        try:
            likes = max(0, int(item.get("likes") or 0))
        except (TypeError, ValueError):
            likes = 0
        results.append(HuggingFaceModel(repo_id=repo_id, downloads=downloads, likes=likes))
        if len(results) >= limit:
            break
    return results

def list_huggingface_gguf_files(
    repo_id: str, *, opener: Callable[..., object] | None = None,
    max_bytes: int = HARD_MAX_MODEL_BYTES,
) -> list[HuggingFaceGGUFFile]:
    """List GGUF files for a validated public repository, excluding known oversized files."""
    if (not _REPO_ID_RE.fullmatch(repo_id)
            or any(part in {".", ".."} for part in repo_id.split("/"))):
        raise ModelSpecError("invalid Hugging Face repo id")
    encoded_repo = urllib.parse.quote(repo_id, safe="/")
    request = urllib.request.Request(
        f"https://huggingface.co/api/models/{encoded_repo}?blobs=true",
        headers={"User-Agent": "RPG-Engine/1.1", "Accept": "application/json"},
    )
    try:
        with _open_url(request, timeout=20, opener=opener) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelDiscoveryError(_safe_huggingface_error(exc, operation="listing")) from None
    except (UnicodeDecodeError, ValueError):
        raise ModelDiscoveryError("Hugging Face returned invalid repository data") from None
    if not isinstance(payload, dict):
        raise ModelDiscoveryError("Hugging Face returned an unexpected repository response")
    siblings = payload.get("siblings", [])
    if not isinstance(siblings, list):
        raise ModelDiscoveryError("Hugging Face repository file list is invalid")
    files = []
    for item in siblings:
        if not isinstance(item, dict):
            continue
        filename = item.get("rfilename")
        if (not isinstance(filename, str) or Path(filename).name != filename
                or not filename.lower().endswith(GGUF_SUFFIX)):
            continue
        raw_size = item.get("size")
        if raw_size is None and isinstance(item.get("lfs"), dict):
            raw_size = item["lfs"].get("size")
        try:
            size = int(raw_size) if raw_size is not None else None
        except (TypeError, ValueError):
            size = None
        if size is not None and (size <= 0 or size > max_bytes):
            continue
        files.append(HuggingFaceGGUFFile(filename=filename, size_bytes=size))
    return sorted(files, key=lambda item: (
        item.size_bytes is None,
        item.size_bytes if item.size_bytes is not None else max_bytes,
        item.filename.lower(),
    ))


def download_huggingface_model(
    spec: ModelSpec,
    models_dir: Path | str,
    *,
    opener: Callable[..., object] | None = None,
    progress_callback: Callable[[int, int | None], None] | None = None,
    max_bytes: int = HARD_MAX_MODEL_BYTES,
) -> InstalledModel:
    """Download one explicitly selected Hugging Face GGUF atomically."""
    spec.validate(hard_max_bytes=max_bytes)
    if spec.expected_size_bytes is not None and spec.expected_size_bytes > max_bytes:
        raise ModelSizeError("model exceeds the hard size ceiling")

    destination_dir = Path(models_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / spec.destination_name
    part = destination.with_name(destination.name + ".part")
    part.unlink(missing_ok=True)

    request = urllib.request.Request(
        spec.resolved_url,
        headers={"User-Agent": "RPG-Engine/1.1", "Accept": "application/octet-stream"},
        method="GET",
    )
    try:
        response = _open_url(request, timeout=60, opener=opener)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelDownloadError(_safe_huggingface_error(exc, operation="download")) from None

    with response as stream:
        header = stream.headers.get("Content-Length") if hasattr(stream, "headers") else None
        total = int(header) if header and header.isdigit() else spec.expected_size_bytes
        if total is not None and total > max_bytes:
            raise ModelSizeError("remote model exceeds the hard size ceiling")
        written = 0
        try:
            with part.open("wb") as output:
                while True:
                    try:
                        chunk = stream.read(_IO_CHUNK_SIZE)
                    except (urllib.error.URLError, TimeoutError, OSError) as exc:
                        raise ModelDownloadError(
                            _safe_huggingface_error(exc, operation="download")
                        ) from None
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise ModelSizeError("download exceeded the hard size ceiling")
                    output.write(chunk)
                    if progress_callback:
                        progress_callback(written, total)
        except Exception:
            part.unlink(missing_ok=True)
            raise

    if spec.expected_size_bytes is not None and written != spec.expected_size_bytes:
        part.unlink(missing_ok=True)
        raise ModelIntegrityError(
            f"downloaded size {written} does not match expected size {spec.expected_size_bytes}"
        )

    try:
        _inspect_model_file(part, max_bytes=max_bytes)
        digest = _sha256_file(part)
        if spec.expected_sha256 and digest.lower() != spec.expected_sha256.lower():
            raise ModelIntegrityError("downloaded model SHA-256 does not match the expected digest")
        part.replace(destination)
        return InstalledModel(destination, written, digest)
    except Exception:
        part.unlink(missing_ok=True)
        raise


def list_installed_models(
    models_dir: Path | str, *, verify_integrity: bool = True
) -> list[InstalledModel]:
    """Enumerate local GGUFs. Full hashing can be disabled for UI listings.

    With ``verify_integrity=False`` only cheap header/size checks are performed;
    callers that will execute a model must use ``validate_model_file`` first.
    """
    directory = Path(models_dir).expanduser().resolve()
    if not directory.exists():
        return []
    result: list[InstalledModel] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.suffix.lower() == GGUF_SUFFIX:
            try:
                if verify_integrity:
                    result.append(validate_model_file(path))
                else:
                    result.append(_inspect_model_file(path))
            except ModelManagerError:
                continue
    return result


def _inspect_model_file(path: Path | str, *, max_bytes: int = HARD_MAX_MODEL_BYTES) -> InstalledModel:
    """Cheap structural validation used before an expensive integrity hash."""
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise ModelManagerError(f"model file not found: {candidate}")
    logical_name = candidate.name[:-5] if candidate.name.endswith(".part") else candidate.name
    if Path(logical_name).suffix.lower() != GGUF_SUFFIX:
        raise ModelSpecError("only GGUF model files are supported")
    size = candidate.stat().st_size
    if size < 8:
        raise ModelFormatError("model file is too small to contain a GGUF header")
    if size > max_bytes:
        raise ModelSizeError(f"model exceeds the {max_bytes / BYTES_PER_GIB:.1f} GiB hard ceiling")
    with candidate.open("rb") as handle:
        header = handle.read(8)
    if header[:4] != GGUF_MAGIC:
        raise ModelFormatError("model file does not contain the GGUF magic header")
    version = int.from_bytes(header[4:8], "little")
    if not GGUF_MIN_VERSION <= version <= GGUF_MAX_VERSION:
        raise ModelFormatError(f"unsupported GGUF version: {version}")
    return InstalledModel(candidate, size)


def _copy_stream(source: Path, destination: Path, *, max_bytes: int) -> None:
    written = 0
    with source.open("rb") as src, destination.open("wb") as dst:
        while True:
            chunk = src.read(_IO_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                destination.unlink(missing_ok=True)
                raise ModelSizeError("model exceeds the hard size ceiling")
            dst.write(chunk)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_IO_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_huggingface_connection(
    *, timeout: float = 8.0, opener: Callable[..., object] | None = None
) -> None:
    """Probe the public Hub model-list endpoint without authentication or downloads.

    Raises ModelDiscoveryError with a sanitized category-specific diagnostic.
    This checks DNS/TLS/HTTP reachability only; it does not guarantee that every
    model repository or large file is accessible.
    """
    if timeout <= 0:
        raise ModelSpecError("connection timeout must be positive")
    request = urllib.request.Request(
        "https://huggingface.co/api/models?limit=1",
        headers={
            "User-Agent": "RPG-Engine/1.1",
            "Accept": "application/json",
        },
    )
    try:
        with _open_url(request, timeout=timeout, opener=opener) as response:
            status_value = getattr(response, "status", None)
            status = int(status_value if status_value is not None else response.getcode())
            if not 200 <= status < 300:
                raise ModelDiscoveryError(f"Hugging Face returned HTTP {status}")
            body = response.read(65536)
            payload = json.loads(body.decode("utf-8")) if body else []
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ModelDiscoveryError("Hugging Face rate limit reached (HTTP 429)") from None
        raise ModelDiscoveryError(f"Hugging Face returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        # socket.timeout can carry an arbitrary message, so classify by type
        # before relying on platform-specific exception text.
        if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
            raise ModelDiscoveryError("Hugging Face connection timed out") from None
        raw = str(reason).lower()
        if any(term in raw for term in (
            "no address associated", "name or service not known",
            "temporary failure in name resolution", "nodename nor servname",
            "getaddrinfo failed",
        )):
            message = "DNS resolution failed for huggingface.co"
        elif "timed out" in raw or "timeout" in raw:
            message = "Hugging Face connection timed out"
        elif "network is unreachable" in raw or "no route to host" in raw:
            message = "Network is unreachable"
        elif "ssl" in raw or "certificate" in raw or "tls" in raw:
            message = "TLS certificate/handshake failed"
        else:
            message = "Could not reach Hugging Face"
        raise ModelDiscoveryError(message) from None
    except (UnicodeDecodeError, ValueError):
        raise ModelDiscoveryError("Hugging Face returned invalid JSON") from None
    if not isinstance(payload, list):
        raise ModelDiscoveryError("Hugging Face returned an unexpected response")
