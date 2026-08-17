"""Network policy helpers for model providers."""

from __future__ import annotations

from urllib.parse import urlparse

from backend.core.policy import AccessMode, PolicyConfig
from backend.llm.errors import ProviderConfigurationError


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def ensure_provider_network_allowed(base_url: str, policy: PolicyConfig) -> None:
    if is_loopback_url(base_url):
        return
    if policy.network_access.default_access == AccessMode.ENABLED:
        return
    msg = "External model provider access is disabled by policy."
    raise ProviderConfigurationError(msg)
