"""Build tools — info, step logs, and listing."""

import asyncio
from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


# Build tools use the legacy GET /builds/{id}, not v3, on purpose: only legacy
# embeds buildActions[].logUrl (per-step log links — v3 has a /actions endpoint but
# no log endpoint at all) plus the full application object (name/repo/team/workflow
# names) and the canonical artifact `url`. v3 returns app_id only and a short-lived
# signed artifact link. Revisit if/when v3 adds a step-logs endpoint.
@mcp.tool
async def get_build_info(build_id: str) -> dict[str, Any]:
    """Get a build's status, app/repo, commit, timing, and per-step status.

    Returns a summary including which steps ran and their status (so you can see
    which step failed). To fetch the actual log text for a step, use
    get_build_step_logs.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_build(build_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "build_id": build_id}
    return {"build": transform.build_summary(payload)}


@mcp.tool
async def get_build_step_logs(build_id: str, step_ids: list[str] | None = None) -> dict[str, Any]:
    """Fetch raw log text for a build's steps.

    Args:
        build_id: The build to fetch logs from.
        step_ids: Step ids (from get_build_info) to fetch. If omitted, fetches the
                  failed steps. Pass explicit ids to inspect non-failed steps.

    Returns each step's raw log text. Logs are returned untrimmed.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_build(build_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "build_id": build_id}

    records = transform.step_records(payload)
    if step_ids:
        wanted = set(step_ids)
        targets = [r for r in records if r["step_id"] in wanted]
    else:
        targets = [r for r in records if r["status"] == "failed"]
    if not targets:
        return {"build_id": build_id, "steps": [],
                "note": "No matching steps." if step_ids else "No failed steps in this build."}

    async def fetch(record: dict[str, Any]) -> dict[str, Any]:
        entry = {k: record[k] for k in ("step_id", "name", "status", "command")}
        if not record["log_url"]:
            entry["error"] = "No log available for this step."
            return entry
        try:
            entry["log"] = await client.get_step_log(record["log_url"])
        except CmApiError as e:
            entry["error"] = e.message
        return entry

    steps = await asyncio.gather(*(fetch(r) for r in targets))
    return {"build_id": build_id, "steps": list(steps)}


@mcp.tool
async def start_build(
    app_id: str,
    workflow_id: str,
    branch: str | None = None,
    tag: str | None = None,
    variable_groups: list[str] | None = None,
    variables: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Trigger a new Codemagic build. This starts a real build (consumes build minutes).

    Confirm the app, workflow, and branch/tag with the user before calling — this has
    side effects. Get app_id and the workflow ids from get_application or
    list_applications; pass real variable group names from list_variable_groups.

    Args:
        app_id: The app to build.
        workflow_id: The workflow id (as defined in the app's config / codemagic.yaml).
        branch: Branch to build. Provide either branch or tag.
        tag: Git tag to build. Provide either branch or tag.
        variable_groups: Names of existing variable groups to attach.
        variables: Inline build-time variables (key/value). Avoid putting secrets here;
                   prefer variable groups.
    """
    if not branch and not tag:
        return {"error": "Provide a branch or a tag to build."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)

    body: dict[str, Any] = {"appId": app_id, "workflowId": workflow_id}
    if branch:
        body["branch"] = branch
    if tag:
        body["tag"] = tag
    environment: dict[str, Any] = {}
    if variable_groups:
        environment["groups"] = variable_groups
    if variables:
        environment["variables"] = variables
    if environment:
        body["environment"] = environment

    try:
        result = await client.start_build(body)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "app_id": app_id}
    build_id = result.get("buildId") if isinstance(result, dict) else None
    return {"started": True, "build_id": build_id, "workflow_id": workflow_id}


@mcp.tool
async def cancel_build(build_id: str) -> dict[str, Any]:
    """Cancel a running Codemagic build.

    Confirm the build id with the user before calling — this stops an in-progress
    build. Use get_build_info or list_team_builds to find the build id.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        status = await client.cancel_build(build_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "build_id": build_id}
    if status == 208:
        return {"cancelled": False, "build_id": build_id,
                "note": "The build had already finished — nothing to cancel."}
    return {"cancelled": True, "build_id": build_id}


@mcp.tool
async def list_team_builds(team_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """List recent builds for a Codemagic team.

    Args:
        team_id: Team to list builds for. If omitted and the token has exactly one
                 team, that team is used automatically.
        limit: Max number of builds to return (default 10).
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)

    if not team_id:
        try:
            teams = transform.team_list(await client.get_user())
        except CmApiError as e:
            return {"error": f"Could not resolve teams: {e.message}", "status_code": e.status_code}
        if not teams:
            return {"error": "No teams found for this token."}
        if len(teams) > 1:
            return {"error": "Multiple teams available — pass a team_id.", "teams": teams}
        team_id = teams[0]["id"]

    try:
        result = await client.get_team_builds(team_id, limit=limit)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "team_id": team_id}
    shaped = transform.builds_list(result)
    return {"team_id": team_id, "count": len(shaped["builds"]), **shaped}
