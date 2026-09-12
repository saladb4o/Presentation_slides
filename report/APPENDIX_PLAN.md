# Plan — AI Use and Validation Appendix
**ECON1596/1597 Assessment 2 · companion to `DRAFT_PLAN.md`**

Target **800–900 words** plus one table. Appendices sit outside the 2,000-word
count, but a bloated appendix reads as padding. Raw material: `08_AI_LOG`
(8 rows) and `07_LIMITATIONS` (13 entries).

---

## 1. The strategic point

Most students treat this appendix as a compliance box: *"AI was used for
brainstorming and grammar; all content is my own."* That earns nothing, because
it is unfalsifiable and identical to everyone else's.

This project can do something almost no other submission can:

> **Show three occasions where AI assistance introduced an error, and the
> validation protocol caught it and killed it — with the wreckage still on
> the record in the workbook.**

That converts the appendix from a disclaimer into **evidence that the validation
was real**. A marker cannot verify "I checked everything." They *can* open
`07_LIMITATIONS`, find the withdrawn SMV:Digital claim sitting there, and see
that the check happened. The workbook is the appendix's corroborating witness.

The governing principle to state explicitly and then demonstrate:

> **Corrections are recorded, not erased.**

---

## 2. Structure

| § | Content | Words |
|---|---|---|
| A.1 | Declaration — tool, dates, scope of use | 100 |
| A.2 | Use-by-use table | table |
| A.3 | What validation actually meant | 150 |
| A.4 | **Three errors caught** — the centrepiece | 350 |
| A.5 | What was not delegated | 80 |
| A.6 | Residual risk | 150 |

### A.1 Declaration

Tool name and version, date range of use, and a one-line scope statement.
**You must name the tool yourself** — I have left it as `[tool, version]` rather
than assert it on your behalf. Dates run from the start of data assembly to
submission, and the log must be extended to cover report drafting, which has
not happened yet.

### A.2 Use-by-use table

Four columns, straight from `08_AI_LOG`: **step · assistance used · how it was
validated · outcome**. Eight rows exist. **Three more must be added before
submission**, covering work the current log does not reach:

- Drafting the report prose (not yet done)
- Building and running the 1,029-check verification suite
- The chart and number-format conventions pass

Rule for the table: every "how it was validated" cell names a *specific,
checkable act* — a source opened, a search run, an assertion executed. Never
"reviewed for accuracy."

### A.3 What validation actually meant

Define the protocol operationally, in four rules, so "validated" has content:

1. Every retained observation carries a `source_id` resolving to a named
   issuing authority in `03_SOURCES`, with a URL and an access date.
2. No value enters the report that is not in `02_MASTER`; no figure sheet
   contains a typed number, only formulas referencing MASTER.
3. Structural claims are enforced by executable assertions, not by reading —
   **1,029 automated checks**, re-runnable, failing the build if violated.
4. Where a value could not be verified against its issuing authority, it was
   **dropped, not softened**.

### A.4 The three errors — the centrepiece

Write each as a short case: *what AI produced · how it was caught · what changed ·
where the record lives.* Roughly 110 words each.

**(i) A fabricated dataset, rejected in full.** An earlier AI-assisted dataset
carried real Eurostat dataset codes and plausible extraction dates, but the
values **inverted the true country ranking** and included interpolated cells
presented as retrieved. Caught by cross-checking against Eurostat's published
ranking. Discarded entirely rather than repaired — a source that fabricates
once cannot be trusted cell by cell. This is the most serious of the three and
should lead.

**(ii) A false claim about SMV:Digital, withdrawn.** An AI-assisted draft
asserted the grant scheme was being defunded and built a contrast on it: a
programme with measured positive effects being cut. Verification found the
scheme's own 2026 pages showing pools open and a further pool opening
**26 October 2026**. No source supported the claim. Withdrawn from the dataset
*and* the argument. Recorded in `09_POLICY` and `07_LIMITATIONS`; a verification
check **fails the build** if that record is ever removed.

**(iii) A statistically flattering sample, self-audited.** Figure 6's adoption
column had been assembled from a press release naming only the top three, bottom
three and three large movers — **a sample drawn from both tails, which inflates
R² by construction**. R² was removed from the chart face, a selection warning
added to F6, and the limitation recorded. The chart now reports direction and
slope only.

If space allows, one sentence noting that the AI-written verification suite also
caught two defects in AI-written build code (uncoloured chart markers, eight
two-part number formats) — the checks are not decorative.

### A.5 What was not delegated

Research question, country, industry and SDG selection; the argument; the
conclusions; the decision to discard the first dataset. Keep it short and
specific — a long list here reads defensively.

### A.6 Residual risk

The section that separates honest work from performed honesty. State plainly
what could still be wrong **despite** the protocol:

- Search-based verification confirms a value was *published*; it does not
  confirm the publication was correct.
- **16 `u`-flagged values** (low reliability, Eurostat) are retained and
  flagged, not corrected.
- Figure 6's sample remains tail-selected — the fix (`isoc_ec_ib20`, all 27
  countries) is identified but not applied.
- No sampling error is reported anywhere in the workbook.

End on the standard, and let it be judged against: *corrections are recorded,
not erased.*

---

## 3. Sequencing

1. Draft A.3–A.6 **now** — they are stable and do not wait on the report.
2. Add the three missing `08_AI_LOG` rows as the drafting happens, not
   retrospectively. A log reconstructed at the end is exactly the artefact
   this appendix is supposed to be better than.
3. Write A.1 last, once the true date range is known.
4. Regenerate the workbook so the printed `08_AI_LOG` matches the appendix —
   **a mismatch between the two is the one failure mode that would actively
   cost marks**, since it proves one of them was written without reference to
   the other.

---

## 4. Open items

| Item | Status |
|---|---|
| Tool name and version for A.1 | **You must supply** |
| Drafting-phase log rows | Written as drafting happens |
| Any AI use in the guest-lecture section (§5) | Blocked with §5 |
| Assessment's own required appendix wording or template | Check the brief — if a form is prescribed, it overrides this structure |
