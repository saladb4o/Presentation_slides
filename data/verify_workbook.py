"""Post-build verification of the data workbook.

Run:  python3 verify_workbook.py

Checks the structural guarantees the workbook claims on its README sheet. Exits
non-zero if any guarantee is broken.
"""

import os
import sys

from openpyxl import load_workbook

PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx",
)

EXPECTED = [
    "00_COVER", "01_README", "02_MASTER", "03_SOURCES", "04_DEFINITIONS",
    "05_CALC", "F1_BRANCHES", "F2_PAYMENTS", "F3_ESALES", "F4_EXCLUSION",
    "F5_EU8", "F6_ADOPT_BENEFIT", "06_RETAIL_GAP", "07_LIMITATIONS", "08_AI_LOG",
]

FIG_SHEETS = ["F1_BRANCHES", "F2_PAYMENTS", "F3_ESALES", "F4_EXCLUSION",
              "F5_EU8", "F6_ADOPT_BENEFIT"]

failures = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        failures.append(msg)


wb = load_workbook(PATH)

# 1. sheets present and non-empty
check(wb.sheetnames == EXPECTED, f"sheet order/names differ: {wb.sheetnames}")
for name in EXPECTED:
    ws = wb[name]
    filled = sum(1 for row in ws.iter_rows() for c in row if c.value not in (None, ""))
    check(filled > 5, f"{name} looks empty ({filled} filled cells)")

# 2. MASTER integrity
m = wb["02_MASTER"]
headers = [c.value for c in m[1]]
check(headers[:12] == ["obs_id", "series_code", "indicator", "geo", "year", "value",
                       "unit", "denominator", "flag", "source_id", "extraction_date",
                       "notes"], f"MASTER headers differ: {headers}")

src_ids = {r[0].value for r in wb["03_SOURCES"].iter_rows(min_row=2, max_col=1)
           if r[0].value}
check(len(src_ids) > 0, "SOURCES sheet has no source_ids")

rows = list(m.iter_rows(min_row=2, values_only=True))
check(len(rows) == 87, f"expected 87 observations, found {len(rows)}")

seen = set()
for r in rows:
    obs_id, code, ind, geo, year, val, unit, denom, flag, src, acc, note = r[:12]
    check(src in src_ids, f"obs {obs_id}: source_id {src!r} not in SOURCES")
    check(bool(unit), f"obs {obs_id}: missing unit")
    check(bool(denom), f"obs {obs_id}: missing denominator")
    check(isinstance(val, (int, float)), f"obs {obs_id}: non-numeric value {val!r}")
    check(bool(acc), f"obs {obs_id}: missing extraction_date")
    key = (code, geo, year)
    check(key not in seen, f"duplicate observation {key}")
    seen.add(key)

# 3. SOURCES completeness
for r in wb["03_SOURCES"].iter_rows(min_row=2, values_only=True):
    if not r[0]:
        continue
    check(bool(r[4]) and str(r[4]).startswith("http"), f"source {r[0]}: bad URL {r[4]!r}")
    check(bool(r[5]), f"source {r[0]}: missing accessed date")
    check(bool(r[6]), f"source {r[0]}: missing Harvard reference")

# 4. figure sheets contain no typed numbers in their data columns
for name in FIG_SHEETS:
    ws = wb[name]
    literals = []
    for row in ws.iter_rows(min_row=5):
        for c in row:
            if c.column == 1:
                continue  # labels and year keys are allowed to be literal
            if isinstance(c.value, (int, float)):
                literals.append(f"{name}!{c.coordinate}={c.value}")
    check(not literals, f"{name}: literal values in data columns: {literals[:5]}")

# 5. every figure data cell that is populated is a formula over MASTER
for name in FIG_SHEETS:
    ws = wb[name]
    formulas = [c.value for row in ws.iter_rows(min_row=5) for c in row
                if isinstance(c.value, str) and c.value.startswith("=")]
    check(len(formulas) > 0, f"{name}: no formulas found")
    bad = [f for f in formulas if "02_MASTER" not in f
           and not any(k in f for k in ("SLOPE(", "RSQ(", "CORREL(",
                                        "INTERCEPT(", "COUNT("))]
    check(not bad, f"{name}: formulas not referencing MASTER: {bad[:3]}")

# 6. CALC sheet is all formulas
calc = wb["05_CALC"]
calc_vals = [c.value for row in calc.iter_rows(min_row=5, min_col=2, max_col=2)
             for c in row if c.value is not None]
check(all(isinstance(v, str) and v.startswith("=") for v in calc_vals),
      "05_CALC column B contains non-formula values")
check(len(calc_vals) >= 15, f"05_CALC has only {len(calc_vals)} derived quantities")

# 7. the denominator break is flagged
buy = [r for r in rows if r[1] == "DK.ECM.IND.BUY"]
r2019 = [r for r in buy if r[4] == 2019][0]
r2020 = [r for r in buy if r[4] == 2020][0]
check(r2019[8] == "b", "2019 online-purchasing row is not flagged 'b'")
check(r2019[7] != r2020[7], "2019 and 2020 denominators are identical")

# 7b. every lookup embedded in a formula resolves to a real observation.
# LibreOffice is unavailable in this container, so instead of recalculating the
# file we re-implement the COUNTIFS/SUMIFS semantics and confirm each (series,
# year) pair a formula asks for actually exists in MASTER. This catches the real
# risk - a mistyped series code or year silently rendering as a blank cell.
import re

LOOKUP_RE = re.compile(
    r"COUNTIFS\('02_MASTER'!\$B:\$B,\"([^\"]+)\",'02_MASTER'!\$E:\$E,(\d{4})\)"
)

master_keys = {(r[1], r[4]) for r in rows}
resolved = 0
for name in FIG_SHEETS + ["05_CALC"]:
    ws = wb[name]
    for row in ws.iter_rows(min_row=5):
        for c in row:
            if not (isinstance(c.value, str) and c.value.startswith("=")):
                continue
            pairs = LOOKUP_RE.findall(c.value)
            if not pairs:
                # F6's OLS cells (SLOPE/RSQ/CORREL/INTERCEPT/COUNT) operate on
                # ranges of lookup cells rather than performing a lookup of
                # their own. Anything else with no lookup is a bug.
                check(any(k in c.value for k in ("SLOPE(", "RSQ(", "CORREL(",
                                                 "INTERCEPT(", "COUNT(")),
                      f"{name}!{c.coordinate}: formula has no parsable lookup")
                continue
            for code, year in pairs:
                resolved += 1
                check((code, int(year)) in master_keys,
                      f"{name}!{c.coordinate}: lookup ({code}, {year}) "
                      f"has no matching observation - cell would render blank")

check(resolved >= 40, f"only {resolved} lookups resolved; expected more")

# 8. charts present
expected_charts = {"F1_BRANCHES": 1, "F2_PAYMENTS": 2, "F3_ESALES": 1,
                   "F4_EXCLUSION": 1, "F5_EU8": 1,
                   "F6_ADOPT_BENEFIT": 1}
for name, n in expected_charts.items():
    check(len(wb[name]._charts) == n,
          f"{name}: expected {n} chart(s), found {len(wb[name]._charts)}")

# ---------------------------------------------------------------- report ---
print(f"{checks} checks run")
if failures:
    print(f"\n{len(failures)} FAILURES:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("all checks passed")
