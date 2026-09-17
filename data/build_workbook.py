"""Build the ECON1596 Assessment 2 data workbook.

Run:  python3 build_workbook.py && python3 verify_workbook.py

The workbook is generated, never hand-edited. To correct a value, edit dataset.py
and rebuild.

TWO RULES THIS BUILD ENFORCES BY CONSTRUCTION
---------------------------------------------
1. Every derived cell is written as a live formula over 02_MASTER *and* carries
   the value Python computed for it. XlsxWriter's write_formula() takes both. The
   formula keeps the workbook auditable in Excel; the cached value means the file
   also displays correctly in a previewer that has no calculation engine, which
   the previous build did not - it shipped 201 formulas and zero cached values,
   so anything without a calc engine showed blank cells and empty charts.

2. A lookup to an observation that does not exist raises at build time. The
   previous build wrapped every lookup in IF(COUNTIFS(...)=0,"",...) so a mistyped
   series code rendered as a silent blank. Failing the build is better than
   rendering a gap that nobody notices.
"""

import os
import sys
from datetime import date

import xlsxwriter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import COUNTRIES, OBS, POLICY_EVENTS, cross_section, validate
from sources import ACCESSED, SOURCES
import style
from style import finish

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx")

STUDENT_ID = "s4040040"
COURSE = "ECON1596/ECON1597 Digital Economy and Policy"
VERSION = "2.0"
BUILT = date.today().isoformat()

MASTER = "02_MASTER"

# 02_MASTER column layout, 0-indexed. The header row is row 0, so observation i
# sits on row i+1 and Excel sees it on row i+2.
M_ID, M_CODE, M_IND, M_GEO, M_YEAR, M_VAL, M_UNIT, M_DENOM, M_FLAG, M_SRC, \
    M_REF, M_NOTE = range(12)

MASTER_HEADERS = [
    "obs_id", "series_code", "indicator", "geo", "year", "value", "unit",
    "denominator", "flag", "source_id", "report_ref", "notes",
]

FIRST = 2                    # first Excel data row on 02_MASTER
LAST = 1 + len(OBS)          # last Excel data row

# Which report figure each series feeds. Read off report/build_figures.py, which
# is the only place the report decides what a figure plots. This is the column
# that lets a marker go from a number in the report to its row here in one step.
FIGURE_SERIES = {
    "Fig 1": ["DK.FIN.BRCH"],
    "Fig 2": ["DK.FIN.INST", "DK.FIN.BRCH", "DK.FIN.EMP"],
    "Fig 4": ["DK.ECM.ENT.TRN", "EU.ECM.ENT.TRN"],
    "Fig 5": ["DK.ENT.AI", "DK.ENT.AI.LRG", "DK.ENT.AI.SME"],
    "Fig 6": ["DK.DGP.EXMP", "DK.DGX.NOUSE", "DK.DGX.DIFF", "DK.DGX.DISADV.LO",
              "DK.DGX.DISADV.HI", "DK.DGX.JUST"],
    "Fig 7": ["DK.SKL.1624", "EU.SKL.1624", "DK.SKL.2554", "EU.SKL.2554",
              "DK.SKL.5574", "EU.SKL.5574"],
    "Fig 8": ["DK.SME.SMVD.INV", "DK.SME.SMVD.NOINV", "DK.SME.SMVD.PROJ"],
    "Fig 9": ["DK.ENV.WEEE", "EU.ENV.WEEE"],
    "Fig 10": ["DK.DGX.EGOV.USE", "EU.DGX.EGOV.USE", "DK.DGX.DIFF",
               "DK.DGX.NOUSE", "DK.DGP.EXMP", "DK.FIN.INST", "DK.FIN.BRCH",
               "DK.FIN.EMP", "DK.ENT.AI.LRG", "DK.ENT.AI.SME"],
    "App. A": ["DK.PRD.LP.PER"],
    "App. D": ["DK.POP.TOT", "DK.DGP.EXMP.N"],
    "App. E": ["DK.PAY.CASH.POS", "DK.PAY.CRD.PHYS", "DK.PAY.WLT.SHR",
               "EU.ECM.IND.BUY"],
}


def _report_refs():
    """series_code -> the figures it feeds, as 'Fig 1; Fig 2'."""
    out = {}
    for fig, codes in FIGURE_SERIES.items():
        for code in codes:
            out.setdefault(code, []).append(fig)
    return {c: "; ".join(f) for c, f in out.items()}


REPORT_REF = _report_refs()

# Observation index. Series codes carry their own geography (DK.*, EU.*, AT.*),
# so code and year identify an observation uniquely - asserted below.
INDEX = {}
for _row in OBS:
    _key = (_row[0], _row[3])
    assert _key not in INDEX, f"duplicate observation: {_key}"
    INDEX[_key] = _row


def val(code, year):
    """The published value, or raise. Raising is the point - see module docstring."""
    try:
        return INDEX[(code, year)][4]
    except KeyError:
        raise KeyError(
            f"no observation {code} {year}. Add it to dataset.py, or stop "
            f"referring to it - do not interpolate one."
        ) from None


def ref(code, year):
    """A live SUMIFS over 02_MASTER returning that observation's value.

    Bounded to the real data rows rather than whole columns: 200-odd formulas
    each scanning $B:$B over a million rows is slow for no gain.
    """
    val(code, year)          # fail here, not silently in Excel
    return (f"SUMIFS('{MASTER}'!$F${FIRST}:$F${LAST},"
            f"'{MASTER}'!$B${FIRST}:$B${LAST},\"{code}\","
            f"'{MASTER}'!$E${FIRST}:$E${LAST},{year})")


def unit_of(code, year):
    return INDEX[(code, year)][5]


def flag_of(code, year):
    return INDEX[(code, year)][7]


def src_of(code, year):
    return INDEX[(code, year)][8]


