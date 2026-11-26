# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-25

### Added

- Eight Agent Skills: `switch-gated-go-live`, `exact-head-approvals`, `source-sweep-before-figures`, `fact-checked-drafts`, `read-only-system-integration`, `drop-folder-ingestion`, `executive-decision-briefs`, and `session-handover-at-limits`.
- One read-only subagent specification: `design-reviewer`.
- Three runnable, standard-library reference examples inside skill folders (`switch_gate.py`, `check_landing.py`, `ingest.py`) with a `unittest` suite (`tests/test_examples.py`).
- Validator rule `readme-entry-missing`: `README.md` must link every skill and every agent.
- Validator rule `example-syntax`: every `skills/*/examples/*.py` file must parse.

### Changed

- The validator report now includes `examples_checked`.
- The installer help text no longer states a fixed number of subagent specs.

## [0.1.0] - 2026-11-24

### Added

- Ten production forward-deployed engineering Agent Skills (`idempotent-external-writes`, `human-in-the-loop-exceptions`, `safe-postgres-migrations`, `financial-reconciliation-discipline`, `safe-spreadsheet-writes`, `fresh-read-only-reviewer`, `two-layer-agent-orchestration`, `upfront-fde-discovery`, `production-job-observability`, and `plain-english-engineering-comms`).
- Five portable read-only and builder subagent specifications (`reviewer`, `scout`, `researcher`, `implementer`, `advisor`).
- End-to-end engineering architecture and methodology guide (`METHODOLOGY.md`).
- Symlink/copy installer script (`scripts/install.sh`) supporting Claude Code, OpenAI Codex / Antigravity, and project-local directories.
- Zero-dependency Python 3.9+ validator (`scripts/validate.py`), `unittest` test suite, and GitHub Actions CI matrix across Linux and macOS.
