#!/usr/bin/env python3
"""Reference landing check: the approval, the review and the tests must all name the commit that lands.

Standard library only (Python 3.9+). Run it as the last step before a merge to a protected branch:

  check_landing.py --head "$(git rev-parse HEAD)" --owner session-b \
      --approval landing/approval.json --review landing/review.json \
      --tests landing/tests.json --lock landing/merge.lock.json

Record shapes (JSON):
  approval  {"commit": "<40 hex>", "approved_by": "...", "approved_at": "<ISO time>", "scope": "..."}
  review    {"commit": "<40 hex>", "verdict": "SHIP", "must_fix": 0}
  tests     {"commit": "<40 hex>", "status": "green"}
  lock      {"owner": "...", "expires_at": "<ISO time>"}

Exit codes: 0 clear to land, 1 refused (reasons printed), 2 usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_APPROVAL_AGE = dt.timedelta(hours=24)


def _time(value: Any) -> Optional[dt.datetime]:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def check(head: str, owner: str, approval: dict[str, Any], review: dict[str, Any], tests: dict[str, Any],
          lock: dict[str, Any], now: Optional[dt.datetime] = None) -> list[str]:
    """Return every reason the landing must not go ahead. An empty list means clear to land."""
    now = now or dt.datetime.now(dt.timezone.utc)
    problems: list[str] = []
    if not FULL_SHA.match(head):
        return [f"head must be a full 40-character commit id, got {head!r}"]

    for label, record in (("approval", approval), ("review", review), ("tests", tests)):
        commit = str(record.get("commit", ""))
        if not FULL_SHA.match(commit):
            problems.append(f"{label} does not name a full commit id (short ids and branch names do not count)")
        elif commit != head:
            problems.append(f"{label} names {commit[:10]} but the head is {head[:10]}: the head moved, "
                            f"so it needs a new {label}")

    if not str(approval.get("approved_by", "")).strip():
        problems.append("approval has no approver")
    approved_at = _time(approval.get("approved_at"))
    if approved_at is None:
        problems.append("approval has no readable approved_at time")
    elif approved_at > now:
        problems.append("approval is dated in the future")
    elif now - approved_at > MAX_APPROVAL_AGE:
        problems.append("approval is older than 24 hours: ask again")

    if review.get("verdict") != "SHIP":
        problems.append(f"review verdict is {review.get('verdict')!r}, not 'SHIP'")
    if review.get("must_fix", 1) != 0:
        problems.append("review still lists must-fix items")
    if tests.get("status") != "green":
        problems.append(f"tests are {tests.get('status')!r} on this commit, not 'green'")

    expires = _time(lock.get("expires_at"))
    if lock.get("owner") != owner:
        problems.append(f"merge lock is held by {lock.get('owner')!r}, not {owner!r}: one landing at a time")
    elif expires is None or expires <= now:
        problems.append("merge lock has expired: take it again before landing")
    return problems


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refuse a landing unless every record names the exact head commit.")
    ap.add_argument("--head", required=True)
    ap.add_argument("--owner", required=True)
    for name in ("approval", "review", "tests", "lock"):
        ap.add_argument(f"--{name}", type=Path, required=True)
    args = ap.parse_args(argv)
    problems = check(args.head, args.owner, _load(args.approval), _load(args.review), _load(args.tests),
                     _load(args.lock))
    for problem in problems:
        print(f"REFUSED: {problem}")
    if not problems:
        print(f"CLEAR TO LAND: {args.head}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
