# Lattis

Run AI agents on a server, interact from anywhere.

I built an agent I liked ([Binsmith](https://github.com/caesarnine/binsmith)) and wanted to use it from my laptop, my phone, wherever. Lattis is what emerged: a server that hosts agents with a TUI for terminals and a web UI for browsers.

I run it on a Linux box in my Tailscale network. Start a conversation on my laptop, pick it up on my phone, everything stays in sync.

## Quick start

```bash
# Run the TUI (starts a local server automatically)
uvx lattis

# Or run the server explicitly, then connect from anywhere
uvx lattis server
```

Open `http://localhost:8000` for the web UI, or run `uvx lattis` from another machine pointing at your server.

## What you get

- **Server + clients**: FastAPI backend, Textual TUI, bundled web UI
- **Persistent conversations**: threads stored in SQLite, survive restarts
- **Pluggable agents**: different agents per thread, swap anytime
- **Works anywhere**: if it can hit HTTP, it can use your agents

## The setup I use

```
┌─────────────────────────────────────────────────────────────┐
│                    Linux server (Tailscale)                 │
│                      lattis server                          │
│                           :8000                             │
└─────────────────────────────────────────────────────────────┘
        ▲                    ▲                    ▲
        │                    │                    │
   ┌────┴────┐         ┌─────┴─────┐        ┌────┴────┐
   │  laptop │         │   phone   │        │  tablet │
   │   TUI   │         │  web UI   │        │  web UI │
   └─────────┘         └───────────┘        └─────────┘
```

Threads persist on the server. I can start something on my laptop, continue on my phone, come back to it days later.

## Agents

Lattis discovers agents automatically from:

1. **Built-ins**: `assistant`, `poetry` (included with Lattis)
2. **Entry points**: any installed package that registers with `lattis.agents`
3. **Explicit specs**: `module:attr` paths via `--agents` or `AGENT_PLUGINS`

[Binsmith](https://github.com/caesarnine/binsmith) is what started all this. Now it's just another plugin:

```bash
uv pip install binsmith
uvx lattis --agent binsmith
```

### Building your own agent

The simplest case - just export a pydantic-ai Agent:

```python
# my_agent.py
from pydantic_ai import Agent

plugin = Agent("google-gla:gemini-2.0-flash", system_prompt="You are helpful.")
```

```bash
uvx lattis --agents my_agent:plugin
```

For more control (custom dependencies, lifecycle hooks), use the plugin API:

```python
from pydantic_ai import Agent
from lattis.plugins import AgentPlugin, AgentRunContext

def create_agent(model: str) -> Agent:
    return Agent(model, system_prompt="...")

def create_deps(ctx: AgentRunContext):
    # Access ctx.workspace, ctx.project_root, ctx.session_id, etc.
    return MyDeps(...)

plugin = AgentPlugin(
    id="my-agent",
    name="My Agent",
    create_agent=create_agent,
    create_deps=create_deps,
)
```

Register via entry point in `pyproject.toml`:

```toml
[project.entry-points."lattis.agents"]
my-agent = "my_package:plugin"
```

## CLI

```bash
lattis                 # TUI (default)
lattis tui             # TUI explicitly
lattis server          # API server + web UI
```

### TUI options

```
--server <url>     Connect to a remote server
--local            Skip server discovery, run in-process
--agent <id>       Default agent (local mode)
--agents <specs>   Extra plugins to load (local mode)
```

The TUI auto-discovers a server on `localhost:8000` if one is running for the same project. Use `--server` to point at a remote machine.

### Server options

```
--host <host>      Interface to bind (default: 127.0.0.1)
--port <port>      Port (default: 8000)
--reload           Auto-reload on code changes
--agent <id>       Default agent
--agents <specs>   Extra plugins to load
```

## TUI commands

```
/help                     Show help
/threads                  List threads
/thread <id>              Switch to thread (creates if needed)
/thread new [id]          Create new thread
/thread delete <id>       Delete thread
/clear                    Clear current thread
/agent                    Show current agent
/agent list [filter]      List available agents
/agent set <id>           Switch agent for this thread
/model                    Show current model
/model list [filter]      List available models
/model set <name>         Switch model
/quit                     Exit
```

## Storage

```
.lattis/
  lattis.db          # SQLite - threads, messages, state
  session_id         # Persistent session identifier
  workspace/         # Shared directory for agents that need it
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_DEFAULT` | `assistant` | Default agent |
| `AGENT_PLUGINS` | | Extra plugins (comma-separated `module:attr`) |
| `LATTIS_SERVER_URL` | | Server URL for remote connections |
| `LATTIS_PROJECT_ROOT` | cwd | Project root for storage |
| `LATTIS_DATA_DIR` | `.lattis` | Data directory |
| `LATTIS_WORKSPACE_DIR` | | Override workspace location |

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended)
- An API key for at least one model provider (Gemini, Anthropic, OpenAI)

```bash
export GEMINI_API_KEY=...     # Google
export ANTHROPIC_API_KEY=...  # Anthropic
export OPENAI_API_KEY=...     # OpenAI
```

## Web UI development

The web UI is bundled from `frontend/`. To rebuild:

```bash
cd frontend
npm install
npm run build
```

Static files are served from `lattis/web/static` when present.
