# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-24

### Added

- Ten production forward-deployed engineering Agent Skills (`idempotent-external-writes`, `human-in-the-loop-exceptions`, `safe-postgres-migrations`, `financial-reconciliation-discipline`, `safe-spreadsheet-writes`, `fresh-read-only-reviewer`, `two-layer-agent-orchestration`, `upfront-fde-discovery`, `production-job-observability`, and `plain-english-engineering-comms`).
- Five portable read-only and builder subagent specifications (`reviewer`, `scout`, `researcher`, `implementer`, `advisor`).
- End-to-end engineering architecture and methodology guide (`METHODOLOGY.md`).
- Symlink/copy installer script (`scripts/install.sh`) supporting Claude Code, OpenAI Codex / Antigravity, and project-local directories.
- Zero-dependency Python 3.9+ validator (`scripts/validate.py`), `unittest` test suite, and GitHub Actions CI matrix across Linux and macOS.
