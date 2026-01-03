"""ASGI application entrypoint for Lattice server."""

from lattice.server.app import create_app

app = create_app()