# --------------------------------------------------------------- 00_COVER ---
def sheet_cover(wb, fmt, contents):
    ws = wb.add_worksheet("00_COVER")
    ws.write(0, 0, "Denmark: digital adoption and policy outcomes", fmt["title"])
    ws.write(1, 0, "Statistical annex to Assessment 2 - Digital Policy and "
                   "Innovation Report", fmt["subtitle"])

    meta = [
        ("Student ID", STUDENT_ID),
        ("Course", COURSE),
        ("Country", "Denmark (assigned by final digit of student ID: 0)"),
        ("Workbook version", VERSION),
        ("Built", BUILT),
        ("Observations", len(OBS)),
        ("Sources", len(SOURCES)),
        ("Coverage", "1991-2026, unbalanced; see 07_LIMITATIONS"),
    ]
    r = 3
    for k, v in meta:
        ws.write(r, 0, k, fmt["label"])
        ws.write(r, 1, v, fmt["text_n"] if not isinstance(v, int) else fmt["int"])
        r += 1

    r += 1
    ws.write(r, 0, "How to trace any number in the report", fmt["section"])
    r += 1
    for line in [
        "1. The figure caption in the report names a workbook sheet.",
        "2. That sheet shows the series_code beside each value.",
        "3. Filter 02_MASTER by that series_code to reach the observation row.",
        "4. The row carries its unit, its denominator and a source_id.",
        "5. Look the source_id up in 03_SOURCES for the authority, the dataset "
        "code, the URL and the date it was retrieved.",
    ]:
        ws.write(r, 0, line, fmt["prose"])
        r += 1

    r += 1
    ws.write(r, 0, "Colour legend", fmt["section"])
    r += 1
    for swatch, text in [
        ("swatch_plain", "Retrieved value, exactly as published by the source"),
        ("swatch_derived", "Derived - calculated by formula from retrieved values"),
        ("swatch_flagged", "Flagged - an estimate, a break in series, or provisional"),
        ("swatch_gap", "Documented gap - the value was not retrieved"),
    ]:
        ws.write_blank(r, 0, None, fmt[swatch])
        ws.write(r, 1, text, fmt["prose_n"])
        r += 1

    r += 1
    ws.write(r, 0, "Contents", fmt["section"])
    r += 1
    contents_at = r
    for name, desc in contents:
        ws.write(r, 0, name, fmt["code"])
        ws.write(r, 1, desc, fmt["prose_n"])
        r += 1

    r += 1
    ws.write(r, 0, "Provenance rule", fmt["label"])
    ws.write(r, 1, "Every value here was verified against the issuing authority "
                   "named in its source_id. Nothing is interpolated, smoothed or "
                   "inferred from a neighbouring year. Gaps are left as gaps.",
             fmt["prose"])
    r += 1
    ws.write(r, 0, "Suggested citation", fmt["label"])
    ws.write(r, 1, f"Denmark: digital adoption and policy outcomes [data "
                   f"workbook], v{VERSION}, {BUILT}. Compiled from the sources "
                   f"listed in 03_SOURCES.", fmt["prose"])

    finish(ws, [(0, 0, 26), (1, 1, 96)], hide_grid=True, landscape=False,
           tab=style.TAB_REFERENCE)
    ws.set_row(0, 22)
    return contents_at


# -------------------------------------------------------------- 02_MASTER ---
def sheet_master(wb, fmt):
    ws = wb.add_worksheet(MASTER)
    for c, h in enumerate(MASTER_HEADERS):
        ws.write(0, c, h, fmt["head"])

    for i, (code, ind, geo, year, value, unit, denom, flag, src, note) \
            in enumerate(OBS):
        r = i + 1
        numfmt = fmt["flagged"] if flag else (
            fmt["int"] if unit == "count" else fmt["num"])
        ws.write_number(r, M_ID, i + 1, fmt["int"])
        ws.write_string(r, M_CODE, code, fmt["code"])
        ws.write_string(r, M_IND, ind, fmt["text"])
        ws.write_string(r, M_GEO, geo, fmt["text_n"])
        ws.write_number(r, M_YEAR, year, fmt["year"])
        ws.write_number(r, M_VAL, value, numfmt)
        ws.write_string(r, M_UNIT, unit, fmt["text_n"])
        ws.write_string(r, M_DENOM, denom, fmt["text"])
        ws.write_string(r, M_FLAG, flag, fmt["text_n"])
        ws.write_string(r, M_SRC, src, fmt["code"])
        ws.write_string(r, M_REF, REPORT_REF.get(code, ""), fmt["text_n"])
        ws.write_string(r, M_NOTE, note, fmt["text"])

    ws.autofilter(0, 0, len(OBS), len(MASTER_HEADERS) - 1)
    finish(ws, [(M_ID, M_ID, 7), (M_CODE, M_CODE, 21), (M_IND, M_IND, 44),
                (M_GEO, M_GEO, 6), (M_YEAR, M_YEAR, 7), (M_VAL, M_VAL, 12),
                (M_UNIT, M_UNIT, 9), (M_DENOM, M_DENOM, 34),
                (M_FLAG, M_FLAG, 6), (M_SRC, M_SRC, 10), (M_REF, M_REF, 15),
                (M_NOTE, M_NOTE, 56)],
           freeze=(1, 2), hide_grid=False, repeat_header=True,
           tab=style.TAB_REFERENCE)
    ws.set_row(0, 30)


# ------------------------------------------------------------- 03_SOURCES ---
def sheet_sources(wb, fmt):
    ws = wb.add_worksheet("03_SOURCES")
    ws.write(0, 0, "Source register", fmt["title"])
    ws.write(1, 0, "Every source_id used in 02_MASTER, with the authority that "
                   "published it and the date it was retrieved.", fmt["subtitle"])

    heads = ["source_id", "authority", "title", "dataset code", "accessed",
             "URL", "Harvard reference"]
    for c, h in enumerate(heads):
        ws.write(3, c, h, fmt["head"])

    used = {r[8] for r in OBS}
    for i, sid in enumerate(sorted(SOURCES)):
        s = SOURCES[sid]
        r = i + 4
        ws.write_string(r, 0, sid, fmt["code"])
        ws.write_string(r, 1, s["authority"], fmt["text"])
        ws.write_string(r, 2, s["title"], fmt["text"])
        ws.write_string(r, 3, s.get("dataset_code", ""), fmt["code"])
        ws.write_string(r, 4, s.get("accessed", ACCESSED), fmt["text_n"])
        url = s.get("url", "")
        if url:
            ws.write_url(r, 5, url, fmt["link"], url)
        else:
            ws.write_string(r, 5, "", fmt["text"])
        ws.write_string(r, 6, s["harvard"], fmt["text"])

    ws.autofilter(3, 0, 3 + len(SOURCES), len(heads) - 1)
    finish(ws, [(0, 0, 10), (1, 1, 30), (2, 2, 42), (3, 3, 16), (4, 4, 11),
                (5, 5, 48), (6, 6, 80)],
           freeze=(4, 1), hide_grid=False, tab=style.TAB_REFERENCE)
    ws.set_row(3, 28)
    return used


