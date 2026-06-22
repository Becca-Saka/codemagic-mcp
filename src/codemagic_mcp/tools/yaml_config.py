"""codemagic.yaml tools — validation against the official schema."""

from typing import Any

import jsonschema
import yaml

from codemagic_mcp.app import mcp
from codemagic_mcp.prompts import YAML_REFERENCES, load_reference, load_skill
from codemagic_mcp.schema import load_schema


@mcp.tool
async def create_codemagic_yaml() -> str:
    """REQUIRED FIRST STEP before writing any codemagic.yaml. Get the authoring playbook.

    Call this BEFORE writing a single line of yaml whenever the user asks to create,
    set up, generate, or migrate a codemagic.yaml / Codemagic build config. Returns
    step-by-step instructions: which inputs to detect vs ask, how to ground the
    structure in the official schema and sample projects, which references to pull,
    and to validate before presenting. Do NOT write codemagic.yaml from memory — a
    config authored without this playbook uses keys the schema rejects and signing/
    publishing blocks that are wrong.
    """
    return load_skill("create_codemagic_yaml")


@mcp.tool
async def codemagic_yaml_reference(topic: str) -> str:
    """Get detailed reference notes for one part of a codemagic.yaml.

    Call this while writing a codemagic.yaml to get the Codemagic-specific patterns
    for an area before writing that section. Topics: definitions-and-anchors,
    build-versioning, environment-and-cache, publishing, triggering, ota-updates.
    """
    try:
        return load_reference(topic)
    except KeyError:
        return f"Unknown topic '{topic}'. Available: {', '.join(YAML_REFERENCES)}."


@mcp.tool
async def validate_codemagic_yaml(yaml_content: str) -> dict[str, Any]:
    """Validate a codemagic.yaml against the official Codemagic JSON schema.

    Call this after writing or editing a codemagic.yaml to catch structural errors
    (unknown keys, bad instance types, wrong shapes) before showing it to the user.
    Returns {valid, errors[]} where each error has a path and message; fix and
    re-validate until valid.
    """
    try:
        parsed = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return {"valid": False, "errors": [{"path": "(root)", "message": f"YAML parse error: {e}"}]}
    if not isinstance(parsed, dict):
        return {"valid": False,
                "errors": [{"path": "(root)", "message": "codemagic.yaml must be a mapping at the top level."}]}

    try:
        schema = await load_schema()
    except RuntimeError as e:
        return {"error": str(e)}

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(parsed), key=lambda e: list(e.absolute_path))
    if not errors:
        return {"valid": True, "errors": []}
    return {
        "valid": False,
        "errors": [
            {"path": " > ".join(str(p) for p in err.absolute_path) or "(root)",
             "message": err.message}
            for err in errors
        ],
    }
