from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic_ai.exceptions import UserError
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

from lattice.agents.plugin import AgentRunContext
from lattice.config import load_or_create_session_id
from lattice.core.messages import merge_messages
from lattice.server.context import AppContext
from lattice.server.deps import get_ctx
from lattice.server.runtime import resolve_agent_plugin, resolve_default_model
from lattice.server.services.sessions import (
    resolve_session_id_from_request,
    resolve_thread_id_from_request,
    select_message_history,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ui/chat")
async def ui_chat(request: Request, ctx: AppContext = Depends(get_ctx)):
    body = await request.body()
    run_input = VercelAIAdapter.build_run_input(body)
    default_session_id = load_or_create_session_id(ctx.config.session_id_path)
    session_id = resolve_session_id_from_request(run_input, default_session_id=default_session_id)
    thread_id = resolve_thread_id_from_request(run_input)
    if not thread_id:
        raise HTTPException(status_code=400, detail="Missing thread id.")

    agent_id, plugin = resolve_agent_plugin(ctx, session_id=session_id, thread_id=thread_id)
    model_name = ctx.store.get_session_model(session_id) or resolve_default_model(plugin)
    try:
        agent = plugin.create_agent(model_name)
    except UserError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    adapter = VercelAIAdapter(agent=agent, run_input=run_input, accept=request.headers.get("accept"))
    thread_state = ctx.store.load_thread(session_id, thread_id, workspace=ctx.workspace)
    message_history = select_message_history(run_input, thread_state.messages)
    if logger.isEnabledFor(logging.DEBUG):
        incoming_roles = [msg.role for msg in run_input.messages]
        history_roles = [getattr(msg, "role", None) for msg in message_history]
        logger.debug(
            "ui_chat session=%s thread=%s agent=%s incoming=%s history=%s",
            session_id,
            thread_id,
            agent_id,
            incoming_roles,
            history_roles,
        )

    run_ctx = AgentRunContext(
        session_id=session_id,
        thread_id=thread_id,
        model=model_name,
        workspace=ctx.workspace,
        project_root=ctx.project_root,
        run_input=run_input,
    )
    deps = plugin.create_deps(run_ctx) if plugin.create_deps else None

    def on_complete(result) -> None:
        incoming_messages = adapter.messages
        history_base = message_history
        merged = merge_messages(history_base, incoming_messages, result.new_messages())
        ctx.store.save_thread(session_id, thread_id, workspace=ctx.workspace, messages=merged)
        if plugin.on_complete:
            plugin.on_complete(run_ctx, result)

    stream = adapter.run_stream(deps=deps, message_history=message_history, on_complete=on_complete)
    return adapter.streaming_response(stream)
