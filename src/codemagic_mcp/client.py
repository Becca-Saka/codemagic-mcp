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
        self, method: str, url: str, *, params: dict[str, Any] | None = None
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, headers=self._headers(), params=params)
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

    async def get_team_builds(self, team_id: str, *, limit: int = 10) -> Any:
        """GET /teams/{team_id}/builds — recent builds for a team."""
        return await self._request(
            "GET",
            f"{V3_BASE_URL}/teams/{team_id}/builds",
            params={"page_size": limit},
        )
