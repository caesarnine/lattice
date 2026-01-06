from __future__ import annotations

from typing import Sequence

from pydantic_ai.messages import ModelMessage

from lattis.domain.sessions import SessionStore


class ThreadAlreadyExistsError(ValueError):
    pass


class ThreadNotFoundError(LookupError):
    pass


def thread_exists(store: SessionStore, *, session_id: str, thread_id: str) -> bool:
    return store.thread_exists(session_id, thread_id)


def require_thread(store: SessionStore, *, session_id: str, thread_id: str) -> None:
    if not thread_exists(store, session_id=session_id, thread_id=thread_id):
        raise ThreadNotFoundError(f"Thread '{thread_id}' not found.")


def list_threads(store: SessionStore, session_id: str) -> list[str]:
    return store.list_threads(session_id)


def create_thread(
    store: SessionStore,
    *,
    session_id: str,
    thread_id: str,
) -> None:
    if thread_exists(store, session_id=session_id, thread_id=thread_id):
        raise ThreadAlreadyExistsError("Thread already exists.")
    store.save_thread(session_id, thread_id, messages=[])


def delete_thread(store: SessionStore, *, session_id: str, thread_id: str) -> None:
    require_thread(store, session_id=session_id, thread_id=thread_id)
    store.delete_thread(session_id, thread_id)


def clear_thread(store: SessionStore, *, session_id: str, thread_id: str) -> None:
    require_thread(store, session_id=session_id, thread_id=thread_id)
    store.save_thread(session_id, thread_id, messages=[])


def load_thread_messages(
    store: SessionStore,
    *,
    session_id: str,
    thread_id: str,
) -> Sequence[ModelMessage]:
    thread_state = store.load_thread(session_id, thread_id)
    if thread_state is None:
        raise ThreadNotFoundError(f"Thread '{thread_id}' not found.")
    return thread_state.messages
