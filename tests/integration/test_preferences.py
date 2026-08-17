from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.api.app import create_app
from backend.core.config import AppSettings, AuthSettings


async def test_preferences_are_authenticated_validated_and_persisted(
    test_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    settings = test_settings.model_copy(
        update={
            "auth": AuthSettings(
                enabled=True,
                bootstrap_admin_username="admin",
                bootstrap_admin_password="admin987",  # noqa: S106 - test bootstrap credential
                session_secret="test-session-secret",  # noqa: S106 - deterministic test secret
            )
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            anonymous = await client.get("/api/v1/preferences")
            await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987"},
            )
            defaults = await client.get("/api/v1/preferences")
            invalid = await client.patch("/api/v1/preferences", json={"response_mode": "unsafe"})
            updated = await client.patch(
                "/api/v1/preferences",
                json={
                    "response_mode": "standard",
                    "technical_depth": "deep",
                    "default_agent": "expert",
                    "intelligence_mode": "quality",
                    "reasoning_mode": "deep",
                    "theme": "dark",
                },
            )
            persisted = await client.get("/api/v1/preferences")

    assert anonymous.status_code == 401
    assert defaults.status_code == 200
    assert defaults.json()["response_mode"] == "direct_expert"
    assert defaults.json()["technical_depth"] == "expert"
    assert defaults.json()["reasoning_mode"] == "auto"
    assert invalid.status_code == 422
    assert updated.status_code == 200
    assert updated.json() == {
        "response_mode": "standard",
        "technical_depth": "deep",
        "default_agent": "expert",
        "intelligence_mode": "quality",
        "reasoning_mode": "deep",
        "theme": "dark",
    }
    assert persisted.json() == updated.json()
