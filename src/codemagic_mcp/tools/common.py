"""Shared helpers for tool modules."""

from typing import Any

from codemagic_mcp.auth import AuthError


def no_token(e: AuthError) -> dict[str, Any]:
    """Standard tool response when no API token is configured."""
    return {"error": "No token configured.", "setup": str(e)}
