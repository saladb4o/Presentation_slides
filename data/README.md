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

## Adding data

Append rows to `OBS` in `dataset.py` using the existing 10-column shape, add any
new source to `SOURCES` in `sources.py`, then rebuild and verify. To extend the
EU cross-section on `F5_EU8`, add rows under series codes matching
`XX.ECM.IND.BUY`; the sheet and its chart expand automatically.

To extend the Figure 6 cross-section, retrieve Eurostat `isoc_ec_ib20` for 2024
for all 27 member states. `F6_ADOPT_BENEFIT` names every country still missing
and the exact series code for each, and recomputes the pairing at build time —
so adding rows moves countries into the plotted table automatically. Doing this
also removes the tail-selection bias documented on that sheet.

## Corrections are recorded, not erased

Where a claim has been withdrawn, the withdrawal stays in the workbook: the
SMV:Digital defunding claim is recorded in `09_POLICY`, `07_LIMITATIONS` and
`08_AI_LOG`, and `verify_workbook.py` fails the build if that record disappears.
A correction that leaves no trace is indistinguishable from never having made
the error, which is precisely what the AI Use and Validation Appendix must be
able to show.
