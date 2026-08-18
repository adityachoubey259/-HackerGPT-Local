"""Workspace and Local Coding Agent endpoints."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.core import get_db_session
from backend.db.models.workspace import Workspace
from backend.services.workspace import (
    PathOutsideWorkspaceError,
    WorkspaceConflictError,
    apply_patch_to_file,
    canonicalize_and_validate_path,
    compute_file_hash,
    generate_directory_tree,
    is_binary_file,
    search_workspace_text,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class OpenWorkspaceRequest(BaseModel):
    path: str = Field(description="Absolute local folder path to open as workspace")


class WorkspaceReadRequest(BaseModel):
    file_path: str


class WorkspacePatchRequest(BaseModel):
    file_path: str
    patch_text: str
    expected_hash: str | None = None


class WorkspaceSearchRequest(BaseModel):
    query: str
    is_regex: bool = False


class CreateTaskRequest(BaseModel):
    user_request: str
    mode: str = "agent"  # ask, plan, edit, agent
    model: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    root_path: str
    trusted: bool
    git_repository: bool
    git_branch: str | None
    language_summary: str | None
    framework_summary: str | None
    created_at: str
    last_opened_at: str


def inspect_git_info(root: Path) -> tuple[bool, str | None]:
    git_dir = root / ".git"
    if not git_dir.exists():
        return False, None
    git_path = shutil.which("git")
    if not git_path:
        return True, "main"
    try:
        proc = subprocess.run(  # noqa: S603
            [git_path, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
    except Exception:  # noqa: S110
        pass
    return True, "main"


def detect_frameworks(root: Path) -> tuple[str, str]:
    langs = []
    frameworks = []

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        langs.append("Python")
        if (root / "pyproject.toml").exists():
            content = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if "fastapi" in content.lower():
                frameworks.append("FastAPI")
            if "django" in content.lower():
                frameworks.append("Django")

    if (root / "package.json").exists():
        langs.append("JavaScript/TypeScript")
        content = (root / "package.json").read_text(encoding="utf-8", errors="ignore")
        if "react" in content.lower():
            frameworks.append("React")
        if "next" in content.lower():
            frameworks.append("Next.js")
        if "express" in content.lower():
            frameworks.append("Express")

    if (root / "Cargo.toml").exists():
        langs.append("Rust")

    if (root / "go.mod").exists():
        langs.append("Go")

    if (root / "CMakeLists.txt").exists() or (root / "Makefile").exists():
        langs.append("C/C++")

    return (
        ", ".join(langs) if langs else "General",
        ", ".join(frameworks) if frameworks else "Standard",
    )


@router.post("/open", response_model=WorkspaceResponse)
async def open_workspace(
    body: OpenWorkspaceRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> WorkspaceResponse:
    target_path = Path(body.path).resolve()  # noqa: ASYNC240
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local workspace directory does not exist: '{body.path}'",
        )

    root_str = str(target_path)
    stmt = select(Workspace).where(Workspace.root_path == root_str)
    res = await session.execute(stmt)
    workspace = res.scalar_one_or_none()

    is_git, git_branch = inspect_git_info(target_path)
    lang_sum, fw_sum = detect_frameworks(target_path)

    if not workspace:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=target_path.name or root_str,
            root_path=root_str,
            trusted=True,  # User explicitly opening folder grants local trust
            git_repository=is_git,
            git_branch=git_branch,
            language_summary=lang_sum,
            framework_summary=fw_sum,
            created_at=datetime.now(UTC),
            last_opened_at=datetime.now(UTC),
        )
        session.add(workspace)
    else:
        workspace.last_opened_at = datetime.now(UTC)
        workspace.git_repository = is_git
        workspace.git_branch = git_branch
        workspace.language_summary = lang_sum
        workspace.framework_summary = fw_sum

    await session.commit()
    await session.refresh(workspace)

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        root_path=workspace.root_path,
        trusted=workspace.trusted,
        git_repository=workspace.git_repository,
        git_branch=workspace.git_branch,
        language_summary=workspace.language_summary,
        framework_summary=workspace.framework_summary,
        created_at=workspace.created_at.isoformat(),
        last_opened_at=workspace.last_opened_at.isoformat(),
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[WorkspaceResponse]:
    stmt = select(Workspace).order_by(Workspace.last_opened_at.desc()).limit(20)
    res = await session.execute(stmt)
    workspaces = res.scalars().all()
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            root_path=w.root_path,
            trusted=w.trusted,
            git_repository=w.git_repository,
            git_branch=w.git_branch,
            language_summary=w.language_summary,
            framework_summary=w.framework_summary,
            created_at=w.created_at.isoformat(),
            last_opened_at=w.last_opened_at.isoformat(),
        )
        for w in workspaces
    ]


@router.get("/{id}/tree", response_model=dict[str, Any])
async def get_workspace_tree(
    id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    stmt = select(Workspace).where(Workspace.id == id)
    res = await session.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    root = Path(workspace.root_path)
    if not root.exists():  # noqa: ASYNC240
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace folder no longer exists"
        )

    tree = generate_directory_tree(root)
    return tree.model_dump()


@router.post("/{id}/read", response_model=dict[str, Any])
async def read_workspace_file(
    id: str,
    body: WorkspaceReadRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    stmt = select(Workspace).where(Workspace.id == id)
    res = await session.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    try:
        fpath = canonicalize_and_validate_path(workspace.root_path, body.file_path)
    except PathOutsideWorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not fpath.exists() or not fpath.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: '{body.file_path}'"
        )

    if is_binary_file(fpath):
        return {
            "file_path": body.file_path,
            "is_binary": True,
            "content": "[Binary file content omitted]",
            "revision_hash": compute_file_hash(fpath),
        }

    content = fpath.read_text(encoding="utf-8", errors="ignore")
    return {
        "file_path": body.file_path,
        "is_binary": False,
        "content": content,
        "revision_hash": compute_file_hash(fpath),
    }


@router.post("/{id}/patch", response_model=dict[str, Any])
async def patch_workspace_file(
    id: str,
    body: WorkspacePatchRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    stmt = select(Workspace).where(Workspace.id == id)
    res = await session.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    try:
        fpath = canonicalize_and_validate_path(workspace.root_path, body.file_path)
    except PathOutsideWorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    fpath.parent.mkdir(parents=True, exist_ok=True)

    try:
        new_hash, diff = apply_patch_to_file(
            fpath, body.patch_text, expected_hash=body.expected_hash
        )
    except WorkspaceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "workspace_conflict",
                "message": str(exc),
                "current_hash": exc.current_hash,
            },
        ) from exc

    return {
        "file_path": body.file_path,
        "new_hash": new_hash,
        "diff": diff,
        "applied": True,
    }


@router.post("/{id}/search", response_model=list[dict[str, Any]])
async def search_workspace(
    id: str,
    body: WorkspaceSearchRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[dict[str, Any]]:
    stmt = select(Workspace).where(Workspace.id == id)
    res = await session.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return search_workspace_text(Path(workspace.root_path), body.query, is_regex=body.is_regex)