# --------------------------------------------------------- 04_DEFINITIONS ---
def sheet_definitions(wb, fmt):
    ws = wb.add_worksheet("04_DEFINITIONS")
    ws.write(0, 0, "What each series measures", fmt["title"])
    ws.write(1, 0, "One row per series code. The denominator is the column that "
                   "decides whether two values may be compared.", fmt["subtitle"])

    heads = ["series_code", "indicator", "geo", "unit", "denominator",
             "observations", "years", "feeds"]
    for c, h in enumerate(heads):
        ws.write(3, c, h, fmt["head"])

    series = {}
    for code, ind, geo, year, value, unit, denom, flag, src, note in OBS:
        s = series.setdefault(code, {"ind": ind, "geo": geo, "unit": unit,
                                     "denom": denom, "years": []})
        s["years"].append(year)

    for i, code in enumerate(sorted(series)):
        s = series[code]
        r = i + 4
        yrs = sorted(s["years"])
        span = str(yrs[0]) if len(yrs) == 1 else f"{yrs[0]}-{yrs[-1]}"
        ws.write_string(r, 0, code, fmt["code"])
        ws.write_string(r, 1, s["ind"], fmt["text"])
        ws.write_string(r, 2, s["geo"], fmt["text_n"])
        ws.write_string(r, 3, s["unit"], fmt["text_n"])
        ws.write_string(r, 4, s["denom"], fmt["text"])
        ws.write_number(r, 5, len(yrs), fmt["int"])
        ws.write_string(r, 6, span, fmt["text_n"])
        ws.write_string(r, 7, REPORT_REF.get(code, ""), fmt["text_n"])

    r = 5 + len(series)
    ws.write(r, 0, "Flag legend", fmt["section"])
    r += 1
    for k, v in [
        ("b", "Break in series - definition or denominator changed. Do not plot across."),
        ("e", "Estimate - the source gives an approximation or a verbal quantity."),
        ("p", "Provisional."),
        ("d", "Definition differs from the rest of the series."),
        ("u", "Low reliability."),
        ("(blank)", "Value as published, with no qualification."),
    ]:
        ws.write_string(r, 0, k, fmt["code"])
        ws.write_string(r, 1, v, fmt["prose_n"])
        r += 1

    r += 1
    ws.write(r, 0, "A caveat about blanks", fmt["section"])
    r += 1
    ws.merge_range(r, 0, r + 2, 7,
                   "Number formats in this workbook carry a fourth, text section "
                   "so that a value which does not exist renders as an en-dash "
                   "rather than as an empty cell: a gap should look like a gap "
                   "and not like an oversight. The cost is that a genuine zero "
                   "would render the same way. No series here has a meaningful "
                   "zero, so the two cannot be confused in this workbook - but "
                   "they could be in one that did.", fmt["prose"])

    finish(ws, [(0, 0, 21), (1, 1, 46), (2, 2, 6), (3, 3, 9), (4, 4, 36),
                (5, 5, 12), (6, 6, 11), (7, 7, 15)],
           freeze=(4, 1), hide_grid=False, tab=style.TAB_REFERENCE)
    ws.set_row(3, 28)
    return len(series)


# ---------------------------------------------------------------- 05_CALC ---
def derived_quantities():
    """The derived numbers the report cites.

    Each entry is (label, words, unit, formula, python_value). The formula is
    what Excel recalculates; the value is what every other viewer displays. They
    are built from the same observations, so a disagreement between them is a
    bug and verify_workbook.py checks for it.
    """
    q = []

    def add(label, words, unit, formula, value):
        q.append((label, words, unit, formula, value))

    b04, b24 = val("DK.FIN.BRCH", 2004), val("DK.FIN.BRCH", 2024)
    add("Bank branches, 2004", "As published.", "count",
        ref("DK.FIN.BRCH", 2004), b04)
    add("Bank branches, 2024", "As published.", "count",
        ref("DK.FIN.BRCH", 2024), b24)
    add("Branch network, change 2004-2024",
        "2024 branches divided by 2004 branches, less one.", "%",
        f"({ref('DK.FIN.BRCH', 2024)}/{ref('DK.FIN.BRCH', 2004)}-1)*100",
        (b24 / b04 - 1) * 100)

    c17, c25 = val("DK.PAY.CASH.POS", 2017), val("DK.PAY.CASH.POS", 2025)
    add("Cash share of physical-retail payments, 2017", "As published.", "%",
        ref("DK.PAY.CASH.POS", 2017), c17)
    add("Cash share of physical-retail payments, 2025", "As published.", "%",
        ref("DK.PAY.CASH.POS", 2025), c25)
    add("Cash share, change 2017-2025",
        "2025 share less 2017 share, in percentage points.", "pp",
        f"{ref('DK.PAY.CASH.POS', 2025)}-{ref('DK.PAY.CASH.POS', 2017)}",
        c25 - c17)
    add("Cash share, proportional decline 2017-2025",
        "The same change expressed against the 2017 level.", "%",
        f"({ref('DK.PAY.CASH.POS', 2025)}/{ref('DK.PAY.CASH.POS', 2017)}-1)*100",
        (c25 / c17 - 1) * 100)

    d14, d24 = val("DK.ECM.ENT.TRN", 2014), val("DK.ECM.ENT.TRN", 2024)
    e14, e24 = val("EU.ECM.ENT.TRN", 2014), val("EU.ECM.ENT.TRN", 2024)
    add("DK e-sales share of turnover, change 2014-2024",
        "Percentage points, Denmark.", "pp",
        f"{ref('DK.ECM.ENT.TRN', 2024)}-{ref('DK.ECM.ENT.TRN', 2014)}", d24 - d14)
    add("EU e-sales share of turnover, change 2014-2024",
        "Percentage points, EU-27 aggregate.", "pp",
        f"{ref('EU.ECM.ENT.TRN', 2024)}-{ref('EU.ECM.ENT.TRN', 2014)}", e24 - e14)
    add("DK lead over EU on e-sales turnover, 2024",
        "Denmark less the EU-27 aggregate, same year and base.", "pp",
        f"{ref('DK.ECM.ENT.TRN', 2024)}-{ref('EU.ECM.ENT.TRN', 2024)}", d24 - e24)

    exmp, diff = val("DK.DGP.EXMP", 2026), val("DK.DGX.DIFF", 2026)
    add("Formally exempt from Digital Post, Q1 2026", "As published.", "%",
        ref("DK.DGP.EXMP", 2026), exmp)
    add("Face difficulty with digital public services", "As published.", "%",
        ref("DK.DGX.DIFF", 2026), diff)
    add("Difficulty as a multiple of formal exemption",
        "The narrowest capability measure divided by the administrative one.",
        "times", f"{ref('DK.DGX.DIFF', 2026)}/{ref('DK.DGP.EXMP', 2026)}",
        diff / exmp)
    add("Face difficulty but are not exempt",
        "Difficulty less formal exemption, in percentage points.", "pp",
        f"{ref('DK.DGX.DIFF', 2026)}-{ref('DK.DGP.EXMP', 2026)}", diff - exmp)

    pop = val("DK.POP.TOT", 2026)
    n26, n25 = val("DK.DGP.EXMP.N", 2026), val("DK.DGP.EXMP.N", 2025)
    add("Resident population, 1 January 2026", "As published.", "count",
        ref("DK.POP.TOT", 2026), pop)
    add("Citizens formally exempt, Q1 2026", "As published.", "count",
        ref("DK.DGP.EXMP.N", 2026), n26)
    add("Change in exempt headcount, 2025 to 2026",
        "2026 headcount less 2025 headcount. The 2025 figure is an estimate.",
        "count", f"{ref('DK.DGP.EXMP.N', 2026)}-{ref('DK.DGP.EXMP.N', 2025)}",
        n26 - n25)

    s16, s55 = val("DK.SKL.1624", 2025), val("DK.SKL.5574", 2025)
    add("Digital skills gap, 16-24 against 55-74",
        "Younger band less older band, percentage points.", "pp",
        f"{ref('DK.SKL.1624', 2025)}-{ref('DK.SKL.5574', 2025)}", s16 - s55)

    lrg, sme = val("DK.ENT.AI.LRG", 2025), val("DK.ENT.AI.SME", 2025)
    add("AI adoption gap, large firms against SMEs",
        "Large-firm adoption less SME adoption, percentage points.", "pp",
        f"{ref('DK.ENT.AI.LRG', 2025)}-{ref('DK.ENT.AI.SME', 2025)}", lrg - sme)

    dkw, euw = val("DK.ENV.WEEE", 2023), val("EU.ENV.WEEE", 2023)
    add("ICT waste recovery, DK against EU-27",
        "Denmark less the EU-27 aggregate, percentage points.", "pp",
        f"{ref('DK.ENV.WEEE', 2023)}-{ref('EU.ENV.WEEE', 2023)}", dkw - euw)

    dke, eue = val("DK.DGX.EGOV.USE", 2024), val("EU.DGX.EGOV.USE", 2024)
    add("E-government use, DK against EU-27",
        "Denmark less the EU-27 aggregate, same base and reference period.", "pp",
        f"{ref('DK.DGX.EGOV.USE', 2024)}-{ref('EU.DGX.EGOV.USE', 2024)}",
        dke - eue)

    return q


