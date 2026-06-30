"""Lean Codemagic REST client — only the calls the MCP needs today.

Auth: x-auth-token header per https://docs.codemagic.io/rest-api/codemagic-rest-api/
Built fresh for the standalone MCP; behaviour referenced from the backend client.
"""

from typing import Any

import httpx

from codemagic_mcp.log import logger

V3_BASE_URL = "https://codemagic.io/api/v3"
LEGACY_BASE_URL = "https://api.codemagic.io"


class CmApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CmApiClient:
    def __init__(self, api_key: str, timeout: float = 30.0):
        if not api_key:
            raise ValueError("Codemagic API key is required")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "x-auth-token": self.api_key}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, url, headers=self._headers(), params=params, json=json
            )
            if response.status_code >= 400:
                logger.warning(
                    "Codemagic API error | status=%d | url=%s",
                    response.status_code,
                    str(response.url),
                )
                raise CmApiError(response.status_code, response.text)
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    async def get_user(self) -> Any:
        """GET /user (legacy) — verifies the token and returns the personal team +
        all teams with names, in one call (the v3 /user hides the personal team id)."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/user")

    async def get_build(self, build_id: str) -> Any:
        """GET /builds/{build_id} (legacy) — returns {application, build}; the build
        carries buildActions (per-step status + logUrl), config, commit, app/repo."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/builds/{build_id}")

    async def list_applications(self) -> Any:
        """GET /apps (legacy) — all apps the token can access."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/apps")

    async def get_application(self, app_id: str) -> Any:
        """GET /apps/{app_id} (legacy) — full app config (workflows, scripts, signing)."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/apps/{app_id}")

    async def add_application_private(self, body: dict[str, Any]) -> Any:
        """POST /apps/new (legacy) — add an app cloned over SSH; body is
        {repositoryUrl, sshKey:{data,passphrase}, projectType?, teamId?}. The
        URL-only POST /apps path is unused: it makes an unauthenticated "generic"
        repo whose builds fail at checkout."""
        return await self._request("POST", f"{LEGACY_BASE_URL}/apps/new", json=body)

    async def delete_application(self, app_id: str) -> Any:
        """DELETE /apps/{app_id} (legacy) — permanently remove an app."""
        return await self._request("DELETE", f"{LEGACY_BASE_URL}/apps/{app_id}")

    async def get_team(self, team_id: str) -> Any:
        """GET /team/{team_id} (legacy) — team config incl. signingFiles + integrations."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/team/{team_id}")

    async def list_app_variable_groups(self, app_id: str) -> Any:
        """GET /apps/{app_id}/variable-groups (v3) — env var group names for the app."""
        return await self._request(
            "GET", f"{V3_BASE_URL}/apps/{app_id}/variable-groups", params={"page_size": 100}
        )

    async def list_team_variable_groups(self, team_id: str) -> Any:
        """GET /teams/{team_id}/variable-groups (v3) — env var group names for the team."""
        return await self._request(
            "GET", f"{V3_BASE_URL}/teams/{team_id}/variable-groups", params={"page_size": 100}
        )

    async def create_app_variable_group(self, app_id: str, name: str) -> Any:
        """POST /apps/{app_id}/variable-groups (v3) — create a group; body {name}."""
        return await self._request(
            "POST", f"{V3_BASE_URL}/apps/{app_id}/variable-groups", json={"name": name}
        )

    async def create_team_variable_group(
        self, team_id: str, name: str, *, selected_apps: list[str] | None = None
    ) -> Any:
        """POST /teams/{team_id}/variable-groups (v3) — create a team group.

        advanced_security limits which apps can read the group; disabled by default."""
        body = {
            "name": name,
            "advanced_security": {
                "enabled": bool(selected_apps),
                "selected_apps": selected_apps or [],
            },
        }
        return await self._request(
            "POST", f"{V3_BASE_URL}/teams/{team_id}/variable-groups", json=body
        )

    async def add_group_variables(
        self, group_id: str, variables: list[dict[str, str]], *, secure: bool
    ) -> Any:
        """POST /variable-groups/{group_id}/variables (v3) — bulk-add variables;
        body {secure, variables:[{name,value}]}."""
        return await self._request(
            "POST",
            f"{V3_BASE_URL}/variable-groups/{group_id}/variables",
            json={"secure": secure, "variables": variables},
        )

    async def update_variable_group(self, group_id: str, body: dict[str, Any]) -> Any:
        """PATCH /variable-groups/{group_id} (v3) — rename / change advanced security."""
        return await self._request(
            "PATCH", f"{V3_BASE_URL}/variable-groups/{group_id}", json=body
        )

    async def delete_variable_group(self, group_id: str) -> Any:
        """DELETE /variable-groups/{group_id} (v3) — remove a group and its variables."""
        return await self._request("DELETE", f"{V3_BASE_URL}/variable-groups/{group_id}")

    async def update_group_variable(
        self, group_id: str, variable_id: str, body: dict[str, Any]
    ) -> Any:
        """PATCH /variable-groups/{group_id}/variables/{variable_id} (v3) —
        change a variable's name/value/secure flag."""
        return await self._request(
            "PATCH",
            f"{V3_BASE_URL}/variable-groups/{group_id}/variables/{variable_id}",
            json=body,
        )

    async def delete_group_variable(self, group_id: str, variable_id: str) -> Any:
        """DELETE /variable-groups/{group_id}/variables/{variable_id} (v3)."""
        return await self._request(
            "DELETE", f"{V3_BASE_URL}/variable-groups/{group_id}/variables/{variable_id}"
        )

    async def list_group_variables(self, group_id: str) -> Any:
        """GET /variable-groups/{group_id}/variables (v3) — variable names in a group."""
        return await self._request(
            "GET", f"{V3_BASE_URL}/variable-groups/{group_id}/variables", params={"page_size": 100}
        )

    async def start_build(self, body: dict[str, Any]) -> Any:
        """POST /builds (legacy) — trigger a build; returns {buildId}."""
        return await self._request("POST", f"{LEGACY_BASE_URL}/builds", json=body)

    async def cancel_build(self, build_id: str) -> int:
        """POST /builds/{build_id}/cancel (legacy) — cancel a running build.

        Returns the HTTP status: 200 cancelled, 208 the build had already finished."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{LEGACY_BASE_URL}/builds/{build_id}/cancel", headers=self._headers()
            )
            if response.status_code >= 400:
                logger.warning("Codemagic API error | status=%d | url=%s",
                               response.status_code, str(response.url))
                raise CmApiError(response.status_code, response.text)
            return response.status_code

    async def get_step_log(self, log_url: str) -> str:
        """Fetch a build step's raw log text from its (absolute) logUrl."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(log_url, headers=self._headers())
            if response.status_code >= 400:
                logger.warning("Codemagic log fetch error | status=%d | url=%s",
                               response.status_code, log_url)
                raise CmApiError(response.status_code, response.text)
            return response.text

    async def get_team_builds(self, team_id: str, *, limit: int = 10) -> Any:
        """GET /teams/{team_id}/builds — recent builds for a team."""
        return await self._request(
            "GET",
            f"{V3_BASE_URL}/teams/{team_id}/builds",
            params={"page_size": limit},
        )

    async def create_public_artifact_url(self, artifact_url: str, expires_at: int) -> Any:
        """POST {artifact_url}/public-url (legacy) — mint a token-free shareable link.

        artifact_url is an artefact's `url` from a build (the /artifacts/{secureFilename}
        endpoint); expires_at is a UNIX timestamp (seconds). Returns {url, expiresAt}."""
        return await self._request(
            "POST", f"{artifact_url}/public-url", json={"expiresAt": expires_at}
        )

    async def list_caches(self, app_id: str) -> Any:
        """GET /apps/{app_id}/caches (legacy) — cache entries for an app."""
        return await self._request("GET", f"{LEGACY_BASE_URL}/apps/{app_id}/caches")

    async def clear_caches(self, app_id: str) -> Any:
        """DELETE /apps/{app_id}/caches (legacy) — remove ALL caches for an app."""
        return await self._request("DELETE", f"{LEGACY_BASE_URL}/apps/{app_id}/caches")

    async def delete_cache(self, app_id: str, cache_id: str) -> Any:
        """DELETE /apps/{app_id}/caches/{cache_id} (legacy) — remove one cache."""
        return await self._request(
            "DELETE", f"{LEGACY_BASE_URL}/apps/{app_id}/caches/{cache_id}"
        )

    async def get_remote_access(self, build_id: str) -> Any:
        """GET /builds/{build_id}/remote-access (v3) — SSH/VNC connection details.

        Returns {ssh:{script_url}, vnc:{host,port,username,password}}. 400s with
        'Remote access is not enabled for this build' unless it was turned on (the
        'Enable SSH/VNC access' checkbox) when the build was started."""
        return await self._request(
            "GET", f"{V3_BASE_URL}/builds/{build_id}/remote-access"
        )
