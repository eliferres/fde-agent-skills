# Contributing

Bug reports, sharper failure-mode examples, and new production-tested skills are welcome.

## Standards for changes

1. Every skill lives at `skills/<kebab-case-name>/SKILL.md` and includes valid YAML frontmatter plus the six required sections (`The failure mode`, `Core rules`, `Step-by-step protocol`, `Worked example`, `Verification checklist`, `Boundaries`).
2. Keep prose concrete, plain, and dry. Avoid em/en dashes, vague hype, or unverified claims.
3. Never include proprietary client names, internal URLs, account IDs, or real credentials.
4. Keep `scripts/validate.py` standard-library only (Python 3.9+) with zero third-party runtime dependencies.

## Run tests before opening a pull request

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```
