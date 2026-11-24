---
name: idempotent-external-writes
description: "Use when building or reviewing any job, script, or agent workflow that writes to an external system with financial or customer-visible side effects: accounting APIs (QuickBooks, Xero, Stripe), ERP updates, billing emails, Drive/S3 archives, or payment execution."
---

# Idempotent External Writes

## The failure mode

Unprotected background jobs fail in two costly ways when calling external APIs:

1. A job times out after the remote API accepted the write, then the runner auto-retries and creates duplicate invoices, bills, emails, or charges.
2. A partial multi-step pipeline (create invoice -> send email -> archive PDF -> tag ERP order) crashes mid-way and leaves systems permanently out of sync with no record of which side effects already landed.

Separating execution from judgment prevents both. Every external side effect gets a deterministic key recorded in your own database before the remote API call runs, and write jobs never blind-retry.

## Core rules

1. **Journal before write.** Insert a row into an append-only write journal with a deterministic `idempotency_key` before calling the external API. Never rely solely on an in-memory set or log file.
2. **Disable blind retries on write jobs.** Set `maxAttempts = 1` (or equivalent zero-retry config) on every job that mutates external state. Read-only ingestion feeds may retry; write jobs must reconcile instead of blindly replaying.
3. **Verify unconfirmed keys before acting.** If a prior run left a journal row in `pending` state (crash between insert and confirmation), query the external API by deterministic reference or memo before deciding whether to write or mark confirmed.
4. **Confirm via API read-back.** After creating or updating an external record, read the record back (or verify the returned immutable ID, line count, and total) before marking the journal row `confirmed`.
5. **Isolate each side effect.** In a multi-step pipeline (invoice, email, PDF archive, ERP tag, tracker row), give each step its own deterministic key derived from `(workflow, source_entity_id, step_name)`. Re-running after a partial failure completes only the unfinished steps.
6. **Build switched off.** Every new write job ships with its execution switch set to off in config or database state. Prove dry-run output against real production reads before enabling live writes.

## Step-by-step protocol

### 1. Define the write journal schema

Keep one append-only Postgres table (or equivalent durable store) owning every external write key:

```sql
CREATE TABLE external_writes (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  idempotency_key   text NOT NULL UNIQUE,
  workflow          text NOT NULL,
  target_system     text NOT NULL,
  source_entity_id  text NOT NULL,
  step_name         text NOT NULL,
  status            text NOT NULL CHECK (status IN ('pending', 'confirmed', 'failed', 'held')),
  external_id       text,
  payload_sha256    text NOT NULL,
  error_summary     text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  confirmed_at      timestamptz
);
```

### 2. Construct deterministic keys from immutable source facts

Never include timestamps, random UUIDs, or run IDs inside an idempotency key. Key on the immutable business identity:

```text
invoice:qbo:{entity_code}:{erp_order_id}:create
invoice:email:{entity_code}:{erp_order_id}:send
invoice:archive:{entity_code}:{erp_order_id}:pdf
invoice:erp:{entity_code}:{erp_order_id}:tag_invoiced
```

For split orders or partial shipments, include the immutable shipment or document sequence number (`{erp_order_id}:{shipment_seq}`).

### 3. Execute the three-phase write cycle

1. **Claim:** Attempt `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id`.
   - If inserted: proceed to remote call.
   - If conflict and existing row is `confirmed`: skip cleanly and log as already completed.
   - If conflict and existing row is `pending`: query the target system by external reference first. If the object exists remotely, record its `external_id` and update status to `confirmed`. If it genuinely does not exist, escalate or require explicit reconciliation rather than blindly inserting a second time.
   - If conflict and `payload_sha256` differs from the stored hash: stop and hold for human review (source data changed after an earlier attempt).
2. **Call and read back:** Call the external API. Verify the returned ID and key totals match the planned payload.
3. **Confirm:** Update the journal row to `confirmed` with `external_id` and `confirmed_at = now()`.

### 4. Enforce safe dry-run mode

Run the exact same code path with a read-only adapter that computes every key, validates every payload, checks existing journal rows, and emits the exact planned write list without calling mutating endpoints.

## Verification checklist

- Re-running the same input batch twice produces zero duplicate external records and logs every second-pass key as already confirmed.
- Simulated crash after the remote write (before DB confirmation) leaves a `pending` row that the next run reconciles by querying the remote API without creating a duplicate.
- Simulated payload drift on an existing key raises a hold instead of silently overwriting.
- Job configuration explicitly sets `maxAttempts = 1` (or zero automatic retries) on write tasks.
- Dry-run mode passes against real production inputs before any live switch is turned on.

## Boundaries

- Do not use this pattern for read-only ingestion or pure cache refreshes, where standard idempotent upserts and exponential backoff retries are simpler.
- Do not store raw secrets, bank account numbers, or full customer PII inside `error_summary` or journal logs.
