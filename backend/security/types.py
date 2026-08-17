"""Security-related types."""

from enum import StrEnum


class TrustBoundary(StrEnum):
    TRUSTED_APPLICATION = "trusted_application"
    USER_INPUT = "user_input"
    REPOSITORY_CONTENT = "repository_content"
    WEB_CONTENT = "web_content"
    DOCUMENT_CONTENT = "document_content"
    EMAIL_CONTENT = "email_content"
    RETRIEVED_CONTENT = "retrieved_content"
    MODEL_OUTPUT = "model_output"
    TOOL_OUTPUT = "tool_output"


class ExecutionPermission(StrEnum):
    READ_ONLY = "READ_ONLY"
    WRITE_LOCAL = "WRITE_LOCAL"
    HIGH_IMPACT = "HIGH_IMPACT"


UNTRUSTED_BOUNDARIES: frozenset[TrustBoundary] = frozenset(
    {
        TrustBoundary.USER_INPUT,
        TrustBoundary.REPOSITORY_CONTENT,
        TrustBoundary.WEB_CONTENT,
        TrustBoundary.DOCUMENT_CONTENT,
        TrustBoundary.EMAIL_CONTENT,
        TrustBoundary.RETRIEVED_CONTENT,
        TrustBoundary.MODEL_OUTPUT,
        TrustBoundary.TOOL_OUTPUT,
    }
)