def sheet_calc(wb, fmt):
    ws = wb.add_worksheet("05_CALC")
    ws.write(0, 0, "Derived quantities", fmt["title"])
    ws.write(1, 0, "Every value in the result column is a live formula over "
                   "02_MASTER. None is typed.", fmt["subtitle"])

    heads = ["quantity", "result", "unit", "how it is built"]
    for c, h in enumerate(heads):
        ws.write(3, c, h, fmt["head"])

    q = derived_quantities()
    for i, (label, words, unit, formula, value) in enumerate(q):
        r = i + 4
        ws.write_string(r, 0, label, fmt["text"])
        cell_fmt = fmt["derived_int"] if unit == "count" else fmt["derived"]
        ws.write_formula(r, 1, "=" + formula, cell_fmt, value)
        ws.write_string(r, 2, unit, fmt["text_n"])
        ws.write_string(r, 3, words, fmt["text"])

    finish(ws, [(0, 0, 46), (1, 1, 14), (2, 2, 8), (3, 3, 62)],
           freeze=(4, 1), hide_grid=False, tab=style.TAB_CHART)
    ws.set_row(3, 22)
    return len(q)


# ------------------------------------------------- figure sheet scaffolding ---
CHART_COL = 6            # charts start at column G; all text stays in A..E
CHART_ROW = 3            # and at row 4, below the title block


def figure_header(ws, fmt, title, blurb):
    ws.write(0, 0, title, fmt["title"])
    ws.write(1, 0, blurb, fmt["subtitle"])


def source_note(ws, fmt, row, text):
    ws.write(row, 0, "Source: " + text, fmt["small"])


def base_chart(wb, kind, title, subtitle=None):
    """A chart with the chrome the previous workbook stripped out.

    Every chart gets a real title on the chart object. The previous build put
    titles in worksheet cells instead, so in Excel each chart was an untitled
    floating graphic whose title neither moved, resized, copied nor printed
    with it.
    """
    ch = wb.add_chart(kind)
    name = title if not subtitle else f"{title}\n{subtitle}"
    ch.set_title({
        "name": name,
        "name_font": {"name": style.FONT, "size": 12, "bold": True,
                      "color": style.NAVY},
    })
    ch.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
    ch.set_plotarea({"border": {"none": True}, "fill": {"none": True}})
    ch.set_size({"width": 760, "height": 460})
    return ch


def axis(name, *, num_format=None, grid=False, cat=False, lo=None, hi=None):
    """An axis with its bounds stated rather than left to Excel.

    Excel's autoscale chose 0 to 120% for a value axis whose data spans 57 to
    96%, which wastes half the plot and flattens the spread. Every value axis
    here sets its own range.
    """
    a = {
        "name": name,
        "name_font": {"name": style.FONT, "size": 10, "color": style.AXIS_INK},
        "num_font": {"name": style.FONT, "size": 9, "color": style.AXIS_INK},
        "line": {"color": style.GRID},
        "major_tick_mark": "none",
        "minor_tick_mark": "none",
    }
    if num_format:
        a["num_format"] = num_format
    a["major_gridlines"] = ({"visible": True,
                             "line": {"color": style.GRID, "width": 0.75}}
                            if grid else {"visible": False})
    if cat:
        a["label_position"] = "low"
    if lo is not None:
        a["min"] = lo
    if hi is not None:
        a["max"] = hi
    return a


def legend_bottom():
    return {"position": "bottom",
            "font": {"name": style.FONT, "size": 9, "color": style.AXIS_INK},
            "border": {"none": True}}


# ------------------------------------------------- F2_PAYMENTS  (chart C1) ---
# The plan for this sheet was a three-series time line. The data does not carry
# one: cash has three observations, the physical card two, the mobile wallet one.
# Drawing three lines would mean inventing a 2017 wallet share of zero, which the
# source does not report - the wallet was not separately measured that year.
# A grouped column on the two years both instruments share says the same thing
# and invents nothing.
PAY_YEARS = [2017, 2025]
PAY_SERIES = [
    ("DK.PAY.CASH.POS", "Cash", style.CAT_1),
    ("DK.PAY.CRD.PHYS", "Physical payment card", style.CAT_2),
    ("DK.PAY.WLT.SHR", "Mobile wallet", style.CAT_3),
]


