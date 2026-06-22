"""Codemagic API token resolution.

The token comes from the CODEMAGIC_API_TOKEN env var, set in the MCP client config
(the standard pattern, e.g. LangSmith). Empty / unexpanded ${...} / <placeholder>
values are treated as not set.
"""

import os

SETUP_INSTRUCTIONS = (
    "Set CODEMAGIC_API_TOKEN in this server's MCP config (the \"env\" block) and "
    "reload your IDE. Get the token in Codemagic → Account settings (top-right "
    "avatar) → API token → Show → Copy."
)


class AuthError(Exception):
    """No usable Codemagic API token is configured."""


def require_token() -> str:
    token = (os.environ.get("CODEMAGIC_API_TOKEN") or "").strip()
    if not token or token.startswith("${") or token.startswith("<"):
        raise AuthError(SETUP_INSTRUCTIONS)
    return token
