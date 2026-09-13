### A.1 Declaration

Generative AI was used throughout the assembly of this report's dataset and in
drafting its prose. The tool and version were **[TOOL AND VERSION — to be
completed by the author]**, used between the start of data assembly and
submission on 17 September 2026. This appendix states what was delegated, how
each delegation was checked, and — the part that matters — four occasions on
which AI assistance introduced an error that validation caught and removed.

The governing principle was that corrections are recorded, not erased. Every
error described below is still visible in the accompanying workbook, in sheets
`07_LIMITATIONS` and `08_AI_LOG`. A marker can verify that the checks happened
rather than taking this appendix's word for it.

### A.2 Use, and how each use was validated

| Step | Assistance used | How it was validated | Outcome |
|---|---|---|---|
| Source identification | Candidate authorities and dataset codes | Each source opened or search-verified against the issuing authority | Register of 23 sources in `03_SOURCES` |
| Value retrieval | Search for published values by indicator | Each value checked against the issuing authority's own publication | Every observation carries a `source_id` |
| Workbook construction | The Python build script | Structural assertions at build time; a separate 1,782-check suite | `build_workbook.py`, re-runnable |
| Figure production | The matplotlib figure script | Nine derived values re-computed and asserted against the report prose | `build_figures.py` |
| Report drafting | Prose drafting and structuring | Every number traced to `02_MASTER`; arithmetic re-derived independently | The report body |
| Self-audit | Adversarial review of the workbook and the draft | Findings checked against raw file contents before acceptance | Eleven defects fixed; see A.4 |
| Analytical framing | Interpretation and framing suggestions | Author reviewed each against the underlying values | Interpretations are the author's |

### A.3 What "validated" means here

The word is used operationally, not as reassurance. Four rules were enforced:

- Every retained observation resolves to a named issuing authority in
  `03_SOURCES`, with a URL and an access date.
- No value appears in the report that is not in `02_MASTER`. No figure sheet in
  the workbook contains a typed number — only formulas referencing `02_MASTER`.
- Structural claims are enforced by executable assertions, not by reading. The
  suite runs 1,782 checks and fails the build if any is violated.
- Where a value could not be verified against its issuing authority, it was
  dropped rather than softened.

### A.4 Four errors AI assistance introduced, and how each was caught

**A fabricated dataset.** An early candidate dataset produced with AI assistance
carried real Eurostat dataset codes and plausible extraction dates. Cross-checking
its country values against Eurostat's published ranking showed the ordering was
inverted — the values were not merely wrong but fabricated around correct-looking
metadata. The dataset was rejected in full, not repaired. This is the most
dangerous failure mode encountered, because the metadata was more convincing than
the numbers.

**A withdrawn policy claim.** An AI-assisted draft asserted that the SMV:Digital
grant scheme was being defunded, and built an argument on it. A search for the
scheme's funding status found its own 2026 grant-pool page documenting pools
still open, with a further pool opening on 26 October 2026 [[SMV1]]. The claim
was withdrawn from both the dataset and the argument. The withdrawal is recorded
in `09_POLICY` and `07_LIMITATIONS` rather than deleted.

**An overclaim about Denmark.** A drafting plan asserted that Denmark "converts
consumer adoption into enterprise e-commerce better than the EU pattern
predicts." Computing the residual distribution refuted it: Denmark's residual is
+0.97 residual standard errors and ranks fourth of eighteen, with Belgium,
Ireland and Italy all further above the line (Appendix C). The claim was cut, and
the workbook now computes the standardised residual as a live cell so the
overclaim cannot quietly return.

**A criticism that was already answered.** A late draft of Section 6 asserted that
the SMV:Digital scheme was "self-reported and uncontrolled: it measures
participation, not effect." The first half was correct. The second was false: a
search for the scheme's evaluation found a register-based effect measurement in
which Digitaliseringsstyrelsen links recipients to Danmarks Statistik records and
compares them with matched control firms [[DG5]]. The report was criticising an
absence that does not exist. The same search established that Act 603 of 2023
[[LOV1]] had already granted the entitlement a second recommendation proposed, and
that a supreme audit institution had rejected the allocation mechanism Appendix F
specified [[BRH1]]. All three were rewritten on the verified position, which in
each case produced a sharper argument than the one it replaced. The lesson is that
an unverified criticism is as much a fabrication risk as an unverified number, and
harder to notice, because a critical claim reads as caution rather than as a
factual assertion requiring a source.

A fifth class is worth recording because it is the opposite failure. During
self-audit, the audit tooling raised four alarms — an under-cited figure, an
off-palette chart, scatters with no y-values, and a mis-sized figure — all four
of which were false, caused by the tooling's own regexes not handling XML
namespaces and object types. They were cleared against the raw file contents. An
AI-generated check is itself an AI artefact and needs the same scepticism as an
AI-generated number.

### A.5 What was not delegated

The research question, the country, the policy instrument, the SDG selection, the
argument and its thesis, and the judgement about which findings are defensible.
Where the evidence and a preferred conclusion disagreed, the evidence was
followed — four times, as recorded above.

### A.6 Residual risk

Direct access to statistical portals was blocked in the build environment, so
most values were verified against search results reporting the issuing
authority's publication rather than by opening the authority's database directly.
The exception is the Eurostat `isoc_ec_ib20` extract, which the author retrieved
from the databrowser and supplied with its own provenance header [[ES7]]. Sixteen
country-level turnover values are flagged `u` in `02_MASTER` for this reason and
should be spot-checked before the workbook is reused. No sampling error is
reported anywhere in the dataset, because the sources do not publish standard
errors alongside these estimates; survey-based figures should be read as point
estimates carrying unquantified uncertainty.
