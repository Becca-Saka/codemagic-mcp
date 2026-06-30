"""Tool modules. Importing this package registers every @mcp.tool definition."""

from codemagic_mcp.tools import (  # noqa: F401
    account,
    apps,
    artifacts,
    builds,
    caches,
    diagnostics,
    remote_access,
    signing,
    yaml_config,
)
