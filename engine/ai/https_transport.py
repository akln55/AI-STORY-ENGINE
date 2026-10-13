"""Verified HTTPS transport shared by external AI providers.

Android Python runtimes may not discover the platform CA bundle reliably.
Prefer certifi roots when installed; otherwise use Python's verified system
trust store. Certificate verification is never disabled.
"""
from __future__ import annotations

import ssl
import urllib.parse
import urllib.request


def open_url(request, *, timeout: float, opener=None):
    """Open a URL with bounded timeout and explicit verified HTTPS trust.

    opener exists for deterministic tests and must be supplied explicitly.
    Local HTTP endpoints (used by the local llama-server) do not receive a TLS
    context; all HTTPS endpoints keep hostname and certificate verification on.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if opener is not None:
        return opener(request, timeout=timeout)

    url = getattr(request, "full_url", None) or str(request)
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme != "https":
        return urllib.request.urlopen(request, timeout=timeout)

    try:
        import certifi
    except ImportError:
        context = ssl.create_default_context()
    else:
        context = ssl.create_default_context(cafile=certifi.where())

    return urllib.request.urlopen(request, timeout=timeout, context=context)
