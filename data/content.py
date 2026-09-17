"""Prose content for 07_LIMITATIONS and the AI log.

Kept out of build_workbook.py because it is writing, not code, and it is the part
most likely to be edited on its own.

Carried over from the previous workbook with its cross-references corrected: the
rebuild dropped the sheets F3_ESALES, F9_CONSOLIDATION and the old F4, so entries
that pointed at them now point at 02_MASTER and at the report figure instead.
Two entries were rewritten rather than repointed, and both are marked below.
"""

# Each entry is (heading, body).
LIMITATIONS = [
    ("No inferential statistics beyond the one cross-section",
     "The longest time series here has six observations. Regression, "
     "cointegration and Granger-causality procedures require far more, and any "
     "such result on these series would be uninterpretable. The workbook "
     "supports description and comparison only. Co-movement between digital "
     "payment adoption and branch closures is presented as association, never "
     "as measured causation. The single exception is the 2024 cross-section on "
     "F6_ADOPT_BENEFIT, which is a genuine sample of 18 countries and is "
     "reported with its n, slope and R-squared on the sheet."),

    ("Figure 6 tail selection - resolved, and what it cost",
     "The adoption column was originally assembled from a Eurostat press "
     "release naming the highest three countries, the lowest three and two "
     "large movers, so most plotted points came from the ends of the EU "
     "distribution. Selecting on the extremes of X inflates the correlation "
     "coefficient regardless of the underlying relationship. The column is now "
     "the complete isoc_ec_ib20 databrowser extract for all 27 member states, "
     "so the selection is gone. The measured cost of the bias is kept because "
     "it is informative: on the 6 tail countries the fit was R-squared 0.853 "
     "with a slope of +0.655; on the complete cross-section it is R-squared "
     "0.674 with a slope of +0.602. Tail selection barely moved the slope and "
     "flattered the fit by 0.18."),

    ("No price deflator on the turnover series",
     "E-sales as a share of enterprise turnover runs 2014 to 2024, spanning "
     "the pandemic and the 2022 inflation episode. Turnover is nominal, and "
     "online and physical retail did not face the same price path. Part of the "
     "measured rise in the e-sales share is therefore relative price movement "
     "rather than real reallocation of activity. No deflator was available and "
     "none has been applied, so the doubling of intensity is nominal."),

    ("Banking series use different base years",
     "Institutions and employment are comparable to each other, both 1991 to "
     "2024. Branch counts begin in 2004. A 2004-2024 branch change and a "
     "1991-2024 employment change are not comparable, and placing the two "
     "percentages side by side in prose would misrepresent both. 05_CALC "
     "labels every window explicitly. Either state both windows or do not draw "
     "the comparison. (This entry previously pointed at sheet F9_CONSOLIDATION, "
     "which the rebuild removed; the three series remain in 02_MASTER and are "
     "drawn as Figure 2 of the report.)"),

    ("No sampling error is reported anywhere",
     "The Eurostat, Nationalbank and Agency for Digital Government figures are "
     "survey estimates and carry sampling error that the issuing authorities "
     "publish but this workbook does not reproduce. Small differences should "
     "not be treated as established: a 2 to 3 point gap between two survey "
     "proportions, or between two eGovernment Benchmark scores, may not be "
     "distinguishable from zero. Directions are more robust than magnitudes "
     "throughout."),

    ("Exclusion shares and exempt headcounts do not share a denominator",
     "REWRITTEN AT REBUILD. The previous workbook derived an implied 15-and-over "
     "population by dividing the exempt headcount by the exemption rate, "
     "because no published population figure had been verified. One has since "
     "been verified and is held as DK.POP.TOT, so 05_CALC now uses it directly "
     "and the derived base is gone. What remains true is the mismatch that "
     "matters: exemption is published on citizens aged 15 and over, whereas the "
     "capability measures are published on 'the population'. Converting a "
     "capability share into a headcount therefore gives an order of magnitude, "
     "not a count."),

    ("A withdrawn claim about SMV:Digital",
     "An earlier draft asserted that SMV:Digital was being defunded, and an "
     "argument was built on the contrast between a programme that works and a "
     "programme being cut. The claim could not be verified. The scheme's own "
     "2026 grant-pool page documents pools still open and a further pool "
     "opening on 26 October 2026. The claim was removed from the dataset and "
     "from the report's argument, and the correction is recorded in 09_POLICY "
     "and in the AI log below rather than silently erased."),

    ("Unbalanced panel",
     "Observation years differ by series because the underlying sources publish "
     "on different cycles: payment habits roughly biennially, Eurostat "
     "annually, branch counts irregularly. Gaps are genuine and are not filled. "
     "F2_PAYMENTS shows the sharpest case - the mobile wallet has one "
     "observation, so it is drawn as a single column and not as a trend."),

    ("Denominator break",
     "Danish online-purchasing figures change base between 2019, which is a "
     "percentage of individuals, and 2020 onward, which is a percentage of "
     "internet users. The 2019 observation carries flag 'b' and is never "
     "plotted with later years."),

    ("Verbal quantities",
     "Values flagged 'e' were published as words rather than figures - 'nearly "
     "one in five', 'just under 36,000'. They are recorded as the stated "
     "approximation with the original wording in the notes column, and drawn in "
     "a lighter tint wherever they are charted."),

    ("Confounded outcome",
     "Branch closures reflect both digitalisation and sectoral consolidation: "
     "219 institutions in 1991, 51 in 2024. The branch series alone cannot "
     "separate these, and the report does not claim that it does."),

    ("Definitional spread in the exclusion measures",
     "The six measures on F4_EXCLUSION range from 4.7% to 25% because they "
     "define the population differently. They are not competing estimates of "
     "one quantity and must not be averaged or presented as a confidence "
     "range."),

    ("Cross-section complete on adoption, incomplete on outcome",
     "The adoption measure covers all 27 member states for 2024, so F5_EU27 is "
     "a complete EU ranking. The enterprise-turnover measure does not: nine "
     "member states hold adoption but not turnover and cannot enter "
     "F6_ADOPT_BENEFIT, which names them on the sheet. Those nine are dropped "
     "by data availability rather than by their position on either axis, which "
     "is why the remaining 18 are treated as a usable cross-section."),

    ("Figure 6 measures two sides of the market",
     "X is a consumer measure, individuals buying online. Y is an "
     "all-enterprise, all-sector measure that includes B2B and EDI ordering. A "
     "positive association indicates that digital commerce runs deep in an "
     "economy. It is not evidence that consumer purchasing causes enterprise "
     "turnover, and it is not written as though it were. There is no control "
     "for national income and this is one year of data."),

    ("Mirror-sourced column",
     "The 16 country-level e-sales turnover values flagged 'u' were retrieved "
     "via search of Eurostat tin00110 rather than from the databrowser "
     "directly. Two values in the same column, the EU-27 aggregate at 19.49 and "
     "Ireland at 38.25, are independently corroborated by source ES5, which "
     "supports the column. Each value should still be spot-checked against the "
     "databrowser before final submission."),

    ("Search-based verification",
     "Direct access to statistical portals was blocked in the build "
     "environment. Values were verified against the issuing authority through "
     "search results reporting those publications. This is weaker than "
     "downloading the dataset: before final submission, spot-check the "
     "high-stakes figures against the source pages directly."),

    ("Discarded material",
     "An earlier candidate dataset was rejected in full after verification "
     "found fabricated values carrying authentic dataset codes and extraction "
     "dates, including a Eurostat cross-section that inverted the true EU "
     "country ranking. None of it survives in this workbook."),

    ("A column that was removed rather than back-filled",
     "REWRITTEN AT REBUILD. The previous workbook carried a compiled_date column "
     "holding one build-time constant, identical on every row, which read as "
     "though it recorded when each value was retrieved. It did not - retrievals "
     "were made across several sessions on different days. The rebuild removes "
     "the column rather than inventing plausible per-value dates, and 03_SOURCES "
     "carries a real accessed date per source instead. Recording true "
     "per-observation retrieval dates requires capturing them at retrieval time "
     "in dataset.py, which is the correct fix and is not retrospective."),
]

