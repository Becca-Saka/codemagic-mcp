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
async def add_application(
    repository_url: str,
    team_id: str | None = None,
    project_type: str | None = None,
    ssh_key_base64: str | None = None,
    ssh_key_passphrase: str | None = None,
) -> dict[str, Any]:
    """Add a new application to Codemagic from a git repository.

    This creates a real app in the user's account — confirm the repository URL (and
    team) with the user before calling. The repository's git provider must already be
    connected to the account; for a private repo not reachable that way, pass an SSH
    key instead (ssh_key_base64 + optional ssh_key_passphrase).

    Args:
        repository_url: SSH or HTTPS clone URL of the repository.
        team_id: Team to add the app to. Omit to add it to the personal account.
        project_type: Optional hint, e.g. "flutter-app".
        ssh_key_base64: Base64-encoded private key, only for a private repo added by key.
        ssh_key_passphrase: Passphrase for that key, if any.

    The SSH key and passphrase are sent to Codemagic and never returned in the output.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)

    body: dict[str, Any] = {"repositoryUrl": repository_url}
    if team_id:
        body["teamId"] = team_id
    if project_type:
        body["projectType"] = project_type

    try:
        if ssh_key_base64:
            body["sshKey"] = {"data": ssh_key_base64, "passphrase": ssh_key_passphrase}
            payload = await client.add_application_private(body)
        else:
            payload = await client.add_application(body)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "repository_url": repository_url}

    app = payload.get("application", payload) if isinstance(payload, dict) else payload
    return {"added": True, "app": transform.app_summary(app)}


@mcp.tool
async def delete_application(app_id: str) -> dict[str, Any]:
    """Permanently delete an application from Codemagic.

    This is destructive and irreversible — it removes the app, its build history, and
    its configuration. Confirm the exact app (name + id, via get_application or
    list_applications) with the user before calling.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.delete_application(app_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "app_id": app_id}
    return {"deleted": True, "app_id": app_id}


@mcp.tool
async def create_variable_group(
    name: str,
    app_id: str | None = None,
    team_id: str | None = None,
    selected_apps: list[str] | None = None,
) -> dict[str, Any]:
    """Create an environment variable group on an app or a team.

    In Codemagic every environment variable lives in a group; create the group first,
    then add variables with add_environment_variables. This creates a real group —
    confirm the name and scope with the user. Pass app_id or team_id.

    Args:
        name: The group name (referenced from a codemagic.yaml `environment.groups`).
        app_id: Create the group on this app. Provide app_id or team_id.
        team_id: Create the group on this team (shared across the team's apps).
        selected_apps: Team groups only — restrict which app ids may read the group
                       (enables advanced security). Omit to allow all team apps.
    """
    if not app_id and not team_id:
        return {"error": "Provide app_id or team_id."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await (
            client.create_app_variable_group(app_id, name) if app_id
            else client.create_team_variable_group(team_id, name, selected_apps=selected_apps)
        )
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "name": name}
    group = payload.get("data", payload) if isinstance(payload, dict) else {}
    scope = {"app_id": app_id} if app_id else {"team_id": team_id}
    return {"created": True, "group_id": group.get("id"), "name": group.get("name", name), **scope}


@mcp.tool
async def add_environment_variables(
    group_id: str, variables: dict[str, str], secure: bool = True
) -> dict[str, Any]:
    """Add environment variables to an existing variable group.

    Get group_id from list_variable_groups or create_variable_group. Variables are
    added as a batch. This writes real values into the account.

    Args:
        group_id: The variable group to add to.
        variables: A name → value map. Values are sent to Codemagic and never returned.
        secure: Store as secured/encrypted (default true). Use false only for clearly
                non-secret config values.

    Returns only the variable names that were added — never the values.
    """
    if not variables:
        return {"error": "Provide at least one variable."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    items = [{"name": k, "value": v} for k, v in variables.items()]
    try:
        await client.add_group_variables(group_id, items, secure=secure)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "group_id": group_id}
    return {"added": True, "group_id": group_id, "secure": secure,
            "variable_names": list(variables.keys())}


@mcp.tool
async def update_environment_variable(
    group_id: str,
    variable_id: str,
    value: str | None = None,
    name: str | None = None,
    secure: bool | None = None,
) -> dict[str, Any]:
    """Update a single environment variable's value, name, or secure flag.

    Get group_id and variable_id from list_variable_groups (each variable carries its
    id). Pass only the fields you want to change. The new value is sent to Codemagic
    and never returned.
    """
    body: dict[str, Any] = {}
    if value is not None:
        body["value"] = value
    if name is not None:
        body["name"] = name
    if secure is not None:
        body["secure"] = secure
    if not body:
        return {"error": "Provide at least one of value, name, or secure to change."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.update_group_variable(group_id, variable_id, body)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "variable_id": variable_id}
    return {"updated": True, "group_id": group_id, "variable_id": variable_id,
            "changed": [k for k in body if k != "value"] + (["value"] if "value" in body else [])}


@mcp.tool
async def delete_environment_variable(group_id: str, variable_id: str) -> dict[str, Any]:
    """Delete a single environment variable from a group.

    Get group_id and variable_id from list_variable_groups. This is destructive —
    confirm which variable with the user first.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.delete_group_variable(group_id, variable_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "variable_id": variable_id}
    return {"deleted": True, "group_id": group_id, "variable_id": variable_id}


@mcp.tool
async def update_variable_group(
    group_id: str, name: str | None = None, selected_apps: list[str] | None = None
) -> dict[str, Any]:
    """Rename a variable group or change which apps may read it (advanced security).

    Pass name to rename. Pass selected_apps to restrict the group to specific app ids
    (enables advanced security); pass an empty list to allow all apps again.
    """
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if selected_apps is not None:
        body["advanced_security"] = {"enabled": bool(selected_apps), "selected_apps": selected_apps}
    if not body:
        return {"error": "Provide a new name or selected_apps."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.update_variable_group(group_id, body)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "group_id": group_id}
    return {"updated": True, "group_id": group_id, "changed": list(body.keys())}


@mcp.tool
async def delete_variable_group(group_id: str) -> dict[str, Any]:
    """Delete a variable group and all the variables in it.

    Get group_id from list_variable_groups. This is destructive and removes every
    variable in the group — confirm with the user first.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.delete_variable_group(group_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "group_id": group_id}
    return {"deleted": True, "group_id": group_id}


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
