---
name: read-only-system-integration
description: "Use when connecting an agent or a job to a new external system (accounting, order management, bank feed, CRM, warehouse): prove the connection with one read, name exactly what it reached, grant least privilege, and allow no writes from an interactive session."
---

# Read-Only System Integration

## The failure mode

1. The connection works, and it points at the wrong account: a sandbox, a second company file, or last year's tenant. Every figure after that is wrong.
2. Someone creates the credential with full access "to save time", and an exploring session can now change live records.
3. A paged read returns the first page only, and the count looks complete.

Connect read-only, prove what the credential reaches with one read, and write the result down before any work depends on it.

## Core rules

1. **Read-only first.** Give the first credential read scopes only. Grant write access later as a separate step for a reviewed job.
2. **Run one proving read.** Fetch the account identity from the system: its name, its environment (live or test), and the last characters of its id.
3. **Tie one count to the screen.** Pick one small count and compare it with what a person sees in the system interface.
4. **Prove the read is complete.** Follow every page and compare the records you fetch with the total the system reports.
5. **Keep secrets in the secret store.** Never place a secret in chat, logs, code, or the connection card.
6. **Sessions do not write.** An interactive session reads only. Writes run through reviewed automation behind a switch.

## Step-by-step protocol

### 1. Ask for the smallest credential

List the read scopes the work needs and ask for those scopes only. Store the credential in the secret store and refer to it by name.

### 2. Run the proving read

Send one first call that asks the system for its identity. Print the answer without the secret.

```text
Connected to: Northwind Supply (live)   account id ends ...7K2Q
Scopes granted: orders.read, items.read
Scopes refused: orders.write (expected)
```

### 3. Tie one count and prove completeness

```text
Open orders, read by API: 3 pages, 214 records fetched, system total 214
Open orders, on screen (checked by R. Okafor, 2 March): 214
```

### 4. Write the connection card

```yaml
system: order management
reached: Northwind Supply (live), account id ends 7K2Q
credential: secret store entry "orders-readonly" (value never recorded here)
scopes: [orders.read, items.read]
write_access: none
proved_on: 2026-03-02
proved_by: one identity read, one count tied to the screen (214 = 214)
limits: 2 requests per second, 100 records per page
owner: R. Okafor
```

### 5. Add write access later, as its own decision

When a job needs write access, request a second credential with the smallest write scope for that job only. Ship the job switched off (see the switch-gated-go-live skill in this library).

## Worked example

An interactive session starts a report on open orders for Northwind Supply. The proving read returns "Northwind Supply (test)", so the session stops because the credential points at the test account. The owner issues a live read-only credential, the next proving read shows "(live)", the open order count ties to the screen at 214, and the connection card above records the result. No figure from the test account reaches a report.

## Verification checklist

- The connection card names the account, the environment, and the id ending.
- The system refuses a write call that uses the credential.
- One count matches the system screen, and a named person checks it.
- The number of records fetched equals the total the system reports.
- The secret appears in no log, no chat message, and no file in the repository.
- No interactive session runs a write.

## Boundaries

- Some systems have no read-only scope. Create a separate user with the lowest role and note that on the connection card.
- The proving read shows what the credential reaches today. Run it again after any credential change.
- This skill covers the connection only. Other skills in this library cover what the job does with the data.
