---
name: drop-folder-ingestion
description: "Use when a job ingests files that people or systems drop into a folder, bucket, or inbox (bank exports, vendor reports, CSV feeds): read each file once by checksum, in a fixed order, hold any file with the wrong shape, and offer a count-only dry run."
---

# Drop-Folder Ingestion

## The failure mode

Drop-folder ingestion fails in four common ways:

1. Someone drops the same export twice under a new file name, and the job loads every row twice.
2. A vendor adds a column, and the job loads half of the file before it fails.
3. Files load out of order, so a later balance lands before the earlier one.
4. The job moves or deletes a file it cannot read, and the evidence disappears.

Identify each file by its bytes, check the file shape before loading any row, and record every loaded file in a ledger.

## Core rules

1. **Identity is the checksum.** Identify every file by the SHA-256 checksum of its bytes, never by the file name or modified time.
2. **A ledger owns "seen".** Store one row per checksum with a unique constraint in the ledger table.
3. **Fixed order.** Sort files the same way on every run using a key from the content or file name (such as the period).
4. **Check the shape first.** Verify the header names, column count, encoding, and presence of at least one data row before loading the first row.
5. **Hold the whole file.** Hold any file with the wrong shape alongside a reason, with no partial loads. When order matters, make later files wait until the held file clears.
6. **One file, one transaction.** Write the ledger row and the data rows in one transaction so they land together or not at all.
7. **Never move or delete the original.** Keep the folder as people left it and let the ledger record what happened. Provide a dry run that prints counts only and writes nothing.

## Step-by-step protocol

### 1. Create the ledger

```sql
CREATE TABLE ingested_files (
  sha256      text PRIMARY KEY,
  file_name   text NOT NULL,
  row_count   integer NOT NULL,
  loaded_at   timestamptz NOT NULL DEFAULT now()
);
```

### 2. Agree the shape in writing

Write the expected header down as a contract with the file producer. The job compares every file header to that contract exactly.

```text
date,reference,amount
```

### 3. Run the dry run and read the counts

```bash
python3 examples/ingest.py --folder inbox --db ledger.db --header date,reference,amount --dry-run
```

The dry run reports how many files are new, seen, held, and waiting, along with how many rows will load. It writes nothing and does not create the ledger.

### 4. Load

```bash
python3 examples/ingest.py --folder inbox --db ledger.db --header date,reference,amount
```

Each new file loads in one transaction. The command returns exit code 1 when any file is held, so a scheduler can raise an alert.

### 5. Clear a held file

Do not edit the job to accept the bad file. Ask the producer for a corrected file, or agree on a new shape and update the contract. Because the corrected file has new bytes, the job treats it as a new file and loads the waiting files after it.

## Worked example

A team receives a daily bank export in an `inbox` folder. On Wednesday, the folder holds three files: Monday's file (loaded on Monday), Tuesday's file where the bank renamed one column, and Wednesday's file with the expected shape. The run holds Tuesday's file, makes Wednesday's file wait so nothing loads out of order, and prints the lines below:

```text
LOADED: 0 new file(s) with 0 row(s), 1 seen, 1 held, 1 waiting
  held: 2026-03-03.csv: header is date,ref,amount; expected date,reference,amount
  waiting: 2026-03-04.csv: an earlier file is held
```

## Verification checklist

- Confirm that the same bytes under a new file name count as seen and load zero rows.
- Confirm that a wrong header, a ragged row, a header-only file, and an empty file are each held whole.
- Confirm that with order enabled, a file after a held file waits, and with order disabled, it loads.
- Confirm that a file changed in the last few seconds is held as still being written.
- Confirm that a dry run leaves the database and the folder unchanged.
- Confirm that the exit code is 1 when any file is held.

The reference example in `examples/ingest.py` passes these checks in the repository test suite.

## Boundaries

- The example reads CSV files. For spreadsheets or PDFs, keep the rules and replace the shape check.
- A checksum proves only that the bytes match. It does not prove two different files hold different business records, so keep row-level keys where rows can repeat across files.
- For a stream or an API feed, use cursor-based ingestion instead.
