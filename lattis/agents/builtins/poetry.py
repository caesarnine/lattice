from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent, RunContext

from lattis.agents.plugin import AgentPlugin, list_known_models
from lattis.settings.env import AGENT_MODEL, first_env


SYSTEM_PROMPT = """\
You are a poetry agent.

Write vivid, high-quality poems with strong imagery and rhythm.

Default behavior:
- Ask 1 clarifying question if the request is ambiguous (style, length, subject, constraints).
- Otherwise, write the poem directly.
- If the user gives constraints (meter, rhyme scheme, form), follow them.

When useful, include a short title on the first line.
"""


POETRY_AGENT_MODEL = "POETRY_AGENT_MODEL"
DEFAULT_MODEL = first_env(POETRY_AGENT_MODEL, AGENT_MODEL) or "google-gla:gemini-3-flash-preview"


@lru_cache(maxsize=8)
def _get_agent(model: str) -> Agent[None, str]:
    agent: Agent[None, str] = Agent(model, deps_type=None)

    @agent.instructions
    def instructions(_ctx: RunContext[None]) -> str:
        return SYSTEM_PROMPT

    return agent


def _create_agent(model: str) -> Agent[None, str]:
    return _get_agent(model)


plugin = AgentPlugin(
    id="poetry",
    name="Poetry",
    create_agent=_create_agent,
    default_model=DEFAULT_MODEL,
    list_models=lambda: list_known_models(default_model=DEFAULT_MODEL),
)
