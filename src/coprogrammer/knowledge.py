"""Read-only, wheel-packaged skills and Markdown templates.

The catalog is an explicit allowlist. Resource requests never become caller-
controlled file paths or network requests.
"""
from __future__ import annotations

from importlib import resources


_SKILLS = (
    ("coprogrammer-project-setup", "Project setup",
     "Add repository-local skills, Markdown instructions and optional MCP configuration."),
    ("coprogrammer-project-covenant", "Project covenant",
     "Audit project instructions, protected paths, ownership and validation conventions."),
    ("coprogrammer-task-brief", "Task brief",
     "Scope a coding request with allowed paths, shared contracts and validation."),
    ("coprogrammer-active-sync", "Active coordination",
     "Coordinate windows through task claims, edit guards, conversations and shared state."),
    ("coprogrammer-pr-digest-review", "Branch digest review",
     "Review branch changes and classify what to preserve, rebuild, defer or reject."),
    ("coprogrammer-integration-plan", "Integration plan",
     "Plan a reviewable integration with validation and rollback evidence."),
)

_TEMPLATES = (
    ("AGENTS", "Repository agent instructions",
     "Concise root instructions linking to the shared coordination guide."),
    ("CLAUDE", "Claude Code instructions",
     "Repository guidance importing AGENTS.md for Claude Code."),
    ("copilot-instructions", "GitHub Copilot instructions",
     "Repository coordination guidance for GitHub Copilot."),
    ("COORDINATION", "Coordination guide",
     "CLI examples for sessions, task ownership, edit guards, messages and recovery."),
    ("task-brief", "Task brief template",
     "Record scope, ownership, validation and expected handoff artifacts."),
    ("handoff", "Development handoff template",
     "Record actual changes, validation, remaining work and coordination state."),
)

_CATALOG = tuple(
    {
        "id": f"{group}/{name}",
        "kind": kind,
        "name": name,
        "title": title,
        "description": description,
        "mime_type": "text/markdown",
        "uri": f"coprogrammer://{group}/{name}",
    }
    for group, kind, rows in (("skills", "skill", _SKILLS),
                              ("templates", "template", _TEMPLATES))
    for name, title, description in rows
)

_RESOURCE_PATHS = {
    doc["id"]: (("assets", "skills", doc["name"], "SKILL.md")
                if doc["kind"] == "skill"
                else ("assets", "templates", doc["name"] + ".md"))
    for doc in _CATALOG
}


def documents() -> list[dict[str, str]]:
    """Return detached metadata for every readable bundled document."""
    return [dict(doc) for doc in _CATALOG]


def read_document(document_id: str) -> str:
    """Read an exact catalog ID, including from an installed wheel."""
    if not isinstance(document_id, str) or document_id not in _RESOURCE_PATHS:
        raise RuntimeError("unknown knowledge document")
    resource = resources.files("coprogrammer").joinpath(*_RESOURCE_PATHS[document_id])
    try:
        return resource.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError("bundled knowledge document is unavailable") from exc
