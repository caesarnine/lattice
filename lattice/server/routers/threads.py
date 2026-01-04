from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

from lattice.core.session import generate_thread_id
from lattice.core.threads import create_thread, delete_thread, list_threads, load_thread_messages
from lattice.protocol.models import (
    ThreadClearResponse,
    ThreadCreateRequest,
    ThreadCreateResponse,
    ThreadDeleteResponse,
    ThreadListResponse,
    ThreadMessagesResponse,
)
from lattice.server.context import AppContext
from lattice.server.deps import get_ctx

router = APIRouter()


@router.get("/sessions/{session_id}/threads", response_model=ThreadListResponse)
async def api_list_threads(session_id: str, ctx: AppContext = Depends(get_ctx)) -> ThreadListResponse:
    return ThreadListResponse(threads=list_threads(ctx.store, session_id))


@router.post("/sessions/{session_id}/threads", response_model=ThreadCreateResponse)
async def api_create_thread(
    session_id: str,
    payload: ThreadCreateRequest,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadCreateResponse:
    thread_id = payload.thread_id or ""
    if not thread_id:
        thread_id = generate_thread_id()
    try:
        create_thread(ctx.store, session_id=session_id, thread_id=thread_id, workspace=ctx.workspace)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ThreadCreateResponse(thread_id=thread_id)


@router.delete("/sessions/{session_id}/threads/{thread_id}", response_model=ThreadDeleteResponse)
async def api_delete_thread(
    session_id: str,
    thread_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadDeleteResponse:
    if thread_id not in list_threads(ctx.store, session_id):
        raise HTTPException(status_code=404, detail="Thread not found.")
    delete_thread(ctx.store, session_id=session_id, thread_id=thread_id)
    return ThreadDeleteResponse(deleted=thread_id)


@router.post(
    "/sessions/{session_id}/threads/{thread_id}/clear",
    response_model=ThreadClearResponse,
)
async def api_clear_thread(
    session_id: str,
    thread_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadClearResponse:
    if thread_id not in list_threads(ctx.store, session_id):
        raise HTTPException(status_code=404, detail="Thread not found.")
    ctx.store.save_thread(session_id, thread_id, workspace=ctx.workspace, messages=[])
    return ThreadClearResponse(cleared=thread_id)


@router.get(
    "/sessions/{session_id}/threads/{thread_id}/messages",
    response_model=ThreadMessagesResponse,
)
async def api_thread_messages(
    session_id: str,
    thread_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadMessagesResponse:
    messages = load_thread_messages(
        ctx.store, session_id=session_id, thread_id=thread_id, workspace=ctx.workspace
    )
    ui_messages = VercelAIAdapter.dump_messages(messages)
    return ThreadMessagesResponse(messages=ui_messages)
