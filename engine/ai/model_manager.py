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
import re
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
        if not _REPO_ID_RE.fullmatch(self.repo_id):
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
    urlopen = opener or urllib.request.urlopen
    try:
        response = urlopen(request, timeout=60)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelDownloadError(f"Hugging Face download failed: {exc}") from exc

    with response as stream:
        header = stream.headers.get("Content-Length") if hasattr(stream, "headers") else None
        total = int(header) if header and header.isdigit() else spec.expected_size_bytes
        if total is not None and total > max_bytes:
            raise ModelSizeError("remote model exceeds the hard size ceiling")
        written = 0
        try:
            with part.open("wb") as output:
                while True:
                    chunk = stream.read(_IO_CHUNK_SIZE)
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
