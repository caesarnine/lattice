from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lattice.domain.threads import ThreadNotFoundError, require_thread
from lattice.protocol.models import ModelListResponse
from lattice.server.context import AppContext
from lattice.server.deps import get_ctx
from lattice.domain.agents import select_agent_for_thread
from lattice.domain.models import list_models, resolve_default_model

router = APIRouter()


@router.get(
    "/sessions/{session_id}/threads/{thread_id}/models",
    response_model=ModelListResponse,
)
async def api_list_thread_models(
    session_id: str,
    thread_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> ModelListResponse:
    try:
        require_thread(ctx.store, session_id=session_id, thread_id=thread_id)
    except ThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    selection = select_agent_for_thread(ctx.store, ctx.registry, session_id=session_id, thread_id=thread_id)
    default_model = resolve_default_model(selection.plugin)
    return ModelListResponse(default_model=default_model, models=list_models(selection.plugin))
