# Data workbook — ECON1596 Assessment 2 (Denmark)

Generates `ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx`, the raw-data
attachment to the Digital Policy and Innovation Report.

## Files

| File | Role |
|---|---|
| `dataset.py` | Every observation, one row each. The only place values are entered. |
| `sources.py` | Source register: authority, URL, access date, Harvard reference. |
| `content.py` | Prose for the limitations and AI-use sheets. Writing, not code. |
| `style.py` | The palette, the cell formats, and the furniture every sheet gets. |
| `build_workbook.py` | Generates the workbook. Run this; never hand-edit the .xlsx. |
| `verify_workbook.py` | Post-build checks on the generated file. Exits non-zero on failure. |
| `preview_charts.py` | Renders the four charts as PNGs so they can be looked at. |

## Usage

```bash
pip install xlsxwriter openpyxl matplotlib
python3 build_workbook.py
python3 verify_workbook.py
python3 preview_charts.py      # optional; writes previews/
```

## Version 2.0 — why this was rebuilt

Version 1.0 was generated with openpyxl and was not usable as submitted. Its
charts had been, in the project's own words, *"verified structurally and audited
in the raw XML, never seen rendered."* Opening it showed what that predicts. The
measured defects, each of which is now a check in `verify_workbook.py`:

| Defect in v1.0 | What now prevents it |
|---|---|
| All 13 charts untitled — titles lived in worksheet cells, so they did not move, resize, copy or print with the chart | Every chart must carry a title and both axis titles on the chart object |
| Every chart anchored on top of its own caption or source note | No chart may cover a populated cell |
| 201 formula cells, zero cached values — blank cells and empty charts in any viewer without a calculation engine | Every formula must carry a cached value, and that value must equal the dataset's |
| No print setup on any of 22 sheets | Every sheet must have an orientation and fit-to-page |
| Cover contents omitted a sheet and misordered another | The contents list must equal the real tab list, in order |
| A mistyped series code rendered as a silent blank | A lookup to an observation that does not exist raises at build time |

Version 2.1 fixed three more, found by auditing the generated file rather than
the build script:

| Defect in v2.0 | What now prevents it |
|---|---|
| 34 cells on `07_LIMITATIONS` clipped, including every entry in the AI log's validation column, because row heights assumed a fixed 95 characters per line whatever the column's real width was | Every wrapped cell in a row whose height the file sets must fit that height, measured against the column's actual width |
| `06_SERIES` repeated row 1 when printed, so page 2 carried the sheet title where the column headings belonged, and five other sheets repeated nothing | A repeated row must carry the navy heading band; `finish()` takes the heading row explicitly instead of assuming row 0 |
| Units reading "million DK", dataset codes and figure references cut off against the occupied cell to their right | Column widths corrected; the audit sweep is recorded below |

### Why openpyxl cannot be asked for a column width

XlsxWriter emits one `<col min=".." max="..">` element per run of equal-width
columns, and openpyxl files that whole run under the **first** column's letter.
`ws.column_dimensions["C"]` on a B:C run returns `None`, which is
indistinguishable from a column nobody set. An audit chased that as a missing
width on the AI log's validation column before checking the XML; the column was
63 wide all along. `verify_workbook.column_widths()` reads the sheet XML, and
anything checking widths must use it.

The data layer was not rebuilt. `dataset.py` and `sources.py` carry 136
observations verified individually against their issuing authorities, and the
statistical portals are unreachable from the build environment; re-entering them
would mean re-verifying, which is how the fabricated-data incident recorded in
`07_LIMITATIONS` was caught in the first place.

## Rules this codebase enforces

1. **A value exists only if it was verified against its issuing authority.**
   Nothing is interpolated, smoothed, or inferred from a neighbouring year.
   Gaps are left as gaps. `F2_PAYMENTS` is the visible case: the mobile wallet
   has one observation, so it is drawn as one column, and the missing 2017
   column is footnoted as a gap rather than plotted as a zero.
2. **`02_MASTER` is the single source of truth.** Every figure sheet and every
   derived quantity is a `SUMIFS` lookup against it, written together with the
   value Python computed for the same lookup.
3. **Denominators are recorded per observation** and series with different
   denominators are never plotted on one axis.
4. **A policy event is evidence** and carries a real date, an honest `precision`
   (`day`/`month`/`year` — never dated more finely than its source allows), a
   legal citation and a `source_id`.
