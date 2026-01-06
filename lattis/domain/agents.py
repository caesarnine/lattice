from __future__ import annotations

from dataclasses import dataclass

from lattis.agents.plugin import AgentPlugin
from lattis.agents.registry import AgentRegistry
from lattis.domain.sessions import SessionStore


@dataclass(frozen=True)
class AgentSelection:
    agent_id: str
    plugin: AgentPlugin
    default_agent_id: str

    @property
    def is_default(self) -> bool:
        return self.agent_id == self.default_agent_id

    @property
    def agent_name(self) -> str:
        return self.plugin.name


def get_default_plugin(registry: AgentRegistry) -> AgentPlugin:
    return registry.agents[registry.default_agent]


def default_agent_selection(registry: AgentRegistry) -> AgentSelection:
    default_id = registry.default_agent
    return AgentSelection(
        agent_id=default_id,
        plugin=registry.agents[default_id],
        default_agent_id=default_id,
    )


def select_agent_for_thread(
    store: SessionStore,
    registry: AgentRegistry,
    *,
    session_id: str,
    thread_id: str,
) -> AgentSelection:
    stored = store.get_thread_settings(session_id, thread_id).agent
    if stored:
        resolved = registry.resolve_id(stored, allow_fuzzy=False)
        if resolved:
            plugin = registry.agents[resolved]
            return AgentSelection(
                agent_id=resolved,
                plugin=plugin,
                default_agent_id=registry.default_agent,
            )
    return default_agent_selection(registry)


def resolve_requested_agent(
    registry: AgentRegistry,
    requested: str,
    *,
    allow_fuzzy: bool = True,
) -> AgentSelection:
    resolved = registry.resolve_id(requested, allow_fuzzy=allow_fuzzy)
    if resolved is None:
        available = ", ".join(sorted({plugin.name for plugin in registry.agents.values()}))
        raise ValueError(f"Unknown or ambiguous agent '{requested}'. Available: {available}")
    plugin = registry.agents[resolved]
    return AgentSelection(
        agent_id=resolved,
        plugin=plugin,
        default_agent_id=registry.default_agent,
    )


def set_thread_agent(
    store: SessionStore,
    registry: AgentRegistry,
    *,
    session_id: str,
    thread_id: str,
    requested: str | None,
) -> AgentSelection:
    settings = store.get_thread_settings(session_id, thread_id)
    if requested is None or not requested.strip():
        settings.agent = None
        store.set_thread_settings(session_id, thread_id, settings)
        return default_agent_selection(registry)

    selection = resolve_requested_agent(registry, requested, allow_fuzzy=True)
    settings.agent = selection.agent_id
    store.set_thread_settings(session_id, thread_id, settings)
    return selection
