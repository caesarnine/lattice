from __future__ import annotations

from collections.abc import Iterable

from pydantic_ai.ui.vercel_ai.request_types import RequestData


def _resolve_extra_string(run_input: RequestData, *keys: str) -> str | None:
    for key in keys:
        value = getattr(run_input, key, None)
        if isinstance(value, str) and value:
            return value
    return None


def resolve_session_id_from_request(run_input: RequestData, *, default_session_id: str) -> str:
    session_id = _resolve_extra_string(run_input, "session_id", "sessionId")
    return session_id or default_session_id


def resolve_thread_id_from_request(run_input: RequestData) -> str | None:
    return _resolve_extra_string(run_input, "thread_id", "threadId")


def incoming_has_history(run_input: RequestData) -> bool:
    roles = {msg.role for msg in run_input.messages}
    return bool(roles.intersection({"assistant", "system"}))


def select_message_history(run_input: RequestData, stored_messages: Iterable) -> list:
    if incoming_has_history(run_input):
        return []
    return list(stored_messages)
