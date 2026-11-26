---
name: two-layer-agent-orchestration
description: "Use when running multiple parallel AI coding agents across a repository or multi-repo platform: separating coordination from execution, isolating git worktrees, and moving locks and state into zero-token local CLIs."
---

# Two-Layer Agent Orchestration

## The failure mode

Running parallel AI agents without structural isolation fails fast:

1. Two agents edit the same branch or working directory and overwrite each other's files.
2. Two parallel branches create SQL migrations with colliding timestamps or merge out of order onto `main`.
3. A coordinator agent burns tens of thousands of tokens relaying status updates, polling workers in loops, or reading multi-megabyte markdown logs just to remember what is open.
4. A long-running coordinator hits context compaction and loses track of active branches and merge order.

Split work cleanly into two layers (one coordinator, isolated worktree builders) and move every mechanical coordination primitive into a zero-token file-locked CLI.

## Core rules

1. **Two layers, clear ownership.**
   - **Layer 1 (Coordinator):** Owns architecture, priority order, milestone specs, go-live calls, and rescuing any task a builder fails twice. Never does bulk file edits across five streams at once.
   - **Layer 2 (Isolated Builders):** Each builder owns one scoped milestone inside its own `git worktree`, executes edits directly, runs targeted tests and real end-to-end output checks, and calls one fresh read-only reviewer before handoff. Never spawn sub-builders for edits the builder can make directly.
2. **One worktree per active stream.** Every parallel build stream runs in an isolated `git worktree` branched from `origin/main`. Never delete a worktree directory while its session is active.
3. **Move mechanical coordination to zero-token local scripts.** Never spend LLM tokens on mutexes, sequence numbers, or status aggregation. Build a small standard-library CLI using OS advisory locks (`fcntl.flock`) and atomic file renames (`os.replace`) for:
   - **Per-repo merge locks** (with automatic TTL expiry, for example 45 minutes, so a crashed session never deadlocks the queue).
   - **Monotonic migration timestamp allocation** (reads existing migrations + lock state and emits the next strictly greater 14-digit timestamp).
   - **File-collision checks** (compares modified files across active worktrees before edits collide).
   - **Compact thread state** (append-safe structured JSON capped under 100 lines per workstream instead of growing multi-megabyte prose logs).
   - **One-screen status board** (prints active workstreams, branch SHAs, open locks, and blocked items in under 40 lines).
4. **Never poll in a loop.** Launch background builds, tests, or worker sessions asynchronously and wait for completion callbacks or notifications instead of burning turns polling status.
5. **Roll over cleanly before context rot.** When the coordinator reaches 2 to 3 compactions, record current state in the compact board, start a fresh coordinator window, and rehydrate from the structured board instead of dragging degraded context forward.
6. **Batch related fixes into one branch.** Group related fixes for a single module or workflow into one coherent branch and one review cycle rather than opening ten micro-PRs that thrash CI minutes.

7. **Approval names the exact commit.** Tie the owner's yes, the review, and the tests to one full commit id. If a rebase or another fix moves the head, run a new review and get a new yes (see the exact-head-approvals skill in this library).
8. **Claim files before editing.** Claim every file or folder a builder will touch before editing. Refuse a second claim on the same path until the first builder releases it or the claim expires.
9. **Write a handover file at a usage limit.** When a session nears a context or usage limit, save its state and a one-line pickup before stopping. See the session-handover-at-limits skill in this library.

## Step-by-step protocol

### 1. Provision isolated worktrees per milestone

```bash
git fetch origin main
git worktree add ../worktrees/feat-invoice-journal -b feat/invoice-journal origin/main
```

Record the workstream in compact JSON state (`workstream`, `branch`, `worktree_path`, `owner`, `status`, `touched_files`, `next_step`).

### 2. Enforce atomic locks via standard-library file locks

```python
import contextlib
import fcntl
import os
from pathlib import Path

@contextlib.contextmanager
def advisory_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
```

Pair every state file write with write-to-temp + `os.replace` inside the lock so concurrent processes never observe half-written JSON.

### 3. Serialize protected merges

Before pushing or merging to `main`:

1. Acquire the per-repo merge lock (`coord merge-acquire --repo <name> --owner <id>`).
2. Rebase or merge latest `origin/main` and confirm green tests + fresh review on the exact head commit.
3. Land the PR / commit after explicit owner approval.
4. Release the merge lock (`coord merge-release --repo <name> --owner <id>`).

### 4. Index decisions without vector-DB overhead

For cross-session organizational memory, index markdown notes and redacted session summaries into a local SQLite FTS5 database using BM25 ranking weighted by recency decay (for example a 60-day half-life). Treat the SQLite file as a rebuildable cache outside git, never as a second source of truth.

### 5. Claim files before editing

Store file claims in the same locked state file as the other coordination records. A claim on a folder covers every file under that folder.

```json
{"claims": [
  {"path": "billing/invoices/", "owner": "session-b", "expires_at": "2026-03-02T14:00:00+00:00"},
  {"path": "reports/returns.sql", "owner": "session-c", "expires_at": "2026-03-02T13:30:00+00:00"}
]}
```

```text
session-d claims billing/invoices/export.py
REFUSED: billing/invoices/ is claimed by session-b until 14:00
```

## Worked example

This sample timeline follows two builder sessions sharing one protected branch across a single morning. When the rebase at 10:45 moves the branch head, the first approval no longer counts.

```text
10:00  session-b claims billing/invoices/ and builds; review says SHIP on commit 4f2a9c1
10:40  the owner approves commit 4f2a9c1
10:45  session-b rebases on main; the head is now 9d1c3e7, so the approval is void
10:50  new review and new tests on 9d1c3e7; new yes at 11:05
11:06  session-b takes the merge lock, lands 9d1c3e7, releases the lock and its claim
11:07  session-c takes the merge lock
```

## Verification checklist

- Every concurrent build stream works in its own `git worktree` on its own branch.
- Zero active workstreams edit overlapping files without an explicit collision check.
- SQL migration timestamps are allocated through a single locked command with zero duplicates across branches.
- Merge lock acquires, rejects concurrent callers, and expires cleanly after TTL on simulated crash.
- Coordinator rehydrates cleanly from the compact board in a fresh window with zero transcript replay.

- The CLI refuses any landing whose head differs from the approved commit.
- The CLI refuses a second claim on a claimed path and releases an expired claim.
- A session that stops at a usage limit leaves a state file with a pickup line.

## Boundaries

- For a single small bug fix or isolated edit, work directly in one branch; do not spin up multi-agent orchestration overhead when one session finishes faster.
- Advisory file locks (`fcntl.flock`) coordinate processes on a single host; for multi-machine CI coordination, back locks with Postgres advisory locks (`pg_advisory_lock`) or GitHub merge queues.
