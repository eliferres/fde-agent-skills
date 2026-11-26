#!/usr/bin/env python3
"""Reference switch gate: one switch per write path, off unless a dated approval turned it on.

Standard library only (Python 3.9+). The store is SQLite here; the same shape works in Postgres.

  switch_gate.py --db gate.db status
  switch_gate.py --db gate.db status invoice.create invoice.email   # named paths; unknown ones read as off
  switch_gate.py --db gate.db on invoice.create --by "R. Okafor" --date 2026-03-02 \
      --evidence runs/dry-run-0301.txt --undo runbooks/void-invoices.md --first-run-limit 5
  switch_gate.py --db gate.db off invoice.create --by "R. Okafor" --reason "totals drift"

Exit codes: 0 done, 1 refused, 2 usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from typing import Callable, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS write_switches (
  switch_key       TEXT PRIMARY KEY,
  enabled          INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  approved_by      TEXT,
  approved_on      TEXT,
  evidence_ref     TEXT,
  undo_ref         TEXT,
  first_run_limit  INTEGER NOT NULL DEFAULT 0,
  live_runs        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS write_switch_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  switch_key  TEXT NOT NULL,
  action      TEXT NOT NULL CHECK (action IN ('on', 'off')),
  actor       TEXT NOT NULL,
  note        TEXT NOT NULL,
  at          TEXT NOT NULL
);
"""


class Refused(Exception):
    """The approval record is incomplete, so the switch stays off."""


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def is_on(conn: sqlite3.Connection, key: str) -> bool:
    """Fail closed: a missing row, a missing table, or any store error reads as off."""
    try:
        row = conn.execute("SELECT enabled FROM write_switches WHERE switch_key = ?", (key,)).fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0] == 1)


def turn_on(conn: sqlite3.Connection, key: str, *, approved_by: str, approved_on: str,
            evidence_ref: str, undo_ref: str, first_run_limit: int) -> None:
    """Turn one write path on. Every part of the approval must be present."""
    missing = [name for name, value in (("approved_by", approved_by), ("approved_on", approved_on),
                                        ("evidence_ref", evidence_ref), ("undo_ref", undo_ref)) if not value.strip()]
    if missing:
        raise Refused(f"approval is missing: {', '.join(missing)}")
    try:
        dt.date.fromisoformat(approved_on)
    except ValueError as exc:
        raise Refused(f"approved_on must be a date like 2026-03-02, got {approved_on!r}") from exc
    if first_run_limit < 1:
        raise Refused("first_run_limit must be 1 or more: the first live run is a small one")
    with conn:
        conn.execute(
            "INSERT INTO write_switches (switch_key, enabled, approved_by, approved_on, evidence_ref, undo_ref, "
            "first_run_limit, live_runs) VALUES (?, 1, ?, ?, ?, ?, ?, 0) "
            "ON CONFLICT (switch_key) DO UPDATE SET enabled = 1, approved_by = excluded.approved_by, "
            "approved_on = excluded.approved_on, evidence_ref = excluded.evidence_ref, "
            "undo_ref = excluded.undo_ref, first_run_limit = excluded.first_run_limit, live_runs = 0",
            (key, approved_by, approved_on, evidence_ref, undo_ref, first_run_limit))
        _event(conn, key, "on", approved_by, f"approved {approved_on}; evidence {evidence_ref}; undo {undo_ref}")


def turn_off(conn: sqlite3.Connection, key: str, *, actor: str, reason: str) -> None:
    """Turning off needs no approval. It is one step and it always works."""
    with conn:
        conn.execute("INSERT INTO write_switches (switch_key, enabled) VALUES (?, 0) "
                     "ON CONFLICT (switch_key) DO UPDATE SET enabled = 0", (key,))
        _event(conn, key, "off", actor or "unknown", reason or "no reason given")


def _event(conn: sqlite3.Connection, key: str, action: str, actor: str, note: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    conn.execute("INSERT INTO write_switch_events (switch_key, action, actor, note, at) VALUES (?, ?, ?, ?, ?)",
                 (key, action, actor, note, now))


def guarded_write(conn: sqlite3.Connection, key: str, items: Iterable[object],
                  write: Callable[[object], object], read_back: Callable[[object, object], bool]) -> dict[str, int]:
    """Write items through one switch.

    The switch is read before EVERY item, so turning it off stops a run that is already going.
    The first live run stops at first_run_limit. A write whose read-back fails turns the switch off.
    """
    report = {"written": 0, "switch_off": 0, "over_first_run_limit": 0, "read_back_failed": 0}
    row = conn.execute("SELECT first_run_limit, live_runs FROM write_switches WHERE switch_key = ?", (key,)).fetchone()
    limit = row[0] if row and row[1] == 0 else None
    for item in items:
        if not is_on(conn, key):
            report["switch_off"] += 1
            continue
        if limit is not None and report["written"] >= limit:
            report["over_first_run_limit"] += 1
            continue
        result = write(item)
        if not read_back(item, result):
            report["read_back_failed"] += 1
            turn_off(conn, key, actor="guarded_write", reason="read-back did not match the planned write")
            continue
        report["written"] += 1
    if report["written"]:
        with conn:
            conn.execute("UPDATE write_switches SET live_runs = live_runs + 1 WHERE switch_key = ?", (key,))
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One switch per write path, off by default.")
    ap.add_argument("--db", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    status = sub.add_parser("status")
    status.add_argument("keys", nargs="*", help="Write paths to report; a path with no row reads as off.")
    on = sub.add_parser("on")
    on.add_argument("key")
    on.add_argument("--by", required=True)
    on.add_argument("--date", required=True)
    on.add_argument("--evidence", required=True)
    on.add_argument("--undo", required=True)
    on.add_argument("--first-run-limit", type=int, required=True)
    off = sub.add_parser("off")
    off.add_argument("key")
    off.add_argument("--by", required=True)
    off.add_argument("--reason", required=True)
    args = ap.parse_args(argv)
    conn = sqlite3.connect(args.db)
    init(conn)
    if args.cmd == "status":
        rows = conn.execute("SELECT switch_key, enabled, approved_by, approved_on FROM write_switches "
                            "ORDER BY switch_key").fetchall()
        known = {row[0] for row in rows}
        rows += [(key, 0, None, None) for key in args.keys if key not in known]
        for key, enabled, by, on_date in sorted(r for r in rows if not args.keys or r[0] in args.keys):
            print(f"{'ON ' if enabled else 'off'}  {key}" + (f"  (approved by {by} on {on_date})" if enabled else ""))
        if not rows:
            print("no switches recorded: every write path is off")
        return 0
    if args.cmd == "on":
        try:
            turn_on(conn, args.key, approved_by=args.by, approved_on=args.date, evidence_ref=args.evidence,
                    undo_ref=args.undo, first_run_limit=args.first_run_limit)
        except Refused as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        print(f"ON   {args.key}")
        return 0
    turn_off(conn, args.key, actor=args.by, reason=args.reason)
    print(f"off  {args.key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
