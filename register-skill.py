#!/usr/bin/env python3
"""Stop hook: scan the turn's transcript for Read calls to SKILL.md
and register each to ~/.claude/skill-registry.md.
"""
import json, sys, os, re, subprocess
from pathlib import Path

REGISTRY = Path.home() / ".claude/skill-registry.md"
EXCLUDED_PREFIXES = (
    Path.home() / ".claude/scheduled-tasks",  # Routines, not skills
    Path.home() / ".claude/skills",            # built-in skills, already discoverable
)

TEMPLATE = """\
# Local Skill Registry

| Skill | Path | Description |
|-------|------|-------------|
"""


def main():
    data = json.load(sys.stdin)
    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return
    p = Path(transcript_path)
    if not p.exists():
        return
    seen = set()
    for line in p.read_text(errors="ignore").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message", entry)
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use" or block.get("name") != "Read":
                continue
            fp = block.get("input", {}).get("file_path", "")
            if not fp.endswith("SKILL.md") or fp in seen:
                continue
            seen.add(fp)
            register_from_path(Path(fp))


def register_from_path(skill_file: Path):
    if not skill_file.exists():
        return
    if any(str(skill_file).startswith(str(prefix)) for prefix in EXCLUDED_PREFIXES):
        return
    text = skill_file.read_text(errors="ignore")[:1200]
    m = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    if not m:
        return
    skill_name = m.group(1).strip().rstrip('"').rstrip("'")
    project = infer_project_name(skill_file)
    register(project, skill_name, skill_file)


def register(project: str, skill_name: str, skill_file: Path):
    unique_id = f"{project}:{skill_name}"

    content = REGISTRY.read_text() if REGISTRY.exists() else ""
    lines = content.splitlines()

    last_match_idx = -1
    for i, line in enumerate(lines):
        if f"`{unique_id}`" in line:
            return
        if f":{skill_name}`" in line:
            last_match_idx = i

    desc = extract_description(skill_file)
    row = f"| `{unique_id}` | `{skill_file}` | {desc} |"

    if not content.strip():
        content = TEMPLATE + row + "\n"
    elif last_match_idx >= 0:
        lines.insert(last_match_idx + 1, row)
        content = "\n".join(lines) + "\n"
    else:
        content = content.rstrip("\n") + "\n" + row + "\n"

    REGISTRY.write_text(content)


def infer_project_name(skill_file: Path) -> str:
    parts = skill_file.parts
    try:
        idx = parts.index(".claude")
        return parts[idx - 1] if idx > 0 else "unknown"
    except ValueError:
        pass
    # No .claude in path: try git repo root, else parent dir name
    try:
        result = subprocess.run(
            ["git", "-C", str(skill_file.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).name
    except (subprocess.SubprocessError, OSError):
        pass
    return skill_file.parent.name


def extract_description(skill_file: Path) -> str:
    text = skill_file.read_text(errors="ignore")[:1200]
    m = re.search(r"description:\s*>?\s*\n?\s*(.+)", text)
    if not m:
        return "(no description)"
    desc = m.group(1).strip().rstrip('"').rstrip("'")
    for sep in ["。", ". ", "，支持"]:
        if sep in desc:
            desc = desc[: desc.index(sep) + len(sep)].rstrip()
            break
    return desc[:80] + "..." if len(desc) > 80 else desc


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
