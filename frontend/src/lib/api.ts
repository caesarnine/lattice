import { AgUiEvent, streamAgUiEvents } from "@/lib/agui";
import type { components } from "@/lib/openapi";

const FALLBACK_HOST =
  typeof window !== "undefined" ? window.location.hostname : "localhost";
const DEFAULT_SERVER_URL = `http://${FALLBACK_HOST}:8000`;

export const SERVER_URL =
  (import.meta.env.VITE_LATTICE_SERVER_URL as string | undefined) ||
  DEFAULT_SERVER_URL;

function resolveSessionId(data: Record<string, unknown>): string {
  const sessionId = data.session_id ?? data.sessionId;
  if (typeof sessionId !== "string" || !sessionId) {
    throw new Error("Server did not return a session id.");
  }
  return sessionId;
}

async function ensureOk(response: Response, fallbackMessage: string) {
  if (response.ok) {
    return;
  }
  let detail = "";
  try {
    const data = await response.json();
    detail = data?.detail ? ` ${data.detail}` : "";
  } catch {
    // ignore JSON errors
  }
  throw new Error(`${fallbackMessage}.${detail}`);
}

export async function getSessionId(): Promise<string> {
  const response = await fetch(`${SERVER_URL}/session`);
  await ensureOk(response, "Failed to load session");
  const data = (await response.json()) as Record<string, unknown>;
  return resolveSessionId(data);
}

export async function listModels(): Promise<{ defaultModel: string; models: string[] }> {
  const response = await fetch(`${SERVER_URL}/models`);
  await ensureOk(response, "Failed to load models");
  const data = (await response.json()) as components["schemas"]["ModelListResponse"];
  return {
    defaultModel: data.default_model ?? "",
    models: data.models ?? []
  };
}

export type AgentInfo = components["schemas"]["AgentInfo"];

export async function listAgents(): Promise<{ defaultAgent: string; agents: AgentInfo[] }> {
  const response = await fetch(`${SERVER_URL}/agents`);
  await ensureOk(response, "Failed to load agents");
  const data = (await response.json()) as components["schemas"]["AgentListResponse"];
  const agents = data.agents ?? [];
  return {
    defaultAgent: data.default_agent ?? "",
    agents: agents.filter((item) => Boolean(item.id))
  };
}

export async function getThreadAgent(
  sessionId: string,
  threadId: string
): Promise<{ agent: string; defaultAgent: string; isDefault: boolean; agentName: string }> {
  const response = await fetch(
    `${SERVER_URL}/sessions/${sessionId}/threads/${threadId}/agent`
  );
  await ensureOk(response, "Failed to load agent");
  const data = (await response.json()) as components["schemas"]["ThreadAgentResponse"];
  return {
    agent: data.agent ?? "",
    defaultAgent: data.default_agent ?? "",
    isDefault: Boolean(data.is_default),
    agentName: data.agent_name ?? ""
  };
}

export async function setThreadAgent(
  sessionId: string,
  threadId: string,
  agent: string | null
): Promise<{ agent: string; defaultAgent: string; isDefault: boolean; agentName: string }> {
  const response = await fetch(
    `${SERVER_URL}/sessions/${sessionId}/threads/${threadId}/agent`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(agent ? { agent } : {})
    }
  );
  await ensureOk(response, "Failed to set agent");
  const data = (await response.json()) as components["schemas"]["ThreadAgentResponse"];
  return {
    agent: data.agent ?? "",
    defaultAgent: data.default_agent ?? "",
    isDefault: Boolean(data.is_default),
    agentName: data.agent_name ?? ""
  };
}

export async function getSessionModel(
  sessionId: string
): Promise<{ model: string; defaultModel: string; isDefault: boolean }> {
  const response = await fetch(`${SERVER_URL}/sessions/${sessionId}/model`);
  await ensureOk(response, "Failed to load model");
  const data = (await response.json()) as components["schemas"]["SessionModelResponse"];
  return {
    model: data.model ?? "",
    defaultModel: data.default_model ?? "",
    isDefault: Boolean(data.is_default)
  };
}

export async function setSessionModel(
  sessionId: string,
  model: string | null
): Promise<{ model: string; defaultModel: string; isDefault: boolean }> {
  const response = await fetch(`${SERVER_URL}/sessions/${sessionId}/model`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(model ? { model } : {})
  });
  await ensureOk(response, "Failed to set model");
  const data = (await response.json()) as components["schemas"]["SessionModelResponse"];
  return {
    model: data.model ?? "",
    defaultModel: data.default_model ?? "",
    isDefault: Boolean(data.is_default)
  };
}

export async function listThreads(sessionId: string): Promise<string[]> {
  const response = await fetch(`${SERVER_URL}/sessions/${sessionId}/threads`);
  await ensureOk(response, "Failed to load threads");
  const data = (await response.json()) as components["schemas"]["ThreadListResponse"];
  return data.threads ?? [];
}

export async function createThread(sessionId: string, threadId?: string): Promise<string> {
  const response = await fetch(`${SERVER_URL}/sessions/${sessionId}/threads`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(threadId ? { thread_id: threadId } : {})
  });
  await ensureOk(response, "Failed to create thread");
  const data = (await response.json()) as components["schemas"]["ThreadCreateResponse"];
  if (!data.thread_id) {
    throw new Error("Server did not return a thread id.");
  }
  return data.thread_id;
}

export async function deleteThread(sessionId: string, threadId: string): Promise<string> {
  const response = await fetch(
    `${SERVER_URL}/sessions/${sessionId}/threads/${threadId}`,
    { method: "DELETE" }
  );
  await ensureOk(response, "Failed to delete thread");
  const data = (await response.json()) as components["schemas"]["ThreadDeleteResponse"];
  return data.deleted ?? threadId;
}

export async function clearThread(sessionId: string, threadId: string): Promise<string> {
  const response = await fetch(
    `${SERVER_URL}/sessions/${sessionId}/threads/${threadId}/clear`,
    { method: "POST" }
  );
  await ensureOk(response, "Failed to clear thread");
  const data = (await response.json()) as components["schemas"]["ThreadClearResponse"];
  return data.cleared ?? threadId;
}

export async function streamThreadEvents(
  sessionId: string,
  threadId: string,
  signal?: AbortSignal
): Promise<AsyncGenerator<AgUiEvent>> {
  const response = await fetch(
    `${SERVER_URL}/sessions/${sessionId}/threads/${threadId}/events`,
    {
      headers: { accept: "text/event-stream" },
      signal
    }
  );
  await ensureOk(response, "Failed to load thread events");
  return streamAgUiEvents(response, signal);
}

export async function runAgentStream(
  payload: Record<string, unknown>,
  signal?: AbortSignal
): Promise<AsyncGenerator<AgUiEvent>> {
  const response = await fetch(`${SERVER_URL}/ag-ui`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      accept: "text/event-stream"
    },
    body: JSON.stringify(payload),
    signal
  });
  await ensureOk(response, "Failed to run agent");
  return streamAgUiEvents(response, signal);
}