# (step, assistance, validation, outcome)
AI_LOG = [
    ("Source identification",
     "Used to identify candidate statistical sources and dataset codes.",
     "Each source opened or search-verified against the issuing authority.",
     "Source register in 03_SOURCES."),
    ("Value retrieval",
     "Used to search for published values by authority and indicator.",
     "Each value checked against a result reporting the issuing authority's own "
     "publication.",
     "Every retained observation carries a source_id."),
    ("Rejection of a prior dataset",
     "A candidate dataset produced with AI assistance was reviewed.",
     "Cross-checked against Eurostat's published country ranking; the values "
     "inverted the true ranking and contained duplicated and interpolated cells.",
     "Dataset rejected in full and excluded."),
    ("Withdrawal of an AI-suggested claim",
     "An AI-assisted draft asserted that the SMV:Digital grant scheme was being "
     "defunded, and an argument was built on that contrast.",
     "Searched for the scheme's funding status. The scheme's own 2026 grant-pool "
     "page documents pools still open and a further pool opening 26 October "
     "2026. No source supported the defunding claim.",
     "Claim withdrawn from the dataset and the argument; the withdrawal is "
     "recorded in 09_POLICY and 07_LIMITATIONS rather than erased."),
    ("Statistical self-audit",
     "Asked to audit its own workbook as a macroeconomic policy reviewer would.",
     "The audit found that the adoption column had been assembled from a press "
     "release naming only the top three, bottom three and three large movers - a "
     "sample drawn from the tails, which inflates R-squared by construction.",
     "Selection warning added and the limitation recorded. Later resolved - see "
     "the two rows below."),
    ("Failed verification attempt",
     "Asked to retrieve Eurostat isoc_ec_ib20 for 2024 for the twelve member "
     "states missing from the scatter, so the tail selection could be removed.",
     "Eurostat and the national statistical offices are unreachable from the "
     "build environment. Web search returned only the same press release, two "
     "country values with no attributable source, and one answer mixing the '% "
     "of internet users' and '% of individuals' denominators in one paragraph.",
     "No values accepted. Recorded because the honest outcome of a verification "
     "attempt is sometimes that it failed."),
    ("Author-supplied authoritative extract",
     "The author retrieved the complete isoc_ec_ib20 table from the Eurostat "
     "databrowser and supplied it as a spreadsheet; AI parsed it into the "
     "dataset.",
     "The extract carries its own provenance header - dataset code, extraction "
     "timestamp, last-update date, and an explicit unit. The ten values it "
     "overlapped with were compared against the rounded press-release figures "
     "already held; all ten agreed to rounding.",
     "All 27 member states plus the EU-27 aggregate added under source ES7. The "
     "scatter went from n=6 to n=18 and R-squared was restored to the chart "
     "face."),
    ("Workbook construction",
     "AI wrote the Python build script that generates this workbook.",
     "Structural assertions run at build time - source_ids resolve, units and "
     "denominators present, no duplicate observations, every lookup resolves to "
     "a real observation or the build fails - and verify_workbook.py re-checks "
     "the generated file afterwards.",
     "build_workbook.py and verify_workbook.py, both re-runnable."),
    ("Workbook rebuild",
     "The first generated workbook was rebuilt after the author found it "
     "unusable. AI diagnosed the defects and wrote the replacement.",
     "The defects were measured in the generated file rather than argued: 13 "
     "untitled charts, every chart anchored over its own caption, 201 formula "
     "cells carrying no cached value, and no print setup on any of 22 sheets. "
     "verify_workbook.py now fails the build on each of those conditions.",
     "This workbook, version 2.0."),
    ("Analytical framing",
     "Used to interpret patterns and suggest framings.",
     "Author reviewed each interpretation against the underlying values.",
     "Interpretations appear in the report, attributed to the author."),
    ("Not delegated to AI",
     "Selection of the research question, country, industries, SDG and policy "
     "comparator; the argument; the conclusions.",
     "n/a",
     "Author's own work."),
]

