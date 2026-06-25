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


def _team_id(owner_team: Any) -> Any:
    return owner_team.get("_id") if isinstance(owner_team, dict) else owner_team


def _repo(app: dict[str, Any]) -> str | None:
    r = app.get("repository") or {}
    return owner_repo(r.get("htmlUrl") or r.get("url"))


def app_summary(app: Any) -> dict[str, Any]:
    """Compact app row for listings (no env vars / secrets)."""
    app = app if isinstance(app, dict) else {}
    return {
        "app_id": app.get("_id"),
        "name": app.get("appName"),
        "project_type": app.get("projectType"),
        "config_source": app.get("settingsSource"),
        "repo": _repo(app),
        "team_id": _team_id(app.get("ownerTeam")),
        "archived": app.get("archived"),
    }


def apps_list(apps_payload: Any) -> list[dict[str, Any]]:
    apps = apps_payload.get("applications", apps_payload) if isinstance(apps_payload, dict) else apps_payload
    return [app_summary(a) for a in apps or []]


def _env_vars(env: Any) -> dict[str, Any]:
    """Env var names/groups only — NEVER the values."""
    if isinstance(env, dict):
        variables, groups = env.get("variables") or [], env.get("groups") or []
    elif isinstance(env, list):
        variables, groups = env, []
    else:
        return {"variables": [], "groups": []}
    return {
        "variables": [
            {"key": v.get("key"), "group": v.get("group"), "secure": v.get("secure")}
            for v in variables if isinstance(v, dict)
        ],
        "groups": groups,
    }


_SAFE_PUBLISHER_FIELDS = ("recipients", "track", "customTrack", "channel", "submitAsDraft",
                          "artifactType")


def _publishers(publishers: Any) -> dict[str, Any]:
    """Publisher targets with safe fields only — drop credentials/tokens."""
    out: dict[str, Any] = {}
    for name, cfg in (publishers or {}).items():
        if not isinstance(cfg, dict):
            continue
        entry = {"enabled": cfg.get("enabled")}
        for f in _SAFE_PUBLISHER_FIELDS:
            if cfg.get(f) is not None:
                entry[f] = cfg[f]
        out[name] = entry
    return out


def _build_settings(bs: Any) -> dict[str, Any]:
    """Build settings as-is (toolchain, platforms, build args, shorebird) minus the
    shorebird storage token."""
    if not isinstance(bs, dict):
        return {}
    settings = dict(bs)
    shorebird = settings.get("shorebird")
    if isinstance(shorebird, dict) and "token" in shorebird:
        shorebird = {k: v for k, v in shorebird.items() if k != "token"}
        settings["shorebird"] = shorebird
    return settings


def _active_test_runners(runners: Any) -> list[str]:
    if not isinstance(runners, dict):
        return []
    return [name for name, cfg in runners.items()
            if isinstance(cfg, dict) and cfg.get("active")]


def _workflow(w: dict[str, Any]) -> dict[str, Any]:
    cs = w.get("codeSigning") or {}
    android, ios = cs.get("android") or {}, cs.get("ios") or {}
    return {
        "id": w.get("_id"),
        "name": w.get("name"),
        "instance_type": w.get("instanceType"),
        "max_build_duration": w.get("maxBuildDuration"),
        "branch_patterns": w.get("branchPatterns"),
        "tag_patterns": w.get("tagPatterns"),
        "build_settings": _build_settings(w.get("buildSettings")),
        "test_runners": _active_test_runners(w.get("testRunners")),
        "scripts": w.get("customScripts"),
        "code_signing": {
            "android": {"enabled": android.get("enabled")},
            "ios": {"bundle_id": ios.get("developerPortalBundleIdentifier")},
        },
        "publishers": _publishers(w.get("publishers")),
        "cache": w.get("dependencyCache"),
        "environment_variables": _env_vars(w.get("environmentVariables")),
    }


