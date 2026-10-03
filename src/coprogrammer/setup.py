"""Preview and install missing project-level knowledge/configuration files.

Existing instructions are preserved. Different skills, generated docs or MCP
configurations are conflicts, never merge targets. No global settings or model
connections are changed or checked. Public previews contain generated content
only, not the contents of existing user files.
"""
from __future__ import annotations

import hashlib
import stat
from pathlib import Path

from . import integrations, knowledge

CLIENT_LAYOUTS = {
    "codex": (".agents/skills", ".codex/config.toml", None),
    "claude": (".claude/skills", ".mcp.json", "CLAUDE.md"),
    "copilot": (".agents/skills", ".vscode/mcp.json", ".github/copilot-instructions.md"),
}
MAX_EXISTING_BYTES = 1_000_000


def _target(root: Path, relative: str) -> Path:
    target = root / relative
    # Fixed catalog paths only. Refuse symlinks/junctions at every component,
    # even when the link currently points inside the requested project.
    current = root
    for part in Path(relative).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        # Resolving an existing Windows lock file may fail to open it and
        # retain different path casing. Inspect non-following metadata instead;
        # junctions and other reparse points remain blocked along with symlinks.
        if (stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise RuntimeError(f"unsafe linked setup path: {relative}")
        mode = metadata.st_mode
        if current == target and not stat.S_ISREG(mode):
            raise RuntimeError(f"setup target is not a regular file: {relative}")
        if current != target and not stat.S_ISDIR(mode):
            raise RuntimeError(f"setup parent is not a directory: {relative}")
    return target


def _files(root: Path, client: str, skills: list[str] | None,
           include_mcp: bool, include_skills: bool) -> list[dict]:
    if client not in CLIENT_LAYOUTS:
        raise RuntimeError("client must be codex, claude, or copilot")
    if type(include_mcp) is not bool or type(include_skills) is not bool:
        raise RuntimeError("setup switches must be boolean")
    available = [d["name"] for d in knowledge.documents() if d["kind"] == "skill"]
    selected = available if skills is None else skills
    if (not isinstance(selected, list) or len(selected) > len(available)
            or any(not isinstance(s, str) or s not in available for s in selected)
            or len(set(selected)) != len(selected)):
        raise RuntimeError("skills must be unique names from knowledge list")
    if not include_skills and skills:
        raise RuntimeError("cannot select skills while skill installation is disabled")
    skill_dir, config_path, instructions = CLIENT_LAYOUTS[client]
    files = []

    def add(path, kind, content):
        files.append({"path": path, "kind": kind, "content": content})

    add("AGENTS.md", "instructions", knowledge.read_document("templates/AGENTS"))
    if instructions:
        name = "CLAUDE" if client == "claude" else "copilot-instructions"
        add(instructions, "instructions", knowledge.read_document(f"templates/{name}"))
    for name in ("COORDINATION", "task-brief", "handoff"):
        add(f"docs/coprogrammer/{name}.md", "template", knowledge.read_document(f"templates/{name}"))
    if include_skills:
        for name in selected:
            add(f"{skill_dir}/{name}/SKILL.md", "skill", knowledge.read_document(f"skills/{name}"))
    if include_mcp:
        add(config_path, "mcp", integrations.client_config(client, root))
    return files


def _prepare(cwd: Path, client: str, skills: list[str] | None,
             include_mcp: bool, include_skills: bool) -> tuple[Path, list[dict], list[str]]:
    root = cwd.resolve()
    if not root.is_dir():
        raise RuntimeError("setup project directory must already exist")
    files = _files(root, client, skills, include_mcp, include_skills)
    warnings = []
    for item in files:
        content = item["content"].encode("utf-8")
        item.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        try:
            target = _target(root, item["path"])
            if not target.exists():
                item["status"] = "create"
            elif target.stat().st_size > MAX_EXISTING_BYTES:
                item["status"] = "preserve" if item["kind"] == "instructions" else "conflict"
            else:
                # Compare only; never include existing bytes in the report.
                with target.open("rb") as handle:
                    existing = handle.read(MAX_EXISTING_BYTES + 1)
                item["status"] = ("unchanged" if existing == content else
                                  "preserve" if item["kind"] == "instructions" else "conflict")
        except (OSError, RuntimeError):
            item["status"] = "blocked"
        if item["status"] == "preserve":
            warnings.append(f"Preserved {item['path']}; review and link docs/coprogrammer/COORDINATION.md manually.")
        if item["status"] in ("conflict", "blocked"):
            warnings.append(f"Resolve {item['path']} manually; setup will not overwrite or follow links.")
        if item["kind"] == "skill":
            name = Path(item["path"]).parent.name
            for directory in (".agents/skills", ".claude/skills", ".github/skills"):
                alternate = f"{directory}/{name}/SKILL.md"
                if alternate != item["path"] and (root / alternate).exists():
                    warnings.append(f"Also present: {alternate}; clients scanning multiple skill directories may discover duplicates.")
    return root, files, warnings


def _report(root: Path, client: str, files: list[dict], warnings: list[str],
            include_content: bool, *, applied: bool = False) -> dict:
    conflicts = [f["path"] for f in files if f["status"] in ("conflict", "blocked")]
    return {
        "format": "coprogrammer.setup.v1", "project": str(root), "client": client,
        "applied": applied, "can_apply": not conflicts, "conflicts": conflicts,
        "files": [{k: v for k, v in item.items() if include_content or k != "content"} for item in files],
        "warnings": warnings,
        "connection": "not_checked",
        "next_steps": ["Review the generated project files and preserve local instructions.",
                       "Keep .coprogrammer/ runtime state out of version control.",
                       "Reload the chosen client and complete its normal project/MCP trust flow.",
                       "Generated MCP paths are machine-specific; regenerate after moving Python, package or project."],
    }


def preview(cwd: Path, client: str, skills: list[str] | None = None,
            include_mcp: bool = True, include_skills: bool = True,
            include_content: bool = False) -> dict:
    root, files, warnings = _prepare(cwd, client, skills, include_mcp, include_skills)
    return _report(root, client, files, warnings, include_content)


def apply(cwd: Path, client: str, skills: list[str] | None = None,
          include_mcp: bool = True, include_skills: bool = True,
          include_content: bool = False) -> dict:
    from .cli import event_log_path
    from .manager_store import transaction

    root, files, warnings = _prepare(cwd, client, skills, include_mcp, include_skills)
    report = _report(root, client, files, warnings, include_content)
    if not report["can_apply"]:
        return report
    # Serialize cooperating installers through the existing local Manager lock.
    # Runtime locking can create the state directory, but no Manager event is
    # appended for installing files and no model/client process is started.
    state_path = event_log_path(root)
    state_root = state_path.parent
    if state_root.is_symlink() or state_root.resolve() != state_root:
        raise RuntimeError("setup refuses linked Manager state directories")
    for name in (state_path.name, state_path.name + ".lock"):
        _target(state_root.parent, f"{state_root.name}/{name}")
    with transaction(state_path):
        root, files, warnings = _prepare(root, client, skills, include_mcp, include_skills)
        report = _report(root, client, files, warnings, include_content)
        if not report["can_apply"]:
            return report
        created: list[tuple[Path, bytes]] = []
        try:
            for item in files:
                if item["status"] != "create":
                    continue
                target = _target(root, item["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target = _target(root, item["path"])
                content = item["content"].encode("utf-8")
                with target.open("xb") as handle:
                    created.append((target, content))
                    handle.write(content)
                item["status"] = "created"
        except (OSError, RuntimeError) as exc:
            # Remove only this run's unchanged completed files. Partial write
            # failures and files changed by others remain visible for recovery.
            for target, expected in reversed(created):
                if not target.is_symlink() and target.is_file() and target.read_bytes() == expected:
                    target.unlink()
            raise RuntimeError("setup write failed; completed unchanged files were rolled back; inspect the target before retrying") from exc
    return _report(root, client, files, warnings, include_content, applied=True)
