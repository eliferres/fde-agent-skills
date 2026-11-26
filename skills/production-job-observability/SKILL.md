---
name: production-job-observability
description: "Use when building or hardening scheduled jobs, ETL feeds, cron tasks, webhooks, or background workers to ensure explicit run ledgers, dead-man missed-run alerts, log redaction, and quiet-day summaries."
---

# Production Job Observability

## The failure mode

Scheduled background jobs rarely fail loudly on day one. Instead, they fail in three silent ways that stay invisible until month-end close:

1. **Silent death:** A cron schedule stops firing, an OAuth token expires, or a worker crashes before reaching its error handler, so zero error alerts fire because the job never ran.
2. **Silent zero-row drift:** An upstream API changes pagination or permissions, the job returns HTTP 200 with 0 rows, marks itself "green," and quietly starves downstream dashboards for weeks.
3. **Alert fatigue and data leaks:** Every healthy run blasts verbose logs into Slack (training stakeholders to mute the channel), or error stack traces dump sensitive financial figures and API credentials into third-party log aggregators.

Treat observability as a database-backed contract: record every run's open and close, enforce sensitive-data redaction at the schema layer, monitor both failures and missed runs, and suppress zero-action noise.

## Core rules

1. **Two-transaction run ledger.** Every scheduled job opens a run record (`open_run`) in its own transaction before doing work, and closes that record (`close_run`) with status, exact counts (`rows_read`, `rows_written`, `rows_held`, `duration_ms`), and a sanitized summary in a second transaction at completion. A run stuck in `running` past its SLA is immediately visible.
2. **Dead-man alerts for missed runs.** Register an expected cadence and due window (`max_gap_minutes`) for every production job in a `job_schedules` table. Run an independent heartbeat check (plus external uptime monitoring such as Sentry or Grafana alerts) that fires when a job misses its window, even if the runner itself never started.
3. **Alert on abnormal row drops and slow runs.** Track expected floor counts or trailing rolling medians per feed. Flag runs that succeed with suspiciously low row counts (for example 0 orders on a weekday) or exceed duration ceilings.
4. **Zero financial figures or secrets in logs.** Enforce redaction mechanically: sanitize exception summaries before persistence, and add a Postgres `CHECK` constraint on run-summary text columns rejecting currency symbols or secret token prefixes where non-finance roles can view job status.
5. **Quiet-day suppression for human summaries.** Record every healthy run in the database and metrics backend, but suppress routine "0 items to process, all good" pings to human chat channels. Page humans only when a job fails, misses its window, surfaces a discrepancy, or requires an explicit approval.
6. **Health checks stay isolated from business logic.** Expose a lightweight `/api/health` endpoint checking database connectivity and critical dependencies without executing heavy queries or exposing internal version details.

7. **Use one meaning for each outcome.** Every job reports one of four outcomes: `good` (did all it should), `partial` (some items done, some held or failed), `failed` (stopped on an error), or `skipped` (ran and found nothing to do, or its switch is off).
8. **Write one step row per step.** Each step of a run writes one row with its outcome and counts. Derive the run's outcome from its steps, and never type it by hand.
9. **Send one run email a day.** Keep per-run pings suppressed and send one daily email with a fixed layout that covers every job and leads with what needs a person. The email arrives every day, so a missing email is itself a signal.

## Step-by-step protocol

### 1. Define the run ledger and schedule contract

```sql
CREATE TABLE job_schedules (
  job_key          text PRIMARY KEY,
  is_enabled       boolean NOT NULL DEFAULT false,
  max_gap_minutes  integer NOT NULL CHECK (max_gap_minutes > 0),
  min_expected_rows integer NOT NULL DEFAULT 0,
  owner_channel    text NOT NULL
);

CREATE TABLE job_runs (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  job_key         text NOT NULL REFERENCES job_schedules(job_key),
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz,
  status          text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
  rows_read       integer NOT NULL DEFAULT 0,
  rows_written    integer NOT NULL DEFAULT 0,
  rows_held       integer NOT NULL DEFAULT 0,
  summary_text    text NOT NULL DEFAULT ''
                  CHECK (summary_text !~ '(\$|sk-|ghp_|gho_|xox[bap]-)')
);
```

