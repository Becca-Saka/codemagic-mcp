"""Cache tools — inspect and clear an app's build caches.

Clearing caches forces the next build to rebuild dependencies from scratch — a
common remediation for stale-cache build failures (see diagnose_build_failure).
"""

from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token


@mcp.tool
async def list_caches(app_id: str) -> dict[str, Any]:
    """List an app's build caches (cache id, workflow, size, age).

    Use this before clearing — to see what's cached and pick a single cache to
    delete. Get app_id from list_applications.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.list_caches(app_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "app_id": app_id}
    caches = transform.caches_list(payload)
    return {"app_id": app_id, "count": len(caches), "caches": caches}


@mcp.tool
async def clear_caches(app_id: str) -> dict[str, Any]:
    """Delete ALL build caches for an app.

    Destructive and irreversible: the next build of every workflow rebuilds its
    caches from scratch (slower). Confirm the exact app (name + id) with the user
    before calling. To remove just one cache, use delete_cache.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.clear_caches(app_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code, "app_id": app_id}
    return {"cleared": True, "app_id": app_id}


@mcp.tool
async def delete_cache(app_id: str, cache_id: str) -> dict[str, Any]:
    """Delete a single build cache from an app.

    Destructive and irreversible. Get cache_id from list_caches and confirm the
    target with the user before calling.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        await client.delete_cache(app_id, cache_id)
    except CmApiError as e:
        return {"error": e.message, "status_code": e.status_code,
                "app_id": app_id, "cache_id": cache_id}
    return {"deleted": True, "app_id": app_id, "cache_id": cache_id}
