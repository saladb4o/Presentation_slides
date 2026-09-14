"""Post-build verification of the data workbook.

Run:  python3 verify_workbook.py

Checks the structural guarantees the workbook claims on its README sheet. Exits
non-zero if any guarantee is broken.
"""

import os
import sys

from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import REFERENCE_ONLY  # noqa: E402

PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx",
)

EXPECTED = [
    "00_COVER", "01_README", "02_MASTER", "03_SOURCES", "04_DEFINITIONS",
    "05_CALC", "F1_BRANCHES", "F2_PAYMENTS", "F3_ESALES", "F4_EXCLUSION",
    "F5_EU27", "F6_ADOPT_BENEFIT", "F7_QUALITY", "F8_SMVDIGITAL",
    "F9_CONSOLIDATION", "F10_SKILLS", "F11_EWASTE", "06_RETAIL_GAP", "07_LIMITATIONS", "08_AI_LOG",
    "09_POLICY",
]

FIG_SHEETS = ["F1_BRANCHES", "F2_PAYMENTS", "F3_ESALES", "F4_EXCLUSION",
              "F5_EU27", "F6_ADOPT_BENEFIT", "F7_QUALITY", "F8_SMVDIGITAL",
              "F9_CONSOLIDATION", "F10_SKILLS", "F11_EWASTE"]

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
                       "unit", "denominator", "flag", "source_id", "compiled_date",
                       "notes"], f"MASTER headers differ: {headers}")

src_ids = {r[0].value for r in wb["03_SOURCES"].iter_rows(min_row=2, max_col=1)
           if r[0].value}
check(len(src_ids) > 0, "SOURCES sheet has no source_ids")

rows = list(m.iter_rows(min_row=2, values_only=True))
check(len(rows) == 136, f"expected 136 observations, found {len(rows)}")

seen = set()
for r in rows:
    obs_id, code, ind, geo, year, val, unit, denom, flag, src, acc, note = r[:12]
    check(src in src_ids, f"obs {obs_id}: source_id {src!r} not in SOURCES")
    check(bool(unit), f"obs {obs_id}: missing unit")
    check(bool(denom), f"obs {obs_id}: missing denominator")
    check(isinstance(val, (int, float)), f"obs {obs_id}: non-numeric value {val!r}")
    check(bool(acc), f"obs {obs_id}: missing compiled_date")
    key = (code, geo, year)
    check(key not in seen, f"duplicate observation {key}")
    seen.add(key)

# 3. SOURCES completeness
for r in wb["03_SOURCES"].iter_rows(min_row=2, values_only=True):
    if not r[0]:
        continue
    # A retrievable address and an access date are what let a marker check a
    # value against its issuer, so every source the workbook draws on must
    # carry both. A spoken guest lecture has neither and cannot be made to:
    # it is exempt only if it supplies no observation, which REFERENCE_ONLY
    # already declares and check 18 already enforces from the other side.
    if r[0] in REFERENCE_ONLY and not r[4] and not r[5]:
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
                                        "INTERCEPT(", "COUNT(", "STEYX(",
                                        "DEVSQ(", "TINV(", "AVERAGE(",
                                        "TTEST("))]
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pathlib
from sources import REFERENCE_ONLY

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
                                                 "INTERCEPT(", "COUNT(",
                                                 "STEYX(", "DEVSQ(", "TINV(",
                                                 "AVERAGE(", "TTEST(")),
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
                   "F4_EXCLUSION": 1, "F5_EU27": 1,
                   "F6_ADOPT_BENEFIT": 1, "F7_QUALITY": 2, "F8_SMVDIGITAL": 1,
                   "F9_CONSOLIDATION": 1, "F10_SKILLS": 1, "F11_EWASTE": 1}
for name, n in expected_charts.items():
    check(len(wb[name]._charts) == n,
          f"{name}: expected {n} chart(s), found {len(wb[name]._charts)}")

# 9. the policy sheet. An event marker is a factual claim about when an
# instrument took effect, so it carries the same evidential burden as a value:
# a real date, an honest precision, a legal citation, a resolvable source, and a
# series that actually exists in MASTER.
from datetime import date as _date

from dataset import OBS, POLICY_EVENTS

