from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai.exceptions import UserError

from lattice.protocol.models import (
    ModelListResponse,
    SessionModelRequest,
    SessionModelResponse,
)
from lattice.server.context import AppContext
from lattice.server.deps import get_ctx
from lattice.server.runtime import resolve_default_model

router = APIRouter()


@router.get("/models", response_model=ModelListResponse)
async def api_list_models(ctx: AppContext = Depends(get_ctx)) -> ModelListResponse:
    default_plugin = ctx.registry.agents[ctx.registry.default_agent]
    default_model = resolve_default_model(default_plugin)
    models: list[str] = []
    if default_plugin.list_models:
        try:
            models = list(default_plugin.list_models())
        except Exception:
            models = []
    return ModelListResponse(default_model=default_model, models=models)


@router.get("/sessions/{session_id}/model", response_model=SessionModelResponse)
async def api_get_session_model(session_id: str, ctx: AppContext = Depends(get_ctx)) -> SessionModelResponse:
    default_plugin = ctx.registry.agents[ctx.registry.default_agent]
    default_model = resolve_default_model(default_plugin)
    model = ctx.store.get_session_model(session_id) or default_model
    return SessionModelResponse(
        model=model,
        default_model=default_model,
        is_default=model == default_model,
    )


@router.put("/sessions/{session_id}/model", response_model=SessionModelResponse)
async def api_set_session_model(
    session_id: str,
    payload: SessionModelRequest,
    ctx: AppContext = Depends(get_ctx),
) -> SessionModelResponse:
    default_plugin = ctx.registry.agents[ctx.registry.default_agent]
    default_model = resolve_default_model(default_plugin)
    model = (payload.model or "").strip() if payload.model is not None else None
    if model:
        try:
            if default_plugin.validate_model:
                default_plugin.validate_model(model)
        except UserError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        ctx.store.set_session_model(session_id, model)
        selected = model
    else:
        ctx.store.set_session_model(session_id, None)
        selected = default_model
    return SessionModelResponse(
        model=selected,
        default_model=default_model,
        is_default=selected == default_model,
    )
