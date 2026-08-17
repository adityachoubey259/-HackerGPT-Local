from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.api.app import create_app
from backend.auth.service import verify_password
from backend.core.config import AppSettings, AuthSettings
from backend.db.models import User
from backend.llm.domain import (
    GenerationSettings,
    LLMMessage,
    LLMStreamEvent,
    LLMStreamEventType,
    ModelCallMetrics,
    ModelTestResponse,
    NormalizedModel,
    ProviderCapability,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderType,
    TokenUsage,
)
from backend.llm.providers.registry import LLMProviderRegistry
from backend.services.chat import ChatService
from backend.services.generation_manager import GenerationManager


@pytest.fixture
def auth_settings(test_settings: AppSettings) -> AppSettings:
    return test_settings.model_copy(
        update={
            "auth": AuthSettings(
                enabled=True,
                bootstrap_admin_username="admin",
                bootstrap_admin_password="admin987",  # noqa: S106 - test bootstrap credential
                session_secret="test-session-secret",  # noqa: S106 - deterministic test secret
            )
        }
    )


async def test_bootstrap_admin_is_seeded_with_password_hash(
    auth_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    app = create_app(auth_settings)
    async with app.router.lifespan_context(app):
        async with app.state.session_factory() as session:
            user = await session.get(User, "local-user")

    assert user is not None
    assert user.password_hash is not None
    assert "admin987" not in user.password_hash
    assert verify_password("admin987", user.password_hash)
    assert user.role == "admin"
    assert user.is_bootstrap is True


async def test_login_me_and_logout(auth_settings: AppSettings, db_engine: AsyncEngine) -> None:
    _ = db_engine
    app = create_app(auth_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987"},
            )
            me = await client.get("/api/v1/auth/me")
            logout = await client.post("/api/v1/auth/logout", json={})
            me_after_logout = await client.get("/api/v1/auth/me")

    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert login.json()["user"] == {
        "id": "local-user",
        "username": "admin",
        "display_name": "Local Admin",
        "role": "admin",
        "is_bootstrap": True,
    }
    assert "password" not in login.text.lower()
    assert me.json()["authenticated"] is True
    assert logout.json()["authenticated"] is False
    assert me_after_logout.json()["authenticated"] is False


async def test_login_failure_and_protected_api_rejection(
    auth_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(auth_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            bad_login = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            protected = await client.get("/api/v1/system/info")

    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert protected.status_code == 401
    assert protected.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_malformed_cookie_is_rejected(
    auth_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(auth_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(auth_settings.auth.session_cookie_name, "not-a-valid-token")
            me = await client.get("/api/v1/auth/me")
            protected = await client.get("/api/v1/system/info")

    assert me.status_code == 200
    assert me.json()["authenticated"] is False
    assert protected.status_code == 401


async def test_change_password_rehashes_and_invalidates_old_cookie(
    auth_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(auth_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987"},
            )
            old_cookie = client.cookies.get(auth_settings.auth.session_cookie_name)
            changed = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "admin987",
                    "new_password": "admin987-new",
                },
            )
            old_password_login = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987"},
            )
            new_password_login = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987-new"},
            )
        async with AsyncClient(transport=transport, base_url="http://testserver") as stale_client:
            assert old_cookie is not None
            stale_client.cookies.set(auth_settings.auth.session_cookie_name, old_cookie)
            stale_me = await stale_client.get("/api/v1/auth/me")
        async with app.state.session_factory() as session:
            user = await session.get(User, "local-user")

    assert changed.status_code == 200
    assert changed.json()["authenticated"] is True
    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200
    assert stale_me.json()["authenticated"] is False
    assert user is not None
    assert user.password_hash is not None
    assert "admin987-new" not in user.password_hash
    assert verify_password("admin987-new", user.password_hash)
    assert user.auth_metadata["password_revision"] == 1


class AuthStreamFakeProvider:
    provider_id = "fake"
    provider_type = ProviderType.OPENAI_COMPATIBLE
    display_name = "Fake Streaming Provider"
    enabled = True
    capabilities = frozenset({ProviderCapability.CHAT, ProviderCapability.STREAMING})

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_id,
            type=self.provider_type,
            status=ProviderHealthStatus.HEALTHY,
            capabilities=list(self.capabilities),
        )

    async def list_models(self) -> list[NormalizedModel]:
        return [await self.get_model("fake-model")]

    async def get_model(self, model_id: str) -> NormalizedModel:
        return NormalizedModel(
            id=model_id,
            name=model_id,
            provider=self.provider_id,
            provider_model_id=model_id,
            context_length=2048,
            capabilities=list(self.capabilities),
        )

    async def generate(
        self,
        model_id: str,
        prompt: str,
        settings: GenerationSettings,
    ) -> ModelTestResponse:
        return ModelTestResponse(
            provider=self.provider_id,
            model=model_id,
            text="ok",
            duration_ms=1,
            metrics=ModelCallMetrics(
                provider=self.provider_id,
                model=model_id,
                duration_ms=1,
                success=True,
            ),
        )

    def stream_chat(
        self,
        model_id: str,
        messages: list[LLMMessage],
        settings: GenerationSettings,
    ) -> AsyncIterator[LLMStreamEvent]:
        async def stream() -> AsyncIterator[LLMStreamEvent]:
            yield LLMStreamEvent(type=LLMStreamEventType.DELTA, text="AUTH_OK")
            yield LLMStreamEvent(
                type=LLMStreamEventType.DONE,
                finish_reason="stop",
                usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        return stream()


async def test_authenticated_chat_stream_requires_and_accepts_session_cookie(
    auth_settings: AppSettings,
    db_engine: AsyncEngine,
) -> None:
    _ = db_engine
    app = create_app(auth_settings)
    body = {
        "conversation_id": None,
        "client_request_id": "request-auth-stream",
        "message": "Verify authenticated streaming.",
        "provider": "fake",
        "model": "fake-model",
        "agent_id": None,
        "settings": {"temperature": 0.7, "top_p": 0.9, "max_output_tokens": 64},
    }
    async with app.router.lifespan_context(app):
        app.state.chat_service = ChatService(
            app.state.session_factory,
            LLMProviderRegistry([AuthStreamFakeProvider()]),
            {"provider": "fake", "model": "fake-model"},
            GenerationManager(),
            "You are HackerGPT Local.",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            rejected = await client.post("/api/v1/chat/stream", json=body)
            login = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin987"},
            )
            accepted = await client.post(
                "/api/v1/chat/stream",
                json=body | {"client_request_id": "request-auth-stream-ok"},
            )

    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "AUTH_REQUIRED"
    assert login.status_code == 200
    assert accepted.status_code == 200
    assert "event: delta" in accepted.text
    assert '"text":"AUTH_OK"' in accepted.text
    assert "event: done" in accepted.text