def app_detail(app_payload: Any) -> dict[str, Any]:
    """Full app config for migration/grounding, with secrets redacted.

    Keeps workflows, scripts, build settings, signing references, and publisher
    targets; redacts env var values, signing passwords/keystores, and publisher
    credentials.
    """
    app = app_payload.get("application", app_payload) if isinstance(app_payload, dict) else {}
    workflows = app.get("workflows") or {}
    return {
        **app_summary(app),
        "project_files": app.get("projectFiles"),
        "branches": app.get("branches"),
        "environment_variables": _env_vars(app.get("appEnvironmentVariables")),
        "workflows": [_workflow(w) for w in workflows.values() if isinstance(w, dict)],
    }


def variable_groups(payload: Any) -> list[dict[str, Any]]:
    """[{id, name}] from a v3 variable-groups payload (names only, no values)."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    return [{"id": g.get("id"), "name": g.get("name")} for g in data or [] if isinstance(g, dict)]


def group_variables(payload: Any) -> list[dict[str, Any]]:
    """[{id, name, secure}] from a v3 group-variables payload (keys only, no values).

    The id is the variable handle for update_environment_variable / delete."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    return [{"id": v.get("id"), "name": v.get("name"), "secure": v.get("secure")}
            for v in data or [] if isinstance(v, dict)]


def team_variable_groups(team_payload: Any) -> list[dict[str, Any]]:
    """Variable groups with their variable keys, from the legacy GET /team payload.

    The team's environmentVariables block holds all groups + variables in one call.
    Returns [{name, apps, variables: [{key, secure}]}] — keys only, never values.
    """
    team = team_payload.get("team", team_payload) if isinstance(team_payload, dict) else {}
    env = team.get("environmentVariables") or {}
    apps_by_group = env.get("apps") or {}
    by_group: dict[str, list[dict[str, Any]]] = {}
    for v in env.get("variables") or []:
        if isinstance(v, dict) and v.get("group"):
            by_group.setdefault(v["group"], []).append({"key": v.get("key"), "secure": v.get("secure")})
    return [
        {"name": g, "apps": apps_by_group.get(g, []), "variables": by_group.get(g, [])}
        for g in env.get("groups") or []
    ]


def team_integrations(team_payload: Any) -> dict[str, Any]:
    """Configured integrations from the legacy GET /team payload (names only).

    Drops secret-ish ids (issuer/key/tenant/client ids); keeps the names the host
    references in yaml (e.g. `integrations: app_store_connect: <name>`) + enabled flags.
    """
    team = team_payload.get("team", team_payload) if isinstance(team_payload, dict) else {}

    def key_names(integration_key: str) -> list[str]:
        keys = (team.get(integration_key) or {}).get("apiKeys") or []
        return [k.get("name") for k in keys if isinstance(k, dict) and k.get("name")]

    def conn(integration_key: str, label_field: str) -> dict[str, Any]:
        i = team.get(integration_key) or {}
        return {"enabled": i.get("isEnabled"), "account": i.get(label_field)}

    return {
        "app_store_connect": key_names("appStoreConnectIntegration"),
        "partner_center": key_names("partnerCenterIntegration"),
        "slack": {"enabled": (team.get("slackIntegration") or {}).get("isEnabled"),
                  "workspace": (team.get("slackIntegration") or {}).get("workspace")},
        "github": conn("githubAppIntegration", "login"),
        "gitlab": conn("gitlabIntegration", "login"),
        "bitbucket": conn("bitbucketIntegration", "login"),
        "email": {"enabled": (team.get("emailIntegration") or {}).get("isEnabled")},
    }


def team_tester_groups(team_payload: Any) -> list[dict[str, Any]]:
    """Tester groups [{name, device_count}] from the legacy GET /team payload."""
    team = team_payload.get("team", team_payload) if isinstance(team_payload, dict) else {}
    return [{"name": g.get("name"), "device_count": len(g.get("devices") or [])}
            for g in team.get("testerGroups") or [] if isinstance(g, dict)]


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
