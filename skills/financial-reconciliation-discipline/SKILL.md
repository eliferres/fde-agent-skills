---
name: financial-reconciliation-discipline
description: "Use when building or auditing financial reports, P&L workbooks, inventory valuations, ad-spend attribution, billing tie-outs, or any data pipeline joining accounting, ERP, e-commerce, bank, and ad platform records."
---

# Financial Reconciliation Discipline

## The failure mode

A financial or operational report that is silently wrong once destroys trust faster than having no report at all. In multi-system businesses, errors almost always enter in the same five places:

1. Joining two systems on free-text names instead of canonical IDs (dropping renamed vendors, trailing spaces, or alternate spellings).
2. Mixing cutoff timestamps across systems (for example warehouse stock pulled Tuesday morning joined against orders pulled Monday night).
3. Treating partial exports as complete (missing secondary ad accounts, unsettled marketplace fees, or unitemized platform charges).
4. Dropping validation failures silently instead of counting and displaying them on the report.
5. Presenting estimates or unverified figures alongside audited numbers without labeling the difference.

Every figure an operator or controller reads must trace back to one named system of record and tie to an independent second source.

## Core rules

1. **Name one system of record per entity before any join.** Before writing SQL or Python, write a short source-of-truth table mapping every entity (items/SKUs, customers, vendors, orders, invoices, payments, inventory counts, ad spend) to exactly one authoritative system and owner. Everything else is a copy. Never average two disagreeing systems or pick whichever looks better today.
2. **Join only through canonical master keys.** Route every cross-system join through a master key table (SKU master, vendor master, account map) linking each system's immutable ID. Never join on display names. Unmapped keys go into an explicit exceptions table for human review, never guessed in code.
3. **Lock one cutoff timestamp across every source.** When reconciling stock, open orders, purchase orders, or cash balances across multiple systems, pull or filter every source to the exact same cutoff timestamp and record that cutoff prominently in the output metadata.
4. **Validate input shape before computing totals.** Check for duplicates, null keys, wrong signs (such as ad spend entered as positive revenue), future dates, missing currencies, and zero-cost bundle/kit lines before aggregating. Display validation failure counts directly in the output; never drop bad rows silently.
5. **Tie every headline total to an independent second source.** Reconcile automated reports against outside ground truth: bank statements, payment processor payouts, accounting ledger totals, or raw platform billing invoices. Document every remaining penny of variance with its root cause.
6. **Audit the full source universe before trusting legacy sheets.** When rebuilding a report, list every active account, store, channel, and fee type from the raw APIs first. Legacy spreadsheets routinely omit newer ad accounts, fee codes, or refund categories.
7. **Separate base cost from landed costs.** In unit economics and costing masters, keep base supplier cost, freight, duties/tariffs, and packaging in separate columns so margin shifts remain diagnosable.
8. **Label unverified figures explicitly.** Mark any figure not yet tied to its primary source as `inference` or `estimated`. Never mix audited actuals and estimates without clear visual separation.

9. **Replicate the prior period's treatment.** Before classifying an item, check how the prior period treated the same kind of item from the same vendor and match it. Only the controller changes a treatment, and every change records a written reason and date.
10. **Flag, never move silently.** When a figure looks wrong, do not reclassify, net, or adjust it quietly. Raise a flag with the evidence and the proposed correction, and leave the books unchanged until a person approves.

## Step-by-step protocol

### 1. Build the system-of-record table

Document this table at the top of the project notes before coding:

| Data domain | System of record | Join key | Refresh cadence | Independent tie-out source |
| --- | --- | --- | --- | --- |
| Orders & gross sales | E-commerce / ERP API | `order_id` | Hourly / daily | Payment processor settlements |
| Accounting P&L & AP | Accounting ledger | `account_id`, `doc_id` | Daily | Bank & corporate card feeds |
| Ad spend | Ad platform billing APIs | `account_id`, `month` | Daily / monthly | Card charges & platform invoices |
| Inventory & kits | Warehouse ERP | `sku`, `kit_bom_id` | Twice daily | Physical counts & receiving logs |

### 2. Run a source completeness sweep

Before calculating margins or net income:

- Enumerate every active store, marketplace, and ad account via API and compare against the accounts currently included in the report.
- Enumerate every fee type or line-item category appearing in raw settlement files and assert 100% map to a defined P&L line (fail or list any unmapped fee type explicitly).
- Audit multi-pack and kit bills of materials against the ERP catalog so bundle COGS never silently defaults to zero or single-unit cost.

### 3. Embed self-checking tie-out tabs and assertions

Every delivered report or pipeline ships with automated tie-out checks:

- **Completeness checks:** Every expected store, channel, and ad account is present for the period.
- **Ledger tie-out:** Report subtotals (gross sales, refunds, fees, ad spend, COGS, net income) equal the source ledger within declared tolerance (typically `$0.00` or `$0.01` rounding).
- **Zero-cost & sign checks:** Flag any sold SKU with zero unit cost, any expense with positive sign, or any negative inventory count.
- **Lineage notes:** Attach source formula or query provenance notes to reconciled cells so any controller can audit how a cell was built in seconds.

### 4. Backtest forecasts against actuals

Before trusting a manual or statistical forecast model, backtest prior forecasts against realized ERP shipments or accounting actuals to expose systematic bias (such as omitted already-shipped orders or spreadsheet sum errors).

### 5. Check treatment against the prior period

This query lists every line whose account differs from the same vendor's account in the prior period. Each row is a flag for the controller, not a change.

```sql
SELECT cur.vendor_id, cur.doc_id, prev.account_id AS prior_account, cur.account_id AS current_account
FROM ledger_lines cur
JOIN LATERAL (
  SELECT p.account_id
  FROM ledger_lines p
  WHERE p.vendor_id = cur.vendor_id AND p.period = '2026-02'
  ORDER BY p.posted_at DESC
  LIMIT 1
) prev ON true
WHERE cur.period = '2026-03' AND cur.account_id <> prev.account_id;
```

## Worked example

This sample output shows a March close for a made-up company where one bill uses a different account than in February, so the report flags it and leaves it alone. Card spend ties to the card statement to the cent.

```text
FLAG 1   Cedar Office Supply, bill 2291, 612.40
         February: Office Supplies. March draft: Equipment.
         Proposed: keep Office Supplies (same items as February). Books unchanged until approved.

TIE-OUT  March card spend: ledger 8,214.55 = card statement 8,214.55 (difference 0.00)
```

## Verification checklist

- System-of-record table is written and agreed before cross-system joins run.
- Zero joins depend on free-text names; all unmapped keys surface in an exceptions tab or list.
- All sources share one documented cutoff timestamp.
- 100% of raw fee types and active ad accounts in the period are mapped or explicitly listed as excluded with a reason.
- Automated tie-out assertions run and pass with exact pass counts recorded (zero silent skips).
- Every remaining variance has a named root cause and owner.

- Every change of treatment from the prior period lists a reason and an approver.
- Every reclassification, netting, or adjustment carries a flag and an approval.

## Boundaries

- Do not alter closed accounting periods or reclassify revenue vs. expense categories without controller or owner sign-off.
- Do not present automated reconciliation outputs as audited GAAP financial statements; state exact source scope and reconciliation date.
