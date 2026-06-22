"""Pure functions that shape Codemagic API responses into tool results.

No network, no state — raw API payload in, trimmed dict/list out. Kept separate
from the tools so they're unit-testable with fixed inputs.
"""

from datetime import datetime
from typing import Any


def duration_seconds(started: Any, finished: Any) -> int | None:
    """Wall-clock seconds between two ISO timestamps, or None."""
    if not started or not finished:
        return None
    try:
        fmt = lambda s: datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return max(0, round((fmt(finished) - fmt(started)).total_seconds()))
    except (ValueError, AttributeError):
        return None


def owner_repo(url: str | None) -> str | None:
    """'owner/repo' from a repository/commit URL, or None."""
    if not url or "://" not in url:
        return None
    parts = [p for p in url.split("://", 1)[1].split("#")[0].split("?")[0].split("/")[1:] if p]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1].removesuffix('.git')}"


def step_log_url(action: Any) -> str | None:
    """Resolve a build step's log URL: action-level, else a subaction's.

    Script steps (e.g. a failed post-clone script) carry logUrl=null on the action
    and the real URL on the subaction — prefer the failed subaction, else any.
    """
    if not isinstance(action, dict):
        return None
    if action.get("logUrl"):
        return action["logUrl"]
    subs = [s for s in (action.get("subactions") or []) if isinstance(s, dict) and s.get("logUrl")]
    if not subs:
        return None
    failed = next((s for s in subs if s.get("status") == "failed"), None)
    return (failed or subs[0])["logUrl"]


def user_profile(user_payload: Any) -> dict[str, Any]:
    """{id, name, email} from the legacy GET /user payload."""
    user = user_payload.get("user", {}) if isinstance(user_payload, dict) else {}
    profile = user.get("user") or {}
    return {"id": user.get("_id"), "name": profile.get("fullName"), "email": profile.get("email")}


def team_list(user_payload: Any) -> list[dict[str, Any]]:
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


def build_summary(build_payload: Any) -> dict[str, Any]:
    """Projection of the legacy GET /builds/{id} payload ({application, build}).

    This is redaction + trimming, NOT analysis: the raw payload is ~3k tokens and
    includes application.appEnvironmentVariables (secrets) and big workflow config
    blobs. We keep every field useful for diagnosing a failure (status, per-step
    status, commit, repo, workflow, timing) and drop secrets/bloat. The host still
    decides what the failure means — add fields here if it ever needs more.
    """
    build = build_payload.get("build", {}) if isinstance(build_payload, dict) else {}
    app = build_payload.get("application", {}) if isinstance(build_payload, dict) else {}
    commit = build.get("commit") or {}
    workflow_id = build.get("workflowId") or build.get("fileWorkflowId")
    workflow = (app.get("workflows") or {}).get(workflow_id) or {}
    repo = (app.get("repository") or {}).get("htmlUrl") or (app.get("repository") or {}).get("url")
    owner_team = app.get("ownerTeam")
    team_id = owner_team.get("_id") if isinstance(owner_team, dict) else owner_team
    actions = build.get("buildActions") or []

    return {
        "build_id": build.get("_id"),
        "status": build.get("status"),
        "message": build.get("message"),
        "version": build.get("version"),
        "branch": build.get("branch"),
        "instance_type": build.get("instanceType"),
        "workflow": {"id": workflow_id, "name": workflow.get("name")},
        "commit": {"hash": commit.get("hash"), "message": commit.get("message"),
                   "author": commit.get("authorName") or commit.get("author_name")},
        "app": {"app_id": app.get("_id"), "name": app.get("appName"),
                "project_type": app.get("projectType"),
                "config_source": app.get("settingsSource"),
                "repo": owner_repo(repo), "team_id": team_id},
        "started_at": build.get("startedAt"),
        "finished_at": build.get("finishedAt"),
        "duration_seconds": duration_seconds(build.get("startedAt"), build.get("finishedAt")),
        "step_count": len(actions),
        "steps": [
            {"step_id": a.get("_id"), "name": a.get("name"), "status": a.get("status"),
             "duration_seconds": duration_seconds(a.get("startedAt"), a.get("finishedAt")),
             "log_url": step_log_url(a)}
            for a in actions
        ],
    }


def step_records(build_payload: Any) -> list[dict[str, Any]]:
    """Per-step records for log fetching: {step_id, name, status, command, log_url}."""
    build = build_payload.get("build", {}) if isinstance(build_payload, dict) else {}
    records: list[dict[str, Any]] = []
    for a in build.get("buildActions") or []:
        commands = [s.get("command") for s in (a.get("subactions") or []) if s.get("command")]
        records.append({
            "step_id": a.get("_id"),
            "name": a.get("name"),
            "status": a.get("status"),
            "command": "\n".join(commands) or None,
            "log_url": step_log_url(a),
        })
    return records


def signing_summary(team_payload: Any) -> dict[str, Any]:
    """Redacted code-signing view from the legacy GET /team/{id} payload.

    Strict allow-list: only non-secret descriptive fields. NEVER include certificate
    passwords, serials, profile UUIDs, key data, or ASC key/issuer ids.
    """
    team = team_payload.get("team", team_payload) if isinstance(team_payload, dict) else {}
    signing = team.get("signingFiles") or {}

    def profile(p: dict[str, Any]) -> dict[str, Any]:
        meta = p.get("meta") or {}
        return {
            "reference_name": p.get("referenceName"),
            "valid": p.get("valid"),
            "bundle_id": meta.get("bundleId") or meta.get("applicationIdentifier"),
            "distribution_type": meta.get("distributionType"),
            "name": meta.get("name"),
            "expiration_date": meta.get("expirationDate"),
            "xcode_managed": meta.get("xcodeManaged"),
            "is_wildcard": meta.get("isWildcard"),
        }

    def named(item: dict[str, Any]) -> dict[str, Any]:
        return {"reference_name": item.get("referenceName"), "valid": item.get("valid")}

    asc = team.get("appStoreConnectIntegration") or {}
    return {
        "profiles": [profile(p) for p in signing.get("profiles") or []],
        "certificates": [named(c) for c in signing.get("certificates") or []],
        "keystores": [named(k) for k in signing.get("keystores") or []],
        "asc_integrations": [k.get("name") for k in (asc.get("apiKeys") or []) if k.get("name")],
    }


def builds_list(team_builds_payload: Any) -> dict[str, Any]:
    """{builds, cursor} from the v3 GET /teams/{id}/builds payload."""
    if isinstance(team_builds_payload, dict):
        return {"builds": team_builds_payload.get("data", []),
                "cursor": team_builds_payload.get("cursor")}
    return {"builds": team_builds_payload or [], "cursor": None}
