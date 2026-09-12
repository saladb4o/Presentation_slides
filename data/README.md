# Data workbook — ECON1596 Assessment 2 (Denmark)

Generates `ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx`, the raw-data
attachment to the Digital Policy and Innovation Report.

## Files

| File | Role |
|---|---|
| `dataset.py` | Every observation, one row each. The only place values are entered. |
| `sources.py` | Source register: authority, URL, access date, Harvard reference. |
| `build_workbook.py` | Generates the workbook. Run this; never hand-edit the .xlsx. |
| `verify_workbook.py` | Post-build structural checks. Exits non-zero on failure. |

## Usage

```bash
pip install openpyxl
python3 build_workbook.py
python3 verify_workbook.py
```

## Rules this codebase enforces

1. **A value exists only if it was verified against its issuing authority.**
   Nothing is interpolated, smoothed, or inferred from a neighbouring year.
   Gaps are left as gaps.
2. **`02_MASTER` is the single source of truth.** Figure sheets contain no typed
   numbers — every cell is a `COUNTIFS`/`SUMIFS` lookup against it.
3. **Denominators are recorded per observation** and series with different
   denominators are never plotted on one axis.
4. **A policy event is evidence and is held to the same standard.** Every row in
   `POLICY_EVENTS` carries a real date, an honest `precision` (`day`/`month`/
   `year` — never dated more finely than its source allows), a legal citation, a
   `source_id`, and the series it bears on.

`verify_workbook.py` checks all three mechanically, including that every lookup
a formula performs resolves to a real observation — a mistyped series code would
otherwise render as a silent blank cell.

## Presentation conventions

Chart styling follows the conventions used in professional financial-analysis
workbooks, and `verify_workbook.py` enforces them so a later edit cannot undo
the pass silently:

- **Chart titles live in cells**, not on chart objects — they align to the sheet
  grid, stay editable, and avoid openpyxl's inconsistent title rendering.
- **Colour routes attention rather than distinguishing categories.** A four-step
  ramp (`E8E8E8` / `A3A3A3` / `2E6DB4` accent / `1F3A5F` navy). Denmark takes the
  accent; comparators recede into grey. Every chart must use the accent
  somewhere — a chart with no subject fails verification.
- **No chart chrome**: no style presets, no gridlines, axis lines hidden, legends
  at the bottom, `gapWidth=80`.
- **Four-part number formats**: positive; negative; zero; text. Because
  `lookup()` returns `""` for an absent observation, the text section makes a
  gap render as an en-dash rather than an empty cell — a gap should look like a
  gap, not like an oversight.

  *Caveat:* a genuine zero also renders as an en-dash. No series in this dataset
  has a meaningful zero, so this is safe here; it would not be in a workbook
  that did.

## Adding data

Append rows to `OBS` in `dataset.py` using the existing 10-column shape, add any
new source to `SOURCES` in `sources.py`, then rebuild and verify. To extend the
EU cross-section on `F5_EU27`, add rows under series codes matching
`XX.ECM.IND.BUY`; the sheet and its chart expand automatically.

The adoption measure (`XX.ECM.IND.BUY`, 2024) is now complete for all 27 member
states from the `isoc_ec_ib20` databrowser extract (`ES7`), so `F5_EU27` is a
full EU ranking and Figure 6 no longer carries a tail-selection bias. What
remains incomplete is the outcome measure: nine member states hold adoption but
not `XX.ECM.ENT.TRN`, and `F6_ADOPT_BENEFIT` names each one with its exact
series code. `cross_section()` in `dataset.py` recomputes the pairing at build
time, so adding those rows moves countries into the plotted table, raises `n`,
and updates the OLS statistics without touching the build script.

Prefer a databrowser extract to a press release. A press release names the
countries that make a story — the top, the bottom, a couple of movers — which is
a sample drawn from the tails. `F6_ADOPT_BENEFIT` keeps the measured cost of
having done that once: the tail-only sample reported R² 0.853 against 0.674 on
the complete cross-section, while the slope moved only from +0.655 to +0.602.

## Corrections are recorded, not erased

Where a claim has been withdrawn, the withdrawal stays in the workbook: the
SMV:Digital defunding claim is recorded in `09_POLICY`, `07_LIMITATIONS` and
`08_AI_LOG`, and `verify_workbook.py` fails the build if that record disappears.
A correction that leaves no trace is indistinguishable from never having made
the error, which is precisely what the AI Use and Validation Appendix must be
able to show.
