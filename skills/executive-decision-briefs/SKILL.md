---
name: executive-decision-briefs
description: "Use when a leader must choose between options (build or buy, vendor A or B, now or later): write a two-page decision brief with the options side by side, the cost, what we accept, when the other option wins, and what to confirm."
---

# Executive Decision Briefs

## The failure mode

1. The document tells the history of the problem for five pages and puts the decision on the last page.
2. The document describes each option in a different shape, so the reader cannot compare them.
3. The recommendation hides its downside, and the leader finds it after choosing.

A two-page brief in a fixed order fixes these failures: it puts the decision first and shows the cost of the recommended option as plainly as its gain.

## Core rules

1. **The decision first.** Open with one sentence that states the choice and one sentence that states the recommendation.
2. **Options side by side.** Put all options in one table and use the same rows for every option.
3. **Cost with sources.** State the cost in money and in time for every option, and give the source for each figure.
4. **What we accept.** State the downside of the recommended option in plain words.
5. **When the other option wins.** List the conditions that would change the recommendation.
6. **What to confirm.** List each unverified fact with an owner and a date.
7. **Two pages.** Keep the brief to two pages. Move anything else to an appendix that the decision does not depend on.

## Step-by-step protocol

### 1. Write the decision sentence and stop

If you cannot state the choice in one sentence, stop: the brief is not ready. Name the decider and the date to decide by.

### 2. Fill the brief in this order

```markdown
# Decision: <the choice in one sentence>

**Decide by:** <date> · **Decider:** <name> · **Can it be undone:** <yes, how / no>

**Recommendation:** <option> because <one reason>.

## Options side by side

| | Option A | Option B |
| --- | --- | --- |
| What it is | | |
| Cost to start | | |
| Cost each month | | |
| Time to live | | |
| Main risk | | |
| Who runs it | | |

## What we accept
<the downside of the recommended option>

## When the other option wins
<the conditions that would change the recommendation>

## What to confirm
| Fact | Owner | By |
| --- | --- | --- |

## Sources
<one line per figure>
```

### 3. Check every figure against its source

Give each number in the table a matching line under Sources. Move any number without a source to "What to confirm".

### 4. Cut to two pages

Remove history, method and anything the decider does not need to make the choice. Keep the table whole.

## Worked example

This example uses a made-up company and made-up figures. A team must choose how to replace a weekly sales report that one person builds by hand in a spreadsheet.

```markdown
# Decision: build the weekly sales report in the database now, or buy a reporting tool

**Decide by:** 9 March · **Decider:** head of operations · **Can it be undone:** yes, the spreadsheet stays for one quarter

**Recommendation:** build it in the database, because the data is already there and the report is one view.

## Options side by side

| | Build in the database | Buy a reporting tool |
| --- | --- | --- |
| What it is | One saved view and a scheduled email | A hosted dashboard product |
| Cost to start | 3 days of engineering | 2,000 set-up fee (vendor quote, 27 Feb) |
| Cost each month | none | 400 (vendor quote, 27 Feb) |
| Time to live | 1 week | 4 weeks |
| Main risk | One engineer knows it | Data leaves our systems |
| Who runs it | Engineering | Operations |

## What we accept
No self-serve charts. A new question needs an engineer.

## When the other option wins
If more than three teams ask for their own reports this quarter, buy the tool.

## What to confirm
| Fact | Owner | By |
| --- | --- | --- |
| The vendor quote covers 10 users | Operations | 5 March |

## Sources
Vendor quote dated 27 February. Engineering estimate from the team lead, 1 March.
```

## Verification checklist

- The brief states the choice first and the recommendation right after it.
- Every option has a value in every row of the table.
- Every figure has a line under Sources.
- "What we accept" names a real downside of the recommended option.
- "When the other option wins" names a condition someone can observe.
- The brief fits on two pages.

## Boundaries

- Do not write a brief for a small yes or no choice. One sentence is enough.
- The brief supports a decision, and the named decider makes it.
- Do not use a brief to report status, because a status report has no options.
