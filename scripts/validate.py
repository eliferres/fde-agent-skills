#!/usr/bin/env python3
"""Validate Agent Skills, subagent specs, reference examples, links, and prose hygiene in this repository.

Standard library only (Python 3.9+).

Exit codes:
  0  all checks passed
  1  one or more validation findings
  2  usage or configuration error
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

__version__ = "0.2.0"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DASH_RE = re.compile(r"[\u2013\u2014]")
SECRET_RE = re.compile(
    r"(?:sk[-]ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|xox[bap]-[0-9A-Za-z-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
BANNED_PROSE_RE = re.compile(
    r"\b(?:delve|crucial|pivotal|landscape|tapestry|testament|underscore|"
    r"showcase|leverage|seamless|robust|comprehensive|streamline|empower|"
    r"elevate|cutting-edge|blazing|effortless)\b",
    re.IGNORECASE,
)

REQUIRED_SKILL_SECTIONS = (
    "## The failure mode",
    "## Core rules",
    "## Step-by-step protocol",
    "## Worked example",
    "## Verification checklist",
    "## Boundaries",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    """Parse flat YAML frontmatter delimited by leading '---' lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, text
    meta: dict[str, str] = {}
    for raw in lines[1:end_idx]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            return None, text
        key, val = stripped.split(":", 1)
        val = val.strip()
        if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
            val = val[1:-1]
        meta[key.strip()] = val
    body = "\n".join(lines[end_idx + 1 :])
    return meta, body


def strip_code_segments(line: str) -> str:
    """Remove inline backtick spans before prose-word linting."""
    return re.sub(r"`[^`]*`", "", line)


def check_markdown_text(rel_path: str, text: str, findings: list[dict[str, Any]]) -> None:
    """Check secrets everywhere, plus dashes and banned filler in prose lines."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        m_sec = SECRET_RE.search(line)
        if m_sec:
            findings.append(
                {
                    "rule": "secret-pattern",
                    "path": rel_path,
                    "line": lineno,
                    "message": f"secret-like token matched ({m_sec.group(0)[:12]}...)",
                }
            )
        if in_fence:
            continue
        if DASH_RE.search(line):
            findings.append(
                {
                    "rule": "no-em-en-dash",
                    "path": rel_path,
                    "line": lineno,
                    "message": "contains an em or en dash; use plain punctuation",
                }
            )
        prose_only = strip_code_segments(line)
        m_ban = BANNED_PROSE_RE.search(prose_only)
        if m_ban:
            findings.append(
                {
                    "rule": "banned-filler",
                    "path": rel_path,
                    "line": lineno,
                    "message": f"contains banned filler word '{m_ban.group(0)}'",
                }
            )


def check_local_links(root: Path, file_path: Path, text: str, findings: list[dict[str, Any]]) -> None:
    """Verify every relative markdown link points to an existing path inside root."""
    rel_file = str(file_path.relative_to(root))
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK_RE.finditer(line):
            target = match.group(1).strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_no_anchor = target.split("#", 1)[0]
            if not target_no_anchor:
                continue
            resolved = (file_path.parent / target_no_anchor).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                findings.append(
                    {
                        "rule": "broken-link",
                        "path": rel_file,
                        "line": lineno,
                        "message": f"link escapes repository root: {target}",
                    }
                )
                continue
            if not resolved.exists():
                findings.append(
                    {
                        "rule": "broken-link",
                        "path": rel_file,
                        "line": lineno,
                        "message": f"broken local link: {target}",
                    }
                )


def check_examples(root: Path, skill_dir: Path, findings: list[dict[str, Any]]) -> int:
    """Verify every reference example under a skill's examples/ folder is valid Python."""
    examples = sorted((skill_dir / "examples").glob("*.py")) if (skill_dir / "examples").is_dir() else []
    for example in examples:
        try:
            ast.parse(example.read_text(encoding="utf-8"), filename=str(example))
        except (SyntaxError, UnicodeDecodeError) as exc:
            findings.append(
                {
                    "rule": "example-syntax",
                    "path": str(example.relative_to(root)),
                    "line": getattr(exc, "lineno", 0) or 0,
                    "message": f"reference example does not parse: {exc.__class__.__name__}",
                }
            )
    return len(examples)


def check_readme_index(root: Path, skill_files: list[Path], agent_files: list[Path],
                       findings: list[dict[str, Any]]) -> None:
    """Verify README.md links every skill and every agent, so nothing ships unlisted."""
    readme = root / "README.md"
    if not readme.is_file():
        return
    targets = {m.group(1).strip().split("#", 1)[0] for m in LINK_RE.finditer(readme.read_text(encoding="utf-8"))}
    for item in [*skill_files, *agent_files]:
        rel = item.relative_to(root).as_posix()
        if rel not in targets:
            findings.append(
                {
                    "rule": "readme-entry-missing",
                    "path": "README.md",
                    "line": 0,
                    "message": f"README.md does not link {rel}",
                }
            )