pol = wb["09_POLICY"]
# Event rows are those carrying a precision keyword in column B; the trailing
# source_note paragraphs on this sheet also occupy column A and must not be
# mistaken for events.
pol_rows = [r for r in pol.iter_rows(min_row=5, max_col=7, values_only=True)
            if r[0] and r[1] in ("day", "month", "year")]
check(len(pol_rows) == len(POLICY_EVENTS),
      f"09_POLICY has {len(pol_rows)} events, dataset has {len(POLICY_EVENTS)}")

master_codes = {r[1] for r in rows}
for when, precision, name, citation, src, desc, related in pol_rows:
    try:
        _date.fromisoformat(str(when))
    except ValueError:
        check(False, f"policy event {name!r}: {when!r} is not a real date")
    check(precision in ("day", "month", "year"),
          f"policy event {name!r}: bad date precision {precision!r}")
    check(bool(citation), f"policy event {name!r}: no legal citation")
    check(src in src_ids, f"policy event {name!r}: source_id {src!r} not in SOURCES")
    check(bool(desc), f"policy event {name!r}: no description")
    check(related in master_codes,
          f"policy event {name!r}: series {related!r} is not in MASTER")

# 10. Figure 6 must not advertise R-squared on the chart face, and must carry
# the selection warning. The sample is drawn from the tails of the adoption
# distribution, so displaying goodness-of-fit as a headline would overstate it.
f6 = wb["F6_ADOPT_BENEFIT"]
check(len(f6._charts) == 1, "F6 should have exactly one chart")
tl = f6._charts[0].series[0].trendline
check(tl is not None, "F6 trendline missing")
# R-squared was withheld while X was a tail-selected press-release sample. X is
# now the complete isoc_ec_ib20 extract, so the statistic is earned and must be
# shown - withholding it now would understate a fit the sample supports.
check(tl.dispRSqr,
      "F6 does not display R-squared; the cross-section is complete on X, so "
      "the statistic is earned and should be on the chart face")
f6_text = " ".join(str(c.value) for row in f6.iter_rows() for c in row
                   if isinstance(c.value, str))
check("SAMPLE - how these points were obtained" in f6_text,
      "F6 has no sample-provenance block")
# The superseded tail-only result is kept deliberately: it measures the bias
# rather than asserting it. Losing it would turn a demonstration back into a
# claim, so the numbers are pinned here.
for phrase in ("tails", "isoc_ec_ib20", "0.853", "0.674", "+0.655", "+0.602"):
    check(phrase in f6_text.lower(),
          f"F6 provenance block does not mention {phrase!r}")
# n must have actually grown; a silent regression to the old sample would
# otherwise leave every surrounding sentence wrong.
n_cell = [c.value for row in f6.iter_rows() for c in row
          if isinstance(c.value, str) and c.value.startswith("=COUNT(")]
check(len(n_cell) == 1, "F6 should have exactly one n formula")
check("$C$5:$C$22" in n_cell[0],
      f"F6 n formula does not span 18 paired countries: {n_cell[0]}")

# 11. The withdrawn SMV:Digital defunding claim must be recorded, not erased.
# A correction that leaves no trace is indistinguishable from never having made
# the error, which is precisely what the AI Use appendix has to be able to show.
all_text = " ".join(
    str(c.value) for sheet in ("09_POLICY", "07_LIMITATIONS", "08_AI_LOG")
    for row in wb[sheet].iter_rows() for c in row if isinstance(c.value, str))
check("defunded" in all_text,
      "the withdrawn SMV:Digital defunding claim is not recorded anywhere")
check(not any("defund" in str(r[11] or "") for r in rows),
      "a defunding claim survives in MASTER notes")

# 12. Chart styling conventions. These are enforced rather than merely applied
# because a later edit that re-adds an Excel style preset or a chart-object
# title would undo the whole presentation pass silently - the workbook would
# still build, still verify, and just look generic again.
# Imported rather than restated. These were duplicated as literals here, so
# changing a palette constant in the builder failed this check instead of
# updating it - the verifier was asserting against a stale copy of the thing it
# was meant to be verifying.
from build_workbook import C_ACCENT as ACCENT, C_GREY as GREY  # noqa: E402
from build_workbook import C_DARK as DARK, C_PALE as PALE      # noqa: E402
PALETTE = {ACCENT, GREY, DARK, PALE}