AI_LOG_FOOTER = (
    "This log records assistance during data assembly and workbook "
    "construction. Complete it with any further AI use during drafting before "
    "submission. The assessment requires that AI-assisted content be verified "
    "and acknowledged."
)

RETAIL_GAP = [
    ("Status", "NOT RETRIEVED"),
    ("Indicator", "Retail trade turnover, volume index (mangdeindeks)"),
    ("Authority", "Danmarks Statistik (DST1); also available via Eurostat "
                  "sts_trtu_a"),
    ("Filters required", "geo=DK; nace_r2=G47; indic_bt=VOL; s_adj=SCA; "
                         "unit=I21 (2021=100)"),
    ("Why not retrieved", "Values are published through StatBank and the "
                          "Eurostat databrowser. This session's network policy "
                          "blocked direct access to both, and the figure could "
                          "not be verified by search. A value that cannot be "
                          "traced is not entered."),
    ("Base year caution", "Danmarks Statistik rebased the index from 2015=100 "
                          "to 2021=100. Series retrieved on different bases "
                          "must not be joined."),
    ("Effect on the analysis", "The e-commerce section rests on the enterprise "
                               "e-sales evidence instead, which is better "
                               "sourced. No conclusion in the report depends on "
                               "this series."),
    ("To fill", "Retrieve from statistikbanken.dk, add rows to dataset.py under "
                "series_code DK.RET.VOL with unit 'index 2021=100', and re-run "
                "build_workbook.py."),
]