def validate_repo(root: Path) -> dict[str, Any]:
    """Run all checks on a repository root and return a structured report."""
    findings: list[dict[str, Any]] = []
    examples_checked = 0
    skills_dir = root / "skills"
    agents_dir = root / "agents"

    skill_files = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []
    agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []

    if not skill_files:
        findings.append(
            {
                "rule": "missing-skills",
                "path": "skills",
                "line": 0,
                "message": "no skills/*/SKILL.md files found",
            }
        )

    for skill_file in skill_files:
        rel_path = str(skill_file.relative_to(root))
        folder_slug = skill_file.parent.name
        text = skill_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if meta is None:
            findings.append(
                {
                    "rule": "frontmatter-invalid",
                    "path": rel_path,
                    "line": 1,
                    "message": "missing or malformed YAML frontmatter",
                }
            )
        else:
            name = meta.get("name", "")
            desc = meta.get("description", "")
            if not SLUG_RE.match(name):
                findings.append(
                    {
                        "rule": "skill-name-format",
                        "path": rel_path,
                        "line": 2,
                        "message": f"invalid skill name '{name}'; expected lowercase kebab-case",
                    }
                )
            if name != folder_slug:
                findings.append(
                    {
                        "rule": "skill-name-mismatch",
                        "path": rel_path,
                        "line": 2,
                        "message": f"frontmatter name '{name}' does not match folder '{folder_slug}'",
                    }
                )
            if len(desc) < 25:
                findings.append(
                    {
                        "rule": "skill-description-short",
                        "path": rel_path,
                        "line": 3,
                        "message": "description must clearly state when the skill applies (at least 25 chars)",
                    }
                )
            for heading in REQUIRED_SKILL_SECTIONS:
                if heading not in body:
                    findings.append(
                        {
                            "rule": "skill-section-missing",
                            "path": rel_path,
                            "line": 1,
                            "message": f"missing required section '{heading}'",
                        }
                    )
        check_markdown_text(rel_path, text, findings)
        check_local_links(root, skill_file, text, findings)
        examples_checked += check_examples(root, skill_file.parent, findings)

    for agent_file in agent_files:
        rel_path = str(agent_file.relative_to(root))
        stem = agent_file.stem
        text = agent_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        if meta is None:
            findings.append(
                {
                    "rule": "frontmatter-invalid",
                    "path": rel_path,
                    "line": 1,
                    "message": "missing or malformed YAML frontmatter",
                }
            )
        else:
            name = meta.get("name", "")
            desc = meta.get("description", "")
            tools = meta.get("tools", "")
            if name != stem or not SLUG_RE.match(name):
                findings.append(
                    {
                        "rule": "agent-name-mismatch",
                        "path": rel_path,
                        "line": 2,
                        "message": f"agent frontmatter name '{name}' must match filename stem '{stem}'",
                    }
                )
            if len(desc) < 20:
                findings.append(
                    {
                        "rule": "agent-description-short",
                        "path": rel_path,
                        "line": 3,
                        "message": "agent description must be at least 20 chars",
                    }
                )
            if not tools.strip():
                findings.append(
                    {
                        "rule": "agent-tools-missing",
                        "path": rel_path,
                        "line": 4,
                        "message": "agent frontmatter must declare 'tools'",
                    }
                )
        check_markdown_text(rel_path, text, findings)
        check_local_links(root, agent_file, text, findings)

    for doc_name in ("README.md", "METHODOLOGY.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md"):
        doc_path = root / doc_name
        if doc_path.is_file():
            text = doc_path.read_text(encoding="utf-8")
            check_markdown_text(doc_name, text, findings)
            check_local_links(root, doc_path, text, findings)

    check_readme_index(root, skill_files, agent_files, findings)

    return {
        "root": str(root),
        "skills_checked": len(skill_files),
        "agents_checked": len(agent_files),
        "examples_checked": examples_checked,
        "findings": findings,
        "ok": len(findings) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="Validate Agent Skills, subagent specs, reference examples, local links, and prose rules.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root directory (default: parent of scripts/).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"validate.py {__version__}",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: root directory does not exist: {root}", file=sys.stderr)
        return 2

    report = validate_repo(root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["findings"]:
            print(f"FAIL [{item['rule']}] {item['path']}:{item['line']}: {item['message']}")
        if report["ok"]:
            print(
                f"PASS: {report['skills_checked']} skills and "
                f"{report['agents_checked']} agents validated with 0 findings "
                f"({report['examples_checked']} reference examples parsed)"
            )
        else:
            print(f"FAIL: {len(report['findings'])} finding(s) in {root}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
