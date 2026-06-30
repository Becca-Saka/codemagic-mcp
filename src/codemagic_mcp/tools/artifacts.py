"""Artifact tools — mint shareable download links for build outputs."""

import time
from typing import Any

from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


@mcp.tool
async def create_public_artifact_url(
    artifact_url: str, expires_in_hours: int = 24
) -> dict[str, Any]:
    """Create a public, token-free download link for a build artifact.

    A build's artifacts (from get_build_info) carry a `url` that only downloads with
    the API token. This mints a shareable link that anyone can open until it expires.

    Args:
        artifact_url: The artifact's `url` from get_build_info.
        expires_in_hours: How long the link stays valid (default 24).
    """
    if expires_in_hours <= 0:
        return {"error": "expires_in_hours must be positive."}
    if "//artifacts/" in artifact_url or "/artifacts/." in artifact_url:
        return {"error": "That looks like a short-lived v3 download link, not a "
                "shareable artifact endpoint. Use the artifact `url` from "
                "get_build_info (not short_lived_download_url from list_team_builds)."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)

    expires_at = int(time.time()) + expires_in_hours * 3600
    try:
        result = await client.create_public_artifact_url(artifact_url, expires_at)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "artifact_url": artifact_url}
    out = result if isinstance(result, dict) else {}
    return {"public_url": out.get("url"), "expires_at": out.get("expiresAt")}
