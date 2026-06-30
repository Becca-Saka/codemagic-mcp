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

Do not diagnose a build failure or write a codemagic.yaml from memory without these.

`start_build` and `cancel_build` have real side effects (a build consumes build
minutes; a cancel stops an in-progress build). Confirm the app, workflow, and
branch/tag — or the build id — with the user before calling either.

Several tools mutate the account: `add_application`, `create_variable_group`,
`add_environment_variables`, `update_environment_variable`, `update_variable_group`.
And these are DESTRUCTIVE and irreversible: `delete_application` (removes an app and
its build history), `delete_variable_group` (removes a group and every variable in
it), `delete_environment_variable`, `clear_caches` (removes all of an app's build
caches), `delete_cache`. Always confirm the exact target with the user before
calling any delete, and never delete something the user did not name.\
"""

mcp = FastMCP("codemagic", instructions=INSTRUCTIONS)
