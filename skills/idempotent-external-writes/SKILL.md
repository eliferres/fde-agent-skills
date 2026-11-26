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

7. **Look before create, by every key the record has.** Before creating a remote record, search the target system by each identifier the record carries (your own reference, the document number, and the source order id). Never match by amount alone, because two real records can share an amount.
8. **Hold twins for review.** When the search finds a remote record with the same counterparty, amount, and date that carries no key to tell it apart from the planned record, hold both for a person and create nothing.
9. **Run a daily one-to-one scan.** Once a day, compare the journal with the target system to check that every confirmed key has exactly one remote record. Report lost writes and duplicates.

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

### 5. Run the daily one-to-one scan

The daily scan runs as a read against the journal and the target system. It reports any confirmed key that has zero remote records or more than one.

```sql
-- remote_records is today's read of what the job created in the target system
SELECT w.idempotency_key, count(r.external_id) AS remote_count
FROM external_writes w
LEFT JOIN remote_records r ON r.reference = w.idempotency_key
WHERE w.status = 'confirmed'
GROUP BY w.idempotency_key
HAVING count(r.external_id) <> 1;   -- 0 = lost write, 2 or more = duplicate
```

## Worked example

A job plans an invoice for order SO-1042 at Harbor Cafe, a made-up customer. The first block shows a search that ends in a create because the existing invoice carries a different order id. The second block shows a twin on order SO-1050: the search finds a hand-entered invoice with no order reference on the same day, so the job holds.

```text
Planned: invoice for order SO-1042, Harbor Cafe, 480.00
  search by our key       invoice:SO-1042:create   -> none
  search by order id      SO-1042                  -> none
  same customer + amount                           -> INV-0977, order SO-1039, 480.00
Decision: CREATE. INV-0977 carries another order id. The amount alone is not a match.
```

```text
Planned: invoice for order SO-1050, Harbor Cafe, 480.00
  search by our key       invoice:SO-1050:create   -> none
  search by order id      SO-1050                  -> none
  same customer + amount                           -> INV-0981, no order id, entered by hand, same day
Decision: HOLD BOTH. Nothing separates INV-0981 from the planned invoice. A person decides.
```

## Verification checklist

- Re-running the same input batch twice produces zero duplicate external records and logs every second-pass key as already confirmed.
- Simulated crash after the remote write (before DB confirmation) leaves a `pending` row that the next run reconciles by querying the remote API without creating a duplicate.
- Simulated payload drift on an existing key raises a hold instead of silently overwriting.
- Job configuration explicitly sets `maxAttempts = 1` (or zero automatic retries) on write tasks.
- Dry-run mode passes against real production inputs before any live switch is turned on.

- A planted remote record with the same amount and a different order id does not block the create.
- A planted hand-entered twin with no reference holds the item and creates nothing.
- The daily scan returns zero rows on a clean day and names the `idempotency_key` for a planted duplicate.

## Boundaries

- Do not use this pattern for read-only ingestion or pure cache refreshes, where standard idempotent upserts and exponential backoff retries are simpler.
- Do not store raw secrets, bank account numbers, or full customer PII inside `error_summary` or journal logs.
