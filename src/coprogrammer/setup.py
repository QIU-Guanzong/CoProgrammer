"""Preview, install and explicitly refresh recorded project setup files.

Instructions are always preserved. Upgrades replace only generated files still
matching their local receipt; customized or unrecorded differences conflict.
Public reports never contain existing file contents. No global settings or
model connections are changed or checked.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from . import integrations, knowledge

CLIENT_LAYOUTS = integrations.CLIENT_LAYOUTS
MAX_EXISTING_BYTES = 1_000_000
MANIFEST_PATH = ".coprogrammer/setup-manifest.json"
MANIFEST_FORMAT = "coprogrammer.setup-manifest.v1"


def _existing(target: Path) -> bytes | None:
    try:
        with target.open("rb") as handle:
            data = handle.read(MAX_EXISTING_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(data) > MAX_EXISTING_BYTES:
        raise RuntimeError("setup file exceeds comparison limit")
    return data


def _manifest(root: Path) -> tuple[dict, bytes | None]:
    raw = _existing(_target(root, MANIFEST_PATH))
    if raw is None:
        return {}, None
    data = json.loads(raw)
    if (not isinstance(data, dict) or set(data) != {"format", "version", "files"}
            or data["format"] != MANIFEST_FORMAT or not isinstance(data["version"], str)
            or not isinstance(data["files"], dict) or len(data["files"]) > 1000):
        raise ValueError("invalid setup manifest")
    for path, entry in data["files"].items():
        if (not isinstance(path, str) or not path or "\\" in path
                or path.startswith("/") or ":" in path
                or any(part in ("", ".", "..") for part in path.split("/"))
                or not isinstance(entry, dict) or set(entry) != {"kind", "sha256"}
                or entry["kind"] not in ("skill", "template", "mcp")
                or not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in entry["sha256"])):
            raise ValueError("invalid setup manifest entry")
    return data["files"], raw


def _replace(root: Path, relative: str, content: bytes, expected: bytes,
             mode: int) -> None:
    # Stage a complete file before rechecking and replacing its project path.
    # The Manager lock protects cooperating installers, not arbitrary editors.
    from .manager_store import _replace_event_log

    target = _target(root, relative)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".coprogrammer-setup-",
                                         delete=False) as handle:
            temporary = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        target = _target(root, relative)
        if _existing(target) != expected:
            raise RuntimeError("setup target changed during application")
        _replace_event_log(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


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
           include_mcp: bool, include_skills: bool, edition: str = "full") -> list[dict]:
    if client not in CLIENT_LAYOUTS:
        raise RuntimeError("client must be one of: " + ", ".join(CLIENT_LAYOUTS))
    if type(include_mcp) is not bool or type(include_skills) is not bool:
        raise RuntimeError("setup switches must be boolean")
    if edition not in ("full", "skills", "mcp"):
        raise RuntimeError("edition must be full, skills, or mcp")
    if edition == "mcp" and (not include_mcp or skills):
        raise RuntimeError("MCP edition cannot disable MCP or select Skills")
    if edition == "skills" and not include_skills:
        raise RuntimeError("Skill edition cannot disable Skills")
    include_mcp = include_mcp and edition != "skills"
    include_skills = include_skills and edition != "mcp"
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

    if edition != "mcp":
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
        if client == "openclaw":
            add(".coprogrammer-kit/openclaw/profile.json", "mcp", integrations.openclaw_profile(root))
    return files


def _prepare(cwd: Path, client: str, skills: list[str] | None,
             include_mcp: bool, include_skills: bool, edition: str = "full",
             upgrade: bool = False) -> tuple[Path, list[dict], list[str], tuple[dict, bytes | None] | None]:
    root = cwd.resolve()
    if not root.is_dir():
        raise RuntimeError("setup project directory must already exist")
    files = _files(root, client, skills, include_mcp, include_skills, edition)
    if type(upgrade) is not bool:
        raise RuntimeError("setup upgrade switch must be boolean")
    warnings = []
    try:
        receipt = _manifest(root)
    except (OSError, RuntimeError, ValueError, RecursionError):
        receipt = None
        warnings.append(f"Inspect {MANIFEST_PATH} manually; invalid or linked setup receipts block application.")
    owned = receipt[0] if receipt is not None else {}
    for item in files:
        content = item["content"].encode("utf-8")
        item.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        item["managed"] = False
        try:
            target = _target(root, item["path"])
            if not target.exists():
                item["status"] = "create"
            elif target.stat().st_size > MAX_EXISTING_BYTES:
                item["status"] = "preserve" if item["kind"] == "instructions" else "conflict"
            else:
                # Compare only; never include existing bytes in the report.
                existing = _existing(target)
                entry = owned.get(item["path"])
                item["managed"] = bool(entry and entry["kind"] == item["kind"]
                                       and existing is not None
                                       and entry["sha256"] == hashlib.sha256(existing).hexdigest())
                item["status"] = ("unchanged" if existing == content else
                                  "preserve" if item["kind"] == "instructions" else
                                  "update" if upgrade and item["managed"] else "conflict")
        except (OSError, RuntimeError):
            item["status"] = "blocked"
        if item["status"] == "preserve":
            warnings.append(f"Preserved {item['path']}; review and link docs/coprogrammer/COORDINATION.md manually.")
        if item["status"] in ("conflict", "blocked"):
            warnings.append(f"Resolve {item['path']} manually; only --upgrade can refresh unchanged recorded files; links remain blocked.")
        if item["kind"] == "skill":
            name = Path(item["path"]).parent.name
            for directory in (".agents/skills", ".claude/skills", ".github/skills"):
                alternate = f"{directory}/{name}/SKILL.md"
                if alternate != item["path"] and (root / alternate).exists():
                    warnings.append(f"Also present: {alternate}; clients scanning multiple skill directories may discover duplicates.")
    return root, files, warnings, receipt


def _report(root: Path, client: str, files: list[dict], warnings: list[str],
            include_content: bool, receipt: tuple[dict, bytes | None] | None,
            *, applied: bool = False, upgrade: bool = False) -> dict:
    conflicts = [f["path"] for f in files if f["status"] in ("conflict", "blocked")]
    if receipt is None:
        conflicts.append(MANIFEST_PATH)
    return {
        "format": "coprogrammer.setup.v1", "project": str(root), "client": client,
        "applied": applied, "can_apply": not conflicts, "conflicts": conflicts,
        "upgrade": upgrade,
        "managed_manifest": {"path": MANIFEST_PATH,
                             "status": "blocked" if receipt is None else
                             "recorded" if receipt[1] is not None or applied else "missing"},
        "files": [{k: v for k, v in item.items() if include_content or k != "content"} for item in files],
        "warnings": warnings,
        "connection": "not_checked",
        "activation": integrations.client_profiles()[client],
        "next_steps": ["Review the generated project files and preserve local instructions.",
                       "Keep .coprogrammer/ runtime state out of version control.",
                       integrations.client_profiles()[client]["instructions"],
                       "After a package or Python path change, preview setup --upgrade, then add --apply to refresh unchanged recorded files."],
    }


def preview(cwd: Path, client: str, skills: list[str] | None = None,
            include_mcp: bool = True, include_skills: bool = True,
            include_content: bool = False, edition: str = "full", upgrade: bool = False) -> dict:
    root, files, warnings, receipt = _prepare(cwd, client, skills, include_mcp, include_skills, edition, upgrade)
    return _report(root, client, files, warnings, include_content, receipt, upgrade=upgrade)


def apply(cwd: Path, client: str, skills: list[str] | None = None,
          include_mcp: bool = True, include_skills: bool = True,
          include_content: bool = False, edition: str = "full", upgrade: bool = False) -> dict:
    from .cli import event_log_path
    from .manager_store import transaction

    root, files, warnings, receipt = _prepare(cwd, client, skills, include_mcp, include_skills, edition, upgrade)
    report = _report(root, client, files, warnings, include_content, receipt, upgrade=upgrade)
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
        root, files, warnings, receipt = _prepare(root, client, skills, include_mcp, include_skills, edition, upgrade)
        report = _report(root, client, files, warnings, include_content, receipt, upgrade=upgrade)
        if not report["can_apply"]:
            return report
        completed: list[tuple[str, bytes, bytes | None, int]] = []
        owned, original_receipt = receipt
        owned = dict(owned)
        try:
            for item in files:
                if item["status"] not in ("create", "update"):
                    if item["status"] == "unchanged" and item["kind"] != "instructions":
                        owned[item["path"]] = {"kind": item["kind"], "sha256": item["sha256"]}
                    continue
                target = _target(root, item["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target = _target(root, item["path"])
                content = item["content"].encode("utf-8")
                old = None
                mode = 0o600
                if item["status"] == "update":
                    old = _existing(target)
                    entry = owned[item["path"]]
                    if old is None or hashlib.sha256(old).hexdigest() != entry["sha256"]:
                        raise RuntimeError("setup target changed during application")
                    mode = stat.S_IMODE(target.stat().st_mode)
                    _replace(root, item["path"], content, old, mode)
                    completed.append((item["path"], content, old, mode))
                    item["status"] = "updated"
                else:
                    with target.open("xb") as handle:
                        completed.append((item["path"], content, None, mode))
                        handle.write(content)
                    item["status"] = "created"
                if item["kind"] != "instructions":
                    owned[item["path"]] = {"kind": item["kind"], "sha256": item["sha256"]}
            from . import __version__
            encoded = (json.dumps({"format": MANIFEST_FORMAT, "version": __version__, "files": owned},
                                  sort_keys=True, indent=2) + "\n").encode("utf-8")
            target = _target(root, MANIFEST_PATH)
            target.parent.mkdir(parents=True, exist_ok=True)
            target = _target(root, MANIFEST_PATH)
            if original_receipt is None:
                with target.open("xb") as handle:
                    completed.append((MANIFEST_PATH, encoded, None, 0o600))
                    handle.write(encoded)
            elif encoded != original_receipt:
                _replace(root, MANIFEST_PATH, encoded, original_receipt,
                         stat.S_IMODE(target.stat().st_mode))
        except (OSError, RuntimeError) as exc:
            # Restore only writes still matching this call's completed bytes.
            # Partial writes and concurrent edits remain visible for recovery.
            for relative, expected, old, mode in reversed(completed):
                try:
                    target = _target(root, relative)
                    if _existing(target) == expected:
                        if old is None:
                            target.unlink()
                        else:
                            _replace(root, relative, old, expected, mode)
                except (OSError, RuntimeError):
                    continue
            raise RuntimeError("setup write failed; unchanged completed writes were rolled back where possible; inspect the target before retrying") from exc
    return _report(root, client, files, warnings, include_content, receipt, applied=True, upgrade=upgrade)
