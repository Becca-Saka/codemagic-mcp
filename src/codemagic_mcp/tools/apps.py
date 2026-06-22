"""Application tools — list apps and read one app's config."""

from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


@mcp.tool
async def list_applications() -> dict[str, Any]:
    """List the Codemagic apps the token can access.

    Returns each app's id, name, project type, config source (file vs ui/Workflow
    Editor), repo, and team. Use get_application for one app's full config.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.list_applications()
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code}
    apps = transform.apps_list(payload)
    return {"count": len(apps), "applications": apps}


@mcp.tool
async def get_application(app_id: str) -> dict[str, Any]:
    """Get one app's full config: workflows, scripts, build settings, signing, publishing.

    Use this to ground a codemagic.yaml or to migrate a Workflow Editor (ui) app to
    yaml — it returns each workflow's scripts, build settings, code-signing setup, and
    publisher targets. Secret values (env var values, signing passwords/keystores,
    publisher credentials) are redacted; env vars are returned as names/groups only.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_application(app_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "app_id": app_id}
    return {"app": transform.app_detail(payload)}
