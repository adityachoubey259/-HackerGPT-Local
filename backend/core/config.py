"""Typed application configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    allow_credentials: bool = True


class DatabaseSettings(BaseModel):
    url: str = "sqlite+aiosqlite:///./data/databases/hackergpt.db"
    echo: bool = False

    @property
    def type(self) -> str:
        return self.url.split(":", maxsplit=1)[0]


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_logs: bool = Field(default=True, validation_alias="json")
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("level")
    @classmethod
    def normalize_level(cls, value: str) -> str:
        level = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            msg = f"log level must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return level


class PathSettings(BaseModel):
    data_dir: Path = Path("data")
    databases_dir: Path = Path("data/databases")
    uploads_dir: Path = Path("data/uploads")
    knowledge_dir: Path = Path("data/knowledge")
    models_dir: Path = Path("data/models")


class ModelEndpointSettings(BaseModel):
    base_url: str = "http://localhost:11434"
    api_key: SecretStr | None = None
    cloud_inference_enabled: bool = False


class FrontendSettings(BaseModel):
    serve_static: bool = True
    dist_dir: Path = Path("frontend/dist")


class AuthSettings(BaseModel):
    enabled: bool = True
    bootstrap_admin_username: str = Field(default="admin", min_length=1, max_length=80)
    bootstrap_admin_password: SecretStr = Field(default=SecretStr("admin987"))
    session_cookie_name: str = "hackergpt_session"
    session_ttl_seconds: int = Field(default=60 * 60 * 24 * 7, ge=300)
    session_secret: SecretStr | None = None
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"


class AppSettings(BaseModel):
    environment: str = "development"
    debug: bool = False
    network_access: bool = False
    api: ApiSettings = Field(default_factory=ApiSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    model_endpoint: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    frontend: FrontendSettings = Field(default_factory=FrontendSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        environment = value.lower()
        allowed = {"development", "test", "production"}
        if environment not in allowed:
            msg = f"environment must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return environment

    def public_config(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "debug": self.debug,
            "network_access": self.network_access,
            "api": {
                "allowed_origins": self.api.allowed_origins,
            },
            "model_endpoint": {
                "base_url": self.model_endpoint.base_url,
                "cloud_inference_enabled": self.model_endpoint.cloud_inference_enabled,
            },
            "frontend": {
                "serve_static": self.frontend.serve_static,
            },
        }


class EnvSettings(BaseSettings):
    environment: str | None = None
    debug: bool | None = None
    api_host: str | None = None
    api_port: int | None = None
    allowed_origins: str | None = None
    database_url: str | None = None
    database_echo: bool | None = None
    log_level: str | None = None
    data_dir: Path | None = None
    databases_dir: Path | None = None
    uploads_dir: Path | None = None
    knowledge_dir: Path | None = None
    models_dir: Path | None = None
    network_access: bool | None = None
    cloud_inference_enabled: bool | None = None
    model_endpoint_base_url: str | None = None
    model_endpoint_api_key: SecretStr | None = None
    serve_frontend: bool | None = None
    frontend_dist_dir: Path | None = None
    auth_enabled: bool | None = None
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: SecretStr | None = None
    auth_session_secret: SecretStr | None = None
    auth_cookie_secure: bool | None = None

    model_config = SettingsConfigDict(
        env_prefix="HACKERGPT_",
        env_file=".env",
        extra="ignore",
    )


DEFAULT_CONFIG_PATH = Path("config/app.yaml")


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        msg = f"YAML config at {path} must contain a mapping"
        raise ValueError(msg)
    return loaded


def _apply_env(settings_data: dict[str, Any], env: EnvSettings) -> dict[str, Any]:
    data = dict(settings_data)
    if env.environment is not None:
        data["environment"] = env.environment
    if env.debug is not None:
        data["debug"] = env.debug
    if env.network_access is not None:
        data["network_access"] = env.network_access

    data.setdefault("api", {})
    if env.api_host is not None:
        data["api"]["host"] = env.api_host
    if env.api_port is not None:
        data["api"]["port"] = env.api_port
    if env.allowed_origins is not None:
        data["api"]["allowed_origins"] = [
            origin.strip() for origin in env.allowed_origins.split(",") if origin.strip()
        ]

    data.setdefault("database", {})
    if env.database_url is not None:
        data["database"]["url"] = env.database_url
    if env.database_echo is not None:
        data["database"]["echo"] = env.database_echo

    data.setdefault("logging", {})
    if env.log_level is not None:
        data["logging"]["level"] = env.log_level

    data.setdefault("paths", {})
    for env_name, config_name in (
        ("data_dir", "data_dir"),
        ("databases_dir", "databases_dir"),
        ("uploads_dir", "uploads_dir"),
        ("knowledge_dir", "knowledge_dir"),
        ("models_dir", "models_dir"),
    ):
        value = getattr(env, env_name)
        if value is not None:
            data["paths"][config_name] = value

    data.setdefault("model_endpoint", {})
    if env.model_endpoint_base_url is not None:
        data["model_endpoint"]["base_url"] = env.model_endpoint_base_url
    if env.model_endpoint_api_key is not None:
        data["model_endpoint"]["api_key"] = env.model_endpoint_api_key
    if env.cloud_inference_enabled is not None:
        data["model_endpoint"]["cloud_inference_enabled"] = env.cloud_inference_enabled
    data.setdefault("frontend", {})
    if env.serve_frontend is not None:
        data["frontend"]["serve_static"] = env.serve_frontend
    if env.frontend_dist_dir is not None:
        data["frontend"]["dist_dir"] = env.frontend_dist_dir
    data.setdefault("auth", {})
    if env.auth_enabled is not None:
        data["auth"]["enabled"] = env.auth_enabled
    if env.bootstrap_admin_username is not None:
        data["auth"]["bootstrap_admin_username"] = env.bootstrap_admin_username
    if env.bootstrap_admin_password is not None:
        data["auth"]["bootstrap_admin_password"] = env.bootstrap_admin_password
    if env.auth_session_secret is not None:
        data["auth"]["session_secret"] = env.auth_session_secret
    if env.auth_cookie_secure is not None:
        data["auth"]["cookie_secure"] = env.auth_cookie_secure
    if os.getenv("BOOTSTRAP_ADMIN_USERNAME"):
        data["auth"]["bootstrap_admin_username"] = os.environ["BOOTSTRAP_ADMIN_USERNAME"]
    if os.getenv("BOOTSTRAP_ADMIN_PASSWORD"):
        data["auth"]["bootstrap_admin_password"] = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]
    return data


def load_settings(config_path: Path | None = None) -> AppSettings:
    path = config_path or Path(os.getenv("HACKERGPT_CONFIG_FILE", str(DEFAULT_CONFIG_PATH)))
    base = AppSettings().model_dump()
    data = _deep_merge(base, _load_yaml(path))
    data = _apply_env(data, EnvSettings())
    try:
        return AppSettings.model_validate(data)
    except ValidationError as exc:
        msg = "Invalid HackerGPT Local configuration"
        raise ValueError(msg) from exc


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
