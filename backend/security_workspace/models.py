"""Domain types for the cybersecurity workspace."""

from __future__ import annotations

from enum import StrEnum


class SecurityMode(StrEnum):
    GENERAL_SECURITY = "general-security"
    WEB_SECURITY = "web-security"
    NETWORK_SECURITY = "network-security"
    ACTIVE_DIRECTORY = "active-directory"
    REVERSE_ENGINEERING = "reverse-engineering"
    MALWARE_ANALYSIS = "malware-analysis"
    FORENSICS = "forensics"
    DETECTION_ENGINEERING = "detection-engineering"
    VULNERABILITY_RESEARCH = "vulnerability-research"
    CLOUD_SECURITY = "cloud-security"
    CONTAINER_SECURITY = "container-security"
    SECURE_CODE_REVIEW = "secure-code-review"


class SecurityScopeType(StrEnum):
    LOCALHOST = "localhost"
    OWNED_HOST = "owned_host"
    LOCAL_VM = "local_vm"
    PRIVATE_LAB = "private_lab"
    CTF = "ctf"
    PRIVATE_CIDR = "private_cidr"
    CONFIGURED_DOMAIN = "configured_domain"
    CONFIGURED_REPOSITORY = "configured_repository"


class FindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


SECURITY_MODES: tuple[str, ...] = tuple(item.value for item in SecurityMode)
SCOPE_TYPES: tuple[str, ...] = tuple(item.value for item in SecurityScopeType)
FINDING_SEVERITIES: tuple[str, ...] = tuple(item.value for item in FindingSeverity)
FINDING_CONFIDENCES: tuple[str, ...] = tuple(item.value for item in FindingConfidence)
