"""The shared FastMCP application instance.

Lives apart from server.py and the tool modules so both can import it without a
circular dependency: tool modules import `mcp` here to register, server.py imports
the tools package to pull those registrations in, then runs `mcp`.
"""

from fastmcp import FastMCP

mcp = FastMCP("codemagic")
