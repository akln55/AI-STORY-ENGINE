import io
import json
import ssl
import urllib.error

import pytest

from engine.ai.connectivity import APIConnectionError, check_api_connection


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit=-1):
        return self.payload[:limit]


def test_openai_compatible_connection_probe_uses_models_endpoint_and_bearer_header():
    def opener(request, timeout):
        assert request.full_url == "https://api.example.invalid/v1/models"
        headers = {key.lower(): value for key, value in request.header_items()}
        assert headers["authorization"] == "Bearer test-only-secret"
        assert timeout == 2
        return FakeResponse({"data": [{"id": "model-a"}, {"id": "model-b"}]})

    result = check_api_connection(
        "OpenAI", endpoint="https://api.example.invalid/v1",
        api_key="test-only-secret", timeout=2, opener=opener,
    )
    assert result.status_code == 200
    assert result.available_models == 2
    assert result.model_ids == ("model-a", "model-b")
    assert "2 model bulundu" in result.message


def test_gemini_connection_probe_uses_api_key_header_without_url_credentials():
    def opener(request, timeout):
        assert request.full_url == "https://generativelanguage.googleapis.com/v1beta/models"
        headers = {key.lower(): value for key, value in request.header_items()}
        assert headers["x-goog-api-key"] == "test-only-secret"
        assert "test-only-secret" not in request.full_url
        return FakeResponse({"models": [{"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]}]})

    result = check_api_connection(
        "Gemini", api_key="test-only-secret", opener=opener,
    )
    assert result.available_models == 1
    assert result.provider == "Gemini"
    assert result.model_ids == ("gemini-2.5-flash",)


def test_connection_probe_translates_dns_error_without_exposing_secret():
    def opener(request, timeout):
        raise urllib.error.URLError("No address associated with hostname")

    with pytest.raises(APIConnectionError) as caught:
        check_api_connection(
            "OpenAI", endpoint="https://api.example.invalid/v1",
            api_key="test-only-secret", opener=opener,
        )
    assert "DNS" in str(caught.value)
    assert "test-only-secret" not in str(caught.value)


def test_connection_probe_does_not_echo_provider_error_body_or_api_key():
    error = urllib.error.HTTPError(
        "https://api.example.invalid/v1/models", 401, "unauthorized", {},
        io.BytesIO(b"rejected test-only-secret"),
    )

    def opener(request, timeout):
        raise error

    with pytest.raises(APIConnectionError) as caught:
        check_api_connection(
            "OpenAI", endpoint="https://api.example.invalid/v1",
            api_key="test-only-secret", opener=opener,
        )
    assert "401" in str(caught.value)
    assert "test-only-secret" not in str(caught.value)
    assert "rejected" not in str(caught.value)


def test_connection_probe_rejects_insecure_remote_endpoint_before_network():
    def opener(request, timeout):
        raise AssertionError("network should not be called")

    with pytest.raises(APIConnectionError, match="localhost"):
        check_api_connection(
            "OpenAI", endpoint="http://api.example.invalid/v1",
            api_key="test-only-secret", opener=opener,
        )


def test_gemini_model_list_filters_out_non_generation_models():
    def opener(request, timeout):
        return FakeResponse({
            "models": [
                {"name": "models/gemini-good", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-embed", "supportedGenerationMethods": ["embedContent"]},
            ]
        })
    result = check_api_connection("Gemini", api_key="test-only-secret", opener=opener)
    assert result.model_ids == ("gemini-good",)


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (ssl.SSLCertVerificationError("certificate verify failed"), "TLS sertifika"),
        (OSError("Connection refused"), "bağlantıyı reddetti"),
        (OSError("Connection reset by peer"), "kesildi"),
        (TimeoutError("timed out"), "zamanında yanıt vermedi"),
    ],
)
def test_connection_probe_classifies_common_network_failures_without_leaking_details(reason, expected):
    def opener(request, timeout):
        raise urllib.error.URLError(reason)

    with pytest.raises(APIConnectionError) as caught:
        check_api_connection(
            "OpenAI", endpoint="https://api.example.invalid/v1",
            api_key="test-only-secret", opener=opener,
        )
    assert expected in str(caught.value)
    assert "test-only-secret" not in str(caught.value)
    assert "example.invalid" not in str(caught.value)


@pytest.mark.parametrize(
    ("provider", "payload"),
    [
        ("OpenAI", {"message": "This is a proxy login page"}),
        ("Gemini", {"data": [{"id": "wrong-provider-shape"}]}),
        ("OpenAI", ["not", "an", "object"]),
    ],
)
def test_connection_probe_rejects_success_status_with_wrong_response_shape(provider, payload):
    def opener(request, timeout):
        return FakeResponse(payload)

    with pytest.raises(APIConnectionError, match="model-listesi"):
        check_api_connection(
            provider,
            endpoint="https://api.example.invalid/v1" if provider == "OpenAI" else "",
            api_key="test-only-secret",
            opener=opener,
        )


def test_empty_but_valid_model_collection_is_still_a_successful_connection():
    result = check_api_connection(
        "OpenAI", endpoint="https://api.example.invalid/v1",
        api_key="test-only-secret",
        opener=lambda request, timeout: FakeResponse({"data": []}),
    )
    assert result.available_models == 0
    assert "0 model bulundu" in result.message
