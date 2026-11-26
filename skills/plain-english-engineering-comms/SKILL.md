---
name: plain-english-engineering-comms
description: "Use when writing engineering updates, go-live decision cards, incident briefs, architecture proposals, or stakeholder messages to enforce plain English, answer-first structure, strongest-counter rigor, and zero AI writing tells."
---

# Plain-English Engineering Communication

## The failure mode

Technical teams lose stakeholder trust and slow decisions in three ways.

1. **Buried decisions:** Four background paragraphs hide what broke, unmet work, or approvals.
2. **Rubber-stamping:** Teams accept first ideas without the strongest counter or second-order operational risks.
3. **AI filler:** Buzzwords, em dashes, hedges, and vague claims hide missing evidence.

Answer first in plain, active English, lead with unmet work, state the strongest counter before agreeing, and put high-stakes decisions in one five-line card.

## Core rules

1. **Answer first, plain English throughout.** Use short sentences, active voice, everyday words, straight quotes, and zero idioms (following ASD-STE100 simplified technical English principles). Keep file paths, raw commit hashes, and terminal commands out of executive prose (place them in a compact reference block at the end only when needed).
2. **Lead every status update with what is still unmet.** Never open a progress update with a victory lap while blockers, failing checks, or unverified steps remain. State what is still open in sentence one.
3. **Give the strongest counter before agreeing.** On every architecture choice, vendor call, or ship proposal, state the strongest factual argument against your recommendation first, then map clear first-, second-, and third-order effects.
4. **Use a compact five-line decision card for high-stakes calls.** For production landings, money or billing actions, outward customer sends, or multi-option tradeoffs, present one uniform card:
   - **Decide:** The exact binary or clear choice needed now.
   - **Recommend:** Your recommended option in one line.
   - **Impact:** What changes right away for users or operators.
   - **Safety:** Verification passed plus exact rollback or undo path.
   - **Catch:** The real tradeoff, limitation, or remaining risk.
5. **Run an anti-AI-slop pass before sending.** Strip inflated vocabulary (`delve`, `crucial`, `pivotal`, `landscape`, `tapestry`, `testament`, `underscore`, `showcase`, `leverage`, `seamless`, `robust`, `comprehensive`, `streamline`, `empower`, `elevate`, `cutting-edge`, `blazing`, `effortless`), em/en dashes used as crutches, "not just X, but Y" rhetorical symmetry, and empty sign-offs.
6. **Never invent facts during editing.** Tightening prose must preserve every claim and number from source systems. Label any unverified estimate explicitly as an inference.

## Step-by-step protocol

### 1. Format high-stakes decisions with the five-line card

```markdown
Kind: Production invoicing switch-on · Ready for live
**Decide:** Enable scheduled daily invoicing writes for tomorrow's 8:00 AM run?
**Recommend:** Yes, switch on after confirming the 21-order dry run tied to source orders.
**Impact:** Shipped wholesale orders create verified invoices, archive PDFs, and email customers automatically while holding edge cases in Slack.
**Safety:** 212 automated tests and a fresh read-only review passed; rollback is flipping one database switch off or reverting the commit.
**Catch:** Split purchase orders with manual broker discounts still pause in the review queue until the first rule is saved.
```

### 2. Run the three-pass edit loop on any external or executive deliverable

1. **Draft:** Write the facts first, answer on line one, every number tied to a live source or test run.
2. **Audit:** Scan for banned buzzwords, em/en dashes, passive voice, buried blockers, unbacked adjectives, and unnecessary internal jargon.
3. **Tighten:** Cut 20% to 30% of word count without dropping a single concrete number, risk, or rollback path.

### 3. Keep small decisions small

For a trivial yes/no question with low blast radius, skip the five-line card and ask in one plain sentence.

## Worked example

This example shows the same made-up status update twice. The second version leads with what is still open and gives numbers a reader can check.

```text
Before: "Great progress this week! The team has been working hard on the export and most things
         are in good shape, although there are a few items we are still looking into."

After:  "Still open: the email step is not tested. Done: the export passes 14 tests and its row
         count ties to the order system (214). Next: test the email step on Thursday."
```

## Verification checklist

- First sentence directly answers the question or names what is still unmet.
- Every number, status, and completion claim comes from verified output, never assumption.
- Proposals include the strongest counter-argument and concrete rollback path.
- Zero banned filler words, zero em/en dashes, and zero invented details.
- High-stakes landings, money moves, and outward sends use the five-line decision card.

## Boundaries

- Plain English does not mean dumbing down technical precision: keep exact metric names, HTTP codes, SQL primitives, and latency numbers when speaking to engineers.
- Never rewrite legal contracts, regulatory filings, or verbatim customer quotes without preserving exact required terminology.
