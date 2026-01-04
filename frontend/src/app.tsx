import React from "react";
import { PanelLeft, Send, Square, ArrowDown, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { cn } from "@/lib/utils";
import { ChatMessage, type ChatRole } from "@/components/ChatMessage";
import { ToolCall } from "@/components/ToolCall";
import { ThreadSidebar } from "@/components/ThreadSidebar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  SERVER_URL,
  createThread,
  getThreadAgent,
  getSessionModel,
  getSessionId,
  listAgents,
  listModels,
  listThreads,
  getThreadMessages,
  runChatStream,
  setThreadAgent,
  setSessionModel,
  type AgentInfo
} from "@/lib/api";
import { type UiMessage, type UiMessagePart, type UiStreamEvent } from "@/lib/vercel";
import { appendToolArgs, parseToolResult } from "@/lib/format";
import { createId } from "@/lib/ids";

const EMPTY_MESSAGE = "";

type UiToolPart = Extract<
  UiMessagePart,
  { toolCallId: string; state: string; type: string }
>;

function isUiToolPart(part: UiMessagePart): part is UiToolPart {
  return (
    typeof (part as { toolCallId?: unknown }).toolCallId === "string" &&
    typeof (part as { state?: unknown }).state === "string"
  );
}

function stringifyToolInput(input: unknown): string {
  if (typeof input === "string") return input;
  if (input == null) return "";
  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}

function describeFilePart(part: UiMessagePart): string | null {
  if (part.type !== "file") return null;
  const filePart = part as Extract<UiMessagePart, { type: "file" }>;
  const label = filePart.filename ?? filePart.mediaType ?? "file";
  return `[${label}]`;
}

function extractToolName(part: UiToolPart): string {
  if (part.type === "dynamic-tool") {
    return (
      (part as { toolName?: unknown }).toolName?.toString() ??
      "tool"
    );
  }
  if (part.type.startsWith("tool-")) {
    return part.type.slice("tool-".length) || "tool";
  }
  return "tool";
}

type MessageItem = {
  kind: "message";
  id: string;
  role: ChatRole;
  content: string;
};

type ToolItem = {
  kind: "tool";
  id: string;
  toolName: string;
  argsRaw: string;
  result?: ReturnType<typeof parseToolResult>;
};

type RenderItem = MessageItem | ToolItem;

