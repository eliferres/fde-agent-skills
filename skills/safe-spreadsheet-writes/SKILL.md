---
name: safe-spreadsheet-writes
description: "Use when any script, automation, or agent writes values, formulas, formatting, notes, or tabs to a live Google Sheet or shared operational workbook."
---

# Safe Spreadsheet Writes

## The failure mode

Automated writes fail when code treats shared spreadsheets like file overwrites.

1. Writing numbers over live formulas breaks downstream totals.
2. A broad `fields` mask wipes formatting, comments, or validation in adjacent columns.
3. Lookups by tab name or column letter (`Column G`) silently hit the wrong cells after a rename or a column insert.
4. Concurrent writers overwrite each other on one workbook with no diff trail.

Treat live spreadsheets like shared production databases: lock the writer, snapshot first, plan target cells, use narrow masks, and diff every cell on read-back.

## Core rules

1. **One active writer at a time.** Claim write ownership for a workbook before modifying it; all other concurrent agents or jobs operate read-only.
2. **Address tabs by numeric sheet ID and columns by header name.** Never hardcode tab names (which humans rename) or column letters (which shift when columns are inserted). Resolve header positions dynamically at runtime and fail closed if a required header is missing or duplicated.
3. **Read narrow ranges only.** Fetch only the named ranges or targeted bounding boxes needed. Never pull an entire multi-tab workbook with full grid formatting into an LLM context window.
4. **Never overwrite a formula with a static value.** Inspect existing formulas before writing. If a target cell contains a formula, keep the formula intact (or require explicit approval in the write plan before replacing it). A planned blank cell is a deliberate change and must appear in the plan explicitly.
5. **Snapshot before every write.** Capture a timestamped full backup snapshot (or named version / copy) of the target workbook before sending any mutating API call so rollback is instant and exact.
6. **Use explicit single-field update masks.** In Google Sheets `batchUpdate` calls, set exact `fields` masks (for example `userEnteredValue` only, or `note` only). Never use `"*"` or wide masks that erase formatting, number styles, or team comments.
7. **Diff every cell after writing.** Read back the affected tabs after the write completes and compare the full grid against the pre-write snapshot plus the approved write plan. Assert **zero off-plan cell changes** (`unexpected_diffs == 0`).
8. **Preserve audit history in cell notes.** When a reconciliation updates a previously published figure, append the prior value, date, and source reason to the cell note rather than silently erasing history.

## Step-by-step protocol

### 1. Build a machine-readable write plan

Before mutating any cell, produce a deterministic JSON plan naming every cell and field that will change:

```json
{
  "spreadsheet_id": "1abc...xyz",
  "cutoff_utc": "2026-11-24T12:00:00Z",
  "planned_writes": [
    {
      "sheet_id": 1048291,
      "header": "Oct 2026 Actual",
      "row_key": "Marketplace Fees",
      "field": "userEnteredValue",
      "old_value": 14200.00,
      "new_value": 15840.50,
      "preserve_formula": false,
      "source": "settlement_export_2026_10"
    }
  ],
  "expected_recalculated_totals": [
    {
      "sheet_id": 1048291,
      "header": "Oct 2026 Actual",
      "row_key": "Total Operating Expenses",
      "formula_preserved": true
    }
  ]
}
```

### 2. Run pre-write safety checks

1. Confirm no other session holds a write claim on the workbook.
2. Snapshot every affected tab (values, formulas, and notes) to local disk or archive storage.
3. Resolve every `(sheet_id, header, row_key)` to concrete coordinates and assert zero ambiguity (no duplicate headers or duplicate row keys).
4. Assert no planned value write targets a cell currently holding a formula unless explicitly flagged in the plan.
5. Present the summary count of planned edits (and any departures from prior structure) for approval before executing on live financial workbooks.

### 3. Execute atomic batch writes

Send updates via structured `batchUpdate` requests using minimal field masks (`userEnteredValue` for values/formulas, `note` for notes). Never mix value writes and broad formatting wipes in the same mask.

### 4. Verify with post-write full-grid diff

Read back every affected tab after the write:

- Every planned cell matches its planned value or formula.
- Every formula cell outside the write plan retains its exact formula string.
- Zero cells outside `planned_writes` (and `expected_recalculated_totals` for formula values) changed between pre-write snapshot and post-write read-back.
- Print the exact verification count (for example `1,280 cells verified, 0 off-plan diffs`).

## Worked example

In this sample run, a job updates two March figures on a shared costing sheet and adds one note that keeps the old value. After the write, the read-back compares every cell on the sheet with the pre-write snapshot to confirm zero off-plan changes.

```text
Plan for sheet 1048291, column "March actual"
  Freight       1,180.00 -> 1,240.00
  Packaging       310.00 ->   295.50
  Note on Freight: "was 1,180.00 until 2 March; carrier invoice 5521"

Read-back: 1,280 cells compared with the snapshot
  2 planned values and 1 planned note changed
  1 total recalculated by its own formula
  0 off-plan changes
```

## Verification checklist

- Pre-write snapshot saved and readable before any API mutation executes.
- Zero tab names or column letters hardcoded in write logic.
- All `batchUpdate` calls specify exact field masks (zero `"*"` masks).
- Post-write diff confirms 100% of planned cells landed and 0 off-plan cells changed.
- Shared sheets designed for human edits clearly label editable vs. view-only tabs and input columns.

## Boundaries

- For local `.xlsx` files on disk, use deterministic workbook libraries and cell diffs rather than cloud Sheets API calls.
- When proposing unapproved edits or questions on a live stakeholder sheet, add a cell note or separate review tab instead of modifying live data cells.
