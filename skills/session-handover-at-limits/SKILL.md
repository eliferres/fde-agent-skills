---
name: session-handover-at-limits
description: "Use when an agent session nears a context, usage, or account limit, or when work must move to another session or person: save the state, a one-line pickup, and the status of each thread so the work continues without re-discovery."
---

# Session Handover at Limits

## The failure mode

1. A session hits its limit in the middle of a task, and the next session spends an hour finding out what is done.
2. The handover is a paragraph of prose from memory that says "tests pass", and nobody can tell on which commit.
3. Three parallel threads share one status note, and the last writer erases the other two.

To fix these failures, save state early and often in a file with fixed parts that point at real artifacts.

## Core rules

1. **Save before the limit.** Write state after each finished section and at a set usage threshold, not when the limit arrives.
2. **One pickup line.** Put the single next action first in the file, written so a new session can start on it.
3. **Fixed parts.** Include sections for done, in flight, next, blocked, and decisions with their reasons.
4. **Point, do not retell.** Name the branch, the commit, the pull request and the path. A new session checks those artifacts, not the prose.
5. **One state per thread.** Give each parallel thread its own section or file, and append updates instead of overwriting them.
6. **Label what is not verified.** Mark unverified items as "not run", "not checked" or "assumed".
7. **No secrets.** Name where a credential lives, never its value.

## Step-by-step protocol

### 1. Create the state file at the start

Create the state file with its fixed parts before the first piece of work. A session updates a file that exists and skips a file planned for later.

```markdown
# STATE: <the work, in a few words>
Updated: <date and time>

## Pickup line
<the single next action, with the path or command>

## Done
- <what is finished> (<branch>, <commit>)

## In flight
- <what is half done, and exactly where it stopped>

## Next
- <ordered list>

## Blocked
- <what, and who can clear it>

## Decisions
- <the decision> because <the reason>

## Not verified
- <claim that was not checked>
```

### 2. Update it at fixed points

Update the state file after each finished section, before any long-running command, and when usage passes a threshold you set at the start. Change the pickup line every time.

### 3. At the limit, stop cleanly

1. Commit or stash work in progress so nothing lives only in the session.
2. Write the final state with the pickup line.
3. Say in one line where the state file is.

### 4. On pickup, verify before acting

```bash
git status --short && git log --oneline -3   # does the repository match the state file?
```

The new session reads the state file first and checks it against the real systems. When the state file and a real system differ, trust the system and correct the file.

## Worked example

This example uses made-up work. A usage limit stops a session migrating four report queries after it finishes the second query.

```markdown
# STATE: move four report queries to the new views
Updated: 2 March 14:20

## Pickup line
Convert query 3 (`reports/returns.sql`) the same way as query 2, then run `make test-reports`.

## Done
- Query 1 and query 2 converted and tested (branch `report-views`, commit `7c1e2a9`)

## In flight
- Query 3: new view drafted in `views/returns.sql`, not yet wired into the report

## Next
- Query 4, then remove the old queries in a separate change

## Blocked
- none

## Decisions
- Keep the old column names in the views because two dashboards read them

## Not verified
- The row counts for query 2 were compared on test data only
```

## Verification checklist

- A new session can state the next action after reading the pickup line alone.
- Every "done" item names a branch and a commit that exist.
- The repository state matches the state file, and the file mentions any uncommitted work.
- Each parallel thread has its own section.
- The state file holds no secret value.

## Boundaries

- A state file is a pointer, not a record of truth. The repository and the live systems are the truth.
- Do not paste long logs or diffs into the state file. Link to them.
- Skip the state file for work that fits in one short session.
