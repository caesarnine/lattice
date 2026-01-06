from __future__ import annotations

import importlib.metadata
import os

from fastapi import APIRouter, Depends

from lattis.runtime.bootstrap import bootstrap_session
from lattis.protocol.schemas import ServerInfoResponse, SessionBootstrapResponse
from lattis.runtime.context import AppContext
from lattis.server.deps import get_ctx
from lattis.domain.agents import get_default_plugin

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/info", response_model=ServerInfoResponse)
async def info(ctx: AppContext = Depends(get_ctx)) -> ServerInfoResponse:
    default_plugin = get_default_plugin(ctx.registry)
    try:
        version = importlib.metadata.version("lattis")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        version = "unknown"
    return ServerInfoResponse(
        version=version,
        pid=os.getpid(),
        project_root=str(ctx.project_root),
        data_dir=str(ctx.config.data_dir),
        workspace_dir=str(ctx.workspace),
        workspace_mode=ctx.config.workspace_mode,
        agent_name=default_plugin.name,
    )


@router.get("/session/bootstrap", response_model=SessionBootstrapResponse)
async def api_session_bootstrap(
    thread_id: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> SessionBootstrapResponse:
    return bootstrap_session(ctx, thread_id=thread_id)