### 2. Wrap every job execution in open/close lifecycle hooks

1. Call `open_run(job_key)` and commit immediately so a hard OOM kill or timeout still leaves an audit trail.
2. Execute the workflow using fixed, whitelisted reason codes for any failure summary (never dump raw exception tracebacks containing headers, tokens, or payloads into public status fields).
3. In a `finally` block, call `close_run(run_id, status, counts, sanitized_summary)`.

### 3. Wire three independent alert layers

- **Immediate failure alert:** Fires on `status = 'failed'` or unhandled runner crash.
- **Dead-man heartbeat:** Runs on a separate scheduler (for example every 15 to 30 minutes) and alerts whenever any enabled job has no `succeeded` run within `max_gap_minutes`, or has a `running` row older than its timeout threshold.
- **Live surface monitor:** For customer-facing apps or storefronts, run periodic synthetic checks verifying HTTP 200, expected content markers, and zero unexpected theme or asset regressions.

### 4. Format run summaries for fast operator triage

When a run has actionable output (writes completed, exceptions held, or failures), emit one short plain-English summary with exact counts:

```text
Wholesale invoicing (2026-11-24 08:00 ET): 21 orders processed, 21 invoices confirmed, 0 duplicates, 2 held in review queue.
```

If 0 orders were due and 0 errors occurred, log to `job_runs` and skip human notifications.

### 5. Record steps and derive the run outcome

Add the `outcome` column to `job_runs` and create the `job_run_steps` table to store each step's outcome and counts. Derive each run's outcome from its step rows with one query.

```sql
ALTER TABLE job_runs ADD COLUMN outcome text
  CHECK (outcome IN ('good', 'partial', 'failed', 'skipped'));

CREATE TABLE job_run_steps (
  run_id     bigint NOT NULL REFERENCES job_runs(id),
  step_no    integer NOT NULL,
  step_name  text NOT NULL,
  outcome    text NOT NULL CHECK (outcome IN ('good', 'partial', 'failed', 'skipped')),
  items_in   integer NOT NULL DEFAULT 0,
  items_out  integer NOT NULL DEFAULT 0,
  note       text NOT NULL DEFAULT '',
  PRIMARY KEY (run_id, step_no)
);

SELECT run_id,
       CASE
         WHEN bool_or(outcome = 'failed')   THEN 'failed'
         WHEN bool_or(outcome = 'partial')  THEN 'partial'
         WHEN bool_and(outcome = 'skipped') THEN 'skipped'
         ELSE 'good'
       END AS run_outcome
FROM job_run_steps
GROUP BY run_id;
```

## Worked example

Four made-up jobs ran on 2 March. The daily email leads with the one thing that needs a person and gives each job one line.

```text
Daily run report, 2 March
NEEDS A PERSON: 2 items held in invoicing (see the review queue)

invoicing      partial   21 read, 19 written, 2 held
bank feed      good      140 read, 140 written
vendor bills   skipped   its switch is off
stock sync     failed    step 2 of 4 (fetch counts): the source timed out
```

## Verification checklist

- Every production job opens and closes a `job_runs` row in two separate transactions.
- A simulated hard crash leaves a visible `running` row caught by the dead-man monitor.
- Attempting to write `$1,250` or a token prefix into `summary_text` is rejected by the database check constraint.
- Every enabled job has a configured `max_gap_minutes` row and an active alert rule verified by a test alert.
- Routine zero-action runs log to the database without spamming Slack or email.

- Every job reports one of the same four outcomes (`good`, `partial`, `failed`, or `skipped`).
- Every step of a run writes one row in `job_run_steps`, and the run's outcome equals the outcome derived from its steps.
- The daily email arrives on a quiet day too.

## Boundaries

- Do not route high-frequency debug telemetry into operational Postgres tables; send traces and request-level metrics to dedicated APM or observability backends (Grafana, Sentry, OpenTelemetry).
- Keep alert thresholds calibrated to real business schedules (for example account for weekends, holidays, and quiet hours so off-hours schedules do not cause false alarms).