5. **Corrections are recorded, not erased.** The withdrawn SMV:Digital defunding
   claim stays in `07_LIMITATIONS` and `09_POLICY`, and `verify_workbook.py`
   fails the build if that record disappears. A correction that leaves no trace
   is indistinguishable from never having made the error, which is exactly what
   the AI Use and Validation Appendix has to be able to show.

## Sheets

Twelve, down from twenty-two. The chart sheets that were dropped duplicated
report figures already rendered at publication quality; their observations remain
in `02_MASTER` and their derived numbers in `05_CALC`.

`06_SERIES` holds the series behind every report figure that is not drawn in this
workbook, deduplicated, with a `feeds` column naming each figure. It replaces the
three separate extract sheets `F1_BRANCHES`, `F11_EWASTE` and `F12_REACH`, which
between them held 34 rows of the same ten columns and overlapped — `DK.FIN.BRCH`
appeared on two of them.

### The figure-number trap

`render.py` numbers figures 1..n **by order of first appearance in the draft**,
so its caption keys are not figure numbers: `[[F6]]` prints as "Figure 4". An
earlier version of the `report_ref` column was written by hand from
`build_figures.py`'s function names and was therefore wrong for almost every
series — it sent a reader after "Fig 9" for what the report prints as Figure 7,
and labelled the payments series "App. E" when it is Figure 3.

`figure_numbers()` in `build_workbook.py` now applies render.py's own rule to the
draft at build time, so the two cannot disagree.

### Sheet references in the report are checked, not listed

`verify_workbook.py` scans `render.py` and the draft for every sheet name they
mention and fails if one does not exist. The previous hand-kept list was built
from a regex matching only `F<digits>_<CAPS>`, so it missed the captions reading
"workbook F9" and "Workbook F8" — and four of those pointed at sheets this
rebuild had removed, with nothing to notice.

## Presentation conventions

**Colour.** Four cell fills, legended on `00_COVER`: no fill for a retrieved
value, pale blue for a derived one, pale amber for a flagged one, pale red for a
documented gap. Nothing else is coloured.

Charts use two schemes, because they answer different questions. `F2_PAYMENTS`
needs three instruments told apart, so it takes slots 1–3 of the validated
categorical palette (blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a`) — all
gates pass, and because aqua sits below 3:1 contrast on white, every column is
directly labelled. `F5_EU27` and `F6_ADOPT_BENEFIT` are highlight charts, where
accent blue marks Denmark and grey means "not the subject"; that pair
deliberately fails a *categorical* chroma check, since grey reading as grey is
the intent. Provenance and the validator output are recorded at the top of
`style.py`.

**Chart chrome.** v1.0 stripped all of it — no gridlines, hidden axis lines, no
number formats — which made a scatter impossible to read off. v2.0 keeps light
horizontal gridlines, axis titles with units, recessive axis lines, and a bottom
legend where there is more than one series.

**Number formats** are four-part: positive; negative; zero; text. The text
section renders an absent value as an en-dash, so a gap looks like a gap rather
than an oversight. The cost is that a genuine zero renders the same way; no
series here has a meaningful zero, and the caveat is stated on `04_DEFINITIONS`
where a reader meets it rather than only in this file.

## The chart previews

`preview_charts.py` redraws the four charts in matplotlib from the same
observations, colours, ordering and labels. This exists because LibreOffice's
Calc filter is broken in the build environment — it fails to load even a two-cell
probe file — so the .xlsx cannot be rendered here, which is precisely how v1.0's
charts went unseen.

The previews are a proxy, not the article. Excel will differ in fonts, spacing
and tick placement. **Open the workbook before submitting.**

What a preview cannot reach at all is the sheets: nine of the twelve carry no
chart, and their defects are widths, row heights and print setup. Those are
checked against the generated .xlsx instead, which is where the v2.0 clipping
was eventually found.

## Adding data

Append rows to `OBS` in `dataset.py` using the existing 10-column shape, add any
new source to `SOURCES` in `sources.py`, then rebuild and verify. `F5_EU27` and
`F6_ADOPT_BENEFIT` recompute their cross-section at build time, so adding the
nine missing `XX.ECM.ENT.TRN` observations moves those countries into the scatter
and updates n, the slope and R² without touching the build script.

Prefer a databrowser extract to a press release. A press release names the
countries that make a story — the top, the bottom, a couple of movers — which is
a sample drawn from the tails. `07_LIMITATIONS` keeps the measured cost of
having done that once: the tail-only sample reported R² 0.853 against 0.674 on
the complete cross-section, while the slope moved only from +0.655 to +0.602.
