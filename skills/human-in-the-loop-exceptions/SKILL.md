---
name: human-in-the-loop-exceptions
description: "Use when designing automated workflows that encounter judgment calls, anomalies, or edge cases: accounting classification, approval queues, Slack or messaging review cards, threshold holds, and learned-rule loops."
---

# Human-in-the-Loop Exception Routing

## The failure mode

Production automations break in two opposite ways when facing edge cases:

1. **Silent guessing:** The code or LLM guesses on an unknown vendor, a 40% price spike, or a split payment and posts garbage into accounting, ERP, or customer systems.
2. **Alert fatigue and amnesia:** The automation stops on every minor variance, dumps raw JSON into chat, and forces a human to answer the same edge case every week because decisions are never stored back as rules.

Automate the deterministic 85% to 90%, route the uncertain 10% to 15% into one structured exception queue, verify every approval cryptographically, and save human rulings as durable rules.

## Core rules

1. **Split deterministic execution from anomaly holds.** Define explicit, numeric hold thresholds up front: unknown entity or SKU, amount variance above threshold (for example >20% against trailing baseline), treatment drift (category changed from prior period), multi-entity ambiguity (for example one deposit covering >15 open invoices), or missing required source field.
2. **Never post to a catch-all bucket.** Refuse to post unknown items to "Uncategorized" or generic fallback codes. Hold them cleanly and keep the rest of the batch moving.
3. **One exception queue across all jobs.** Route holds from every workflow into a single database table and one review surface (such as one private Slack channel plus an internal web queue), not scattered emails or per-job log files.
4. **Authenticate every human decision.** Verify webhook signatures (for example Slack HMAC-SHA256 with timestamp replay protection within 5 minutes) and check the acting user ID against an authorized approver list before applying any state change.
5. **Persist rulings as learned rules.** When a reviewer resolves an exception ("Always classify vendor X as Software Hosting" or "Ignore fee code Y"), offer a one-click option to save the ruling to a `learned_rules` table scoped by entity and key so future runs handle that case deterministically.
6. **Guard against approval-card forgery.** Strip or reject invisible Unicode controls, control characters, and line-drawing borders in untrusted fields before rendering an approval card so external text cannot spoof a button or status line.

## Step-by-step protocol

### 1. Define the exception and learned-rule tables

```sql
CREATE TABLE held_exceptions (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  exception_key   text NOT NULL UNIQUE,
  workflow        text NOT NULL,
  reason_code     text NOT NULL,
  summary         text NOT NULL,
  context_json    jsonb NOT NULL,
  status          text NOT NULL CHECK (status IN ('open', 'approved', 'rejected', 'resolved')),
  decided_by      text,
  decided_at      timestamptz,
  decision_note   text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE learned_rules (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workflow        text NOT NULL,
  match_key       text NOT NULL,
  action_json     jsonb NOT NULL,
  approved_by     text NOT NULL,
  source_hold_id  bigint REFERENCES held_exceptions(id),
  active          boolean NOT NULL DEFAULT true,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workflow, match_key)
);
```

### 2. Evaluate items in strict order

For each item in a batch:

1. Check exact deterministic rules (explicit mappings and active `learned_rules`).
2. Run anomaly guards (variance cap, duplicate window, missing join key, sign check).
3. If clean: proceed to the idempotent write path.
4. If flagged: upsert into `held_exceptions` by `exception_key` (so repeated runs never spam duplicate cards for the same open hold) and continue processing clean items in the batch.

### 3. Render plain-English approval cards

Every approval message sent to a human must fit on one phone screen and answer four questions:

- **What paused:** Plain-English description and exact source identifier.
- **Why it paused:** Exact rule or threshold triggered (for example "Amount is 34% above 90-day vendor average").
- **Proposed action:** Exact target system and field values if approved.
- **Buttons:** `Approve once`, `Approve + save rule`, or `Hold / Skip`.

### 4. Process the callback safely

On webhook receipt:

1. Verify raw request body HMAC signature and reject timestamps older than 5 minutes.
2. Verify the responder ID is authorized for that workflow.
3. Update `held_exceptions` inside a transaction with `WHERE status = 'open'` so double-clicks cannot trigger two executions.
4. If `Approve + save rule` was selected, write to `learned_rules` inside the same transaction.
5. Enqueue the concrete item for execution through the idempotent write path, then update the original card with the final outcome and actor name.

## Verification checklist

- A planted anomaly (for example >20% variance or unmapped vendor) pauses in `held_exceptions` while valid items in the same run complete normally.
- Re-running the job while the exception is still open produces zero duplicate Slack or chat messages.
- An invalid or replayed webhook signature returns HTTP 401 and changes zero rows.
- Double-clicking Approve applies the action at most once.
- Choosing `Approve + save rule` causes the next run with the same key to clear automatically without paging a human.

## Boundaries

- Do not expose sensitive totals, account numbers, or customer PII in public or wide-access channels; route financial holds only to locked, role-scoped channels.
- Never allow a learned rule to bypass hard security, duplicate-write, or permission boundaries.
