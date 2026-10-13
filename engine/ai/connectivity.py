"""Low-cost, secret-safe connectivity probes for configured AI providers.

The probe calls a provider's model-list endpoint; it does not generate text,
consume generation tokens, or log the API key. It is a configuration check,
not a guarantee that every selected model supports the engine's JSON contract.
"""
from __future__ import annotations

from engine.ai.https_transport import open_url
from dataclasses import dataclass
import json
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request


class APIConnectionError(RuntimeError):
    """Safe, user-facing AI provider connection error."""


@dataclass(frozen=True)
class APIConnectionResult:
    provider: str
    status_code: int
    available_models: int | None
    message: str
    model_ids: tuple[str, ...] = ()


def _network_error_message(exc: BaseException) -> str:
    raw = str(getattr(exc, "reason", exc)).lower()
    if any(term in raw for term in (
        "no address associated", "name or service not known",
        "temporary failure in name resolution", "nodename nor servname",
        "getaddrinfo failed",
    )):
        return "DNS çözümlemesi başarısız. İnternet bağlantısını ve Android ağ izinlerini kontrol et."
    if "timed out" in raw or "timeout" in raw:
        return "Sunucu zamanında yanıt vermedi. Bağlantını kontrol edip tekrar dene."
    if "network is unreachable" in raw or "no route to host" in raw:
        return "Ağa erişilemiyor. İnternet bağlantını kontrol edip tekrar dene."
    return "Sunucuya ulaşılamadı. İnternet bağlantısını ve endpoint adresini kontrol et."


def check_api_connection(
    provider: str,
    *,
    endpoint: str = "",
    api_key: str,
    timeout: float = 12.0,
    opener: Callable[..., object] | None = None,
) -> APIConnectionResult:
    """Check API auth/connectivity through a low-cost model-list request.

    The opener argument is injectable for deterministic tests. Error messages
    deliberately omit response bodies, request URLs, and credentials.
    """
    if not api_key or not api_key.strip():
        raise APIConnectionError("API anahtarı gerekli.")
    if timeout <= 0:
        raise APIConnectionError("Bağlantı zaman aşımı pozitif olmalı.")

    normalized = provider.strip().lower()
    if normalized == "gemini":
        label = "Gemini"
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        headers = {
            "Accept": "application/json",
            "x-goog-api-key": api_key.strip(),
            "User-Agent": "RPG-Engine/1.1",
        }
    elif normalized in {"openai", "openai-compatible", "openai compatible"}:
        label = "OpenAI-compatible API"
        base = endpoint.strip().rstrip("/")
        if not base:
            raise APIConnectionError("API endpoint gerekli.")
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise APIConnectionError("Endpoint https:// veya http:// ile başlamalı.")
        if parsed.username or parsed.password or parsed.fragment:
            raise APIConnectionError("Endpoint içinde kullanıcı bilgisi veya fragment kullanılamaz.")
        if parsed.scheme == "http" and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
            raise APIConnectionError("Güvenlik nedeniyle HTTP yalnızca localhost için kullanılabilir.")
        if base.endswith("/chat/completions"):
            url = base[:-len("/chat/completions")] + "/models"
        elif base.endswith("/models"):
            url = base
        else:
            url = base + "/models"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
            "User-Agent": "RPG-Engine/1.1",
        }
    else:
        raise APIConnectionError("Desteklenmeyen API sağlayıcısı.")

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with open_url(request, timeout=timeout, opener=opener) as response:
            status_value = getattr(response, "status", None)
            status = int(status_value if status_value is not None else response.getcode())
            body = response.read(65536)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise APIConnectionError("API anahtarı kabul edilmedi (HTTP 401). Anahtarı kontrol et.") from None
        if exc.code == 403:
            raise APIConnectionError("Sağlayıcı erişimi reddetti (HTTP 403). Hesap veya API erişimini kontrol et.") from None
        if exc.code == 404:
            raise APIConnectionError("Model-listesi endpoint'i bulunamadı (HTTP 404). Endpoint adresini kontrol et.") from None
        if exc.code == 429:
            raise APIConnectionError("Sağlayıcı istek sınırına ulaştı (HTTP 429). Biraz sonra dene.") from None
        raise APIConnectionError(f"Sağlayıcı HTTP {exc.code} döndürdü.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise APIConnectionError(_network_error_message(exc)) from None

    if not 200 <= status < 300:
        raise APIConnectionError(f"Sağlayıcı beklenmeyen HTTP {status} durumu döndürdü.")
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, ValueError):
        raise APIConnectionError("Sunucu yanıt verdi ancak geçerli JSON döndürmedi.") from None

    model_count = None
    model_ids: list[str] = []
    if isinstance(payload, dict):
        collection = payload.get("data")
        if not isinstance(collection, list):
            collection = payload.get("models")
        if isinstance(collection, list):
            model_count = len(collection)
            for item in collection:
                if not isinstance(item, dict):
                    continue
                model_id = item.get("id") or item.get("name")
                if not isinstance(model_id, str) or not model_id.strip():
                    continue
                if label == "Gemini":
                    supported = item.get("supportedGenerationMethods")
                    if isinstance(supported, list) and "generateContent" not in supported:
                        continue
                    if model_id.startswith("models/"):
                        model_id = model_id[len("models/"):]
                if model_id not in model_ids:
                    model_ids.append(model_id)
                if len(model_ids) >= 30:
                    break
    offered_count = len(model_ids) if model_ids else model_count
    suffix = f" · {offered_count} model bulundu" if offered_count is not None else ""
    return APIConnectionResult(
        provider=label,
        status_code=status,
        available_models=offered_count,
        message=f"{label} bağlantısı başarılı{suffix}.",
        model_ids=tuple(model_ids),
    )
