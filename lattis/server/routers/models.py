from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lattis.domain.threads import ThreadNotFoundError
from lattis.protocol.schemas import ModelListResponse
from lattis.runtime.context import AppContext
from lattis.runtime.thread_state import list_thread_models
from lattis.server.deps import get_ctx

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
        return list_thread_models(ctx, session_id=session_id, thread_id=thread_id)
    except ThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
