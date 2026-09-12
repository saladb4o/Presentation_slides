# Drafting plan — ECON1596/1597 Assessment 2
**Denmark · Digital Policy and Innovation Report · 2,000 words ±10% · due 17 Sep 2026**

Target length **2,100 words** of body prose. References, figure captions, the AI Use
and Validation Appendix and the workbook are outside the count.

---

## 0. One thing to confirm before drafting

The section map below is reconstructed from the brief as discussed earlier: five
numbered questions, Q3 requiring an SDG link, Q4 the distributional question,
Q5 drawn from the guest lecture and worth 8 of 50 marks (16%). **Paste the brief's
question list and marks split and I will re-cut the word budget against it**; the
argument spine and the evidence assignments below do not change either way.

---

## 1. The argument spine

One thesis, carried through every section, so the report reads as an argument and
not five disconnected answers:

> **Denmark's digital transition is close to complete in breadth and incomplete in
> depth, and the instrument that delivered the breadth — legal compulsion — is the
> reason the depth is missing.**

Three moves:

1. **Compulsion worked.** Mandatory Digital Post (LOV nr 528 af 11/06/2012;
   businesses 2013, citizens 1 Nov 2014) plus a single identity rail (NemID → MitID)
   produced adoption no voluntary programme has matched.
2. **Compulsion is not preference.** After 1 Nov 2014 the adoption series measures
   *compliance with a legal obligation*, not revealed demand. This is the report's
   sharpest analytical move and it reframes every subsequent number.
3. **What compulsion cannot buy.** Service quality (DK 82.2 vs EU 84.64), SME depth
   (AI 40.99% vs 74.52% in large firms), and the residual excluded population
   (16.5% in difficulty against 4.7% formally exempt) are all things a mandate
   cannot legislate into existence.

The **verified-savings finding is the empirical spine**: of the ~DKK 1bn/yr projected
Digital Post saving, Rigsrevisionen could verify only **DKK 450m** — postage, paper,
envelopes. The wage and overhead component was never substantiated; the
cross-government study was abandoned when KL declined to take part. **55.0% of the
business case is unverified.** A policy that compelled 5.07m people rests on a
half-audited benefit. That sentence does more work than any other in the report.

---

## 2. Section map, word budget and evidence

| § | Function | Words | Figure | Anchor numbers |
|---|---|---|---|---|
| — | Title block, no abstract | — | — | — |
| 1 | Context and the policy instrument | 300 | Table 1 (09_POLICY) | LOV nr 528/2012; citizens mandatory 1 Nov 2014; MitID required 22 Sep 2022; NemID retired 31 Oct 2023 |
| 2 | Adoption → economic effect | 480 | **F1**, **F2**, **F6** | Branches 2,025 → 665 (**−67.2%**, 2004–2024); cash 23% → **9%** of in-store payments (2017–2025); wallets **32%**; F6 now **n=18**, slope **+0.602** (se 0.105, **t=5.75**), **R² 0.674** |
| 3 | Denmark's digital economy vs the EU + SDG | 420 | **F3**, **F7** | E-sales turnover DK 17.05 → **33.31%** vs EU 16.43 → **19.49%**; SME digital intensity **92.45%** vs 71.39%; DPS citizen score **82.2 vs 84.64** (−2.44) |
| 4 | Who is left behind | 420 | **F4** | **4.7%** formally exempt (238,479 citizens) vs **16.5%** in difficulty vs **22%** upper-bound disadvantaged; skills 92.06% (16–24) vs **67.81%** (55–74) |
| 5 | Guest lecture question | 320 | — | **BLOCKED** — needs the speaker's content |
| 6 | Recommendation and limitations | 160 | **F8** | SMV:Digital: ~7,000 projects, **65%** invested further, 2% no plans — the only control-group evidence in the workbook |
|   | **Total** | **2,100** | 7 of 9 figures cited | |

### Notes on the harder sections

**§2 is the lecturer's exhibit.** The requirement was an x–y relationship or a
regression showing more adoption → more economic effect. F6 is now a genuine
regression: **n=18**, slope **+0.602 pp of enterprise turnover per pp of consumer
adoption**, standard error 0.105, **t = 5.75** on 16 degrees of freedom, **R² =
0.674**. Quote all four.

