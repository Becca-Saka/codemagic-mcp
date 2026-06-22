"""Skill playbooks — instructional prompts the host model runs (no code logic)."""

from importlib import resources


def load_skill(name: str) -> str:
    """Load a skill markdown file from the packaged skills/ directory."""
    return (resources.files("codemagic_mcp") / "skills" / f"{name}.md").read_text(encoding="utf-8")
