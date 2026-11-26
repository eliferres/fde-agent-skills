---
name: exact-head-approvals
description: "Use when landing changes on a protected branch from parallel human or agent sessions: the approval names one full commit id, the review report and the tests name the same commit, and a merge lock lets one landing through at a time."
---

# Exact-Head Approvals

## The failure mode

Protected branches break in three common ways:

1. A person approves a pull request, then two more commits land on the branch. The merge carries code nobody reviewed or approved.
2. The review report says "looks good" about a branch name, so nobody can tell which commit the reviewer read.
3. Two sessions merge within the same minute. Each change passes tests alone, and nobody tests the pair together.

Tie the approval, the review report, and the test result to one full commit id, and let one landing through at a time.

## Core rules

1. **Full commit id only.** The approval names a full commit id (forty characters). A branch name, a pull request number, or a short id does not count.
2. **Matching review and tests.** The review report and the test result name the same full commit id.
3. **A moved head voids all three.** One new commit, even a typo fix, requires a new review, a new test run, and a new approval.
4. **One landing at a time.** A session takes the merge lock with an owner and an expiry before it lands, and releases the lock after it lands.
5. **A script checks every record.** Run a check script as the last step before the merge. The script compares the head commit id to every record and refuses on any mismatch.
6. **Approvals expire.** An approval older than a day expires, so ask for a new approval.

## Step-by-step protocol

### 1. Freeze the head and write down its commit id

```bash
git rev-parse HEAD   # the one commit that may land
```

Every record from this step onward carries that full commit id.

### 2. Collect three records for that commit

Store the review report, the test result, and the approval as three small records, each naming the commit id. The approver reads the review report and the test result before giving approval.

```json
{"commit": "4f2a9c1e0b7d3a5c8e6f1b2d4a7c9e0f3b5d8a1c", "verdict": "SHIP", "must_fix": 0}
{"commit": "4f2a9c1e0b7d3a5c8e6f1b2d4a7c9e0f3b5d8a1c", "status": "green"}
{"commit": "4f2a9c1e0b7d3a5c8e6f1b2d4a7c9e0f3b5d8a1c", "approved_by": "R. Okafor",
 "approved_at": "2026-03-02T11:30:00+00:00", "scope": "invoice export fix"}
```

### 3. Take the merge lock

Acquire the merge lock atomically as one record (a lock file or one row) with an owner and an expiry. If another session holds the lock, wait and do not land beside it.

```json
{"owner": "session-b", "expires_at": "2026-03-02T12:10:00+00:00"}
```

### 4. Run the landing check, then land that exact commit

```bash
head="$(git rev-parse HEAD)"
python3 examples/check_landing.py --head "$head" --owner session-b \
  --approval landing/approval.json --review landing/review.json \
  --tests landing/tests.json --lock landing/merge.lock.json \
  && git push origin "$head:refs/heads/main"
```

Push the exact commit id instead of the branch name so a commit added after the check cannot ride along. Release the merge lock after the push completes.

### 5. When the head moves, start again

If a rebase or a fix moves the head, the old records are void. Review the new commit, run the tests on it, and ask for a new approval that names the new commit id.

## Worked example

Session B holds an approval for commit `4f2a9c1e0b`. A teammate pushes a one-line fix, and the branch head moves to `9d1c3e7a2f`. Session B runs the landing check, and the tool refuses the landing with the three lines below, so Session B asks for a new review, a new test run, and a new approval on `9d1c3e7a2f`.

```text
REFUSED: approval names 4f2a9c1e0b but the head is 9d1c3e7a2f: the head moved, so it needs a new approval
REFUSED: review names 4f2a9c1e0b but the head is 9d1c3e7a2f: the head moved, so it needs a new review
REFUSED: tests names 4f2a9c1e0b but the head is 9d1c3e7a2f: the head moved, so it needs a new tests
```

## Verification checklist

- Confirm that matching approval, review, and test records for the head pass the check.
- Confirm that a head moved by one commit fails on the approval, review, and test records.
- Confirm that a short commit id or a branch name in any record fails the check.
- Confirm that a review verdict other than `SHIP`, an open `must_fix`, or tests that are not `green` each fail the check.
- Confirm that a merge lock held by another owner or an expired lock fails the check.
- Confirm that an approval older than 24 hours fails the check.

The reference example in `examples/check_landing.py` passes these checks in the repository test suite.

## Boundaries

- This protocol is a team rule backed by a script. Keep the host's branch protection on as the hard limit.
- The check does not replace the review. It proves only which commit the reviewer read.
- For a solo repository with one writer, the merge lock adds little, so you can skip the lock and keep the commit-named approval.
