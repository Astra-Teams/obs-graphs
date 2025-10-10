"""Obsidian Graphs - AI-powered workflow automation for Obsidian vaults."""

from .main import app


def get_container():
    from .container import get_container as _get_container

    return _get_container()


__all__ = ["app", "get_container"]
