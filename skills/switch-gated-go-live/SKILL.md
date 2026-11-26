---
name: switch-gated-go-live
description: "Use when shipping or reviewing any job, automation, or agent workflow that will write to a live system (invoices, emails, orders, payments, records): give every write path its own switch, ship it off, and turn it on only with a dated approval, a tested undo, and a read-back."
---

# Switch-Gated Go-Live

## The failure mode

Live writes fail in three ways:

1. The deploy is the go-live. Code that merges starts writing to live systems the same hour.
2. One global "live" flag turns every write on at once. A team that wants invoices also gets emails.
3. Weeks later, nobody can say who approved the switch-on, on what evidence, or how to undo it.

Split deploying code from turning a write on: give each write path its own switch, and leave each switch off until a person signs a dated approval.

## Core rules

1. **One switch per write path.** A job that creates invoices and sends emails uses two switches (`invoice.create` and `invoice.email`). Never use one global flag.
2. **Off is the default.** A missing row, an unknown value, or a store the job cannot read all mean off (fail closed).
3. **Data, not code.** Store every switch in data, not in code. Turning a switch on or off needs no deploy and leaves an event row behind.
4. **Dated approval required.** A dated approval turns a switch on and records the approver, the date, the evidence (the dry-run output they saw), the undo, and the first-run limit. If any part is missing, the switch stays off.
5. **Read at every write.** Read the switch at the moment of each write, not once at start-up. Turning a switch off stops a run that is already going.
6. **Small, verified first run.** Write a few records on the first live run, read each one back from the target system, and compare it to the plan.
7. **One-step off.** Turning a switch off takes one step and needs no approval. Test the off step before the first switch-on.

## Step-by-step protocol

### 1. Store the switches as data

Keep one table for switches and one append-only table for switch events. Set the default of `enabled` to `false` so every new switch starts off.

```sql
CREATE TABLE write_switches (
  switch_key       text PRIMARY KEY,              -- one per write path: 'invoice.create'
  enabled          boolean NOT NULL DEFAULT false,
  approved_by      text,
  approved_on      date,
  evidence_ref     text,                          -- the dry-run output the approver saw
  undo_ref         text,                          -- the tested undo runbook or script
  first_run_limit  integer NOT NULL DEFAULT 0,
  live_runs        integer NOT NULL DEFAULT 0
);

CREATE TABLE write_switch_events (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  switch_key  text NOT NULL,
  action      text NOT NULL CHECK (action IN ('on', 'off')),
  actor       text NOT NULL,
  note        text NOT NULL,
  at          timestamptz NOT NULL DEFAULT now()
);
```

### 2. Build and prove the write with the switch off

With the switch off, the job runs the same code path, plans every write, and prints the plan as a dry run. Run the dry run against real reads. Save the dry-run output as the evidence for the approval.

### 3. Record the approval and turn the switch on

The approver reviews the dry-run output and the undo, then gives approval. The command refuses to turn the switch on if any required field is missing.

```bash
python3 examples/switch_gate.py --db gate.db on invoice.create \
  --by "R. Okafor" --date 2026-03-02 \
  --evidence runs/dry-run-0301.txt --undo runbooks/void-invoices.md \
  --first-run-limit 5
```

### 4. Guard every write

Pass every planned item through one guard function. The guard reads the switch before each item, stops the first live run at the first-run limit, and reads each write back from the target system. If a read-back does not match the plan, the guard turns the switch off.

```python
report = guarded_write(conn, "invoice.create", planned_invoices,
                       write=create_invoice, read_back=invoice_matches_plan)
# {'written': 5, 'switch_off': 0, 'over_first_run_limit': 37, 'read_back_failed': 0}
```

### 5. Turn it off in one step

```bash
python3 examples/switch_gate.py --db gate.db off invoice.create --by "R. Okafor" --reason "totals drift"
```

Turning a switch off needs no approval and takes effect on the next item. Turning the switch on again requires a new dated approval.

## Worked example

Northwind Supply ships a job that creates invoices and emails them, gated by two switches: `invoice.create` and `invoice.email`. On Monday, the dry run plans 42 invoices. The finance lead approves `invoice.create` with a first-run limit of 5. The first live run writes 5 invoices, reads all 5 back, and leaves 37 for the next run, while `invoice.email` stays off until its own approval a week later. After that first approval, the switch status shows:

```text
ON   invoice.create  (approved by R. Okafor on 2026-03-02)
off  invoice.email
```

## Verification checklist

- Confirm that a fresh database with no switch rows writes nothing.
- Confirm that an approval missing an undo, evidence, approver, or date fails and leaves the switch off.
- Confirm that turning on one write path leaves every other path off.
- Confirm that the first live run stops at the first-run limit.
- Confirm that turning the switch off during a run stops the remaining items.
- Confirm that a failed read-back turns the switch off and writes an event row.

The reference example in `examples/switch_gate.py` passes all six checks in the repository test suite.

## Boundaries

- A switch is not a permission system. Keep database roles and API scopes as the hard limit.
- Do not use write switches for read-only jobs or presentation feature flags. A plain config value is enough for those cases.
- A switch does not make a write safe to repeat. Pair it with idempotency keys (see the idempotent-external-writes skill in this library).
