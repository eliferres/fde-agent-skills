---
name: upfront-fde-discovery
description: "Use before building any new client automation, internal platform, dashboard, or major feature to align on scope, edge cases, architecture, visual references, and explicit go-live gates in one pass."
---

# Upfront FDE Discovery and Three-Step Delivery

## The failure mode

Forward-deployed engineering engagements stall or ship the wrong thing for three recurring reasons:

1. **Endless back-and-forth chat interrogations:** Asking stakeholders twenty scattered questions across five chat threads guarantees answered questions get lost and asked again a week later.
2. **Building before checking existing truth:** Asking stakeholders facts that already live in the codebase, database, or prior documents wastes executive time and erodes trust.
3. **Shipping silently into live systems:** Merging a new automation that immediately sends customer emails or writes accounting entries before stakeholders verify dry-run output causes irreversible mistakes.

Run every new automation or major feature through three clear stages: **Questions -> Plan -> Live**.

## Core rules

1. **Search before asking.** Before asking a stakeholder any factual question, inspect the repository, database schema, live configs, and prior project notes first. Only ask genuine business-logic or preference decisions that do not exist in any system.
2. **One structured discovery pass per sitting.** When open business questions remain, compile them into one structured, plain-English discovery artifact (short one-sentence questions with concrete context and a default recommendation) so the stakeholder answers everything in a single sitting. File every saved answer back into the project record the same day so an answered question is never asked twice.
3. **One upfront plain-English spec before coding.** For any new product, automation, or major feature, present one concise upfront spec and wait for an explicit typed go-ahead (`start`) before writing code. Skip this gate for small bug fixes, copy tweaks, or work inside an already-approved spec.
4. **Visual-first for anything people see.** For every screen, dashboard, portal view, or customer-facing PDF:
   - Name a real visual reference first (never invent layout grammar from scratch).
   - Sketch the flow or component diagram before prose.
   - Enforce a strict word cap so operator screens stay scannable.
   - Show a clickable prototype on sample data before building full backend wiring.
5. **Build switched off.** Every new automation lands in production with all external write switches set to off. Run dry-run proofs against real production reads, show the exact planned output to the owner, and require a separate explicit sign-off to switch live writes on.

## Step-by-step protocol

### Stage 1: Questions (Discovery)

1. Audit existing systems and write down what is already known vs. genuinely unknown.
2. Draft crisp questions (one sentence ending in `?`, under two lines on a phone) grouped with short factual context ("Why this matters" and "Current system behavior").
3. Omit raw financial totals from shared question headers if the document reaches broad audiences.
4. Capture answers once, store them verbatim in the project spec or state record, and mark each question closed.

### Stage 2: Plan (Upfront Spec)

Deliver one tight spec covering five blocks:

1. **Job and done line:** One sentence on what it does, who uses it, and the concrete end-to-end outcome that proves it works (actual email, live DB row, verified report, or working screen).
2. **Visual reference (if UI or document):** Real reference, flow diagram, and word budget.
3. **Architecture and data:** System of record, idempotency key design, where failures surface (logs and alerts), and exact rollback or undo path.
4. **Risks and edge cases:** Empty state, duplicates, retries, timeouts, concurrent runs, and security or money boundaries.
5. **Open forks and strongest counter:** Any decision fork with a clear recommendation and the strongest argument against it.

Save the approved spec cleanly in `SPEC.md` (or the project record) once the owner gives the explicit go-ahead.

### Stage 3: Live (Dry-Run -> Switch-On)

1. Implement behind an explicit write switch (default `false` in database or config).
2. Run full dry-run against real production read data and inspect actual generated payloads or reports.
3. Pass automated tests and a fresh read-only review.
4. Present a crisp go-live card stating exactly what the job will write or send on its next scheduled run, when that run happens, and how to roll back.
5. Flip the write switch only after explicit owner confirmation, then verify the first real scheduled run end to end.

## Verification checklist

- Zero questions asked that could have been answered by reading the repo or database.
- Every answered discovery question is filed in one canonical record and never resurfaced.
- Upfront spec names concrete end-to-end verification criteria and an explicit undo path.
- Any new UI or PDF names a visual reference and starts from a sample-data prototype.
- New write automations ship switched off and prove dry-run output before live enablement.

## Boundaries

- Do not force a full three-stage ceremony on trivial bug fixes, dependency patches, or one-line config changes.
- A click on a prototype button or casual "looks interesting" is not a go-live approval; require an explicit written confirmation for live write switches and production launches.
