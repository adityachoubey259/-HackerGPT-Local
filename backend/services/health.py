"""Health and system services."""

from __future__ import annotations

import platform
import socket
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.health import DependencyStatus, ReadinessResponse
from backend.api.schemas.system import SystemInfoResponse
from backend.core.config import AppSettings
from backend.core.version import APP_VERSION


class HealthService:
    def __init__(self, settings: AppSettings, startup_monotonic: float | None = None) -> None:
        self._settings = settings
        self._startup_monotonic = (
            startup_monotonic if startup_monotonic is not None else time.monotonic()
        )

    async def readiness(self, session: AsyncSession) -> ReadinessResponse:
        dependencies: dict[str, DependencyStatus] = {}
        try:
            await session.execute(text("SELECT 1"))
            dependencies["database"] = DependencyStatus(
                status="ok",
                details={"type": self._settings.database.type},
            )
        except Exception as exc:
            dependencies["database"] = DependencyStatus(
                status="unavailable",
                details={"type": self._settings.database.type, "error": exc.__class__.__name__},
            )
        status = "ok" if all(item.status == "ok" for item in dependencies.values()) else "degraded"
        return ReadinessResponse(status=status, dependencies=dependencies)

    def system_info(self) -> SystemInfoResponse:
        return SystemInfoResponse(
            application_version=APP_VERSION,
            environment=self._settings.environment,
            python_version=sys.version.split()[0],
            operating_system=platform.system(),
            architecture=platform.machine(),
            hostname=socket.gethostname() if self._settings.environment != "production" else None,
            database_type=self._settings.database.type,
            debug=self._settings.debug,
            uptime_seconds=round(time.monotonic() - self._startup_monotonic, 3),
        )
