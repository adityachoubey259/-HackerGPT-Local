"""URL safety helpers for policy-controlled research."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit

from backend.api.errors import ApplicationError
from backend.core.policy import ResearchPolicy


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not host:
        raise ApplicationError(
            "RESEARCH_URL_NOT_ALLOWED",
            "Research retrieval only supports absolute HTTP and HTTPS URLs.",
            status_code=400,
        )
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/"
    return urlunsplit((scheme, f"{host}{port}", path, parsed.query, ""))


def domain_for_url(url: str) -> str:
    parsed = urlsplit(normalize_url(url))
    return (parsed.hostname or "").lower()


def ensure_url_allowed(url: str, policy: ResearchPolicy) -> str:
    normalized = normalize_url(url)
    domain = domain_for_url(normalized)
    if _matches(domain, policy.blocked_domains):
        raise ApplicationError(
            "RESEARCH_DOMAIN_BLOCKED",
            "The URL is blocked by research policy.",
            status_code=403,
            details={"domain": domain},
        )
    if policy.allowed_domains and not _matches(domain, policy.allowed_domains):
        raise ApplicationError(
            "RESEARCH_DOMAIN_NOT_ALLOWED",
            "The URL is outside the configured research allowlist.",
            status_code=403,
            details={"domain": domain},
        )
    if policy.block_private_networks and _is_private_host(domain):
        raise ApplicationError(
            "RESEARCH_PRIVATE_NETWORK_BLOCKED",
            "Research retrieval blocks loopback, link-local, and private network targets "
            "by default.",
            status_code=403,
            details={"domain": domain},
        )
    return normalized


def _matches(domain: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        normalized = pattern.lower().strip()
        if not normalized:
            continue
        if domain == normalized or domain.endswith(f".{normalized}"):
            return True
    return False


def _is_private_host(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return host in {"localhost", "localhost.localdomain"}
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )
