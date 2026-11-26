---
name: source-sweep-before-figures
description: "Use when a plan, report, or message is about to state a figure, count, date, or status: list every system that holds the fact, read each one, and reconcile the answers before the number is written."
---

# Source Sweep Before Figures

## The failure mode

1. A plan states a count from the first system that answers, while a second system holds a different count.
2. A writer pulls a figure from memory or from last month's document and states it as current.
3. Two sources disagree, and the writer picks one or averages them without saying so.

Before you write a figure, sweep every system that holds the fact and settle every difference in the open.

## Core rules

1. **Map the sources first.** For each fact, name the system of record and every other place that holds a copy.
2. **Read every source.** Check every system on the map instead of stopping at the first hit.
3. **Record each read.** Write down the query or screen, the read time, and the value you get.
4. **Treat a difference as a finding.** Explain the difference (timing, scope, or a known gap) or report it as open. Never average values and never pick one silently.
5. **List sources you did not read.** Mark any source you cannot reach as "not read" instead of leaving it out.
6. **Treat memory and old documents as leads.** They tell you where to look. They are not sources for a current figure.

## Step-by-step protocol

### 1. Write the sweep table before any read

List every source that holds the fact and mark which one is the system of record. An empty table with the right rows sets the plan for the sweep.

```markdown
| Fact | Source | Role | Read at | Value | Note |
| --- | --- | --- | --- | --- | --- |
| Open purchase orders | Order system | system of record | | | |
| Open purchase orders | Buyer's tracking sheet | copy | | | |
| Open purchase orders | Warehouse receiving list | copy | | | |
```

### 2. Read each source with the same scope

Apply the same date cut-off and the same definition in every read (here, what counts as "open"). Record each value and its read time in the table.

### 3. Reconcile every difference

For each pair of sources that differs, find the records that explain the gap. Name those records in the table. Leave any gap without an explanation open, and report it as open.

### 4. State the figure with its source and time

```text
Open purchase orders: 42 (order system, read 2 March 09:10).
The buyer's sheet shows 39: three orders raised on 1 March are not yet entered there.
The warehouse list shows 44: it still counts two orders cancelled on 28 February.
```

## Worked example

A planner is about to write "about 40 open purchase orders" in a plan. The sweep reads 42 in the order system, 39 in the buyer's tracking sheet, and 44 in the warehouse receiving list. Tracing the differences finds three orders from 1 March not yet entered in the buyer's tracking sheet and two cancelled orders still on the warehouse receiving list. The plan states 42 with the source and the read time, and lists the two clean-up tasks. The finished sweep table appears below.

```markdown
| Fact | Source | Role | Read at | Value | Note |
| --- | --- | --- | --- | --- | --- |
| Open purchase orders | Order system | system of record | 2 Mar 09:10 | 42 | |
| Open purchase orders | Buyer's tracking sheet | copy | 2 Mar 09:14 | 39 | 3 orders from 1 Mar not entered |
| Open purchase orders | Warehouse receiving list | copy | 2 Mar 09:20 | 44 | 2 cancelled orders still listed |
```

## Verification checklist

- Every figure in the document has a row in a sweep table.
- Every row holds a read time and a value, or says "not read".
- Every difference carries a named explanation, or the document reports it as open.
- The figure in the text matches the system of record value in the table.
- No figure rests on memory or on an earlier document alone.

## Boundaries

- One source is enough for a rough estimate that you label as an estimate.
- The sweep reads sources and does not edit copies. Raise any clean-up work as its own task.
- Money figures require more than a sweep: tie each money figure to an independent second source (see the financial-reconciliation-discipline skill in this library).
