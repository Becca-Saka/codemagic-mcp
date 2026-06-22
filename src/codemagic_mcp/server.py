"""Codemagic MCP server entry point.

Importing the tools package registers every @mcp.tool on the shared app instance;
main() then runs it over stdio.
"""

from codemagic_mcp import tools  # noqa: F401  — side effect: registers tools
from codemagic_mcp.app import mcp


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