export default function App() {
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [threads, setThreads] = React.useState<string[]>([]);
  const [currentThread, setCurrentThread] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<RenderItem[]>([]);
  const [input, setInput] = React.useState("");
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [agent, setAgent] = React.useState<string | null>(null);
  const [agentName, setAgentName] = React.useState<string | null>(null);
  const [defaultAgent, setDefaultAgent] = React.useState<string | null>(null);
  const [agents, setAgents] = React.useState<AgentInfo[] | null>(null);
  const [isLoadingAgents, setIsLoadingAgents] = React.useState(false);
  const [model, setModel] = React.useState<string | null>(null);
  const [defaultModel, setDefaultModel] = React.useState<string | null>(null);
  const [models, setModels] = React.useState<string[] | null>(null);
  const [isLoadingModels, setIsLoadingModels] = React.useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = React.useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = React.useState(false);
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null);
  const [isThreadPanelOpen, setIsThreadPanelOpen] = React.useState(false);
  const [showScrollButton, setShowScrollButton] = React.useState(false);

  const messageMap = React.useRef(new Map<string, number>());
  const toolMap = React.useRef(new Map<string, number>());
  const runAbort = React.useRef<AbortController | null>(null);
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const modelLabel = model ?? defaultModel ?? "";
  const agentLabel = agentName ?? agent ?? defaultAgent ?? "";

  const resetMaps = React.useCallback(() => {
    messageMap.current = new Map();
    toolMap.current = new Map();
  }, []);

  const resetThreadState = React.useCallback(() => {
    setItems([]);
    resetMaps();
  }, [resetMaps]);

  const addMessageItem = React.useCallback((message: MessageItem) => {
    setItems((prev) => {
      const next = [...prev, message];
      messageMap.current.set(message.id, next.length - 1);
      return next;
    });
  }, []);

  const updateMessageContent = React.useCallback((messageId: string, delta: string) => {
    if (!delta) return;

    setItems((prev) => {
      const index = messageMap.current.get(messageId);
      if (index === undefined) {
        const fallbackMessage: MessageItem = {
          kind: "message",
          id: messageId,
          role: "assistant",
          content: delta
        };
        const next = [...prev, fallbackMessage];
        messageMap.current.set(messageId, next.length - 1);
        return next;
      }

      const next = [...prev];
      const item = next[index];
      if (item.kind !== "message") return prev;
      next[index] = {
        ...item,
        content: item.content + delta
      };
      return next;
    });
  }, []);


  const addToolItem = React.useCallback((tool: ToolItem) => {
    setItems((prev) => {
      const next = [...prev, tool];
      toolMap.current.set(tool.id, next.length - 1);
      return next;
    });
  }, []);

  const updateToolItem = React.useCallback(
    (toolId: string, updater: (item: ToolItem) => ToolItem) => {
      setItems((prev) => {
        const index = toolMap.current.get(toolId);
        if (index === undefined) return prev;
        const next = [...prev];
        const item = next[index];
        if (item.kind !== "tool") return prev;
        next[index] = updater(item);
        return next;
      });
    },
    []
  );

  const ensureToolItem = React.useCallback(
    (toolCallId: string, toolName?: string) => {
      if (toolMap.current.has(toolCallId)) {
        if (toolName) {
          updateToolItem(toolCallId, (item) => ({
            ...item,
            toolName: item.toolName === "tool" ? toolName : item.toolName
          }));
        }
        return;
      }

      addToolItem({
        kind: "tool",
        id: toolCallId,
        toolName: toolName ?? "tool",
        argsRaw: ""
      });
    },
    [addToolItem, updateToolItem]
  );

  const setToolArgs = React.useCallback(
    (toolCallId: string, input: unknown) => {
      if (!toolCallId) return;
      ensureToolItem(toolCallId);
      updateToolItem(toolCallId, (item) => ({
        ...item,
        argsRaw: stringifyToolInput(input)
      }));
    },
    [ensureToolItem, updateToolItem]
  );

  const handleStreamEvent = React.useCallback(
    (event: UiStreamEvent) => {
      switch (event.type) {
        case "text-start": {
          const messageId = typeof event.id === "string" ? event.id : "";
          if (!messageId) return;
          addMessageItem({
            kind: "message",
            id: messageId,
            role: "assistant",
            content: EMPTY_MESSAGE
          });
          return;
        }
        case "text-delta": {
          const messageId = typeof event.id === "string" ? event.id : "";
          const delta = typeof event.delta === "string" ? event.delta : "";
          if (!messageId) return;
          updateMessageContent(messageId, delta);
          return;
        }
        case "text-end":
          return;
        case "reasoning-start": {
          const messageId = typeof event.id === "string" ? event.id : "";
          if (!messageId) return;
          if (!messageMap.current.has(messageId)) {
            addMessageItem({
              kind: "message",
              id: messageId,
              role: "thinking",
              content: EMPTY_MESSAGE
            });
          }
          return;
        }
        case "reasoning-delta": {
          const messageId = typeof event.id === "string" ? event.id : "";
          const delta = typeof event.delta === "string" ? event.delta : "";
          if (!messageId) return;
          updateMessageContent(messageId, delta);
          return;
        }
        case "reasoning-end":
          return;
        case "tool-input-start": {
          const toolCallId = typeof event.toolCallId === "string" ? event.toolCallId : "";
          if (!toolCallId) return;
          const toolName =
            typeof event.toolName === "string" && event.toolName
              ? event.toolName
              : "tool";
          ensureToolItem(toolCallId, toolName);
          return;
        }
        case "tool-input-delta": {
          const toolCallId = typeof event.toolCallId === "string" ? event.toolCallId : "";
          const delta =
            typeof event.inputTextDelta === "string" ? event.inputTextDelta : "";
          if (!toolCallId) return;
          ensureToolItem(toolCallId);
          if (delta) {
            updateToolItem(toolCallId, (item) => ({
              ...item,
              argsRaw: appendToolArgs(item.argsRaw, delta)
            }));
          }
          return;
        }
        case "tool-input-available": {
          const toolCallId = typeof event.toolCallId === "string" ? event.toolCallId : "";
          if (!toolCallId) return;
          const toolName =
            typeof event.toolName === "string" && event.toolName
              ? event.toolName
              : "tool";
          ensureToolItem(toolCallId, toolName);
          setToolArgs(toolCallId, event.input);
          return;
        }
        case "tool-output-available": {
          const toolCallId = typeof event.toolCallId === "string" ? event.toolCallId : "";
          if (!toolCallId) return;
          ensureToolItem(toolCallId);
          updateToolItem(toolCallId, (item) => ({
            ...item,
            result: parseToolResult(event.output)
          }));
          return;
        }
        case "tool-output-error": {
          const toolCallId = typeof event.toolCallId === "string" ? event.toolCallId : "";
          if (!toolCallId) return;
          ensureToolItem(toolCallId);
          const errorText =
            typeof event.errorText === "string" && event.errorText
              ? event.errorText
              : "Tool error";
          updateToolItem(toolCallId, (item) => ({
            ...item,
            result: parseToolResult({ stderr: errorText, exit_code: 1 })
          }));
          return;
        }
        case "error": {
          const errorText =
            typeof event.errorText === "string" && event.errorText
              ? event.errorText
              : "Unknown error";
          addMessageItem({
            kind: "message",
            id: createId("error"),
            role: "system",
            content: `Run error: ${errorText}`
          });
          return;
        }
        default:
          return;
      }
    },
    [
      addMessageItem,
      ensureToolItem,
      setToolArgs,
      updateMessageContent,
      updateToolItem
    ]
  );

  const hydrateUiMessages = React.useCallback(
    (messages: UiMessage[]) => {
      resetThreadState();

      const collectText = (parts: UiMessagePart[]) => {
        const chunks: string[] = [];
        for (const part of parts) {
          if (part.type === "text" && typeof part.text === "string") {
            chunks.push(part.text);
            continue;
          }
          const fileLabel = describeFilePart(part);
          if (fileLabel) {
            chunks.push(fileLabel);
          }
        }
        return chunks.join("\n").trim();
      };

      for (const message of messages) {
        if (message.role === "system") {
          const content = collectText(message.parts);
          if (content) {
            addMessageItem({
              kind: "message",
              id: message.id || createId("system"),
              role: "system",
              content
            });
          }
          continue;
        }

        if (message.role === "user") {
          const content = collectText(message.parts);
          if (content) {
            addMessageItem({
              kind: "message",
              id: message.id || createId("user"),
              role: "user",
              content
            });
          }
          continue;
        }

        if (message.role !== "assistant") {
          continue;
        }

        let buffer = "";
        let usedMessageId = false;

        const flushBuffer = () => {
          if (!buffer.trim()) {
            buffer = "";
            return;
          }
          addMessageItem({
            kind: "message",
            id: !usedMessageId && message.id ? message.id : createId("assistant"),
            role: "assistant",
            content: buffer
          });
          usedMessageId = true;
          buffer = "";
        };

        for (const part of message.parts) {
          if (part.type === "text" && typeof part.text === "string") {
            buffer += part.text;
            continue;
          }

          const fileLabel = describeFilePart(part);
          if (fileLabel) {
            buffer += fileLabel;
            continue;
          }

          if (part.type === "reasoning" && typeof part.text === "string") {
            flushBuffer();
            if (part.text.trim()) {
              addMessageItem({
                kind: "message",
                id: createId("thinking"),
                role: "thinking",
                content: part.text
              });
            }
            continue;
          }

          if (isUiToolPart(part)) {
            flushBuffer();
            const toolName = extractToolName(part);
            ensureToolItem(part.toolCallId, toolName);
            if (part.input !== undefined) {
              setToolArgs(part.toolCallId, part.input);
            }
            if (part.state === "output-available") {
              updateToolItem(part.toolCallId, (item) => ({
                ...item,
                result: parseToolResult(part.output)
              }));
            }
            if (part.state === "output-error") {
              const errorText =
                typeof part.errorText === "string" && part.errorText
                  ? part.errorText
                  : "Tool error";
              updateToolItem(part.toolCallId, (item) => ({
                ...item,
                result: parseToolResult({ stderr: errorText, exit_code: 1 })
              }));
            }
          }
        }

        flushBuffer();
      }
    },
    [addMessageItem, ensureToolItem, resetThreadState, setToolArgs, updateToolItem]
  );

  const scrollToBottom = React.useCallback(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, []);

  const handleScroll = React.useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 100;
    setShowScrollButton(!isAtBottom);
  }, []);

  React.useEffect(() => {
    if (!showScrollButton) {
      scrollToBottom();
    }
  }, [items, scrollToBottom, showScrollButton]);

  const loadThreads = React.useCallback(
    async (session: string) => {
      setIsLoadingThreads(true);
      try {
        const list = await listThreads(session);
        setThreads(list);
        return list;
      } finally {
        setIsLoadingThreads(false);
      }
    },
    []
  );

  const loadThreadHistory = React.useCallback(
    async (session: string, threadId: string) => {
      setIsLoadingHistory(true);
      try {
        const messages = await getThreadMessages(session, threadId);
        hydrateUiMessages(messages);
      } catch (error) {
        addMessageItem({
          kind: "message",
          id: createId("history-error"),
          role: "system",
          content: `Failed to load history: ${
            error instanceof Error ? error.message : String(error)
          }`
        });
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [addMessageItem, hydrateUiMessages]
  );

  const loadThreadAgent = React.useCallback(async (session: string, threadId: string) => {
    const payload = await getThreadAgent(session, threadId);
    setAgent(payload.agent);
    setAgentName(payload.agentName || null);
    setDefaultAgent(payload.defaultAgent);
  }, []);

  const loadSessionModel = React.useCallback(async (session: string) => {
    const payload = await getSessionModel(session);
    setModel(payload.model);
    setDefaultModel(payload.defaultModel);
  }, []);

  const loadAgents = React.useCallback(async () => {
    if (agents && agents.length) {
      return;
    }
    setIsLoadingAgents(true);
    try {
      const payload = await listAgents();
      setAgents(payload.agents);
      setDefaultAgent((prev) => prev ?? payload.defaultAgent);
    } finally {
      setIsLoadingAgents(false);
    }
  }, [agents]);

  const loadModels = React.useCallback(async () => {
    if (models && models.length) {
      return;
    }
    setIsLoadingModels(true);
    try {
      const payload = await listModels();
      setModels(payload.models);
      setDefaultModel((prev) => prev ?? payload.defaultModel);
    } finally {
      setIsLoadingModels(false);
    }
  }, [models]);

  const handleSelectAgent = React.useCallback(
    async (nextAgent: string | null) => {
      if (!sessionId || !currentThread) return;
      try {
        const payload = await setThreadAgent(sessionId, currentThread, nextAgent);
        setAgent(payload.agent);
        setAgentName(payload.agentName || null);
        setDefaultAgent(payload.defaultAgent);
        setStatusMessage(payload.isDefault ? "Agent reset to default." : "Agent updated.");
        setTimeout(() => setStatusMessage(null), 2000);
        await loadSessionModel(sessionId);
      } catch (error) {
        setStatusMessage(
          error instanceof Error ? error.message : "Failed to update agent"
        );
      }
    },
    [currentThread, loadSessionModel, sessionId]
  );

  const handleSelectModel = React.useCallback(
    async (nextModel: string | null) => {
      if (!sessionId) return;
      try {
        const payload = await setSessionModel(sessionId, nextModel);
        setModel(payload.model);
        setDefaultModel(payload.defaultModel);
        setStatusMessage(payload.isDefault ? "Model reset to default." : "Model updated.");
        setTimeout(() => setStatusMessage(null), 2000);
      } catch (error) {
        setStatusMessage(
          error instanceof Error ? error.message : "Failed to update model"
        );
      }
    },
    [sessionId]
  );

  React.useEffect(() => {
    let active = true;

    const init = async () => {
      try {
        setStatusMessage("Connecting to server...");
        const session = await getSessionId();
        if (!active) return;
        setSessionId(session);
        await loadSessionModel(session);
        const list = await loadThreads(session);
        let threadId = list[0];
        if (!threadId) {
          threadId = await createThread(session);
          setThreads([threadId]);
        }
        if (!active) return;
        setCurrentThread(threadId);
        await loadThreadAgent(session, threadId);
        await loadThreadHistory(session, threadId);
        setStatusMessage(null);
      } catch (error) {
        if (!active) return;
        setStatusMessage(
          error instanceof Error ? error.message : "Failed to start client"
        );
      }
    };

    init();

    return () => {
      active = false;
      runAbort.current?.abort();
    };
  }, [loadSessionModel, loadThreadAgent, loadThreadHistory, loadThreads]);

  const handleSelectThread = async (threadId: string) => {
    if (!sessionId) return;
    if (threadId === currentThread) {
      setIsThreadPanelOpen(false);
      return;
    }
    runAbort.current?.abort();
    setIsThreadPanelOpen(false);
    setCurrentThread(threadId);
    await loadThreadAgent(sessionId, threadId);
    await loadThreadHistory(sessionId, threadId);
  };

  const handleCreateThread = async () => {
    if (!sessionId) return;
    try {
      const newThread = await createThread(sessionId);
      setThreads((prev) => [newThread, ...prev]);
      setCurrentThread(newThread);
      setIsThreadPanelOpen(false);
      await loadThreadAgent(sessionId, newThread);
      await loadThreadHistory(sessionId, newThread);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Failed to create thread"
      );
    }
  };

  const handleRefreshThreads = async () => {
    if (!sessionId) return;
    try {
      const list = await loadThreads(sessionId);
      if (list.length && !currentThread) {
        setCurrentThread(list[0]);
      }
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Failed to refresh threads"
      );
    }
  };

  const handleSend = async () => {
    if (!sessionId || !currentThread) return;
    if (isStreaming) {
      handleStop();
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) return;

    setInput("");
    addMessageItem({
      kind: "message",
      id: createId("user"),
      role: "user",
      content: trimmed
    });

    resetMaps();
    setIsStreaming(true);

    const controller = new AbortController();
    runAbort.current = controller;

    const payload = {
      trigger: "submit-message",
      id: createId("run"),
      messages: [
        {
          id: createId("msg"),
          role: "user",
          parts: [
            {
              type: "text",
              text: trimmed
            }
          ]
        }
      ],
      session_id: sessionId,
      thread_id: currentThread
    };

    try {
      const stream = await runChatStream(payload, controller.signal);
      for await (const event of stream) {
        handleStreamEvent(event);
      }
    } catch (error) {
      handleStop();
      if (!controller.signal.aborted) {
        addMessageItem({
          kind: "message",
          id: createId("run-error"),
          role: "system",
          content: `Run error: ${
            error instanceof Error ? error.message : String(error)
          }`
        });
      }
    } finally {
      setIsStreaming(false);
      runAbort.current = null;
    }
  };

  const handleStop = () => {
    if (runAbort.current) {
      runAbort.current.abort();
      setIsStreaming(false);
    }
  };

  const handleComposerKey = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="mobile-app-container relative bg-slate-50 md:bg-transparent">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 top-12 h-56 w-56 rounded-full bg-teal-200/40 blur-3xl" />
        <div className="absolute -right-32 top-48 h-72 w-72 rounded-full bg-orange-200/50 blur-3xl" />
      </div>

      <div className="relative mx-auto flex h-full w-full max-w-7xl flex-col md:flex-row md:gap-6 md:p-6">
        <div className="hidden md:block md:w-80">
            <ThreadSidebar
              threads={threads}
              currentThread={currentThread}
              onSelect={handleSelectThread}
              onCreate={handleCreateThread}
              onRefresh={handleRefreshThreads}
              isLoading={isLoadingThreads}
              sessionId={sessionId}
              serverUrl={SERVER_URL}
              agent={agent}
              agentName={agentName}
              defaultAgent={defaultAgent}
              agents={agents}
              isLoadingAgents={isLoadingAgents}
              onLoadAgents={loadAgents}
              onSelectAgent={handleSelectAgent}
              model={model}
              defaultModel={defaultModel}
              models={models}
              isLoadingModels={isLoadingModels}
              onLoadModels={loadModels}
              onSelectModel={handleSelectModel}
            />
          </div>

        <main className="flex min-w-0 min-h-0 flex-1 flex-col border-ink-200/70 bg-glass shadow-soft overflow-hidden md:rounded-3xl md:border">
          <header className="flex-none flex min-w-0 items-center justify-between gap-4 px-4 py-5 md:px-6">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.3em] text-ink-500">
                Active Thread
              </div>
              <div className="text-xl font-display text-ink-900 truncate max-w-[250px] md:max-w-none">
                {currentThread ?? ""}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                className="md:hidden"
                onClick={() => setIsThreadPanelOpen(true)}
              >
                <PanelLeft size={16} />
                Threads
              </Button>
              <span className="rounded-full border border-ink-200 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-ink-600">
                {isStreaming ? "Streaming" : "Idle"}
              </span>
              {agentLabel ? (
                <span
                  title={agentLabel}
                  className="max-w-[220px] truncate rounded-full border border-ink-200 bg-white/70 px-4 py-2 text-[11px] font-semibold text-ink-600"
                >
                  Agent: {agentLabel}
                </span>
              ) : null}
              {modelLabel ? (
                <span
                  title={modelLabel}
                  className="max-w-[220px] truncate rounded-full border border-ink-200 bg-white/70 px-4 py-2 text-[11px] font-semibold text-ink-600"
                >
                  Model: {modelLabel}
                </span>
              ) : null}
              {statusMessage ? (
                <span className="text-xs text-ink-500">{statusMessage}</span>
              ) : null}
            </div>
          </header>

          <Separator />

          <ScrollArea 
            className="flex-1 min-w-0 min-h-0 relative touch-pan-y" 
            viewportRef={scrollRef}
            onScroll={handleScroll}
          >
            <div className="flex w-full min-w-0 min-h-full flex-col gap-3 p-4 md:gap-4 md:p-6">
              {items.length === 0 && !isLoadingHistory ? (
                <div className="flex flex-col items-center justify-center flex-1 py-12 px-4 text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-teal-50 text-teal-600 shadow-sm border border-teal-100">
                    <Sparkles size={32} />
                  </div>
                  <h3 className="mb-2 text-xl font-display text-ink-900">
                    {agentName ? `Meet ${agentName}` : "Meet your agent"}
                  </h3>
                  <p className="max-w-xs text-sm text-ink-500 leading-relaxed">
                    Your personal agent for building toolkits and automating tasks. How can I help you today?
                  </p>
                </div>
              ) : null}

              {isLoadingHistory ? (
                <div className="rounded-3xl border border-dashed border-ink-200 bg-white/60 p-8 text-center text-sm text-ink-500">
                  Loading thread history…
                </div>
              ) : null}

              <AnimatePresence>
                {showScrollButton && (
                  <motion.button
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    onClick={scrollToBottom}
                    className="fixed bottom-32 right-8 z-50 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-lg border border-ink-200 text-ink-600 hover:bg-ink-50 md:bottom-36 md:right-12"
                  >
                    <ArrowDown size={18} />
                  </motion.button>
                )}
              </AnimatePresence>

              {items.map((item) => {
                if (item.kind === "message") {
                  const isUser = item.role === "user";
                  return (
                    <div
                      key={item.id}
                      className={`flex w-full min-w-0 ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      <ChatMessage
                        role={item.role}
                        content={item.content}
                        className="max-w-[98%] md:max-w-[85%]"
                      />
                    </div>
                  );
                }

                return (
                  <div key={item.id} className="flex w-full min-w-0 justify-start">
                    <ToolCall
                      toolName={item.toolName}
                      argsRaw={item.argsRaw}
                      result={item.result}
                      className="max-w-[98%] md:max-w-[85%]"
                    />
                  </div>
                );
              })}
            </div>
          </ScrollArea>

          <Separator />

          <div className="flex-none px-4 py-4 pb-8 md:px-6 md:pb-6">
            <div className="relative flex flex-col gap-2 rounded-[2rem] border border-ink-200/80 bg-white p-2 shadow-soft transition-all focus-within:border-teal-400/50 focus-within:shadow-glow">
              <Textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleComposerKey}
                className="min-h-[60px] resize-none border-0 bg-transparent px-4 py-3 text-base shadow-none focus-visible:ring-0 md:text-sm touch-manipulation"
                placeholder={agentName ? `Message ${agentName}...` : "Message the agent..."}
                style={{ fontSize: "16px" }}
              />
              <div className="flex items-center justify-between px-2 pb-1">
                <div className="text-[10px] font-medium text-ink-400 px-3 uppercase tracking-widest desktop-hint">
                  Shift+Enter for newline
                </div>
                <Button 
                  onClick={handleSend} 
                  disabled={!isStreaming && !input.trim()}
                  size="sm"
                  className={cn(
                    "h-10 rounded-full px-5 transition-all shadow-sm",
                    isStreaming 
                      ? "bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200" 
                      : "bg-ink-900 text-white hover:bg-ink-800"
                  )}
                >
                  {isStreaming ? (
                    <>
                      <Square size={14} className="fill-current" />
                      <span className="ml-2 font-semibold">Stop</span>
                    </>
                  ) : (
                    <>
                      <Send size={14} />
                      <span className="ml-2 font-semibold text-xs">Send</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </main>
      </div>

      {isThreadPanelOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-ink-900/40 backdrop-blur-sm"
            onClick={() => setIsThreadPanelOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 top-0">
            <ThreadSidebar
              threads={threads}
              currentThread={currentThread}
              onSelect={handleSelectThread}
              onCreate={handleCreateThread}
              onRefresh={handleRefreshThreads}
              isLoading={isLoadingThreads}
              sessionId={sessionId}
              serverUrl={SERVER_URL}
              agent={agent}
              agentName={agentName}
              defaultAgent={defaultAgent}
              agents={agents}
              isLoadingAgents={isLoadingAgents}
              onLoadAgents={loadAgents}
              onSelectAgent={handleSelectAgent}
              model={model}
              defaultModel={defaultModel}
              models={models}
              isLoadingModels={isLoadingModels}
              onLoadModels={loadModels}
              onSelectModel={handleSelectModel}
              onClose={() => setIsThreadPanelOpen(false)}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