def sheet_payments(wb, fmt):
    ws = wb.add_worksheet("F2_PAYMENTS")
    figure_header(ws, fmt, "Instrument shares of physical-retail payments",
                  "Denmark, 2017 and 2025. Shares of the number of payments in "
                  "physical retail, so the three are directly comparable.")

    ws.write(3, 0, "instrument", fmt["head"])
    for j, y in enumerate(PAY_YEARS):
        ws.write(3, 1 + j, str(y), fmt["head"])
    ws.write(3, 3, "series_code", fmt["head"])

    for i, (code, label, _colour) in enumerate(PAY_SERIES):
        r = 4 + i
        ws.write_string(r, 0, label, fmt["text_n"])
        for j, y in enumerate(PAY_YEARS):
            if (code, y) in INDEX:
                ws.write_formula(r, 1 + j, "=" + ref(code, y), fmt["derived"],
                                 val(code, y))
            else:
                ws.write_blank(r, 1 + j, None, fmt["gap"])
        ws.write_string(r, 3, code, fmt["code"])

    note_row = 4 + len(PAY_SERIES) + 1
    ws.write(note_row, 0, "The mobile wallet was not separately reported in "
                          "2017; the blank is a gap, not a zero.", fmt["small"])
    source_note(ws, fmt, note_row + 1,
                "Danmarks Nationalbank, Danskernes betalingsvaner. Series "
                "DK.PAY.CASH.POS, DK.PAY.CRD.PHYS, DK.PAY.WLT.SHR in 02_MASTER.")

    ch = base_chart(wb, {"type": "column"},
                    "Cash gave up 14 points of retail payments in eight years",
                    "Share of the number of physical-retail payments, Denmark")
    for i, (code, label, colour) in enumerate(PAY_SERIES):
        ch.add_series({
            "name": label,
            "categories": ["F2_PAYMENTS", 3, 1, 3, 2],
            "values": ["F2_PAYMENTS", 4 + i, 1, 4 + i, 2],
            "fill": {"color": colour},
            "border": {"none": True},
            "gap": 60,
            # Direct labels on every column. Three series is inside the limit
            # where direct labelling is expected, and the aqua slot sits below
            # 3:1 contrast on a white surface, so the relief rule requires them.
            "data_labels": {"value": True, "num_format": '0"%"',
                            "font": {"name": style.FONT, "size": 9,
                                     "color": style.AXIS_INK}},
        })
    ch.set_x_axis(axis("Year", cat=True))
    ch.set_y_axis(axis("% of the number of payments", num_format='0"%"',
                       grid=True, lo=0, hi=80))
    ch.set_legend(legend_bottom())
    ws.insert_chart(CHART_ROW, CHART_COL, ch)

    finish(ws, [(0, 0, 26), (1, 2, 11), (3, 3, 21), (4, 5, 3)],
           hide_grid=True, tab=style.TAB_CHART)


# ------------------------------------------------ F4_EXCLUSION  (chart C2) ---
# Five definitions of one phenomenon, ordered narrowest to widest so the ladder
# reads down the page. The two bounds of the "digitally disadvantaged" range are
# shown as separate bars rather than as one bar with an error whisker, because a
# range whose ends come from the same estimate should not be drawn as though one
# end were the measurement and the other a deviation.
EXCLUSION = [
    ("DK.DGP.EXMP", 2026, "Formally exempt from Digital Post",
     "administrative status"),
    ("DK.DGX.NOUSE", 2026, "Do not use digital public services",
     "self-reported non-use"),
    ("DK.DGX.DIFF", 2026, "Face difficulty using digital public services",
     "capability"),
    ("DK.DGX.DISADV.LO", 2025, "'Digitally disadvantaged', lower bound",
     "capability estimate"),
    ("DK.DGX.DISADV.HI", 2025, "'Digitally disadvantaged', upper bound",
     "capability estimate"),
    ("DK.DGX.JUST", 2022, "'Digitally disadvantaged', broadest definition",
     "capability estimate"),
]


def sheet_exclusion(wb, fmt):
    ws = wb.add_worksheet("F4_EXCLUSION")
    figure_header(ws, fmt, "Six measures of digital exclusion in Denmark",
                  "The same phenomenon under six definitions. The spread between "
                  "them is the finding, not a discrepancy to be resolved.")

    for c, h in enumerate(["measure", "%", "basis", "year", "source",
                           "series_code"]):
        ws.write(3, c, h, fmt["head"])

    rows = sorted(EXCLUSION, key=lambda e: val(e[0], e[1]))
    for i, (code, year, label, basis) in enumerate(rows):
        r = 4 + i
        ws.write_string(r, 0, label, fmt["text_n"])
        is_est = flag_of(code, year) == "e"
        ws.write_formula(r, 1, "=" + ref(code, year),
                         fmt["flagged"] if is_est else fmt["derived"],
                         val(code, year))
        ws.write_string(r, 2, basis, fmt["text_n"])
        ws.write_number(r, 3, year, fmt["year"])
        ws.write_string(r, 4, src_of(code, year), fmt["code"])
        ws.write_string(r, 5, code, fmt["code"])

    note_row = 4 + len(rows) + 1
    ws.write(note_row, 0, "Amber rows are estimates rather than published "
                          "counts, and are drawn in the lighter tint.",
             fmt["small"])
    source_note(ws, fmt, note_row + 1,
                "Digitaliseringsstyrelsen, Eurostat and Justitia, as recorded "
                "per row in 03_SOURCES.")

    ch = base_chart(wb, {"type": "bar"},
                    "Exclusion is four to five times wider than exemption",
                    "Denmark, % of the stated population base")
    ch.add_series({
        "name": "Share of population",
        "categories": ["F4_EXCLUSION", 4, 0, 3 + len(rows), 0],
        "values": ["F4_EXCLUSION", 4, 1, 3 + len(rows), 1],
        "fill": {"color": style.ACCENT},
        "border": {"none": True},
        "gap": 50,
        "points": [{"fill": {"color": style.ACCENT_LIGHT
                             if flag_of(c, y) == "e" else style.ACCENT}}
                   for c, y, _l, _b in rows],
        "data_labels": {"value": True, "num_format": '0.0"%"',
                        "font": {"name": style.FONT, "size": 9,
                                 "color": style.AXIS_INK}},
    })
    ch.set_x_axis(axis("% of the stated population base", num_format='0"%"',
                       grid=True, lo=0, hi=28))
    ch.set_y_axis(axis("Measure", cat=True))
    ch.set_legend({"none": True})
    ws.insert_chart(CHART_ROW, CHART_COL, ch)

    finish(ws, [(0, 0, 44), (1, 1, 8), (2, 2, 20), (3, 3, 7), (4, 4, 9),
                (5, 5, 20)], hide_grid=True, tab=style.TAB_CHART)


