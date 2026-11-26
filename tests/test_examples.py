"""Tests for the runnable reference examples that ship inside skill folders."""
from __future__ import annotations

import datetime as dt
import importlib.util
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"


def load_module(skill: str, file_name: str):
    path = SKILLS / skill / "examples" / file_name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


switch_gate = load_module("switch-gated-go-live", "switch_gate.py")
check_landing = load_module("exact-head-approvals", "check_landing.py")
ingest = load_module("drop-folder-ingestion", "ingest.py")

APPROVAL = dict(approved_by="R. Okafor", approved_on="2026-03-02", evidence_ref="runs/dry-run.txt",
                undo_ref="runbooks/void.md", first_run_limit=2)


class SwitchGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        switch_gate.init(self.conn)
        self.sent: list[object] = []

    def write(self, item: object) -> object:
        self.sent.append(item)
        return item

    def test_unknown_switch_and_missing_table_read_as_off(self) -> None:
        self.assertFalse(switch_gate.is_on(self.conn, "invoice.create"))
        self.assertFalse(switch_gate.is_on(sqlite3.connect(":memory:"), "invoice.create"))

    def test_turn_on_refuses_an_incomplete_approval(self) -> None:
        for field, bad in (("approved_by", ""), ("undo_ref", " "), ("evidence_ref", ""), ("approved_on", "March 2"), ("first_run_limit", 0)):
            with self.subTest(field=field), self.assertRaises(switch_gate.Refused):
                switch_gate.turn_on(self.conn, "invoice.create", **{**APPROVAL, field: bad})
        self.assertFalse(switch_gate.is_on(self.conn, "invoice.create"))

    def test_cli_status_reads_an_unrecorded_path_as_off(self) -> None:
        script = SKILLS / "switch-gated-go-live" / "examples" / "switch_gate.py"
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "gate.db")
            base = [sys.executable, str(script), "--db", db]
            on = subprocess.run([*base, "on", "invoice.create", "--by", "R. Okafor", "--date", "2026-03-02",
                                 "--evidence", "runs/dry-run.txt", "--undo", "runbooks/void.md",
                                 "--first-run-limit", "5"], capture_output=True, text=True, check=False)
            self.assertEqual(on.returncode, 0, on.stderr)
            out = subprocess.run([*base, "status", "invoice.create", "invoice.email"],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(out.stdout.splitlines(), ["ON   invoice.create  (approved by R. Okafor on 2026-03-02)",
                                                   "off  invoice.email"])

    def test_switch_is_per_write_path(self) -> None:
        switch_gate.turn_on(self.conn, "invoice.create", **APPROVAL)
        self.assertTrue(switch_gate.is_on(self.conn, "invoice.create"))
        self.assertFalse(switch_gate.is_on(self.conn, "invoice.email"))

    def test_off_switch_writes_nothing(self) -> None:
        report = switch_gate.guarded_write(self.conn, "invoice.create", [1, 2, 3], self.write, lambda i, r: True)
        self.assertEqual(self.sent, [])
        self.assertEqual(report["switch_off"], 3)

    def test_first_live_run_stops_at_the_limit_and_later_runs_do_not(self) -> None:
        switch_gate.turn_on(self.conn, "invoice.create", **APPROVAL)
        first = switch_gate.guarded_write(self.conn, "invoice.create", [1, 2, 3, 4], self.write, lambda i, r: True)
        self.assertEqual((first["written"], first["over_first_run_limit"]), (2, 2))
        second = switch_gate.guarded_write(self.conn, "invoice.create", [3, 4, 5], self.write, lambda i, r: True)
        self.assertEqual(second["written"], 3)

    def test_turning_off_mid_run_stops_the_rest(self) -> None:
        switch_gate.turn_on(self.conn, "invoice.create", **{**APPROVAL, "first_run_limit": 10})

        def write_then_trip(item: object) -> object:
            self.sent.append(item)
            if item == 2:
                switch_gate.turn_off(self.conn, "invoice.create", actor="on-call", reason="stop")
            return item

        report = switch_gate.guarded_write(self.conn, "invoice.create", [1, 2, 3, 4], write_then_trip, lambda i, r: True)
        self.assertEqual(self.sent, [1, 2])
        self.assertEqual((report["written"], report["switch_off"]), (2, 2))

    def test_failed_read_back_turns_the_switch_off_and_leaves_an_event(self) -> None:
        switch_gate.turn_on(self.conn, "invoice.create", **{**APPROVAL, "first_run_limit": 10})
        report = switch_gate.guarded_write(self.conn, "invoice.create", [1, 2, 3], self.write, lambda i, r: i != 2)
        self.assertEqual((report["written"], report["read_back_failed"], report["switch_off"]), (1, 1, 1))
        self.assertFalse(switch_gate.is_on(self.conn, "invoice.create"))
        actions = [row[0] for row in self.conn.execute("SELECT action FROM write_switch_events ORDER BY id")]
        self.assertEqual(actions, ["on", "off"])


HEAD = "a" * 40
NOW = dt.datetime(2026, 3, 2, 12, 0, tzinfo=dt.timezone.utc)


def landing(**changes: object) -> dict:
    records = {
        "approval": {"commit": HEAD, "approved_by": "R. Okafor", "approved_at": "2026-03-02T11:30:00+00:00"},
        "review": {"commit": HEAD, "verdict": "SHIP", "must_fix": 0},
        "tests": {"commit": HEAD, "status": "green"},
        "lock": {"owner": "session-b", "expires_at": "2026-03-02T12:10:00+00:00"},
    }
    for dotted, value in changes.items():
        record, key = dotted.split("__")
        records[record][key] = value
    return records


def problems(head: str = HEAD, **changes: object) -> list[str]:
    return check_landing.check(head, "session-b", now=NOW, **landing(**changes))


class CheckLandingTests(unittest.TestCase):
    def test_matching_records_are_clear_to_land(self) -> None:
        self.assertEqual(problems(), [])

    def test_a_moved_head_voids_approval_review_and_tests(self) -> None:
        found = problems(head="b" * 40)
        self.assertEqual(len(found), 3)
        self.assertTrue(all("head moved" in p for p in found))

    def test_short_ids_and_branch_names_do_not_count(self) -> None:
        self.assertTrue(any("full commit id" in p for p in problems(approval__commit="aaaaaaa")))
        self.assertTrue(any("full 40-character" in p for p in problems(head="main")))

    def test_each_single_fault_is_refused(self) -> None:
        cases = {
            "approval__approved_by": " ",
            "approval__approved_at": "2026-02-27T11:30:00+00:00",
            "review__verdict": "FIX THEN SHIP",
            "review__must_fix": 1,
            "tests__status": "red",
            "lock__owner": "session-a",
            "lock__expires_at": "2026-03-02T11:59:00+00:00",
        }
        for dotted, value in cases.items():
            with self.subTest(case=dotted):
                self.assertEqual(len(problems(**{dotted: value})), 1)

    def test_cli_refuses_when_a_record_file_is_missing(self) -> None:
        script = SKILLS / "exact-head-approvals" / "examples" / "check_landing.py"
        out = subprocess.run([sys.executable, str(script), "--head", HEAD, "--owner", "session-b", "--approval",
                              "none.json", "--review", "none.json", "--tests", "none.json", "--lock", "none.json"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 1)
        self.assertIn("REFUSED", out.stdout)


HEADER = ["date", "reference", "amount"]
GOOD = "date,reference,amount\n2026-03-01,INV-1001,120.00\n2026-03-01,INV-1002,75.50\n"


class IngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.conn = sqlite3.connect(":memory:")

    def drop(self, name: str, text: str) -> None:
        (self.folder / name).write_text(text, encoding="utf-8")

    def run_ingest(self, **kwargs: object) -> dict:
        return ingest.run(self.folder, self.conn, HEADER, **{"dry_run": False, **kwargs})

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def test_dry_run_counts_and_writes_nothing(self) -> None:
        self.drop("2026-03-01.csv", GOOD)
        counts = self.run_ingest(dry_run=True)
        self.assertEqual((counts["new"], counts["rows"]), (1, 2))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0], 0)
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["2026-03-01.csv"])

    def test_a_file_is_loaded_once_even_when_renamed(self) -> None:
        self.drop("2026-03-01.csv", GOOD)
        self.assertEqual(self.run_ingest()["new"], 1)
        self.drop("copy of 2026-03-01.csv", GOOD)
        again = self.run_ingest()
        self.assertEqual((again["new"], again["seen"]), (0, 2))
        self.assertEqual(self.count("ingested_rows"), 2)

    def test_wrong_shapes_are_held_whole(self) -> None:
        shapes = {
            "wrong header": "date,ref,amount\n2026-03-01,INV-1,1.00\n",
            "ragged row": GOOD + "2026-03-01,INV-1003\n",
            "header only": "date,reference,amount\n",
            "empty": "",
        }
        for label, text in shapes.items():
            with self.subTest(shape=label):
                rows, reason = ingest.check_shape(text.encode("utf-8"), HEADER)
                self.assertEqual(rows, [])
                self.assertTrue(reason)
        self.drop("2026-03-02.csv", shapes["ragged row"])
        self.assertEqual(self.run_ingest()["held"], 1)
        self.assertEqual(self.count("ingested_rows"), 0)

    def test_later_files_wait_for_a_held_one_unless_order_is_free(self) -> None:
        self.drop("2026-03-01.csv", "bad,header\n1,2\n")
        self.drop("2026-03-02.csv", GOOD)
        strict = self.run_ingest()
        self.assertEqual((strict["held"], strict["waiting"], strict["new"]), (1, 1, 0))
        free = self.run_ingest(strict_order=False)
        self.assertEqual((free["held"], free["new"]), (1, 1))

    def test_a_file_still_being_written_is_held(self) -> None:
        self.drop("2026-03-01.csv", GOOD)
        self.assertEqual(self.run_ingest(settle_seconds=3600)["held"], 1)

    def test_cli_exit_code_reports_a_held_file(self) -> None:
        self.drop("2026-03-01.csv", "bad\n1\n")
        script = SKILLS / "drop-folder-ingestion" / "examples" / "ingest.py"
        out = subprocess.run([sys.executable, str(script), "--folder", str(self.folder), "--db",
                              str(self.folder / "ledger.db"), "--header", "date,reference,amount", "--dry-run"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 1)
        self.assertIn("DRY RUN (nothing written)", out.stdout)
        self.assertFalse((self.folder / "ledger.db").exists())


if __name__ == "__main__":
    unittest.main()
