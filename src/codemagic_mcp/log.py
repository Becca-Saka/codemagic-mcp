"""Tiny stdlib logging shim so ported code has a logger without backend coupling."""

import logging
import os

logger = logging.getLogger("codemagic_mcp")

if not logger.handlers:
    handler = logging.StreamHandler()  # stderr — keeps stdout clean for stdio MCP
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("CODEMAGIC_MCP_LOG_LEVEL", "INFO").upper())
