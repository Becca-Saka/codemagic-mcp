"""Codemagic MCP server.

Auth: the Codemagic API token comes from the CODEMAGIC_API_TOKEN env var, set in
the MCP client config (the standard pattern, e.g. LangSmith). When it's missing the
tools return setup instructions instead of failing silently.

Tools:
  - verify_connection — confirm the token works (GET /user) and list teams.
  - list_team_builds — recent builds for a team.
"""

import os
from typing import Any

from fastmcp import FastMCP

from codemagic_mcp.client import CmApiClient, CmApiError

mcp = FastMCP("codemagic")

SETUP_INSTRUCTIONS = (
    "Set CODEMAGIC_API_TOKEN in this server's MCP config (the \"env\" block) and "
    "reload your IDE. Get the token in Codemagic → Account settings (top-right "
    "avatar) → API token → Show → Copy."
)


class AuthError(Exception):
    pass


def _token() -> str:
    token = (os.environ.get("CODEMAGIC_API_TOKEN") or "").strip()
    # Treat empty / unexpanded ${...} / <placeholder> values as not set.
    if not token or token.startswith("${") or token.startswith("<"):
        raise AuthError(SETUP_INSTRUCTIONS)
    return token


def _teams(user_payload: Any) -> list[dict[str, Any]]:
    """Teams from the legacy GET /user: the personal team first, then the rest.

    Shape: {"user": {"personalTeam": {"_id","name"}, "teams": [{"_id","name"}, ...]}}
    """
    user = user_payload.get("user", {}) if isinstance(user_payload, dict) else {}
    teams: list[dict[str, Any]] = []
    personal = user.get("personalTeam") or {}
    if personal.get("_id"):
        teams.append({"id": personal["_id"], "name": personal.get("name") or "Personal",
                      "personal": True})
    for team in user.get("teams") or []:
        if isinstance(team, dict) and team.get("_id"):
            teams.append({"id": team["_id"], "name": team.get("name") or "(unnamed)",
                          "personal": False})
    return teams


@mcp.tool
async def verify_connection() -> dict[str, Any]:
    """Verify the Codemagic token (GET /user) and list the teams it can access."""
    try:
        client = CmApiClient(_token())
    except AuthError as e:
        return {"connected": False, "error": "No token configured.", "setup": str(e)}
    try:
        payload = await client.get_user()
    except CmApiError as e:
        if e.status_code in (401, 403):
            return {"connected": False, "error": "Token rejected by Codemagic.",
                    "setup": SETUP_INSTRUCTIONS}
        return {"connected": False, "status_code": e.status_code, "error": e.message}
    user = payload.get("user", {}) if isinstance(payload, dict) else {}
    profile = user.get("user") or {}
    return {
        "connected": True,
        "user": {"id": user.get("_id"), "name": profile.get("fullName"),
                 "email": profile.get("email")},
        "teams": _teams(payload),
    }


@mcp.tool
async def list_team_builds(team_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """List recent builds for a Codemagic team.

    Args:
        team_id: Team to list builds for. If omitted and the token has exactly one
                 team, that team is used automatically.
        limit: Max number of builds to return (default 10).
    """
    try:
        client = CmApiClient(_token())
    except AuthError as e:
        return {"error": "No token configured.", "setup": str(e)}

    if not team_id:
        try:
            teams = _teams(await client.get_user())
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
    builds = result.get("data", []) if isinstance(result, dict) else (result or [])
    cursor = result.get("cursor") if isinstance(result, dict) else None
    return {"team_id": team_id, "count": len(builds), "builds": builds, "cursor": cursor}


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