The tail-selection story is now an *asset* rather than a caveat, and §2 should
spend two sentences on it. The earlier six-country sample drawn from a press
release reported **R² 0.853 with a slope of +0.655**; on the complete
cross-section the slope barely moved while the fit fell by 0.18. That is a
demonstration of selection bias measured on the report's own data — worth more
than the R² itself.

Denmark's residual is **+4.34pp**: it converts consumer adoption into enterprise
e-commerce better than the EU pattern predicts. That is a finding §3 can use.

**§3 carries the SDG.** Recommendation: **SDG 8** (Target 8.2, productivity through
technological upgrading) — it sits on the e-sales and SME-intensity evidence the
report already builds, so the SDG paragraph costs ~60 words instead of a new
argument. The alternative, **SDG 12** on ICT waste (DK **15.37%** vs EU **80.23%**),
is a far more arresting contrast and a genuine Danish failure — but it is orthogonal
to the thesis and would need its own 150 words to justify. **SDG 8 unless you want
the contrarian angle.**

**§4 must not overclaim.** Denmark's weakest age band, 55–74 at **67.81%**, still
beats the EU average *for that same band* (42.60%) by just over 25pp. So Danish
exclusion is **not a skills deficit** — it is a mandate calibrated above the bottom
of its own distribution. Note that the 42.60% comparator currently lives in a
`note` field, not as its own observation: if §4 cites it, promote it to a real
`EU.SKL.5574` row in `02_MASTER` first, per the tracing rule above. The gap between 4.7%
relieved and 16.5% struggling is an *administrative* gap, not a capability one.
That distinction is the section.

---

## 3. Drafting sequence

1. **§2 first** — the lecturer's stated requirement, and the section whose numbers
   are hardest. Everything else is easier once the spine holds.
2. **§4 second** — the most memorable evidence; write it while fresh.
3. **§3**, then **§1** — context is easiest to write last, and shortest when written
   backwards from the argument it has to set up.
4. **§6**, then trim to budget.
5. **§5 last**, when the guest-lecture notes exist.
6. **References**, RMIT Harvard, from `03_SOURCES` — the Harvard string is already
   built for all 22 sources, so this is transcription, not composition.
7. **AI Use and Validation Appendix**, from `08_AI_LOG`.

---

## 4. Rules for the draft

- **Every number in the prose traces to a workbook cell.** No figure enters the
  report that is not in `02_MASTER`. If the draft needs a number that is not there,
  the number gets verified and added to the workbook first, or the sentence changes.
- **Percentage points and percentages are never conflated.** Cash fell **14pp**, or
  **to 39% of its 2017 share** — never "fell 14%".
- **Denominators are stated where they shift.** The 2019→2020 online-purchasing
  break (% of individuals → % of internet users) is flagged in text if that series
  is cited at all.
- **Corrections stay visible.** The withdrawn SMV:Digital defunding claim is
  recorded in `07_LIMITATIONS` and `08_AI_LOG` and should be named in the appendix
  as a worked example of validation catching an error.
- **Policy specificity**, per the lecturer: name the instrument, the section, the
  date. "Lov om betalinger §81, amended 1 July 2022" — not "cash rules changed".

---

## 5. Format

`Assignment 2 ECON1596 _ [class group] _ s4040040.docx` — Times New Roman 12,
1.5 spacing, justified, 1-inch margins, numbered sections, figures captioned
**"Figure n — title. Source: … Full series in accompanying workbook, sheet Fn."**

Class group is still a placeholder.

---

## 6. Blockers and pre-submission checks

| Item | Status |
|---|---|
| §5 guest lecture content | **Hard blocker** — 8 marks, cannot be drafted |
| Class group code for the filename | Needed |
| SDG choice | SDG 8 recommended, awaiting your call |
| Open v4 in real Excel | Charts verified structurally, never seen rendered |
| 16 `u`-flagged tin00110 values | Spot-check against the Eurostat databrowser |
| Figure 6 expansion | **Done** — n=18, complete on X; nine states still lack the turnover measure |