# ----------------------------------------------------- F5_EU27  (chart C3) ---
def sheet_eu27(wb, fmt):
    ws = wb.add_worksheet("F5_EU27")
    figure_header(ws, fmt, "Individuals who bought online, EU-27, 2024",
                  "All 27 member states on one base. Denmark is the subject; "
                  "the other 26 are context.")

    for c, h in enumerate(["geo", "country", "%", "series_code",
                           "EU-27 average"]):
        ws.write(3, c, h, fmt["head"])

    rows = sorted(
        [(g, val(f"{g}.ECM.IND.BUY", 2024)) for g in COUNTRIES
         if (f"{g}.ECM.IND.BUY", 2024) in INDEX],
        key=lambda t: -t[1])

    for i, (geo, v) in enumerate(rows):
        r = 4 + i
        ws.write_string(r, 0, geo, fmt["code"])
        ws.write_string(r, 1, COUNTRIES[geo], fmt["text_n"])
        ws.write_formula(r, 2, "=" + ref(f"{geo}.ECM.IND.BUY", 2024),
                         fmt["derived"], v)
        ws.write_string(r, 3, f"{geo}.ECM.IND.BUY", fmt["code"])
        # The reference line needs a value on every category, so the aggregate
        # is repeated down the column rather than typed once. It is the same
        # live lookup each time, not 27 copies of a number.
        ws.write_formula(r, 4, "=" + ref("EU.ECM.IND.BUY", 2024),
                         fmt["derived"], val("EU.ECM.IND.BUY", 2024))

    eu_row = 4 + len(rows) + 1
    ws.write_string(eu_row, 1, "EU-27 aggregate", fmt["label"])
    ws.write_formula(eu_row, 2, "=" + ref("EU.ECM.IND.BUY", 2024),
                     fmt["derived"], val("EU.ECM.IND.BUY", 2024))
    ws.write_string(eu_row, 3, "EU.ECM.IND.BUY", fmt["code"])
    source_note(ws, fmt, eu_row + 2,
                "Eurostat isoc_ec_ib20. The aggregate is listed below the "
                "ranking rather than inside it, because it is not a country.")

    ch = base_chart(wb, {"type": "column"},
                    f"Denmark ranks {[g for g, _ in rows].index('DK') + 1} of "
                    f"{len(rows)} on online purchasing",
                    "% of internet users who bought online, 2024")
    ch.add_series({
        "name": "Bought online",
        "categories": ["F5_EU27", 4, 0, 3 + len(rows), 0],
        "values": ["F5_EU27", 4, 2, 3 + len(rows), 2],
        "fill": {"color": style.CONTEXT},
        "border": {"none": True},
        "gap": 30,
        "points": [{"fill": {"color": style.ACCENT if g == "DK"
                             else style.CONTEXT}} for g, _ in rows],
    })
    line = wb.add_chart({"type": "line"})
    line.add_series({
        "name": "EU-27 average",
        "categories": ["F5_EU27", 4, 0, 3 + len(rows), 0],
        "values": ["F5_EU27", 4, 4, 3 + len(rows), 4],
        "line": {"color": style.NAVY, "width": 1.25, "dash_type": "dash"},
        "marker": {"type": "none"},
    })
    ch.combine(line)

    ch.set_x_axis(axis("Member state", cat=True))
    ch.set_y_axis(axis("% of internet users", num_format='0"%"', grid=True,
                       lo=0, hi=100))
    ch.set_legend(legend_bottom())
    ws.insert_chart(CHART_ROW, CHART_COL, ch)

    finish(ws, [(0, 0, 7), (1, 1, 22), (2, 2, 9), (3, 3, 20), (4, 4, 14)],
           freeze=(4, 0), hide_grid=True, tab=style.TAB_CHART)
    return [g for g, _ in rows].index("DK") + 1, len(rows)


