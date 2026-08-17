"""Local single-user authentication service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import AuthSettings
from backend.core.time import utc_now
from backend.db.models import User
from backend.db.repositories.sqlalchemy import LOCAL_USER_ID, SqlAlchemyUserRepository

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390_000
SESSION_ALGORITHM = "HS256"


class AuthenticatedUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    is_bootstrap: bool
    password_revision: int = 0


class AuthService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: AuthSettings,
        *,
        data_dir: Path,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._secret = _load_or_create_session_secret(settings, data_dir)

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @property
    def cookie_name(self) -> str:
        return self._settings.session_cookie_name

    @property
    def ttl_seconds(self) -> int:
        return self._settings.session_ttl_seconds

    @property
    def cookie_secure(self) -> bool:
        return self._settings.cookie_secure

    @property
    def cookie_samesite(self) -> Literal["lax", "strict", "none"]:
        return self._settings.cookie_samesite

    async def bootstrap_admin(self) -> None:
        if not self.enabled:
            return
        username = self._settings.bootstrap_admin_username.strip()
        password = self._settings.bootstrap_admin_password.get_secret_value()
        async with self._session_factory() as session:
            repo = SqlAlchemyUserRepository(session)
            existing = await repo.get_by_username(username)
            if existing is not None:
                await session.commit()
                return
            local_user = await repo.get(LOCAL_USER_ID)
            user = local_user or User(
                id=LOCAL_USER_ID,
                display_name="Local Admin",
            )
            if local_user is None:
                session.add(user)
                await session.flush()
            await repo.set_auth_fields(
                user,
                username=username,
                password_hash=hash_password(password),
                role="admin",
                is_bootstrap=True,
                auth_metadata={
                    "bootstrap_seeded": True,
                    "trusted_instructions": False,
                    "seeded_at": utc_now().isoformat(),
                },
            )
            await session.commit()

    async def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        async with self._session_factory() as session:
            repo = SqlAlchemyUserRepository(session)
            user = await repo.get_by_username(username.strip())
            if user is None or user.password_hash is None:
                return None
            if not verify_password(password, user.password_hash):
                return None
            await repo.record_login(user, utc_now().isoformat())
            await session.commit()
            return _safe_user(user)

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> AuthenticatedUser | None:
        if len(new_password) < 8 or len(new_password) > 200:
            return None
        if hmac.compare_digest(current_password, new_password):
            return None
        async with self._session_factory() as session:
            repo = SqlAlchemyUserRepository(session)
            user = await repo.get(user_id)
            if user is None or user.password_hash is None:
                return None
            if not verify_password(current_password, user.password_hash):
                return None
            next_revision = _password_revision(user.auth_metadata) + 1
            metadata = user.auth_metadata | {
                "password_changed_at": utc_now().isoformat(),
                "password_revision": next_revision,
            }
            await repo.update_password_hash(user, hash_password(new_password), metadata)
            await session.commit()
            return _safe_user(user)

    async def user_from_token(self, token: str | None) -> AuthenticatedUser | None:
        if not token:
            return None
        payload = self._verify_token(token)
        if payload is None:
            return None
        user_id = _string_value(payload, "sub")
        username = _string_value(payload, "username")
        if user_id is None or username is None:
            return None
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get(user_id)
            if user is None or user.username != username or user.password_hash is None:
                return None
            if _password_revision(user.auth_metadata) != _token_password_revision(payload):
                return None
            return _safe_user(user)

    def create_session_token(self, user: AuthenticatedUser) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "alg": SESSION_ALGORITHM,
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "pwd_rev": user.password_revision,
            "iat": now,
            "exp": now + self.ttl_seconds,
            "nonce": secrets.token_urlsafe(18),
        }
        encoded = _b64_json(payload)
        signature = _sign(encoded, self._secret)
        return f"{encoded}.{signature}"

    def _verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            encoded, signature = token.split(".", maxsplit=1)
        except ValueError:
            return None
        expected = _sign(encoded, self._secret)
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            payload = json.loads(_b64_decode(encoded).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        exp = payload.get("exp")
        if not isinstance(exp, int) or exp < int(time.time()):
            return None
        return payload


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        [
            PBKDF2_ALGORITHM,
            str(PBKDF2_ITERATIONS),
            _b64_bytes(salt),
            _b64_bytes(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", maxsplit=3)
        iterations = int(iterations_text)
        salt = _b64_decode(salt_text)
        expected = _b64_decode(digest_text)
    except (ValueError, TypeError):
        return False
    if algorithm != PBKDF2_ALGORITHM:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _safe_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        username=user.username or "",
        display_name=user.display_name,
        role=user.role,
        is_bootstrap=user.is_bootstrap,
        password_revision=_password_revision(user.auth_metadata),
    )


def _password_revision(metadata: dict[str, Any]) -> int:
    value = metadata.get("password_revision")
    return value if isinstance(value, int) and value >= 0 else 0


def _token_password_revision(payload: dict[str, Any]) -> int:
    value = payload.get("pwd_rev")
    return value if isinstance(value, int) and value >= 0 else 0


def _load_or_create_session_secret(settings: AuthSettings, data_dir: Path) -> bytes:
    configured = settings.session_secret
    if configured is not None:
        return configured.get_secret_value().encode("utf-8")
    auth_dir = data_dir / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    secret_path = auth_dir / "session-secret.key"
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip().encode("utf-8")
    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    return secret.encode("utf-8")


def _sign(encoded_payload: str, secret: bytes) -> str:
    digest = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return _b64_bytes(digest)


def _b64_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _b64_bytes(raw)


def _b64_bytes(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _string_value(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None
