"""Fetch and cache the official Codemagic codemagic.yaml JSON schema.

In-memory cache + on-disk cache with a 24h TTL, and a stale-on-failure fallback so
a transient network error doesn't break validation.
"""

import json
import time
from pathlib import Path
from typing import Any

import httpx

from codemagic_mcp.log import logger

SCHEMA_URL = "https://codemagic.io/codemagic-schema.json"
_TTL_SECONDS = 24 * 60 * 60

_mem: dict[str, Any] = {"schema": None, "ts": 0.0}


def _cache_file() -> Path:
    base = Path.home() / ".cache"
    return base / "codemagic-mcp" / "codemagic-schema.json"


def _read_file() -> dict[str, Any] | None:
    try:
        return json.loads(_cache_file().read_text())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _write_file(schema: dict[str, Any]) -> None:
    path = _cache_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(schema))
    except OSError:
        logger.warning("Could not write schema cache", exc_info=True)


def _file_is_fresh() -> bool:
    try:
        return time.time() - _cache_file().stat().st_mtime < _TTL_SECONDS
    except OSError:
        return False


async def load_schema() -> dict[str, Any]:
    """Return the Codemagic schema, using fresh caches when available."""
    if _mem["schema"] is not None and time.time() - _mem["ts"] < _TTL_SECONDS:
        return _mem["schema"]

    if _file_is_fresh():
        cached = _read_file()
        if cached is not None:
            _mem.update(schema=cached, ts=time.time())
            return cached

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(SCHEMA_URL)
            response.raise_for_status()
            schema = response.json()
    except (httpx.HTTPError, ValueError) as e:
        stale = _mem["schema"] or _read_file()  # stale beats nothing
        if stale is not None:
            logger.warning("Using stale Codemagic schema: %s", e)
            return stale
        raise RuntimeError(f"Could not fetch Codemagic schema: {e}") from e

    _mem.update(schema=schema, ts=time.time())
    _write_file(schema)
    return schema
