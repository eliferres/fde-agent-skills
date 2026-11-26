# fde-agent-skills

Production agent skills, read-only subagent specs, and forward-deployed engineering methodology for Claude Code, OpenAI Codex, Cursor, and Antigravity.

This repository holds eighteen domain-neutral skills and six drop-in subagent specs from live production systems (data warehouses, idempotent accounting automations, Postgres migrations, reconciled financial reporting, go-live control, and parallel agent orchestration). Three skills ship a runnable reference example with tests, and the repository uses zero runtime dependencies with a Python 3.9+ validator tested in CI.

[![ci](https://github.com/eliferres/fde-agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/eliferres/fde-agent-skills/actions/workflows/ci.yml)
![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

## Install in ten seconds

Clone the repository and install every skill into your agent runtime:

```bash
git clone https://github.com/eliferres/fde-agent-skills.git
cd fde-agent-skills

# Preview without touching any files
./scripts/install.sh --target claude --dry-run

# Install skills for Claude Code (~/.claude/skills)
./scripts/install.sh --target claude

# Install skills + subagent specs (~/.claude/skills and ~/.claude/agents)
./scripts/install.sh --target claude --with-agents

# Install skills for OpenAI Codex / Antigravity (~/.agents/skills)
./scripts/install.sh --target agents

# Install into a single repository's .claude/ directory
./scripts/install.sh --target project --dest /path/to/your-repo
```

Use `--mode copy` instead of the default `--mode symlink` if you prefer standalone copies that do not track this checkout.

## Skills included

Every skill follows the open `SKILL.md` format (YAML frontmatter with concrete activation triggers, exact failure modes, rules, step-by-step protocols, SQL/JSON templates, verification checklists, and explicit boundaries).

| Skill | Problem it solves |
| --- | --- |
| [`idempotent-external-writes`](skills/idempotent-external-writes/SKILL.md) | Prevents duplicate invoices, bills, emails, and partial failures using a pre-write Postgres journal, `maxAttempts = 1`, and API read-back confirmation. |
| [`human-in-the-loop-exceptions`](skills/human-in-the-loop-exceptions/SKILL.md) | Routes the uncertain 10% to 15% of automated batches to HMAC-verified approval cards and saves human rulings back as learned rules. |
| [`safe-postgres-migrations`](skills/safe-postgres-migrations/SKILL.md) | Pairs every migration with a tested undo script, AST classification, non-superuser `up -> undo` schema equality checks, least-privilege roles, and RLS redaction. |
| [`financial-reconciliation-discipline`](skills/financial-reconciliation-discipline/SKILL.md) | Enforces one system of record per domain, canonical master-key joins, single cutoff timestamps, source completeness sweeps, and independent second-source tie-outs. |
| [`safe-spreadsheet-writes`](skills/safe-spreadsheet-writes/SKILL.md) | Protects shared Google Sheets with single-writer claims, ID/header lookup, pre-write snapshots, single-field update masks, formula protection, and full post-write cell diffs. |
| [`fresh-read-only-reviewer`](skills/fresh-read-only-reviewer/SKILL.md) | Separates maker from checker with a fresh read-only reviewer that runs real outputs first, reads diffs second, cites exact `file:line` proof, and caps at two rounds. |
| [`two-layer-agent-orchestration`](skills/two-layer-agent-orchestration/SKILL.md) | Scales parallel AI coding sessions using isolated git worktrees and a zero-token `fcntl.flock` CLI for merge locks, monotonic migration timestamps, and compact JSON state. |
| [`upfront-fde-discovery`](skills/upfront-fde-discovery/SKILL.md) | Runs client engagements through Questions -> Plan -> Live: search before asking, one structured discovery sitting, visual-first specs, and build-switched-off delivery. |
| [`production-job-observability`](skills/production-job-observability/SKILL.md) | Replaces silent cron failures with two-transaction run ledgers, dead-man missed-run alerts, database-enforced log redaction, and quiet-day summary suppression. |
| [`plain-english-engineering-comms`](skills/plain-english-engineering-comms/SKILL.md) | Enforces answer-first updates, unmet-work-first status reports, strongest-counter rigor, five-line decision cards, and an anti-AI-filler edit pass. |
| [`switch-gated-go-live`](skills/switch-gated-go-live/SKILL.md) | Splits deploy from go-live with one off-by-default switch per write path that requires a dated approval, a tested undo, a small first run, and a read-back. |
| [`exact-head-approvals`](skills/exact-head-approvals/SKILL.md) | Ties the approval, the review, and the tests to one full commit id and lets one landing through at a time with a merge lock. |
| [`source-sweep-before-figures`](skills/source-sweep-before-figures/SKILL.md) | Reads every system that holds a fact and reconciles the differences before a plan states a figure. |
| [`fact-checked-drafts`](skills/fact-checked-drafts/SKILL.md) | Attaches a claim-and-confidence block to an email or memo draft, works every claim to High, and cuts what cannot be verified. |
| [`read-only-system-integration`](skills/read-only-system-integration/SKILL.md) | Proves a new connection with one read, names the account it reaches, grants least privilege, and keeps writes out of interactive sessions. |
| [`drop-folder-ingestion`](skills/drop-folder-ingestion/SKILL.md) | Reads each dropped file once by checksum in a fixed order, holds any file with the wrong shape, and offers a count-only dry run. |
| [`executive-decision-briefs`](skills/executive-decision-briefs/SKILL.md) | Puts a choice on two pages: options side by side, the cost, what we accept, when the other option wins, and what to confirm. |
| [`session-handover-at-limits`](skills/session-handover-at-limits/SKILL.md) | Saves state, a one-line pickup, and per-thread status so work survives a context, usage, or account limit. |

## Reference examples

Three skills ship a small runnable example in an `examples/` folder inside the skill, and each example uses the Python standard library only and runs in the test suite.

| Example | What it shows |
| --- | --- |
| [`switch_gate.py`](skills/switch-gated-go-live/examples/switch_gate.py) | A switch per write path that fails closed, refuses an incomplete approval, limits the first live run, and turns itself off on a failed read-back. |
| [`check_landing.py`](skills/exact-head-approvals/examples/check_landing.py) | A landing check that refuses unless the approval, the review, the tests and the merge lock all match the head commit. |
| [`ingest.py`](skills/drop-folder-ingestion/examples/ingest.py) | A checksum ledger for dropped CSV files with held and waiting states and a dry run that writes nothing. |

## Subagent templates

Six clean, portable agent specifications live under `agents/` and pair directly with the skills above:

| Agent | Role | Access |
| --- | --- | --- |
| [`reviewer`](agents/reviewer.md) | Independent pre-merge verification (real output first, diff second, evidence-only verdict). | Read-only + tests |
| [`scout`](agents/scout.md) | Fast codebase and log reconnaissance returning exact `file:line` quotes. | Read-only |
| [`researcher`](agents/researcher.md) | Primary-source documentation and API verification with strongest counter. | Read-only + web |
| [`implementer`](agents/implementer.md) | Tightly scoped worktree builder that runs tests and real end-to-end output. | Read + write |
| [`advisor`](agents/advisor.md) | Second opinion on architecture, specs, and root-cause diagnoses. | Read-only |
| [`design-reviewer`](agents/design-reviewer.md) | Fresh-eyes design judge for screens, prototypes, dashboards, and PDFs that checks clarity at a glance, the word ceiling, fidelity to the named reference, and both desktop and phone. | Read-only |

## Where these rules came from

Every skill in this repository comes from real operational scars rather than theory. Over a five-week production engagement for a multi-brand e-commerce group (4 brands, 3 legal entities), these patterns governed:

- **5,085 commits** and **399 merged PRs** with a **0% revert rate** across the first 188 merged PRs.
- **263 Postgres migrations** paired with **138 tested undo scripts** and **18 least-privilege roles**.
- **5 production accounting automations** hitting **105 confirmed external writes** on the first live invoicing run with **0 duplicates across 960 invoices** and **4,093+ automated finance tests**.
- **944 marketplace reconciliation checks**, **65 website P&L checks**, and **351,029 verified spreadsheet cells** with zero off-plan edits.
- **16 of 16 planted reviewer defects caught** in blind empirical evaluation (with 6 of 6 clean controls passing).

Read [`METHODOLOGY.md`](METHODOLOGY.md) for the end-to-end architecture connecting these pieces.

## Validate locally

The repository ships with a zero-dependency Python 3.9+ validator and `unittest` suite that checks YAML frontmatter, required skill sections, reference examples, the README index, internal links, secret patterns, and writing standards:

```bash
python3 scripts/validate.py
python3 scripts/validate.py --json
python3 -m unittest discover -s tests -v
```

Exit codes: `0` clean, `1` validation findings, `2` usage or path error.

## Companion CLI tools

These skills pair with the standalone, zero-dependency CLI tools on [github.com/eliferres](https://github.com/eliferres), including [claude-code-guardrails](https://github.com/eliferres/claude-code-guardrails), [agent-eval-harness](https://github.com/eliferres/agent-eval-harness), [surface-audit](https://github.com/eliferres/surface-audit), [approval-wall](https://github.com/eliferres/approval-wall), [codex-hook-bridge](https://github.com/eliferres/codex-hook-bridge), and [session-continuity](https://github.com/eliferres/session-continuity).

## Limitations

- Skills instruct agents; they are not hard enforcement by themselves. Pair them with mechanical CI checks, database constraints, and deterministic pre-execution hooks for safety-critical boundaries.
- Subagent YAML `tools` lists follow Claude Code conventions and may need light adaptation for other agent runtimes.
- SQL examples target Postgres 15+ (and managed Postgres such as Supabase); syntax for identity columns or `CHECK` regexes differs in MySQL or SQLite.

See [CONTRIBUTING.md](CONTRIBUTING.md) to propose fixes or new skills. Released under the [MIT License](LICENSE).
