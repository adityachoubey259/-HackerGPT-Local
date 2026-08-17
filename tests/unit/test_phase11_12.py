from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.errors import ApplicationError
from backend.api.schemas.research import ResearchRunRequest
from backend.api.schemas.security import SecurityWorkspaceCreate, StaticReviewRequest
from backend.core.policy import PolicyConfig, ResearchPolicy
from backend.research.safety import ensure_url_allowed
from backend.services.research import ResearchService
from backend.services.security_workspace import SecurityWorkspaceService


async def test_research_disabled_records_offline_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = ResearchService(session_factory, PolicyConfig())

    response = await service.run(ResearchRunRequest(query="latest sqlite release"))

    assert response.session.status == "offline"
    assert response.sources == []
    assert response.session.diagnostics["reason"] == "policy_disabled"


def test_research_blocks_private_network_targets() -> None:
    policy = ResearchPolicy(enabled=True)

    with pytest.raises(ApplicationError) as error:
        ensure_url_allowed("http://127.0.0.1:8000/health", policy)

    assert error.value.code == "RESEARCH_PRIVATE_NETWORK_BLOCKED"


async def test_security_static_review_is_read_only_and_detects_patterns(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    vulnerable = tmp_path / "sample.py"
    vulnerable.write_text(
        "import subprocess\nAPI_KEY = 'abc123abc123abc123'\nsubprocess.run('id', shell=True)\n",
        encoding="utf-8",
    )
    service = SecurityWorkspaceService(
        session_factory,
        PolicyConfig(),
        workspace_root=tmp_path,
    )
    workspace = await service.create_workspace(
        SecurityWorkspaceCreate(
            name="Static Review",
            mode="secure-code-review",
            description="Read-only test workspace.",
        )
    )

    response = await service.static_review(
        StaticReviewRequest(
            paths=["sample.py"],
            workspace_id=workspace.id,
            persist_findings=False,
        )
    )

    assert response.persisted == 0
    assert response.scanned_files == 1
    assert {finding.category for finding in response.findings} >= {"secrets", "command-execution"}
