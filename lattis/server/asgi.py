"""ASGI application entrypoint for Lattis server."""

from lattis.server.app import create_app

app = create_app()
