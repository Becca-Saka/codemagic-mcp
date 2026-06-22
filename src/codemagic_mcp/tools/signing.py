"""Signing tools — a team's uploaded code-signing identities (redacted)."""

from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


@mcp.tool
async def get_team_signing(team_id: str) -> dict[str, Any]:
    """List a team's uploaded code-signing identities (certs, profiles, keystores).

    Use this when diagnosing a signing failure or setting up signing in a
    codemagic.yaml — to check which profiles/certificates exist, whether they're
    valid, and whether a profile's bundle_id matches the app. Secret values
    (passwords, serials, profile UUIDs, key ids) are never returned.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_team(team_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "team_id": team_id}
    return {"team_id": team_id, "signing": transform.signing_summary(payload)}
