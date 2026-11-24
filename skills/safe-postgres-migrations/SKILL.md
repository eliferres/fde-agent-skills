---
name: safe-postgres-migrations
description: "Use when writing, reviewing, or applying Postgres or Supabase SQL migrations, RLS policies, database roles, grants, or schema changes that touch production data."
---

# Safe Postgres Migrations

## The failure mode

Database migrations in fast-moving teams fail in four predictable ways:

1. A destructive or reshaping statement (`DROP`, `TRUNCATE`, column type change, or `CREATE OR REPLACE` altering behavior) lands unnoticed inside a routine feature PR with no backup or rollback path.
2. An undo script is written on paper and never executed, then fails during an incident because it needs superuser privileges or leaves broken grants, triggers, or policies behind.
3. A migration embeds `BEGIN` / `COMMIT`, breaking the migration runner's transaction boundary.
4. Sensitive tables or financial columns leak through overly broad roles, missing Row-Level Security (RLS), or `SECURITY DEFINER` functions without pinned `search_path`.

Every schema change should be parsed mechanically, paired with a tested undo script, proven on an empty non-superuser database, and applied to staging before live.

## Core rules

1. **Pair every migration with an undo file.** Every new file in `migrations/<timestamp>_<name>.sql` ships with a matching `undo/<timestamp>_<name>.sql` in the same pull request.
2. **Classify statements with a real SQL parser.** Parse migrations with Postgres's own grammar (for example `pglast`, not brittle regexes) to classify three dimensions:
   - **Deletes or reshapes:** `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `ALTER TABLE ... DROP/TYPE`, `CREATE OR REPLACE`.
   - **Access changes:** `GRANT`, `REVOKE`, `CREATE POLICY`, `ALTER POLICY`, `CREATE ROLE`, `ALTER ROLE`, `ENABLE/DISABLE ROW LEVEL SECURITY`.
   - **Replacements:** Replacing views, functions, or triggers that downstream callers depend on.
3. **Require an explicit cleanup header on destructive changes.** Any migration that deletes or reshapes data must open (before the first SQL statement) with a `-- Clean-up:` comment stating where affected data moved, which readers changed, and why the removal is safe.
4. **No top-level transaction control inside files.** Forbid bare `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`, and `START TRANSACTION` in migration and undo files so the apply runner controls the single transaction cleanly.
5. **Prove undo round-trip schema equality without superuser rights.** In CI, spin up an empty database owned by a non-superuser role (matching managed Postgres like Supabase), apply all base migrations, capture `pg_dump --schema-only`, apply the PR's migrations, run their undo scripts in reverse order, capture `pg_dump --schema-only` again, and fail the PR if the two dumps differ by even one line.
6. **Least-privilege roles and server-side redaction.** Create task-scoped roles (read-only feeds, specific write jobs, web reader) instead of sharing an admin login. Enforce row visibility via RLS and strip restricted fields (such as revenue, margin, or salary) inside server-side views or `SECURITY DEFINER` functions with `SET search_path = pg_catalog, public` before any payload leaves the database.
7. **Monotonic migration timestamps.** Allocate migration timestamps through a single locked allocator or timestamp check so parallel branches never collide on migration order.

## Step-by-step protocol

### 1. Migration file header format

For additive-only changes, state the purpose briefly. For any destructive or reshaping change, lead with the required cleanup line:

```sql
-- Clean-up: legacy_orders_temp replaced by core.orders in migration 20261110120000;
-- all readers migrated in PR #142; archive snapshot verified in cold_archive.legacy_orders_temp.

DROP TABLE IF EXISTS staging.legacy_orders_temp;
```

### 2. Write the paired undo file

An undo file must:

- Restore dropped or altered objects, grants, indexes, triggers, and RLS policies cleanly.
- Never reference internal migration history tables (such as `supabase_migrations`) outside comments.
- Execute cleanly under the same non-superuser role used in production.

### 3. Run the three-stage verification gate

1. **Static parse:** Parse both the migration and its undo file; reject syntax errors, forbidden transaction statements, or missing `-- Clean-up:` lines.
2. **Round-trip proof:** Apply base -> dump schema A -> apply new migration(s) -> apply undo(s) newest-first -> dump schema B -> assert `diff(A, B) == empty`.
3. **Staging then live:** Apply to staging first, verify affected views, roles, and live queries, then apply to production through the tested apply command (never ad-hoc console edits).

### 4. Harden access and performance

- Every `SECURITY DEFINER` function explicitly sets `SET search_path = ''` (or pinned schemas) and validates caller role via `auth.uid()` / `current_user`.
- Preserve grants when rebuilding transformed views or dbt models (use in-place replacement patterns instead of `DROP ... CASCADE` that silently wipes permissions).
- In CI test databases with many small queries, consider `SET jit = off` to avoid JIT compilation overhead slowing down SQL test suites.

## Verification checklist

- Every added migration has a matching undo file with the identical filename.
- Static SQL AST check passes with zero unclassified destructive statements and zero top-level transaction blocks.
- Automated `up -> undo` schema diff on a non-superuser Postgres database returns zero differences.
- Any new role has only the minimum required `USAGE`, `SELECT`, `INSERT`, or `UPDATE` grants.
- Any new table exposed to web clients has RLS enabled and tested for both authorized and unauthorized roles.

## Boundaries

- Schema round-trip checks prove structural equality (tables, columns, grants, policies, functions, indexes), not row-level restoration; destructive data migrations still require an explicit pre-change backup or archive table.
- Never run `DROP`, `TRUNCATE`, or bulk `DELETE` against live production without explicit owner confirmation and a verified backup.
