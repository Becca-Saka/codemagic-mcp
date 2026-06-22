"""Skill playbooks — instructional prompts the host model runs (no code logic)."""

from importlib import resources

# codemagic.yaml reference topics the host can pull on demand (skills/references/*.md).
YAML_REFERENCES = (
    "definitions-and-anchors",
    "build-versioning",
    "environment-and-cache",
    "code-signing",
    "publishing",
    "triggering",
    "ota-updates",
)


def load_skill(name: str) -> str:
    """Load a skill markdown file from the packaged skills/ directory."""
    return (resources.files("codemagic_mcp") / "skills" / f"{name}.md").read_text(encoding="utf-8")


def load_reference(name: str) -> str:
    """Load a codemagic.yaml reference markdown file by topic name."""
    if name not in YAML_REFERENCES:
        raise KeyError(name)
    return (
        resources.files("codemagic_mcp") / "skills" / "references" / f"{name}.md"
    ).read_text(encoding="utf-8")
