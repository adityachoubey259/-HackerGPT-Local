"""Safe persisted user preferences."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.schemas.preferences import UserPreferencesPatch, UserPreferencesResponse
from backend.core.policy import PolicyConfig, ResponseMode, TechnicalDepth
from backend.db.repositories.sqlalchemy import SqlAlchemySettingRepository

PREFERENCE_KEY_PREFIX = "user_preferences:"


class PreferenceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PolicyConfig,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy

    async def get(self, user_id: str) -> UserPreferencesResponse:
        async with self._session_factory() as session:
            setting = await SqlAlchemySettingRepository(session).get(_key(user_id))
            if setting is None:
                return self.defaults()
            return _preferences_from_payload(setting.value, self.defaults())

    async def patch(self, user_id: str, patch: UserPreferencesPatch) -> UserPreferencesResponse:
        current = await self.get(user_id)
        updates = patch.model_dump(exclude_unset=True)
        payload = current.model_dump(mode="json") | updates
        preferences = _preferences_from_payload(payload, self.defaults())
        async with self._session_factory() as session:
            await SqlAlchemySettingRepository(session).set(
                _key(user_id),
                preferences.model_dump(mode="json"),
            )
            await session.commit()
        return preferences

    async def effective_policy(self, user_id: str) -> PolicyConfig:
        preferences = await self.get(user_id)
        response = self._policy.effective_response.model_copy(
            update={
                "default_mode": preferences.response_mode,
                "technical_depth": preferences.technical_depth,
            }
        )
        return self._policy.model_copy(update={"response_behavior": response}, deep=True)

    def defaults(self) -> UserPreferencesResponse:
        response = self._policy.effective_response
        return UserPreferencesResponse(
            response_mode=response.default_mode,
            technical_depth=_normalize_depth(response.technical_depth),
            default_agent="expert" if response.default_mode is ResponseMode.DIRECT_EXPERT else None,
            intelligence_mode="auto",
            theme="system",
        )


def _key(user_id: str) -> str:
    return f"{PREFERENCE_KEY_PREFIX}{user_id}"


def _preferences_from_payload(
    payload: dict[str, object],
    defaults: UserPreferencesResponse,
) -> UserPreferencesResponse:
    merged = defaults.model_dump(mode="json") | payload
    return UserPreferencesResponse.model_validate(merged)


def _normalize_depth(depth: TechnicalDepth) -> TechnicalDepth:
    if depth is TechnicalDepth.ADVANCED:
        return TechnicalDepth.DEEP
    return depth
