from __future__ import annotations

import ssl
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from engine.ai import https_transport


def test_https_transport_uses_certifi_and_keeps_certificate_verification(monkeypatch):
    fake_context = SimpleNamespace(
        check_hostname=True,
        verify_mode=ssl.CERT_REQUIRED,
    )
    create_context = Mock(return_value=fake_context)
    urlopen = Mock(return_value="response")
    monkeypatch.setitem(sys.modules, "certifi", SimpleNamespace(where=lambda: "/trusted/roots.pem"))
    monkeypatch.setattr(https_transport.ssl, "create_default_context", create_context)
    monkeypatch.setattr(https_transport.urllib.request, "urlopen", urlopen)

    request = https_transport.urllib.request.Request("https://api.example.test/models")
    result = https_transport.open_url(request, timeout=7)

    assert result == "response"
    create_context.assert_called_once_with(cafile="/trusted/roots.pem")
    urlopen.assert_called_once_with(request, timeout=7, context=fake_context)
    assert fake_context.check_hostname is True
    assert fake_context.verify_mode == ssl.CERT_REQUIRED


def test_local_http_transport_does_not_create_or_pass_tls_context(monkeypatch):
    create_context = Mock(side_effect=AssertionError("HTTP must not create TLS context"))
    urlopen = Mock(return_value="response")
    monkeypatch.setattr(https_transport.ssl, "create_default_context", create_context)
    monkeypatch.setattr(https_transport.urllib.request, "urlopen", urlopen)

    request = https_transport.urllib.request.Request("http://127.0.0.1:8080/health")
    result = https_transport.open_url(request, timeout=1)

    assert result == "response"
    create_context.assert_not_called()
    urlopen.assert_called_once_with(request, timeout=1)


def test_injected_transport_opener_remains_available_for_deterministic_tests():
    request = https_transport.urllib.request.Request("https://api.example.test/models")
    opener = Mock(return_value="fake-response")

    result = https_transport.open_url(request, timeout=3, opener=opener)

    assert result == "fake-response"
    opener.assert_called_once_with(request, timeout=3)
