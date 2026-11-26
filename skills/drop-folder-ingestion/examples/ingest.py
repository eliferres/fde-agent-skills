#!/usr/bin/env python3
"""Reference drop-folder ingestion: each CSV file is read once by checksum, in name order.

Standard library only (Python 3.9+). The ledger is SQLite here; the same shape works in Postgres.

  ingest.py --folder inbox --db ledger.db --header date,reference,amount --dry-run
  ingest.py --folder inbox --db ledger.db --header date,reference,amount

A file is one of:
  new      first time these exact bytes are seen, and the shape is right
  seen     these exact bytes were loaded before (whatever the file is called now)
  held     the shape is wrong; nothing from the file is loaded
  waiting  an earlier file is held, and order matters, so this one waits

--dry-run prints the counts only and writes nothing. Originals are never moved or deleted.
Exit codes: 0 nothing held, 1 one or more files held, 2 usage error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingested_files (
  sha256      TEXT PRIMARY KEY,
  file_name   TEXT NOT NULL,
  row_count   INTEGER NOT NULL,
  loaded_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ingested_rows (
  sha256   TEXT NOT NULL REFERENCES ingested_files (sha256),
  line_no  INTEGER NOT NULL,
  payload  TEXT NOT NULL,
  PRIMARY KEY (sha256, line_no)
);
"""


@dataclass
class Decision:
    name: str
    sha256: str
    status: str  # new | seen | held | waiting
    reason: str
    rows: list[list[str]]


def check_shape(data: bytes, header: list[str]) -> tuple[list[list[str]], str]:
    """Return (rows, "") when the file has the agreed shape, else ([], reason)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], "not UTF-8 text"
    table = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not table:
        return [], "empty file"
    got = [cell.strip().lower() for cell in table[0]]
    if got != header:
        return [], f"header is {','.join(got)}; expected {','.join(header)}"
    rows = table[1:]
    if not rows:
        return [], "header only, no rows"
    for line_no, row in enumerate(rows, 2):
        if len(row) != len(header):
            return [], f"line {line_no} has {len(row)} columns; expected {len(header)}"
    return rows, ""


def _seen(conn: sqlite3.Connection, digest: str) -> bool:
    try:
        return conn.execute("SELECT 1 FROM ingested_files WHERE sha256 = ?", (digest,)).fetchone() is not None
    except sqlite3.OperationalError:  # no ledger yet (a dry run never creates one)
        return False


def plan(folder: Path, conn: sqlite3.Connection, header: list[str], *, strict_order: bool = True,
         settle_seconds: float = 0.0) -> list[Decision]:
    """Decide what to do with every CSV in the folder. Reads only; writes nothing."""
    decisions: list[Decision] = []
    blocked = False
    for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".csv"):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if _seen(conn, digest):
            decisions.append(Decision(path.name, digest, "seen", "", []))
            continue
        if blocked:
            decisions.append(Decision(path.name, digest, "waiting", "an earlier file is held", []))
            continue
        if settle_seconds and time.time() - path.stat().st_mtime < settle_seconds:
            reason, rows = "still being written (changed in the last few seconds)", []
        else:
            rows, reason = check_shape(data, header)
        if reason:
            decisions.append(Decision(path.name, digest, "held", reason, []))
            blocked = strict_order
        else:
            decisions.append(Decision(path.name, digest, "new", "", rows))
    return decisions


def load(conn: sqlite3.Connection, decision: Decision) -> None:
    """Load one new file: the ledger row and every data row land together or not at all."""
    with conn:
        conn.execute("INSERT INTO ingested_files (sha256, file_name, row_count) VALUES (?, ?, ?)",
                     (decision.sha256, decision.name, len(decision.rows)))
        conn.executemany("INSERT INTO ingested_rows (sha256, line_no, payload) VALUES (?, ?, ?)",
                         [(decision.sha256, n, ",".join(row)) for n, row in enumerate(decision.rows, 2)])


def run(folder: Path, conn: sqlite3.Connection, header: list[str], *, dry_run: bool, strict_order: bool = True,
        settle_seconds: float = 0.0) -> dict[str, int]:
    if not dry_run:
        conn.executescript(SCHEMA)
    decisions = plan(folder, conn, header, strict_order=strict_order, settle_seconds=settle_seconds)
    counts = {"new": 0, "seen": 0, "held": 0, "waiting": 0, "rows": 0}
    for decision in decisions:
        counts[decision.status] += 1
        if decision.status == "new":
            counts["rows"] += len(decision.rows)
            if not dry_run:
                load(conn, decision)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read each dropped CSV once, by checksum, in name order.")
    ap.add_argument("--folder", type=Path, required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--header", required=True, help="Agreed column names, comma separated.")
    ap.add_argument("--dry-run", action="store_true", help="Print counts only; write nothing.")
    ap.add_argument("--any-order", action="store_true", help="Do not make later files wait for a held one.")
    ap.add_argument("--settle-seconds", type=float, default=0.0)
    args = ap.parse_args(argv)
    if not args.folder.is_dir():
        print(f"error: not a folder: {args.folder}", file=sys.stderr)
        return 2
    header = [h.strip().lower() for h in args.header.split(",") if h.strip()]
    if args.dry_run:  # open the ledger read-only when it exists; never create it
        conn = (sqlite3.connect(f"file:{Path(args.db).resolve().as_posix()}?mode=ro", uri=True)
                if Path(args.db).exists() else sqlite3.connect(":memory:"))
    else:
        conn = sqlite3.connect(args.db)
    counts = run(args.folder, conn, header, dry_run=args.dry_run, strict_order=not args.any_order,
                 settle_seconds=args.settle_seconds)
    mode = "DRY RUN (nothing written)" if args.dry_run else "LOADED"
    print(f"{mode}: {counts['new']} new file(s) with {counts['rows']} row(s), {counts['seen']} seen, "
          f"{counts['held']} held, {counts['waiting']} waiting")
    if not args.dry_run or counts["held"]:
        for d in plan(args.folder, conn, header, strict_order=not args.any_order,
                      settle_seconds=args.settle_seconds):
            if d.status in ("held", "waiting"):
                print(f"  {d.status}: {d.name}: {d.reason}")
    return 1 if counts["held"] else 0


if __name__ == "__main__":
    sys.exit(main())
