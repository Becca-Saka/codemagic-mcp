"""Application tools — list apps and read one app's config."""

import asyncio
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
async def list_variable_groups(
    app_id: str | None = None, team_id: str | None = None, include_variables: bool = True
) -> dict[str, Any]:
    """List environment variable groups (and their variable keys) for an app or team.

    Pass an app_id or a team_id. With include_variables (default), each group also
    lists its variable keys (never the values) so you can reference real groups and
    vars when writing a codemagic.yaml (secrets belong in groups).
    """
    if not app_id and not team_id:
        return {"error": "Provide app_id or team_id."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    scope = {"app_id": app_id} if app_id else {"team_id": team_id}

    try:
        # Team route with keys: one legacy /team call carries all groups + variables.
        if team_id and include_variables:
            groups = transform.team_variable_groups(await client.get_team(team_id))
        else:
            payload = await (
                client.list_app_variable_groups(app_id) if app_id
                else client.list_team_variable_groups(team_id)
            )
            groups = transform.variable_groups(payload)
            if include_variables:  # app route: fetch each group's keys (v3, no values)
                variable_lists = await asyncio.gather(
                    *(client.list_group_variables(g["id"]) for g in groups)
                )
                for g, vars_payload in zip(groups, variable_lists):
                    g["variables"] = transform.group_variables(vars_payload)
                    g.pop("id", None)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, **scope}
    return {"count": len(groups), "variable_groups": groups, **scope}


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
