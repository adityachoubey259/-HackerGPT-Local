"""Model provider endpoints."""

from fastapi import APIRouter, Query, Request
from starlette import status

from backend.api.errors import ApplicationError
from backend.api.schemas.models import (
    ModelTestRequest,
    ModelTestResponse,
    NormalizedModel,
    ProviderHealth,
)
from backend.llm.errors import (
    InvalidGenerationParametersError,
    ModelNotFoundError,
    ModelProviderError,
    ModelRequestTimeoutError,
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from backend.services.models import ModelService
from backend.system.hardware import cached_hardware_report

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[NormalizedModel])
async def list_models(
    request: Request,
    provider: str | None = Query(default=None),
) -> list[NormalizedModel]:
    service: ModelService = request.app.state.model_service
    try:
        return await service.list_models(cached_hardware_report(), provider)
    except ModelProviderError as exc:
        raise _to_api_error(exc) from exc


@router.get("/providers", response_model=list[ProviderHealth])
async def list_providers(request: Request) -> list[ProviderHealth]:
    service: ModelService = request.app.state.model_service
    return await service.providers()


@router.get("/details", response_model=NormalizedModel)
async def model_details(
    request: Request,
    provider: str = Query(min_length=1),
    model: str = Query(min_length=1),
) -> NormalizedModel:
    service: ModelService = request.app.state.model_service
    try:
        return await service.get_model(provider, model, cached_hardware_report())
    except ModelProviderError as exc:
        raise _to_api_error(exc) from exc


@router.post("/test", response_model=ModelTestResponse)
async def test_model(
    request: Request,
    body: ModelTestRequest,
) -> ModelTestResponse:
    service: ModelService = request.app.state.model_service
    try:
        return await service.test_model(body)
    except ModelProviderError as exc:
        raise _to_api_error(exc) from exc


def _to_api_error(exc: ModelProviderError) -> ApplicationError:
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, ProviderUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, ProviderConfigurationError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ModelNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ModelRequestTimeoutError):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    elif isinstance(exc, InvalidGenerationParametersError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, ProviderResponseError):
        status_code = status.HTTP_502_BAD_GATEWAY
    return ApplicationError(exc.code, str(exc) or exc.message, status_code=status_code)
