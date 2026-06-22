"""Account / connection tools."""

from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import SETUP_INSTRUCTIONS, AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


@mcp.tool
async def verify_connection() -> dict[str, Any]:
    """Verify the Codemagic token (GET /user) and list the teams it can access."""
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return {"connected": False, **no_token(e)}
    try:
        payload = await client.get_user()
    except CmApiError as e:
        if e.status_code in (401, 403):
            return {"connected": False, "error": "Token rejected by Codemagic.",
                    "setup": SETUP_INSTRUCTIONS}
        return {"connected": False, "status_code": e.status_code, "error": e.message}
    return {
        "connected": True,
        "user": transform.user_profile(payload),
        "teams": transform.team_list(payload),
    }
