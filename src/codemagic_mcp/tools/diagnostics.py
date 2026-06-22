"""Diagnostics tools — skill playbooks the host runs."""

from codemagic_mcp.app import mcp
from codemagic_mcp.prompts import load_skill


@mcp.tool
async def diagnose_build_failure() -> str:
    """Get the playbook for diagnosing a failed Codemagic build.

    Call this FIRST whenever the user asks why a build failed, to investigate or fix
    a build, or to look into build errors — before calling the other build tools.
    Returns step-by-step instructions covering which tools to call, what to look for
    in the logs, how to classify the failure, and how to ground Codemagic-specific
    claims against the official sources. Then follow the returned playbook.
    """
    return load_skill("diagnose_build_failure")
