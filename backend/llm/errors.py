"""Provider/domain errors for model runtimes."""

from __future__ import annotations


class ModelProviderError(Exception):
    code = "MODEL_PROVIDER_ERROR"
    message = "Model provider error."


class ProviderUnavailableError(ModelProviderError):
    code = "PROVIDER_UNAVAILABLE"
    message = "Model provider is unavailable."


class ProviderConfigurationError(ModelProviderError):
    code = "PROVIDER_CONFIGURATION_ERROR"
    message = "Model provider is misconfigured."


class ModelNotFoundError(ModelProviderError):
    code = "MODEL_NOT_FOUND"
    message = "Model was not found."


class ModelRequestTimeoutError(ModelProviderError):
    code = "MODEL_REQUEST_TIMEOUT"
    message = "Model provider request timed out."


class InvalidGenerationParametersError(ModelProviderError):
    code = "INVALID_GENERATION_PARAMETERS"
    message = "Generation parameters are invalid."


class ProviderResponseError(ModelProviderError):
    code = "PROVIDER_RESPONSE_ERROR"
    message = "Model provider returned an unexpected response."
