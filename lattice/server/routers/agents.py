from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lattice.protocol.models import (
    AgentInfo,
    AgentListResponse,
    ThreadAgentRequest,
    ThreadAgentResponse,
)
from lattice.server.context import AppContext
from lattice.server.deps import get_ctx
from lattice.server.runtime import resolve_agent_plugin

router = APIRouter()


@router.get("/agents", response_model=AgentListResponse)
async def api_list_agents(ctx: AppContext = Depends(get_ctx)) -> AgentListResponse:
    agents = [AgentInfo(id=agent_id, name=plugin.name) for agent_id, plugin in ctx.registry.agents.items()]
    return AgentListResponse(default_agent=ctx.registry.default_agent, agents=agents)


@router.get(
    "/sessions/{session_id}/threads/{thread_id}/agent",
    response_model=ThreadAgentResponse,
)
async def api_get_thread_agent(
    session_id: str,
    thread_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadAgentResponse:
    default_agent = ctx.registry.default_agent
    agent_id, plugin = resolve_agent_plugin(ctx, session_id=session_id, thread_id=thread_id)
    return ThreadAgentResponse(
        agent=agent_id,
        default_agent=default_agent,
        is_default=agent_id == default_agent,
        agent_name=plugin.name,
    )


@router.put(
    "/sessions/{session_id}/threads/{thread_id}/agent",
    response_model=ThreadAgentResponse,
)
async def api_set_thread_agent(
    session_id: str,
    thread_id: str,
    payload: ThreadAgentRequest,
    ctx: AppContext = Depends(get_ctx),
) -> ThreadAgentResponse:
    default_agent = ctx.registry.default_agent
    settings = ctx.store.get_thread_settings(session_id, thread_id)
    requested = (payload.agent or "").strip() if payload.agent is not None else None
    if requested:
        resolved = ctx.registry.resolve_id(requested, allow_fuzzy=True)
        if resolved is None:
            available = ", ".join(sorted({plugin.name for plugin in ctx.registry.agents.values()}))
            raise HTTPException(
                status_code=400,
                detail=f"Unknown or ambiguous agent '{requested}'. Available: {available}",
            )
        settings.agent = resolved
        ctx.store.set_thread_settings(session_id, thread_id, settings)
        selected = resolved
    else:
        settings.agent = None
        ctx.store.set_thread_settings(session_id, thread_id, settings)
        selected = default_agent

    plugin = ctx.registry.agents[selected]
    return ThreadAgentResponse(
        agent=selected,
        default_agent=default_agent,
        is_default=selected == default_agent,
        agent_name=plugin.name,
    )