for name, n_charts in expected_charts.items():
    ws = wb[name]
    for i, ch in enumerate(ws._charts):
        where = f"{name} chart[{i}]"
        # Titles live in cells, not on chart objects.
        check(ch.title is None, f"{where}: has a chart-object title; "
                                f"titles belong in a cell above the chart")
        check(ch.style is None, f"{where}: carries an Excel style preset")
        for ax_name in ("x_axis", "y_axis"):
            ax = getattr(ch, ax_name, None)
            if ax is None:
                continue
            check(ax.majorGridlines is None, f"{where}: {ax_name} has gridlines")
            check(ax.spPr is not None and ax.spPr.ln is not None
                  and ax.spPr.ln.noFill,
                  f"{where}: {ax_name} line is not hidden")
        if ch.legend is not None:
            check(ch.legend.position == "b",
                  f"{where}: legend is not at the bottom")

        # Every chart uses the palette and nothing else.
        used = set()
        for s in ch.series:
            g = s.graphicalProperties
            if g is not None and g.solidFill is not None:
                used.add(g.solidFill if isinstance(g.solidFill, str)
                         else g.solidFill.srgbClr)
            for dp in (s.data_points or []):
                if dp.spPr is not None and dp.spPr.solidFill is not None:
                    f = dp.spPr.solidFill
                    used.add(f if isinstance(f, str) else f.srgbClr)
            if s.marker is not None and s.marker.spPr is not None \
                    and s.marker.spPr.solidFill is not None:
                f = s.marker.spPr.solidFill
                used.add(f if isinstance(f, str) else f.srgbClr)
        used.discard(None)
        check(used, f"{where}: no series colour set; it will render in "
                    f"Excel's default palette")
        check(used <= PALETTE,
              f"{where}: colours outside the palette: {sorted(used - PALETTE)}")
        check(ACCENT in used,
              f"{where}: the accent colour is absent - nothing in this chart "
              f"is marked as its subject")

# 13. Every chart has a title cell directly above its anchor. openpyxl records
# the anchor zero-indexed, so the title row is the anchor row (1-indexed) minus
# one - i.e. the cell immediately above where the chart is placed.
for name in expected_charts:
    ws = wb[name]
    for i, ch in enumerate(ws._charts):
        frm = ch.anchor._from
        title_cell = ws.cell(row=frm.row, column=frm.col + 1)
        check(isinstance(title_cell.value, str) and title_cell.value.strip(),
              f"{name} chart[{i}]: no title cell at {title_cell.coordinate} "
              f"(directly above the chart anchor)")

# 14. Missing values must render as an en-dash, not as an empty cell. lookup()
# returns "" for an absent observation, which lands in the text section of the
# four-part format - so the format must define that section.
for name in FIG_SHEETS:
    ws = wb[name]
    for row in ws.iter_rows(min_row=5):
        for c in row:
            if not (isinstance(c.value, str) and c.value.startswith("=")):
                continue
            if c.column == 1:
                continue
            check(c.number_format.count(";") == 3,
                  f"{name}!{c.coordinate}: number format {c.number_format!r} "
                  f"is not four-part; a missing value would render blank")

# 15. Same four-part rule on 05_CALC. Found by audit: the calc sheet was using
# bare "0.00"/"0.0%"/"#,##0", so a missing input would have rendered as an empty
# cell there while every figure sheet showed an en-dash.
ws = wb["05_CALC"]
for row in ws.iter_rows(min_row=2):
    for c in row:
        if isinstance(c.value, str) and c.value.startswith("=") and c.column == 2:
            check(c.number_format.count(";") == 3,
                  f"05_CALC!{c.coordinate}: number format "
                  f"{c.number_format!r} is not four-part")

# 16. Every series family in MASTER must be documented in 04_DEFINITIONS.
# Found by audit: 35 of 113 observations sat on families with no definition
# entry, including the series behind F9 and F10. Traceability is the whole
# claim this workbook makes, so an undocumented series is a defect, not a gap.
defs_text = " ".join(str(c.value) for row in wb["04_DEFINITIONS"].iter_rows()
                     for c in row if c.value)
