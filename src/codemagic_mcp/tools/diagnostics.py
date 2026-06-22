"""Diagnostics tools — skill playbooks the host runs."""

from codemagic_mcp.app import mcp
from codemagic_mcp.prompts import load_skill


@mcp.tool
async def diagnose_build_failure() -> str:
    """REQUIRED FIRST STEP for any failed-build question. Get the diagnosis playbook.

    Call this BEFORE any other build tool whenever the user asks why a build failed,
    to investigate, fix, or look into a build / build errors. Returns step-by-step
    instructions: which tools to call, what to look for in the logs, how to classify
    the failure, and how to ground Codemagic-specific claims against the official
    sources — then follow it. Do NOT diagnose from memory or skip straight to
    get_build_info/get_build_step_logs; a diagnosis done without this playbook misses
    the silent-signing heuristic and the required documentation grounding, and will
    be wrong or unverified.
    """
    return load_skill("diagnose_build_failure")
