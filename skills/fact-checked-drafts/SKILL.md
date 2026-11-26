---
name: fact-checked-drafts
description: "Use when drafting an email, memo, or report for a person to send that states facts about money, dates, people, or system state: attach a claim-and-confidence block, work every claim to High, and cut what cannot be verified."
---

# Fact-Checked Drafts

## The failure mode

1. A draft reads well and holds one wrong date, and the sender learns about the error from the reply.
2. The approver cannot tell which sentences come from a check and which come from a guess, so the approver checks every sentence or checks none.
3. A writer softens an unverified claim with "roughly" and leaves it in the draft.

List every checkable claim with its source and a confidence level, and keep only High claims in the draft.

## Core rules

1. **List every checkable claim.** Put one claim on each line: amounts, dates, names, counts, statuses, and earlier promises.
2. **Use three confidence levels.** Mark a claim High when you read it from the system of record in this session or when two independent sources agree. Mark it Medium for one indirect source, and Low for memory or inference.
3. **Run one deeper lookup.** Check every Medium or Low claim one more time before the approver sees the draft.
4. **High or cut.** Cut any claim that stays below High, rewrite it as a question to the reader, or label it as an assumption in the text.
5. **Remove the block before sending.** Attach the claim check block when you hand over the draft, and remove it before the person sends the message.
6. **Match the draft and the block.** Every number in the draft equals the matching number in the block.

## Step-by-step protocol

### 1. Write the draft, then pull out the claims

Read the draft one sentence at a time. Turn each fact a reader can check into one line in the claim check block.

### 2. Source and grade each claim

```text
CLAIM CHECK
1. Invoice 1042 is for 1,250.00                      | billing system, read today      | High
2. It was due on 14 February                         | billing system, read today      | High
3. We sent a reminder on 20 February                 | sent-mail search, one result    | High
4. The customer promised payment "by month end"      | my notes from a call            | Low
```

### 3. Work the Medium and Low claims

Run one deeper lookup for each Medium or Low claim. In the example above, a search of the mail thread finds no written promise, so claim 4 stays Low.

### 4. Cut or rewrite what is not High

```text
Before: "As you promised payment by month end, ..."
After:  "Could you confirm the date we should expect payment?"
```

### 5. Hand over the draft with the block

The approver reads the claim check block first and the draft second. Remove the block before a person sends the message.

## Worked example

A draft payment reminder for invoice 1042 holds four claims. Three claims reach High from the billing system and the sent-mail search. The fourth claim, a payment promise from a call, has no written record, so the writer rewrites that sentence as a question. The approver reviews the final block below, removes the block, and sends the message.

```text
CLAIM CHECK
1. Invoice 1042 is for 1,250.00                      | billing system, read today      | High
2. It was due on 14 February                         | billing system, read today      | High
3. We sent a reminder on 20 February                 | sent-mail search, one result    | High
(cut) The customer promised payment by month end     | no written record; asked instead
```

## Verification checklist

- Every amount, date, name, count, and status in the draft has a line in the block.
- Every remaining line is High and names its source.
- The block marks every cut or rewritten claim as cut.
- Each number in the draft equals the matching number in the block.
- The sent message contains no claim check block.

## Boundaries

- The block checks facts and does not check tone or judgment.
- An opinion or a recommendation is not a claim. State clearly that it is a view.
- This skill prepares a draft. A person approves and sends the message.
