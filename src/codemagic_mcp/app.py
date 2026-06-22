"""The shared FastMCP application instance.

Lives apart from server.py and the tool modules so both can import it without a
circular dependency: tool modules import `mcp` here to register, server.py imports
the tools package to pull those registrations in, then runs `mcp`.
"""

from fastmcp import FastMCP

INSTRUCTIONS = """\
Codemagic CI/CD tools. Two tools return playbooks you must follow before acting —
they carry Codemagic-specific rules and grounding you would otherwise get wrong:

- BEFORE investigating, diagnosing, or fixing a FAILED build, call
  `diagnose_build_failure` first and follow what it returns.
- BEFORE creating or generating a codemagic.yaml, call `create_codemagic_yaml`
  first and follow it. BEFORE migrating a Workflow Editor (UI) app to a
  codemagic.yaml, call `migrate_ui_to_yaml` first. While writing, pull
  `codemagic_yaml_reference(topic)` for area-specific patterns, and ALWAYS run
  `validate_codemagic_yaml` before presenting the yaml.

Do not diagnose a build failure or write a codemagic.yaml from memory without these.\
"""

mcp = FastMCP("codemagic", instructions=INSTRUCTIONS)
