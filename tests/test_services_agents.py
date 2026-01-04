from __future__ import annotations

import pytest

from lattice.agents.plugin import AgentPlugin
from lattice.agents.registry import AgentRegistry
from lattice.domain.agents import (
    resolve_requested_agent,
    select_agent_for_thread,
    set_thread_agent,
)
from lattice.domain.sessions import ThreadSettings


class FakeStore:
    def __init__(self) -> None:
        self._thread_settings: dict[tuple[str, str], ThreadSettings] = {}

    def get_thread_settings(self, session_id: str, thread_id: str) -> ThreadSettings:
        return self._thread_settings.get((session_id, thread_id), ThreadSettings())

    def set_thread_settings(self, session_id: str, thread_id: str, settings: ThreadSettings) -> None:
        self._thread_settings[(session_id, thread_id)] = settings


def _make_plugin(agent_id: str, name: str) -> AgentPlugin:
    return AgentPlugin(id=agent_id, name=name, create_agent=lambda model: object())


@pytest.fixture()
def agent_ctx():
    store = FakeStore()
    default_plugin = _make_plugin("alpha", "Alpha")
    other_plugin = _make_plugin("beta", "Beta Agent")
    registry = AgentRegistry(
        agents={"alpha": default_plugin, "beta": other_plugin},
        default_agent="alpha",
    )
    return store, registry


def test_select_agent_for_thread_uses_stored_id(agent_ctx) -> None:
    store, registry = agent_ctx
    store.set_thread_settings("s1", "t1", ThreadSettings(agent="beta"))
    selection = select_agent_for_thread(store, registry, session_id="s1", thread_id="t1")
    assert selection.agent_id == "beta"
    assert selection.agent_name == "Beta Agent"
    assert selection.is_default is False


def test_select_agent_for_thread_falls_back_when_not_exact(agent_ctx) -> None:
    store, registry = agent_ctx
    store.set_thread_settings("s1", "t1", ThreadSettings(agent="Beta"))
    selection = select_agent_for_thread(store, registry, session_id="s1", thread_id="t1")
    assert selection.agent_id == "alpha"
    assert selection.is_default is True


def test_set_thread_agent_resets_to_default(agent_ctx) -> None:
    store, registry = agent_ctx
    selection = set_thread_agent(store, registry, session_id="s1", thread_id="t1", requested=None)
    assert selection.agent_id == "alpha"
    assert selection.is_default is True
    settings = store.get_thread_settings("s1", "t1")
    assert settings.agent is None


def test_set_thread_agent_unknown_raises(agent_ctx) -> None:
    store, registry = agent_ctx
    with pytest.raises(ValueError):
        set_thread_agent(store, registry, session_id="s1", thread_id="t1", requested="unknown")


def test_resolve_requested_agent_allows_fuzzy_by_name(agent_ctx) -> None:
    _, registry = agent_ctx
    selection = resolve_requested_agent(registry, "be")
    assert selection.agent_id == "beta"
