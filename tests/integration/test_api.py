from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.api.app import create_app
from backend.core.config import AppSettings, ModelEndpointSettings


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/v1/health", 200),
        ("/api/v1/health/ready", 200),
        ("/api/v1/system/info", 200),
        ("/api/v1/config/public", 200),
    ],
)
async def test_api_foundation_endpoints(
    test_settings: AppSettings,
    path: str,
    expected_status: int,
) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(path)
    assert response.status_code == expected_status
    assert response.headers["X-Request-ID"]


async def test_health_endpoint_response(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/health", headers={"X-Request-ID": "client-id-1"})
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "client-id-1"


async def test_readiness_reports_database(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/health/ready")
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["database"]["status"] == "ok"


async def test_system_info_is_safe(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/system/info")
    body = response.json()
    assert body["application_version"] == "1.0.0-rc.1"
    assert body["environment"] == "test"
    assert "environment_variables" not in body


async def test_public_config_does_not_leak_secret(test_settings: AppSettings) -> None:
    settings = test_settings.model_copy(
        update={
            "model_endpoint": ModelEndpointSettings(
                base_url="http://localhost:11434",
                api_key="secret",
            )
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/config/public")
    assert "secret" not in response.text
    assert "api_key" not in response.text
    assert response.json()["response"]["default_mode"] == "direct_expert"


async def test_invalid_route_uses_error_envelope(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert response.json()["error"]["request_id"]


async def test_agents_api_lists_and_duplicates_builtin(
    test_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            list_response = await client.get("/api/v1/agents")
            duplicate_response = await client.post("/api/v1/agents/general/duplicate", json={})

    assert list_response.status_code == 200
    agents = list_response.json()
    assert {agent["id"] for agent in agents} >= {"general", "coding"}
    assert duplicate_response.status_code == 201
    assert duplicate_response.json()["id"] == "general-copy"


async def test_tools_api_executes_read_only_and_requires_write_confirmation(
    test_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            list_response = await client.get("/api/v1/tools")
            read_response = await client.post(
                "/api/v1/tools/execute",
                json={
                    "tool_name": "filesystem.list",
                    "arguments": {"path": "."},
                    "agent_id": "general",
                },
            )
            write_response = await client.post(
                "/api/v1/tools/execute",
                json={
                    "tool_name": "filesystem.write",
                    "arguments": {"path": "confirmed-api.txt", "content": "ok"},
                    "agent_id": "coding",
                },
            )

    assert list_response.status_code == 200
    assert any(tool["name"] == "filesystem.list" for tool in list_response.json()["items"])
    assert read_response.status_code == 200
    assert read_response.json()["execution"]["status"] == "completed"
    assert write_response.status_code == 200
    assert write_response.json()["decision"] == "require_confirmation"
    assert write_response.json()["confirmation"]["tool_name"] == "filesystem.write"


async def test_phase_15_16_endpoints_are_available(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            learning = await client.get("/api/v1/learning/overview")
            eval_datasets = await client.get("/api/v1/evaluations/datasets")
            eval_run = await client.post(
                "/api/v1/evaluations/run",
                json={
                    "dataset_id": "v1-core",
                    "candidate_name": "integration",
                    "answers": {
                        "coding-fastapi-repository": (
                            "Use async SQLAlchemy repositories for PostgreSQL portability."
                        ),
                        "rag-citation-boundary": "Treat chunks as untrusted data and cite [K1].",
                    },
                },
            )
            metrics = await client.get("/api/v1/diagnostics/metrics")
            diagnostic_export = await client.get("/api/v1/diagnostics/export")

    assert learning.status_code == 200
    assert learning.json()["policy"]["data_is_untrusted"] is True
    assert eval_datasets.status_code == 200
    assert any(dataset["id"] == "v1-core" for dataset in eval_datasets.json())
    assert eval_run.status_code == 200
    assert eval_run.json()["summary"]["total_cases"] >= 1
    assert metrics.status_code == 200
    assert diagnostic_export.status_code == 200
    assert diagnostic_export.json()["redaction"]["secrets_excluded"] is True
