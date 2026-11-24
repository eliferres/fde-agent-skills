"""Tests for scripts/install.sh."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL = REPO_ROOT / "scripts" / "install.sh"


def run_install(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALL), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class InstallScriptTests(unittest.TestCase):
    def test_dry_run_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "target"
            proc = run_install("--target", "claude", "--dest", str(dest), "--with-agents", "--dry-run")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertFalse(dest.exists())
            self.assertIn("10 skill(s), 5 agent(s)", proc.stdout)

    def test_symlink_install_and_idempotent_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "claude-home"
            proc1 = run_install("--target", "claude", "--dest", str(dest), "--with-agents")
            self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
            skills_installed = sorted((dest / "skills").iterdir())
            agents_installed = sorted((dest / "agents").iterdir())
            self.assertEqual(len(skills_installed), 10)
            self.assertEqual(len(agents_installed), 5)
            for p in skills_installed:
                self.assertTrue(p.is_symlink())
                self.assertTrue((p / "SKILL.md").is_file())
            for p in agents_installed:
                self.assertTrue(p.is_symlink())
                self.assertTrue(p.is_file())

            # Re-running symlink mode replaces symlinks cleanly.
            proc2 = run_install("--target", "claude", "--dest", str(dest), "--with-agents")
            self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)

    def test_copy_install_to_project_and_refuse_overwrite_real_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dest = Path(tmp) / "sample-repo"
            repo_dest.mkdir()
            proc1 = run_install("--target", "project", "--dest", str(repo_dest), "--mode", "copy")
            self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
            skills_dir = repo_dest / ".claude" / "skills"
            self.assertEqual(len(list(skills_dir.iterdir())), 10)
            for p in skills_dir.iterdir():
                self.assertFalse(p.is_symlink())
                self.assertTrue((p / "SKILL.md").is_file())

            # Re-running copy mode refuses to overwrite non-symlink directories silently.
            proc2 = run_install("--target", "project", "--dest", str(repo_dest), "--mode", "copy")
            self.assertEqual(proc2.returncode, 1)
            self.assertIn("already exists", proc2.stderr)

    def test_project_target_requires_dest(self) -> None:
        proc = run_install("--target", "project")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--dest", proc.stderr)

    def test_missing_option_value_exits_two(self) -> None:
        proc = run_install("--target")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("requires a value", proc.stderr)


if __name__ == "__main__":
    unittest.main()
