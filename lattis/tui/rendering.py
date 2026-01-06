from __future__ import annotations

import json
from typing import Any, Callable
from uuid import uuid4

from pydantic_ai.ui.vercel_ai.request_types import (
    DynamicToolInputAvailablePart,
    DynamicToolOutputAvailablePart,
    DynamicToolOutputErrorPart,
    FileUIPart,
    ReasoningUIPart,
    TextUIPart,
    ToolInputAvailablePart,
    ToolOutputAvailablePart,
    ToolOutputErrorPart,
    UIMessage,
)
from textual.containers import VerticalScroll

from lattis.tui.widgets import ChatMessage, ToolCall


class ChatRenderer:
    def __init__(
        self,
        *,
        get_chat: Callable[[], VerticalScroll],
        scroll_to_bottom: Callable[[], None],
    ) -> None:
        self._get_chat = get_chat
        self._scroll_to_bottom = scroll_to_bottom
        self._current_assistant: ChatMessage | None = None
        self._current_thinking: ChatMessage | None = None
        self._tool_calls: dict[str, ToolCall] = {}
        self._message_map: dict[str, ChatMessage] = {}
        self._event_handlers = {
            "text-start": self._on_text_start_event,
            "text-delta": self._on_text_delta_event,
            "reasoning-start": self._on_reasoning_start_event,
            "reasoning-delta": self._on_reasoning_delta_event,
            "tool-input-start": self._on_tool_input_start_event,
            "tool-input-delta": self._on_tool_input_delta_event,
            "tool-input-available": self._on_tool_input_available_event,
            "tool-output-available": self._on_tool_output_available_event,
            "tool-output-error": self._on_tool_output_error_event,
            "error": self._on_error_event,
        }

    def reset(self) -> None:
        self._current_assistant = None
        self._current_thinking = None
        self._tool_calls = {}
        self._message_map = {}

    def handle_stream_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if not isinstance(event_type, str):
            return
        handler = self._event_handlers.get(event_type)
        if handler:
            handler(event)

    def add_user_message(self, content: str) -> None:
        chat = self._get_chat()
        chat.mount(ChatMessage(role="user", content=content))
        self._scroll_to_bottom()

    def add_assistant_message(self, content: str) -> None:
        chat = self._get_chat()
        msg = ChatMessage(role="assistant", content=content)
        chat.mount(msg)
        self._current_assistant = msg
        self._scroll_to_bottom()

    def add_thinking_message(self, content: str) -> None:
        chat = self._get_chat()
        msg = ChatMessage(role="thinking", content=content)
        chat.mount(msg)
        self._current_thinking = msg
        self._scroll_to_bottom()

    def add_system_message(self, content: str) -> None:
        chat = self._get_chat()
        chat.mount(ChatMessage(role="system", content=content))
        self._scroll_to_bottom()

    def handle_text_start(self, message_id: str, *, role: str = "assistant") -> None:
        msg = ChatMessage(role=role)
        if role == "assistant":
            self._current_assistant = msg
        chat = self._get_chat()
        chat.mount(msg)
        self._message_map[message_id] = msg
        self._scroll_to_bottom()

    def handle_text_delta(self, message_id: str, delta: str) -> None:
        msg = self._message_map.get(message_id)
        if msg is None:
            msg = ChatMessage(role="assistant")
            chat = self._get_chat()
            chat.mount(msg)
            self._message_map[message_id] = msg
            self._current_assistant = msg
            self._scroll_to_bottom()
        msg.append_content(delta)

    def _on_text_start_event(self, event: dict[str, Any]) -> None:
        message_id = str(event.get("id") or uuid4().hex)
        self.handle_text_start(message_id)

    def _on_text_delta_event(self, event: dict[str, Any]) -> None:
        message_id = str(event.get("id") or "")
        delta = str(event.get("delta") or "")
        if message_id:
            self.handle_text_delta(message_id, delta)

    def _on_reasoning_start_event(self, event: dict[str, Any]) -> None:
        message_id = str(event.get("id") or uuid4().hex)
        self.handle_thinking_start(message_id)

    def _on_reasoning_delta_event(self, event: dict[str, Any]) -> None:
        message_id = str(event.get("id") or "")
        delta = str(event.get("delta") or "")
        if message_id:
            self.handle_thinking_delta(message_id, delta)

    def _on_tool_input_start_event(self, event: dict[str, Any]) -> None:
        self._handle_tool_input_event(event, include_args=False)

    def _on_tool_input_delta_event(self, event: dict[str, Any]) -> None:
        tool_call_id = str(event.get("toolCallId") or "")
        delta = str(event.get("inputTextDelta") or "")
        if tool_call_id and delta:
            self.append_tool_args(tool_call_id, delta)

    def _on_tool_input_available_event(self, event: dict[str, Any]) -> None:
        self._handle_tool_input_event(event, include_args=True)

    def _handle_tool_input_event(self, event: dict[str, Any], *, include_args: bool) -> None:
        tool_call_id = str(event.get("toolCallId") or "")
        if not tool_call_id:
            return
        tool_name = str(event.get("toolName") or "tool")
        args = event.get("input") if include_args else ""
        self.add_tool_call(tool_name, args, tool_call_id)

    def _on_tool_output_available_event(self, event: dict[str, Any]) -> None:
        tool_call_id = str(event.get("toolCallId") or "")
        if tool_call_id:
            self.set_tool_result(tool_call_id, event.get("output"))

    def _on_tool_output_error_event(self, event: dict[str, Any]) -> None:
        tool_call_id = str(event.get("toolCallId") or "")
        error_text = str(event.get("errorText") or "Tool error")
        if tool_call_id:
            self.set_tool_result(tool_call_id, {"stderr": error_text, "exit_code": 1})

    def _on_error_event(self, event: dict[str, Any]) -> None:
        error_text = str(event.get("errorText") or "Unknown error")
        self.add_system_message(f"Run error: {error_text}")

    def handle_thinking_start(self, message_id: str) -> None:
        msg = ChatMessage(role="thinking")
        chat = self._get_chat()
        chat.mount(msg)
        self._message_map[message_id] = msg
        self._current_thinking = msg
        self._scroll_to_bottom()

    def handle_thinking_delta(self, message_id: str, delta: str) -> None:
        msg = self._message_map.get(message_id)
        if msg is None:
            msg = ChatMessage(role="thinking")
            chat = self._get_chat()
            chat.mount(msg)
            self._message_map[message_id] = msg
            self._current_thinking = msg
            self._scroll_to_bottom()
        msg.append_content(delta)

    def add_tool_call(self, tool_name: str, args: Any, tool_call_id: str) -> None:
        tool_widget = self._tool_calls.get(tool_call_id)
        if tool_widget is None:
            tool_widget = ToolCall(tool_name, args, tool_call_id)
            self._tool_calls[tool_call_id] = tool_widget
            chat = self._get_chat()
            chat.mount(tool_widget)
            self._scroll_to_bottom()
            return

        tool_widget.update_tool_name(tool_name)
        if args:
            payload = args if isinstance(args, str) else json.dumps(args)
            tool_widget.append_args(payload)

    def append_tool_args(self, tool_call_id: str, delta: str) -> None:
        tool_widget = self._tool_calls.get(tool_call_id)
        if tool_widget is None:
            tool_widget = ToolCall("tool", "", tool_call_id)
            self._tool_calls[tool_call_id] = tool_widget
            chat = self._get_chat()
            chat.mount(tool_widget)
        tool_widget.append_args(delta)

    def set_tool_result(self, tool_call_id: str, result: Any) -> None:
        if tool_call_id not in self._tool_calls:
            return

        tool_widget = self._tool_calls[tool_call_id]

        data = result
        if hasattr(data, "content"):
            data = data.content
        if hasattr(data, "data"):
            data = data.data

        output = ""
        exit_code = 0
        timed_out = False
        stdout = ""
        stderr = ""

        if hasattr(data, "stdout"):
            stdout = data.stdout or ""
            stderr = data.stderr or ""
            exit_code = data.exit_code
            timed_out = bool(getattr(data, "timed_out", False))
        elif isinstance(data, dict):
            stdout = data.get("stdout", "") or ""
            stderr = data.get("stderr", "") or ""
            exit_code = data.get("exit_code", 0)
            timed_out = bool(data.get("timed_out", False))
        else:
            output = str(data)

        if stdout or stderr:
            if stdout and stderr:
                output = f"{stdout}\n{stderr}"
            else:
                output = stdout or stderr

        output = self._truncate_output(output)
        tool_widget.set_result(output, exit_code, timed_out=timed_out)

    def hydrate_ui_messages(self, messages: list[UIMessage]) -> None:
        for message in messages:
            if message.role == "system":
                content = self._collect_ui_text(message.parts)
                if content:
                    self.add_system_message(content)
                continue
            if message.role == "user":
                content = self._collect_ui_text(message.parts)
                if content:
                    self.add_user_message(content)
                continue
            if message.role == "assistant":
                self._render_assistant_parts(message.parts)

    def _collect_ui_text(self, parts: list[Any]) -> str:
        chunks: list[str] = []
        for part in parts:
            if isinstance(part, TextUIPart):
                if part.text:
                    chunks.append(part.text)
            elif isinstance(part, FileUIPart):
                label = part.filename or part.media_type or "file"
                chunks.append(f"[{label}]")
        return "\n".join(chunks).strip()

    def _render_assistant_parts(self, parts: list[Any]) -> None:
        buffer: list[str] = []

        def flush_buffer() -> None:
            if not buffer:
                return
            content = "".join(buffer).strip()
            buffer.clear()
            if content:
                self.add_assistant_message(content)

        for part in parts:
            if isinstance(part, TextUIPart):
                buffer.append(part.text)
                continue
            if isinstance(part, ReasoningUIPart):
                flush_buffer()
                if part.text:
                    self.add_thinking_message(part.text)
                continue
            if isinstance(part, FileUIPart):
                label = part.filename or part.media_type or "file"
                buffer.append(f"[{label}]")
                continue
            if isinstance(part, ToolInputAvailablePart):
                flush_buffer()
                tool_name = part.type.removeprefix("tool-")
                self.add_tool_call(tool_name, part.input or "", part.tool_call_id)
                continue
            if isinstance(part, ToolOutputAvailablePart):
                flush_buffer()
                tool_name = part.type.removeprefix("tool-")
                self.add_tool_call(tool_name, part.input or "", part.tool_call_id)
                if part.output is not None:
                    self.set_tool_result(part.tool_call_id, part.output)
                continue
            if isinstance(part, ToolOutputErrorPart):
                flush_buffer()
                tool_name = part.type.removeprefix("tool-")
                self.add_tool_call(tool_name, part.input or "", part.tool_call_id)
                self.set_tool_result(part.tool_call_id, {"stderr": part.error_text, "exit_code": 1})
                continue
            if isinstance(part, DynamicToolInputAvailablePart):
                flush_buffer()
                self.add_tool_call(part.tool_name, part.input or "", part.tool_call_id)
                continue
            if isinstance(part, DynamicToolOutputAvailablePart):
                flush_buffer()
                self.add_tool_call(part.tool_name, part.input or "", part.tool_call_id)
                if part.output is not None:
                    self.set_tool_result(part.tool_call_id, part.output)
                continue
            if isinstance(part, DynamicToolOutputErrorPart):
                flush_buffer()
                self.add_tool_call(part.tool_name, part.input or "", part.tool_call_id)
                self.set_tool_result(part.tool_call_id, {"stderr": part.error_text, "exit_code": 1})
                continue

        flush_buffer()

    def _truncate_output(self, output: str, limit: int = 4000) -> str:
        if len(output) <= limit:
            return output
        return output[:limit] + f"\n... (truncated, {len(output) - limit} chars)"