# --------------------------------------------- F6_ADOPT_BENEFIT (chart C4) ---
def ols(xs, ys):
    """Slope, intercept and R-squared. Plain OLS, no library."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return slope, intercept, 1 - ss_res / ss_tot


def sheet_adopt_benefit(wb, fmt):
    ws = wb.add_worksheet("F6_ADOPT_BENEFIT")
    figure_header(ws, fmt, "Adoption against economic effect, EU, 2024",
                  "Citizen adoption on the horizontal axis, enterprise outcome "
                  "on the vertical. Only countries holding both measures appear.")

    paired, _awaiting_x, awaiting_y = cross_section(2024)
    for c, h in enumerate(["geo", "country", "bought online (%)",
                           "e-sales, % of turnover"]):
        ws.write(3, c, h, fmt["head"])

    xs, ys = [], []
    for i, geo in enumerate(paired):
        r = 4 + i
        x = val(f"{geo}.ECM.IND.BUY", 2024)
        y = val(f"{geo}.ECM.ENT.TRN", 2024)
        xs.append(x)
        ys.append(y)
        ws.write_string(r, 0, geo, fmt["code"])
        ws.write_string(r, 1, COUNTRIES[geo], fmt["text_n"])
        ws.write_formula(r, 2, "=" + ref(f"{geo}.ECM.IND.BUY", 2024),
                         fmt["derived"], x)
        ws.write_formula(r, 3, "=" + ref(f"{geo}.ECM.ENT.TRN", 2024),
                         fmt["derived"], y)

    slope, intercept, r2 = ols(xs, ys)
    n = len(paired)

    # The live statistics Appendix A promises this sheet computes. Excel
    # recalculates them from the cells above; the cached values are what a
    # previewer displays.
    stat_row = 4 + n + 1
    xr = f"'F6_ADOPT_BENEFIT'!$C$5:$C${4 + n}"
    yr = f"'F6_ADOPT_BENEFIT'!$D$5:$D${4 + n}"
    ws.write(stat_row, 0, "OLS, computed live from the table above",
             fmt["section"])
    for j, (label, formula, value, unit) in enumerate([
        ("n", f"COUNT({xr})", n, "countries"),
        ("slope", f"SLOPE({yr},{xr})", slope, "pp per pp"),
        ("intercept", f"INTERCEPT({yr},{xr})", intercept, "pp"),
        ("R-squared", f"RSQ({yr},{xr})", r2, ""),
    ]):
        r = stat_row + 1 + j
        ws.write_string(r, 0, label, fmt["label"])
        ws.write_formula(r, 1, "=" + formula,
                         fmt["derived_int"] if label == "n" else fmt["derived"],
                         value)
        ws.write_string(r, 2, unit, fmt["text_n"])

    gap_row = stat_row + 6
    ws.write(gap_row, 0, f"Holding adoption but not the outcome measure, so "
                         f"absent from this table: "
                         f"{', '.join(awaiting_y) if awaiting_y else 'none'}.",
             fmt["small"])
    source_note(ws, fmt, gap_row + 1,
                "Eurostat isoc_ec_ib20 and isoc_ec_evaln2. The pairing is "
                "recomputed at build time from 02_MASTER.")

    # subtype MUST be "marker_only". XlsxWriter keeps any truthy subtype string
    # it is given, and only suppresses the connecting line when the subtype is
    # exactly that; an earlier "markers" left Excel joining the 18 points in row
    # order, which drew a zigzag across the plot. The explicit line:none below
    # makes the intent independent of the subtype name.
    ch = base_chart(wb, {"type": "scatter", "subtype": "marker_only"},
                    "Adoption explains part of the outcome, not all of it",
                    f"EU, 2024. n = {n}, slope {slope:+.3f}, R-squared {r2:.3f}")
    ch.add_series({
        "name": "Member state",
        "categories": ["F6_ADOPT_BENEFIT", 4, 2, 3 + n, 2],
        "values": ["F6_ADOPT_BENEFIT", 4, 3, 3 + n, 3],
        "line": {"none": True},
        "marker": {"type": "circle", "size": 8,
                   "fill": {"color": style.CONTEXT},
                   "border": {"color": "#FFFFFF", "width": 1.25}},
        "points": [{"fill": {"color": style.ACCENT if g == "DK"
                             else style.CONTEXT},
                    "border": {"color": "#FFFFFF", "width": 1.25}}
                   for g in paired],
        "trendline": {"type": "linear",
                      "line": {"color": style.NAVY, "width": 1.25,
                               "dash_type": "dash"}},
    })
    ch.set_x_axis(axis("Individuals who bought online (% of internet users)",
                       num_format='0"%"', grid=True, lo=50, hi=100))
    ch.set_y_axis(axis("E-sales (% of enterprise turnover)", num_format='0"%"',
                       grid=True, lo=0, hi=40))
    ch.set_legend({"none": True})
    ws.insert_chart(CHART_ROW, CHART_COL, ch)

    finish(ws, [(0, 0, 38), (1, 1, 22), (2, 2, 17), (3, 3, 20)],
           hide_grid=True, tab=style.TAB_CHART)
    return n, slope, r2, xs, ys, paired


# -------------------------------------------------- series-extract sheets ---
# F1_BRANCHES, F11_EWASTE and F12_REACH carry no chart. They exist because the
# report cites them by name - "workbook F1_BRANCHES" names a series, not a
# figure - and the report is not being touched in this rebuild. Each is the
# observations behind one report figure, which is all the citation promises.
EXTRACTS = [
    ("F1_BRANCHES", "Danish retail bank branches",
     "The series behind Figure 1 of the report. Years are uneven because the "
     "authority publishes irregularly; they are not interpolated.",
     ["DK.FIN.BRCH"],
     "Finans Danmark, Institutter, filialer og ansatte."),
    ("F11_EWASTE", "ICT waste recycled or prepared for reuse",
     "The series behind Figure 9 of the report. Denmark against the EU-27 "
     "aggregate, same year and same base.",
     ["DK.ENV.WEEE", "EU.ENV.WEEE"],
     "European Commission, WEEE recovery statistics."),
    ("F12_REACH", "How far the digital state reaches, and who it misses",
     "The series behind Figure 10 of the report. Levels rather than "
     "differences: these measures do not share a denominator and are never "
     "differenced.",
     ["DK.DGX.EGOV.USE", "EU.DGX.EGOV.USE", "DK.DGX.DIFF", "DK.DGX.NOUSE",
      "DK.DGP.EXMP", "DK.FIN.INST", "DK.FIN.BRCH", "DK.FIN.EMP",
      "DK.ENT.AI.LRG", "DK.ENT.AI.SME"],
     "As recorded per row in 03_SOURCES."),
]


def sheet_extract(wb, fmt, name, title, blurb, codes, source):
    ws = wb.add_worksheet(name)
    figure_header(ws, fmt, title, blurb)

    for c, h in enumerate(["series_code", "indicator", "geo", "year", "value",
                           "unit", "denominator", "flag", "source"]):
        ws.write(3, c, h, fmt["head"])

    rows = sorted([r for r in OBS if r[0] in codes],
                  key=lambda r: (codes.index(r[0]), r[3]))
    for i, (code, ind, geo, year, value, unit, denom, flag, src, _note) \
            in enumerate(rows):
        r = 4 + i
        ws.write_string(r, 0, code, fmt["code"])
        ws.write_string(r, 1, ind, fmt["text"])
        ws.write_string(r, 2, geo, fmt["text_n"])
        ws.write_number(r, 3, year, fmt["year"])
        cell = fmt["flagged"] if flag else (
            fmt["derived_int"] if unit == "count" else fmt["derived"])
        ws.write_formula(r, 4, "=" + ref(code, year), cell, value)
        ws.write_string(r, 5, unit, fmt["text_n"])
        ws.write_string(r, 6, denom, fmt["text"])
        ws.write_string(r, 7, flag, fmt["text_n"])
        ws.write_string(r, 8, src, fmt["code"])

    source_note(ws, fmt, 4 + len(rows) + 1, source)
    finish(ws, [(0, 0, 21), (1, 1, 44), (2, 2, 6), (3, 3, 7), (4, 4, 12),
                (5, 5, 9), (6, 6, 34), (7, 7, 6), (8, 8, 9)],
           freeze=(4, 1), hide_grid=False, tab=style.TAB_SUPPORT)
    ws.set_row(3, 22)
    return len(rows)


# -------------------------------------------------------------- 09_POLICY ---
def sheet_policy(wb, fmt):
    ws = wb.add_worksheet("09_POLICY")
    ws.write(0, 0, "Policy events", fmt["title"])
    ws.write(1, 0, "Dated instruments with their legal citations. A policy event "
                   "is evidence and is held to the same standard as a number: no "
                   "event is dated more finely than its source allows.",
             fmt["subtitle"])

    for c, h in enumerate(["date", "precision", "event", "legal citation",
                           "source", "bears on", "what it does"]):
        ws.write(3, c, h, fmt["head"])

    for i, (when, precision, event, citation, src, what, series) in \
            enumerate(sorted(POLICY_EVENTS)):
        r = 4 + i
        ws.write_string(r, 0, when, fmt["text_n"])
        ws.write_string(r, 1, precision, fmt["text_n"])
        ws.write_string(r, 2, event, fmt["text"])
        ws.write_string(r, 3, citation, fmt["text"])
        ws.write_string(r, 4, src, fmt["code"])
        ws.write_string(r, 5, series, fmt["code"])
        ws.write_string(r, 6, what, fmt["text"])

    finish(ws, [(0, 0, 12), (1, 1, 10), (2, 2, 40), (3, 3, 28), (4, 4, 9),
                (5, 5, 20), (6, 6, 70)],
           freeze=(4, 1), hide_grid=False, tab=style.TAB_SUPPORT)
    ws.set_row(3, 22)
    return len(POLICY_EVENTS)


# --------------------------------------------------------- 07_LIMITATIONS ---
def sheet_limitations(wb, fmt):
    from content import AI_LOG, AI_LOG_FOOTER, LIMITATIONS, RETAIL_GAP

    ws = wb.add_worksheet("07_LIMITATIONS")
    ws.write(0, 0, "Limitations, gaps, and the AI use log", fmt["title"])
    ws.write(1, 0, "Read before citing any value.", fmt["subtitle"])

    r = 3
    ws.write(r, 0, "What this data cannot support", fmt["section"])
    r += 2
    ws.write(r, 0, "limitation", fmt["head"])
    ws.write(r, 1, "detail", fmt["head"])
    r += 1
    for head, body in LIMITATIONS:
        ws.write_string(r, 0, head, fmt["label"])
        ws.write_string(r, 1, body, fmt["prose"])
        ws.set_row(r, max(14, 11 * (len(body) // 95 + 1)))
        r += 1

    r += 2
    ws.write(r, 0, "Documented gap - retail trade volume index", fmt["section"])
    r += 1
    ws.write(r, 0, "Recorded rather than silently omitted.", fmt["subtitle"])
    r += 1
    for k, v in RETAIL_GAP:
        ws.write_string(r, 0, k, fmt["label"])
        ws.write_string(r, 1, v, fmt["gap"])
        ws.set_row(r, max(14, 11 * (len(v) // 95 + 1)))
        r += 1

    r += 2
    ws.write(r, 0, "AI use and validation log", fmt["section"])
    r += 1
    ws.write(r, 0, "Raw material for the AI Use and Validation Appendix, which "
                   "is submitted separately.", fmt["subtitle"])
    r += 2
    for c, h in enumerate(["step", "AI assistance used", "how it was validated",
                           "outcome"]):
        ws.write(r, c, h, fmt["head"])
    r += 1
    for step, used, validated, outcome in AI_LOG:
        ws.write_string(r, 0, step, fmt["label"])
        ws.write_string(r, 1, used, fmt["prose"])
        ws.write_string(r, 2, validated, fmt["prose"])
        ws.write_string(r, 3, outcome, fmt["prose"])
        longest = max(len(used), len(validated), len(outcome))
        ws.set_row(r, max(14, 11 * (longest // 44 + 1)))
        r += 1

    r += 1
    ws.write_string(r, 0, AI_LOG_FOOTER, fmt["small"])

    finish(ws, [(0, 0, 34), (1, 1, 62), (2, 2, 62), (3, 3, 52)],
           hide_grid=True, tab=style.TAB_CAUTION)
    return len(LIMITATIONS), len(AI_LOG)


# ------------------------------------------------------------------ build ---
CONTENTS = [
    ("00_COVER", "This sheet - what the workbook is and how to read it"),
    ("02_MASTER", "Every observation, one row each. Start here."),
    ("03_SOURCES", "Source register: authority, dataset code, URL, access date"),
    ("04_DEFINITIONS", "What each series measures, and its denominator"),
    ("05_CALC", "Derived quantities, as live formulas over 02_MASTER"),
    ("F2_PAYMENTS", "Chart - instrument shares of physical-retail payments"),
    ("F4_EXCLUSION", "Chart - six measures of digital exclusion"),
    ("F5_EU27", "Chart - online purchasing across all 27 member states"),
    ("F6_ADOPT_BENEFIT", "Chart - adoption against economic effect, with OLS"),
    ("F1_BRANCHES", "Series behind report Figure 1"),
    ("F11_EWASTE", "Series behind report Figure 9"),
    ("F12_REACH", "Series behind report Figure 10"),
    ("09_POLICY", "Dated policy instruments with legal citations"),
    ("07_LIMITATIONS", "What the data cannot support, plus the AI use log"),
]


def main():
    n_obs = validate()
    wb = xlsxwriter.Workbook(OUT, {"strings_to_numbers": False})
    wb.set_properties({
        "title": "Denmark: digital adoption and policy outcomes",
        "subject": "ECON1596 Assessment 2 data workbook",
        "author": STUDENT_ID,
        "comments": f"Generated by build_workbook.py, v{VERSION}, {BUILT}.",
    })
    fmt = style.formats(wb)

    sheet_cover(wb, fmt, CONTENTS)
    sheet_master(wb, fmt)
    used = sheet_sources(wb, fmt)
    n_series = sheet_definitions(wb, fmt)
    n_calc = sheet_calc(wb, fmt)

    sheet_payments(wb, fmt)
    sheet_exclusion(wb, fmt)
    dk_rank, n_countries = sheet_eu27(wb, fmt)
    n_pairs, slope, r2, _xs, _ys, _paired = sheet_adopt_benefit(wb, fmt)

    n_extract = 0
    for name, title, blurb, codes, source in EXTRACTS:
        n_extract += sheet_extract(wb, fmt, name, title, blurb, codes, source)

    n_policy = sheet_policy(wb, fmt)
    n_lim, n_ai = sheet_limitations(wb, fmt)

    # The contents list must match the tabs that actually exist. The previous
    # workbook's cover omitted a sheet and misordered another, which is exactly
    # the drift this assertion prevents.
    built = [ws.get_name() for ws in wb.worksheets()]
    listed = [n for n, _ in CONTENTS]
    assert built == listed, f"contents list does not match tabs:\n{built}\n{listed}"

    wb.close()

    unknown = used - set(SOURCES)
    assert not unknown, f"observations cite unknown sources: {sorted(unknown)}"

    print(f"wrote {os.path.relpath(OUT, HERE)}")
    print(f"  {len(built)} sheets, 4 charts")
    print(f"  {n_obs} observations across {n_series} series, "
          f"{len(SOURCES)} sources ({len(used)} cited)")
    print(f"  {n_calc} derived quantities, {n_extract} rows in series extracts")
    print(f"  {n_policy} policy events, {n_lim} limitations, {n_ai} AI log rows")
    print(f"  Denmark ranks {dk_rank} of {n_countries} on online purchasing")
    print(f"  OLS on {n_pairs} pairs: slope {slope:+.3f}, R-squared {r2:.3f}")


if __name__ == "__main__":
    main()
