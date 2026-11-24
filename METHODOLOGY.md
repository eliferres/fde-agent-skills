# Forward-Deployed Engineering Methodology

High-speed AI-assisted software delivery does not come from looser controls. It comes from turning recurring operational mistakes into mechanical checks, isolating execution from review, and keeping human judgment focused on high-stakes ambiguity.

This methodology was distilled from building and operating production internal data platforms, automated bookkeeping pipelines, multi-channel financial reconciliations, and role-scoped web portals under real business deadlines (5,085 commits, 263 database migrations with 138 tested undo scripts, 4,093+ automated finance tests, and 0 reverts across the first 188 merged pull requests in a five-week multi-brand e-commerce engagement).

## 1. Three-step delivery: Questions -> Plan -> Live

Every new automation or internal application passes through three explicit gates:

1. **Questions (Discovery):** Search existing code, schemas, and prior records first. Compile only genuine business-logic unknowns into one structured discovery artifact answered in a single sitting. File answers once so no answered question is ever asked twice.
2. **Plan (Upfront Spec):** Write one plain-English specification naming the concrete done-line, real visual reference (for any UI or report), system of record, idempotency key design, failure modes, rollback path, and strongest counter-argument. Wait for explicit confirmation before building.
3. **Live (Switched Off -> Dry-Run -> Switch-On):** Ship every write automation with its execution switch off by default. Prove dry-run payloads against real production reads, clear automated tests plus a fresh read-only review, and flip writes on only after explicit owner sign-off.

See [`skills/upfront-fde-discovery/SKILL.md`](skills/upfront-fde-discovery/SKILL.md).

## 2. Seven-layer data foundation

Operational data flows in strictly one direction so raw history is never mutated in place and consumer views stay auditable:

```text
External Systems (Storefronts, ERP, Accounting, Banks, Ads, Sheets)
  -> 1. Connection Registry (Vault-backed OAuth & API credentials)
  -> 2. Immutable Raw History (append-only snapshots & CDC feeds)
  -> 3. Reference & Master Mapping (canonical SKU, vendor, account IDs)
  -> 4. Clean Core Views (dbt Core / SQL transformations)
  -> 5. Departmental Marts (Finance, Operations, Inventory, Marketing)
  -> 6. Access & Redaction Layer (Postgres RLS, scoped roles, money redaction)
  -> 7. Consumption Doors (Web Portal, Reconciled Sheets, Read-Only MCP, Jobs)
```

Core invariants:

- Every domain has exactly one system of record before any cross-system join runs.
- Every join runs on canonical master keys, never free-text names.
- Sensitive financial columns are stripped inside the database layer before payloads reach non-finance roles.

See [`skills/financial-reconciliation-discipline/SKILL.md`](skills/financial-reconciliation-discipline/SKILL.md) and [`skills/safe-postgres-migrations/SKILL.md`](skills/safe-postgres-migrations/SKILL.md).

## 3. Four shared primitives behind every production automation

Every scheduled job or operational workflow shares four non-negotiable engineering primitives:

1. **Pre-write idempotency journal:** Every external write logs a deterministic key in Postgres before calling a remote API, disables automatic blind retries (`maxAttempts = 1`), and confirms via API read-back. See [`skills/idempotent-external-writes/SKILL.md`](skills/idempotent-external-writes/SKILL.md).
2. **Unified human-in-the-loop exception router:** Deterministic cases execute automatically; anomalies pause into one queue, surface as HMAC-verified interactive cards, and persist approved rulings as learned rules. See [`skills/human-in-the-loop-exceptions/SKILL.md`](skills/human-in-the-loop-exceptions/SKILL.md).
3. **Database-backed observability and dead-man alerting:** Every job opens and closes a two-transaction run record, enforces zero secrets or currency figures in public status logs via database constraints, alerts on missed schedules and row-count drops, and suppresses routine quiet-day noise. See [`skills/production-job-observability/SKILL.md`](skills/production-job-observability/SKILL.md).
4. **Safe external artifact writes:** Shared spreadsheets and reports follow single-writer claims, ID/header addressing, pre-write snapshots, explicit single-field update masks, and full post-write cell diffs. See [`skills/safe-spreadsheet-writes/SKILL.md`](skills/safe-spreadsheet-writes/SKILL.md).

## 4. Two-layer AI orchestration with zero-token coordination

Parallel AI coding sessions scale cleanly when strategic decisions stay centralized and execution stays isolated:

- **Layer 1 (Coordinator):** Sets priorities, approves milestone specs, resolves cross-stream conflicts, and owns go-live judgment.
- **Layer 2 (Isolated Builders):** Each builder works in its own `git worktree`, runs targeted unit tests and real end-to-end verification directly, and hands off clean commits.
- **Zero-token local coordination:** Mechanical mutexes belong in small standard-library scripts using `fcntl.flock` and atomic file renames (`os.replace`): per-repo merge locks with TTL expiry, strictly monotonic 14-digit SQL migration timestamp allocation, file-collision checks, and compact structured JSON state.
- **Zero-vector session recall:** Index project notes and redacted session summaries in local SQLite FTS5 with BM25 ranking and recency decay. Keep the index outside git as a rebuildable cache.

See [`skills/two-layer-agent-orchestration/SKILL.md`](skills/two-layer-agent-orchestration/SKILL.md).

## 5. Maker is never checker, backed by planted-fault evals

No session approves its own merge:

1. Mechanical CI walls run first (SQL AST migration classification and undo round-trip schema diff, type checking, linting, unit tests, visual baselines, secret scanning).
2. Every non-trivial change runs real end-to-end verification before a fresh, read-only reviewer inspects the output first and the diff second.
3. The reviewer emits an evidence-only verdict (`SHIP`, `FIX THEN SHIP`, or `STOP`) citing exact `file:line` proof or live command output, capped at two rounds.
4. Both static gates and reviewer prompts are benchmarked periodically against planted-fault test suites (in production testing: 16 of 16 planted reviewer defects caught with 6 of 6 clean controls passing, and 13 of 15 planted static rule violations caught with 7 of 7 clean controls passing).

See [`skills/fresh-read-only-reviewer/SKILL.md`](skills/fresh-read-only-reviewer/SKILL.md) and [`agents/reviewer.md`](agents/reviewer.md).

## 6. Communication as an engineering control

Ambiguous updates create operational risk. Every stakeholder update follows plain-English rules: answer first, lead status updates with what is still unmet, state the strongest counter before agreeing, and wrap landings, billing changes, or outward sends in one uniform five-line decision card.

See [`skills/plain-english-engineering-comms/SKILL.md`](skills/plain-english-engineering-comms/SKILL.md).
