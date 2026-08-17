from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.app import create_app
from backend.core.config import AppSettings


async def test_model_api_handles_ollama_offline(
    test_settings: AppSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
providers:
  ollama:
    enabled: true
    type: ollama
    base_url: http://127.0.0.1:9
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("HACKERGPT_MODELS_CONFIG_FILE", str(config_path))
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            providers = await client.get("/api/v1/models/providers")
            models = await client.get("/api/v1/models")
            explicit_models = await client.get("/api/v1/models", params={"provider": "ollama"})
            test_response = await client.post(
                "/api/v1/models/test",
                json={"provider": "ollama", "model": "missing", "prompt": "hello"},
            )
    assert providers.status_code == 200
    assert providers.json()[0]["status"] == "unavailable"
    assert models.status_code == 200
    assert models.json() == []
    assert explicit_models.status_code == 503
    assert explicit_models.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert test_response.status_code == 503


async def test_invalid_provider_and_generation_parameters(
    test_settings: AppSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text("providers: {}\n", encoding="utf-8")
    monkeypatch.setenv("HACKERGPT_MODELS_CONFIG_FILE", str(config_path))
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            invalid_provider = await client.get("/api/v1/models", params={"provider": "missing"})
            invalid_params = await client.post(
                "/api/v1/models/test",
                json={
                    "provider": "missing",
                    "model": "model",
                    "prompt": "hello",
                    "settings": {"temperature": 3},
                },
            )
    assert invalid_provider.status_code == 503
    assert invalid_provider.json()["error"]["request_id"]
    assert invalid_params.status_code == 422


async def test_hardware_endpoint_is_safe(test_settings: AppSettings) -> None:
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/system/hardware")
    body = response.json()
    assert response.status_code == 200
    assert "environment_variables" not in body
    assert "operating_system" in body
