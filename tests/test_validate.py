"""Tests for scripts/validate.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATE = REPO_ROOT / "scripts" / "validate.py"


def run_validate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_valid_skill(root: Path, slug: str = "demo-skill") -> Path:
    path = root / "skills" / slug / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
name: {slug}
description: "Use when testing validation rules on a realistic minimal skill fixture."
---

# Demo Skill

## The failure mode

Things break without checks.

## Core rules

1. Keep rules explicit.

## Step-by-step protocol

Run step one.

## Worked example

One made-up case.

## Verification checklist

- Output verified.

## Boundaries

- Test fixture only.
""",
        encoding="utf-8",
    )
    return path


class ValidateRepoTests(unittest.TestCase):
    def test_real_repository_passes_cleanly(self) -> None:
        proc = run_validate("--root", str(REPO_ROOT), "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["skills_checked"], 18)
        self.assertEqual(data["agents_checked"], 6)
        self.assertEqual(data["examples_checked"], 3)
        self.assertEqual(data["findings"], [])

    def test_version_flag(self) -> None:
        proc = run_validate("--version")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("validate.py 0.2.0", proc.stdout)

    def test_missing_root_exits_two(self) -> None:
        proc = run_validate("--root", "/nonexistent/path/for/fde-agent-skills-test")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error:", proc.stderr)

    def test_catches_name_mismatch_and_missing_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = write_valid_skill(root, "alpha-skill")
            text = skill.read_text(encoding="utf-8")
            text = text.replace("name: alpha-skill", "name: wrong-skill")
            text = text.replace("## Boundaries", "## Notes")
            skill.write_text(text, encoding="utf-8")

            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            rules = {item["rule"] for item in json.loads(proc.stdout)["findings"]}
            self.assertIn("skill-name-mismatch", rules)
            self.assertIn("skill-section-missing", rules)

    def test_catches_em_dash_and_banned_filler_in_prose_but_not_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = write_valid_skill(root, "prose-skill")
            text = skill.read_text(encoding="utf-8")
            text += "\nThis uses a seamless workflow \u2014 badly.\n"
            skill.write_text(text, encoding="utf-8")

            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            rules = {item["rule"] for item in json.loads(proc.stdout)["findings"]}
            self.assertIn("no-em-en-dash", rules)
            self.assertIn("banned-filler", rules)

    def test_catches_broken_local_link_and_secret_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = write_valid_skill(root, "sec-skill")
            text = skill.read_text(encoding="utf-8")
            fake_secret = "ghp_" + "A" * 24
            text += f"\nSee [missing](../../does-not-exist.md) and `{fake_secret}`.\n"
            skill.write_text(text, encoding="utf-8")

            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            rules = {item["rule"] for item in json.loads(proc.stdout)["findings"]}
            self.assertIn("broken-link", rules)
            self.assertIn("secret-pattern", rules)

    def test_catches_invalid_agent_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_valid_skill(root, "ok-skill")
            agent = root / "agents" / "checker.md"
            agent.parent.mkdir(parents=True, exist_ok=True)
            agent.write_text(
                """---
name: wrong-name
description: "Too short"
---

Body.
""",
                encoding="utf-8",
            )
            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            rules = {item["rule"] for item in json.loads(proc.stdout)["findings"]}
            self.assertIn("agent-name-mismatch", rules)
            self.assertIn("agent-description-short", rules)
            self.assertIn("agent-tools-missing", rules)

    def test_catches_skill_and_agent_missing_from_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_valid_skill(root, "listed-skill")
            write_valid_skill(root, "unlisted-skill")
            agent = root / "agents" / "checker.md"
            agent.parent.mkdir(parents=True, exist_ok=True)
            agent.write_text(
                '---\nname: checker\ndescription: "Read-only checker used as a fixture."\ntools: Read\n---\n\nBody.\n',
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "# Fixture\n\n[listed](skills/listed-skill/SKILL.md)\n", encoding="utf-8"
            )
            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            messages = [i["message"] for i in json.loads(proc.stdout)["findings"] if i["rule"] == "readme-entry-missing"]
            self.assertEqual(len(messages), 2)
            self.assertTrue(any("skills/unlisted-skill/SKILL.md" in m for m in messages))
            self.assertTrue(any("agents/checker.md" in m for m in messages))

    def test_catches_reference_example_that_does_not_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = write_valid_skill(root, "example-skill")
            examples = skill.parent / "examples"
            examples.mkdir()
            (examples / "good.py").write_text("print('ok')\n", encoding="utf-8")
            (examples / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            proc = run_validate("--root", str(root), "--json")
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertEqual(data["examples_checked"], 2)
            self.assertEqual([i["path"] for i in data["findings"]], ["skills/example-skill/examples/broken.py"])


if __name__ == "__main__":
    unittest.main()
