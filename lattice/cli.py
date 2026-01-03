from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import uvicorn

from lattice.client import AgentClient
from lattice.client.inprocess import create_inprocess_client
from lattice.tui.app import run_tui

DEFAULT_SERVER_URL = os.getenv("LATTICE_SERVER_URL")
DEFAULT_AUTO_DISCOVER_PORT = 8000


@dataclass
class ConnectionInfo:
    """Information about the TUI's connection mode."""

    mode: str  # "server" or "local"
    server_url: str | None = None

    @property
    def status_message(self) -> str:
        if self.mode == "server" and self.server_url:
            return f"Connecting to {self.server_url}..."
        return "Starting in local mode..."

    @property
    def header_label(self) -> str:
        if self.mode == "server" and self.server_url:
            # Extract host:port for display
            parsed = urlparse(self.server_url)
            return f":{parsed.port}" if parsed.port else parsed.netloc
        return "local"


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if not argv:
        argv = ["tui"]
    elif argv[0].startswith("-") and argv[0] not in {"-h", "--help"}:
        argv = ["tui", *argv]
    args = parser.parse_args(argv)

    command = args.command or "tui"
    if command == "tui":
        _run_tui_command(args)
        return
    if command == "server":
        _run_server_command(args)
        return

    parser.print_help()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lattice", description="Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    tui_parser = subparsers.add_parser("tui", help="Run the TUI client")
    _add_tui_args(tui_parser)

    server_parser = subparsers.add_parser("server", help="Run the API server")
    _add_server_args(server_parser)

    return parser


def _add_tui_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER_URL,
        help="Connect to a specific server URL",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Force local mode (skip server auto-discovery)",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Default agent id or name for this session (local/in-process mode only)",
    )
    parser.add_argument(
        "--agents",
        default=None,
        help="Comma-separated agent plugin specs to load (local/in-process mode only)",
    )


def _add_server_args(parser: argparse.ArgumentParser) -> None:
    env_workspace = (os.getenv("LATTICE_WORKSPACE_MODE") or "").strip().lower()
    default_workspace = "central" if env_workspace == "central" else "local"
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload",
    )
    parser.add_argument(
        "--workspace",
        choices=("local", "central"),
        default=default_workspace,
        help="Workspace mode (default: %(default)s)",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Default agent id or name",
    )
    parser.add_argument(
        "--agents",
        default=None,
        help="Comma-separated agent plugin specs to load",
    )


def _run_tui_command(args: argparse.Namespace) -> None:
    project_root = Path.cwd()

    client, connection_info = _create_tui_client(args, project_root=project_root)
    print(connection_info.status_message)
    run_tui(client=client, connection_info=connection_info)


def _run_server_command(args: argparse.Namespace) -> None:
    project_root = Path.cwd()
    os.environ.setdefault("LATTICE_PROJECT_ROOT", str(project_root))
    os.environ.setdefault("LATTICE_WORKSPACE_MODE", args.workspace)
    if args.agent:
        os.environ["AGENT_DEFAULT"] = str(args.agent)
    if args.agents:
        os.environ["AGENT_PLUGINS"] = str(args.agents)

    uvicorn.run("lattice.server.asgi:app", host=args.host, port=args.port, reload=args.reload)


def _normalize_server_url(url: str) -> str:
    if "://" not in url:
        url = f"http://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        raise SystemExit(f"Invalid server URL: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _server_healthy(server_url: str) -> bool:
    try:
        response = httpx.get(f"{server_url}/health", timeout=1.0)
    except httpx.RequestError:
        return False
    return response.status_code == 200


def _is_same_project(server_url: str, project_root: Path) -> bool:
    """Check if the server is running for the same project."""
    try:
        info = httpx.get(f"{server_url}/info", timeout=2.0).json()
    except Exception:
        return False

    server_root = info.get("project_root")
    if not isinstance(server_root, str) or not server_root:
        return False

    try:
        expected = project_root.resolve()
        actual = Path(server_root).resolve()
    except OSError:
        return False

    return actual == expected


def _create_tui_client(
    args: argparse.Namespace, *, project_root: Path
) -> tuple[AgentClient, ConnectionInfo]:
    agent_spec = getattr(args, "agent", None)
    agents = getattr(args, "agents", None)
    agent_specs = [item.strip() for item in agents.split(",")] if isinstance(agents, str) and agents else None

    # --local flag: skip all discovery, use in-process
    if getattr(args, "local", False):
        client, _ = create_inprocess_client(
            project_root=project_root,
            workspace_mode="local",
            agent_specs=agent_specs,
            default_agent=agent_spec,
        )
        return client, ConnectionInfo(mode="local")

    # --server URL: explicit connection (no project validation)
    server = getattr(args, "server", None)
    if server:
        server_url = _normalize_server_url(server)
        if not _server_healthy(server_url):
            print(
                f"Server not reachable at {server_url}. Start it with `lattice server`.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return AgentClient(server_url), ConnectionInfo(mode="server", server_url=server_url)

    # Auto-discovery: check default port, validate project
    auto_url = f"http://127.0.0.1:{DEFAULT_AUTO_DISCOVER_PORT}"
    if _server_healthy(auto_url):
        if _is_same_project(auto_url, project_root):
            return AgentClient(auto_url), ConnectionInfo(mode="server", server_url=auto_url)
        # Different project - silently fall back to local

    # Fallback: in-process
    client, _ = create_inprocess_client(
        project_root=project_root,
        workspace_mode="local",
        agent_specs=agent_specs,
        default_agent=agent_spec,
    )
    return client, ConnectionInfo(mode="local")
