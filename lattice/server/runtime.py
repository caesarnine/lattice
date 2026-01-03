from __future__ import annotations

import os

from lattice.agents.plugin import AgentPlugin
from lattice.server.context import AppContext


def resolve_default_model(plugin: AgentPlugin) -> str:
    configured = (plugin.default_model or "").strip()
    if configured:
        return configured
    env = (os.getenv("AGENT_MODEL") or os.getenv("LATTICE_MODEL") or "").strip()
    if env:
        return env
    models = []
    if plugin.list_models:
        try:
            models = list(plugin.list_models())
        except Exception:
            models = []
    return models[0] if models else ""


def resolve_agent_plugin(ctx: AppContext, *, session_id: str, thread_id: str) -> tuple[str, AgentPlugin]:
    stored = ctx.store.get_thread_settings(session_id, thread_id).agent
    if stored:
        resolved = ctx.registry.resolve_id(stored, allow_fuzzy=False)
        if resolved:
            plugin = ctx.registry.agents[resolved]
            return resolved, plugin
    agent_id = ctx.registry.default_agent
    return agent_id, ctx.registry.agents[agent_id]