families = set()
for r in range(2, m.max_row + 1):
    code = m.cell(row=r, column=2).value
    if code:
        families.add(".".join(code.split(".")[1:]))
for fam in sorted(families):
    check(fam in defs_text,
          f"series family {fam} has no entry in 04_DEFINITIONS")

# 17. A figure's source note must name every source its own data carries.
# Found by audit: F6 credited X to ES4 - the superseded rounded press release
# whose tail selection that very sheet criticises - while the data carried ES7.
# Checking that source_ids resolve is not enough; the prose has to agree with
# the data it sits under.
sources = wb["03_SOURCES"]
sid_list = [str(sources.cell(row=r, column=1).value)
            for r in range(2, sources.max_row + 1)
            if sources.cell(row=r, column=1).value]
SID_RE = re.compile(r"\b(" + "|".join(sorted(sid_list, key=len, reverse=True)) + r")\b")
LOOK_RE = re.compile(r"'02_MASTER'!\$B:\$B,\"([^\"]+)\","
                     r"'02_MASTER'!\$E:\$E,(\d+)\)")
src_of = {}
for r in range(2, m.max_row + 1):
    code = m.cell(row=r, column=2).value
    if code:
        src_of[(code, m.cell(row=r, column=5).value)] = \
            m.cell(row=r, column=10).value
for name in FIG_SHEETS:
    ws = wb[name]
    used, cited = set(), set()
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                for mt in LOOK_RE.finditer(c.value):
                    got = src_of.get((mt.group(1), int(mt.group(2))))
                    if got:
                        used.add(got)
            elif isinstance(c.value, str):
                cited.update(SID_RE.findall(c.value))
    for sid in sorted(used - cited):
        check(False,
              f"{name} draws on {sid} but never names it in prose; a marker "
              f"tracing that value has nowhere to go")

# 18. Every declared source must be reachable from something. Found by audit:
# three sources were declared, attached to no observation and cited nowhere.
all_cited = set()
for ws in wb:
    if ws.title == "03_SOURCES":
        continue
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str):
                all_cited.update(SID_RE.findall(c.value))
used_by_obs = {m.cell(row=r, column=10).value
               for r in range(2, m.max_row + 1)
               if m.cell(row=r, column=2).value}
# The workbook is not the only consumer. A source may legitimately carry no
# observation and appear in no workbook cell, and still be doing real work by
# supporting an argument in the report - the two Danish and comparative legal
# sources are exactly that. Scanning the report drafts here keeps this check
# from forcing such a source into REFERENCE_ONLY, which would in turn make the
# report-side check on REFERENCE_ONLY vacuous. Between them the two checks
# leave no way for a declared source to be reachable from nothing.
_draft_dir = pathlib.Path(__file__).resolve().parent.parent / "report" / "draft"
_draft_text = "".join(f.read_text() for f in sorted(_draft_dir.rglob("*.md")))
# Bracketed citation tokens only. A bare mention in prose or in the Section 5
# planning stub is scaffolding, not a citation, and must not satisfy this check.
cited_in_report = set(re.findall(r"\[\[([A-Z]+\d*)(?::[yb])?\]\]", _draft_text))
for sid in sid_list:
    check(sid in all_cited or sid in used_by_obs or sid in cited_in_report
          or sid in REFERENCE_ONLY,
          f"source {sid} is declared but carries no observation and is cited "
          f"nowhere - not in the workbook, not in the report - and is not "
          f"declared REFERENCE_ONLY. Remove it or cite it")

# 19. (code,year) must be unique. Every figure lookup is a SUMIFS on those two
# keys, so a duplicate pair would be silently SUMMED into a doubled value that
# looks entirely plausible on the chart.
seen_keys = {}
for r in range(2, m.max_row + 1):
    code = m.cell(row=r, column=2).value
    if not code:
        continue
    key = (code, m.cell(row=r, column=5).value)
    check(key not in seen_keys,
          f"duplicate (series_code, year) {key} at rows "
          f"{seen_keys.get(key)} and {r}: SUMIFS lookups would double it")
    seen_keys[key] = r

# ---------------------------------------------------------------- report ---
print(f"{checks} checks run")
if failures:
    print(f"\n{len(failures)} FAILURES:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("all checks passed")
