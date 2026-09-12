"""Build the ECON1596 Assessment 2 data workbook.

Run:  python3 build_workbook.py

The workbook is generated, never hand-edited. To correct a value, edit dataset.py
and re-run; every downstream sheet and chart updates because they are formula views
of 02_MASTER rather than pasted copies.
"""

import os
from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.chart.marker import Marker
from openpyxl.chart.trendline import Trendline
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from dataset import COUNTRIES, OBS, cross_section, validate
from sources import ACCESSED, SOURCES

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx",
)

STUDENT_ID = "s4040040"
COURSE = "ECON1596/ECON1597 Digital Economy and Policy"
VERSION = "1.0"
BUILT = date.today().isoformat()

# ---------------------------------------------------------------- styling ---
NAVY = "FF1F3A5F"
INK = "FF1A1A1A"

F_HEAD = PatternFill("solid", fgColor=NAVY)
F_RAW = PatternFill("solid", fgColor="FFF2F2F2")       # retrieved values
F_CALC = PatternFill("solid", fgColor="FFE8F0F6")      # formula-derived
F_FLAG = PatternFill("solid", fgColor="FFFDF2E0")      # flagged / uncertain
F_GAP = PatternFill("solid", fgColor="FFF7E4E4")       # documented gap

T_HEAD = Font(name="Calibri", size=10, bold=True, color="FFFFFFFF")
T_TITLE = Font(name="Calibri", size=16, bold=True, color=NAVY)
T_SUB = Font(name="Calibri", size=11, bold=True, color=NAVY)
T_BODY = Font(name="Calibri", size=10, color=INK)
T_SMALL = Font(name="Calibri", size=9, color="FF5A5A5A")
T_MONO = Font(name="Consolas", size=9, color=INK)

THIN = Side(style="thin", color="FFBFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")


def header_row(ws, row, labels, widths=None):
    for i, label in enumerate(labels, start=1):
        c = ws.cell(row=row, column=i, value=label)
        c.fill, c.font, c.border = F_HEAD, T_HEAD, BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 28


def title_block(ws, title, subtitle=None):
    ws["A1"] = title
    ws["A1"].font = T_TITLE
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = T_SMALL
    ws.row_dimensions[1].height = 22


def lookup(series, year):
    """Formula returning the MASTER value for (series, year), or "" if absent."""
    m = "'02_MASTER'"
    cond = f'{m}!$B:$B,"{series}",{m}!$E:$E,{year}'
    return f'=IF(COUNTIFS({cond})=0,"",SUMIFS({m}!$F:$F,{cond}))'


def source_note(ws, row, text):
    c = ws.cell(row=row, column=1, value=text)
    c.font = T_SMALL
    c.alignment = WRAP


# ------------------------------------------------------------------ sheets ---
def sheet_cover(wb):
    ws = wb.create_sheet("00_COVER")
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 78

    ws["A1"] = "Denmark: Digital Adoption and Policy Outcomes"
    ws["A1"].font = Font(name="Calibri", size=18, bold=True, color=NAVY)
    ws["A2"] = "Statistical annex to Assessment 2 - Digital Policy and Innovation Report"
    ws["A2"].font = Font(name="Calibri", size=11, color="FF5A5A5A")

    rows = [
        ("Student ID", STUDENT_ID),
        ("Course", COURSE),
        ("Assessment", "Assessment 2 - Digital Policy and Innovation Report"),
        ("Country", "Denmark (assigned by final digit of student ID: 0)"),
        ("Workbook version", VERSION),
        ("Built", BUILT),
        ("Observations", str(len(OBS))),
        ("Coverage", "1991-2026, unbalanced; see 07_LIMITATIONS"),
        ("", ""),
        ("Suggested citation",
         f"Denmark: Digital Adoption and Policy Outcomes [data workbook], "
         f"v{VERSION}, {BUILT}. Compiled from the sources listed in 03_SOURCES."),
        ("", ""),
        ("Provenance rule",
         "Every value in this workbook was verified against the issuing authority "
         "named in its source_id. No value is interpolated, smoothed, or inferred "
         "from a neighbouring year. Gaps are left as gaps."),
        ("Structure rule",
         "02_MASTER is the single source of truth. Every figure sheet and every "
         "derived quantity is a formula view of it, not a pasted copy."),
    ]
    r = 4
    for k, v in rows:
        ws.cell(row=r, column=1, value=k).font = T_SUB
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.alignment = T_BODY, WRAP
        if len(v) > 90:
            ws.row_dimensions[r].height = 42
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="CONTENTS").font = T_SUB
    r += 1
    contents = [
        ("01_README", "Conventions, flag legend, how to trace any value"),
        ("02_MASTER", "Every observation, one row each"),
        ("03_SOURCES", "Source register with URLs, access dates, Harvard references"),
        ("04_DEFINITIONS", "What each indicator measures, and what it excludes"),
        ("05_CALC", "Derived quantities, as live formulas"),
        ("F1_BRANCHES", "Figure 1 - bank branch network, 2004-2024"),
        ("F2_PAYMENTS", "Figure 2 - payment instrument shares, 2017-2025"),
        ("F3_ESALES", "Figure 3 - e-sales share of turnover, DK vs EU"),
        ("F4_EXCLUSION", "Figure 4 - measures of digital exclusion"),
        ("F5_EU8", "Figure 5 - online purchasing, verified EU countries, 2024"),
        ("F6_ADOPT_BENEFIT", "Figure 6 - adoption vs economic effect, EU 2024"),
        ("06_RETAIL_GAP", "Documented gap - retail volume index not retrieved"),
        ("07_LIMITATIONS", "Data quality statement - read before citing"),
        ("08_AI_LOG", "AI use and validation log"),
    ]
    for name, desc in contents:
        ws.cell(row=r, column=1, value=name).font = T_MONO
        ws.cell(row=r, column=2, value=desc).font = T_BODY
        r += 1

    ws.sheet_view.showGridLines = False
    return ws


def sheet_readme(wb):
    ws = wb.create_sheet("01_README")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 96
    title_block(ws, "How to read this workbook")

    r = 4
    blocks = [
        ("PURPOSE",
         "This workbook is the raw-data attachment to a 2,000-word policy report on "
         "Denmark's digital transformation. It is designed so that any number "
         "appearing in the report can be traced to an issuing authority, a "
         "denominator and an access date without consulting the author."),
        ("TRACING A VALUE",
         "1. Find the value on a figure sheet.  2. Read its series_code.  "
         "3. Filter 02_MASTER by that series_code to find the observation row.  "
         "4. Take its source_id to 03_SOURCES for the authority, URL and access "
         "date.  5. Check 04_DEFINITIONS for what the indicator does and does not "
         "cover."),
        ("SINGLE SOURCE OF TRUTH",
         "02_MASTER holds every observation. Figure sheets contain no typed numbers "
         "- each cell is a COUNTIFS/SUMIFS lookup against 02_MASTER. Correcting a "
         "value in 02_MASTER updates every sheet and chart that uses it."),
        ("DENOMINATORS",
         "The denominator column in 02_MASTER is load-bearing, not decorative. "
         "Eurostat's Danish online-purchasing figures change base between 2019 "
         "(% of individuals) and 2020 onward (% of internet users). Series with "
         "different denominators are never plotted on one axis."),
    ]
    for k, v in blocks:
        ws.cell(row=r, column=1, value=k).font = T_SUB
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.alignment = T_BODY, WRAP
        ws.row_dimensions[r].height = 58
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="FLAG LEGEND").font = T_SUB
    r += 1
    header_row(ws, r, ["Flag", "Meaning"], [22, 96])
    r += 1
    for f, m in [
        ("b", "Break in series - definition or denominator changed. Do not plot across."),
        ("e", "Estimate - source gives an approximation or a verbal quantity."),
        ("p", "Provisional."),
        ("d", "Definition differs from the rest of the series."),
        ("u", "Low reliability."),
        ("(blank)", "Value as published, no qualification."),
    ]:
        ws.cell(row=r, column=1, value=f).font = T_MONO
        ws.cell(row=r, column=2, value=m).font = T_BODY
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="COLOUR LEGEND").font = T_SUB
    r += 1
    for fill, label in [
        (F_RAW, "Retrieved value - as published by the source"),
        (F_CALC, "Derived - calculated by formula from retrieved values"),
        (F_FLAG, "Flagged - estimate, break, or otherwise qualified"),
        (F_GAP, "Documented gap - value not retrieved"),
    ]:
        c = ws.cell(row=r, column=1, value="")
        c.fill, c.border = fill, BOX
        ws.cell(row=r, column=2, value=label).font = T_BODY
        r += 1

    r += 2
    ws.cell(row=r, column=1, value="BEFORE CITING").font = T_SUB
    c = ws.cell(row=r, column=2,
                value="Read 07_LIMITATIONS. Several series have very few "
                      "observations and none supports inferential statistics.")
    c.font, c.alignment = T_BODY, WRAP

    ws.sheet_view.showGridLines = False
    return ws


def sheet_master(wb):
    ws = wb.create_sheet("02_MASTER")
    cols = ["obs_id", "series_code", "indicator", "geo", "year", "value", "unit",
            "denominator", "flag", "source_id", "extraction_date", "notes"]
    header_row(ws, 1, cols, [8, 22, 46, 7, 7, 11, 12, 40, 6, 10, 14, 54])

    for i, row in enumerate(OBS, start=1):
        code, ind, geo, year, val, unit, denom, flag, src, note = row
        r = i + 1
        vals = [i, code, ind, geo, year, val, unit, denom, flag, src, ACCESSED, note]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.font = T_MONO if j in (2, 10) else T_BODY
            c.border, c.alignment = BOX, TOP
            c.fill = F_FLAG if flag else F_RAW
        ws.cell(row=r, column=6).number_format = (
            "#,##0" if unit == "count" else "0.00"
        )
        ws.cell(row=r, column=3).alignment = WRAP
        ws.cell(row=r, column=8).alignment = WRAP
        ws.cell(row=r, column=12).alignment = WRAP

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:L{len(OBS) + 1}"
    return ws


def sheet_sources(wb):
    ws = wb.create_sheet("03_SOURCES")
    header_row(ws, 1,
               ["source_id", "authority", "publication", "dataset code", "URL",
                "accessed", "RMIT Harvard reference"],
               [10, 30, 44, 24, 56, 12, 76])
    r = 2
    for sid, s in SOURCES.items():
        vals = [sid, s["authority"], s["title"], s["dataset_code"], s["url"],
                s["accessed"], s["harvard"]]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.font = T_MONO if j == 1 else T_BODY
            c.border, c.alignment, c.fill = BOX, WRAP, F_RAW
        ws.row_dimensions[r].height = 46
        r += 1
    ws.freeze_panes = "B2"
    return ws


def sheet_definitions(wb):
    ws = wb.create_sheet("04_DEFINITIONS")
    header_row(ws, 1,
               ["series_code", "what it measures", "what it excludes / watch for"],
               [24, 62, 72])
    defs = [
        ("DK.PAY.CASH.POS",
         "Cash as a share of the NUMBER of payments made at physical points of sale.",
         "Not a share of value. Excludes e-commerce entirely."),
        ("DK.PAY.CRD.PHYS",
         "Physical payment cards as a share of the number of in-store payments.",
         "Falls partly because wallets replace the physical card, not because "
         "card payment declines."),
        ("DK.PAY.WLT.SHR",
         "Card-based mobile wallets as a share of the number of in-store payments.",
         "Wallet payments are card payments. Do not add to the card share."),
        ("DK.PAY.WLT.OWN",
         "Share of CITIZENS with a wallet solution on their phone.",
         "Different denominator from the payment-share series. Memo only - "
         "deliberately excluded from Figure 2."),
        ("DK.FIN.BRCH",
         "Number of retail bank branches operated by Danish credit institutions.",
         "Consolidation and digitalisation both reduce this. The series alone "
         "cannot separate the two causes."),
        ("DK.ECM.IND.BUY",
         "Individuals who purchased goods or services online in the last 12 months.",
         "DENOMINATOR BREAK at 2020: % of individuals before, % of internet users "
         "after. Never plot 2019 with later years."),
        ("DK.ECM.ENT.TRN",
         "E-commerce sales as a share of total enterprise turnover.",
         "Measures INTENSITY of online selling, not how many firms sell online. "
         "Pair with DK.ECM.ENT.SHR."),
        ("DK.ECM.ENT.SHR",
         "Share of enterprises making any e-sales.",
         "Measures BREADTH of adoption. Flat breadth with rising intensity means "
         "incumbents deepening, not new entrants."),
        ("DK.DGP.EXMP",
         "Citizens formally exempt from mandatory Digital Post under the statutory "
         "exemption regime.",
         "An administrative status, not a measure of capability. A citizen may "
         "struggle without being exempt."),
        ("DK.DGX.DIFF",
         "Population estimated to face difficulties using digital public services.",
         "A capability estimate, not an administrative count. Much larger than the "
         "exemption rate - that gap is the analytical point."),
        ("DK.DGX.JUST",
         "Justitia's estimate of the digitally disadvantaged adult population.",
         "Think-tank estimate, broadest definition of the five. Cite as an upper "
         "bound, not as an official statistic."),
        ("DK.GOV.DPS.CIT",
         "eGovernment Benchmark composite score for citizen-facing digital public "
         "services.",
         "A composite index, not a usage rate. Denmark scores BELOW the EU average "
         "despite near-universal mandated use."),
        ("DK.ENV.WEEE",
         "Share of collected ICT-related electrical waste recycled or prepared for "
         "reuse.",
         "Covers two WEEE categories only. Denominator is waste COLLECTED, not "
         "waste generated."),
    ]
    r = 2
    for code, what, watch in defs:
        ws.cell(row=r, column=1, value=code).font = T_MONO
        for j, v in [(2, what), (3, watch)]:
            c = ws.cell(row=r, column=j, value=v)
            c.font, c.alignment = T_BODY, WRAP
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
            ws.cell(row=r, column=j).fill = F_RAW
        ws.row_dimensions[r].height = 44
        r += 1
    ws.freeze_panes = "A2"
    return ws


def sheet_calc(wb):
    ws = wb.create_sheet("05_CALC")
    title_block(ws, "Derived quantities",
                "Every cell below is a live formula over 02_MASTER. No pasted numbers.")
    header_row(ws, 4, ["quantity", "formula result", "unit", "how it is built"],
               [46, 16, 14, 74])

    def L(series, year):
        return lookup(series, year)[1:]  # strip leading '=' for embedding

    items = [
        ("Bank branches, 2004", lookup("DK.FIN.BRCH", 2004), "count",
         "Direct lookup from 02_MASTER."),
        ("Bank branches, 2024", lookup("DK.FIN.BRCH", 2024), "count",
         "Direct lookup from 02_MASTER."),
        ("Branch network change, 2004-2024",
         f"=({L('DK.FIN.BRCH', 2024)}/{L('DK.FIN.BRCH', 2004)})-1", "%",
         "Headline structural change for Figure 1."),
        ("Cash share change, 2017-2025",
         f"={L('DK.PAY.CASH.POS', 2025)}-{L('DK.PAY.CASH.POS', 2017)}", "pp",
         "Percentage-point change, not a growth rate - both terms are shares."),
        ("Cash share, proportional decline 2017-2025",
         f"=({L('DK.PAY.CASH.POS', 2025)}/{L('DK.PAY.CASH.POS', 2017)})-1", "%",
         "Cash fell to roughly a third of its 2017 share."),
        ("DK e-sales turnover share, change 2014-2024",
         f"=({L('DK.ECM.ENT.TRN', 2024)}/{L('DK.ECM.ENT.TRN', 2014)})-1", "%",
         "Tests the 'enterprise plateau' claim. Intensity nearly doubled."),
        ("EU e-sales turnover share, change 2014-2024",
         f"=({L('EU.ECM.ENT.TRN', 2024)}/{L('EU.ECM.ENT.TRN', 2014)})-1", "%",
         "Comparator for the line above."),
        ("DK lead over EU on e-sales turnover, 2024",
         f"={L('DK.ECM.ENT.TRN', 2024)}-{L('EU.ECM.ENT.TRN', 2024)}", "pp",
         "Denmark's margin over the EU average."),
        ("Exclusion ratio: difficulty vs formal exemption",
         f"={L('DK.DGX.DIFF', 2026)}/{L('DK.DGP.EXMP', 2026)}", "ratio",
         "How many times larger the capability measure is than the "
         "administrative one. The core Q4 statistic."),
        ("Citizens struggling but NOT exempt",
         f"={L('DK.DGX.DIFF', 2026)}-{L('DK.DGP.EXMP', 2026)}", "pp",
         "Population facing difficulty without statutory relief."),
        ("Digital skills gap, 16-24 vs 55-74",
         f"={L('DK.SKL.1624', 2025)}-{L('DK.SKL.5574', 2025)}", "pp",
         "Generational gradient in basic digital skills."),
        ("AI adoption gap, large firms vs SMEs",
         f"={L('DK.ENT.AI.LRG', 2025)}-{L('DK.ENT.AI.SME', 2025)}", "pp",
         "Depth-of-adoption gap behind the 'breadth without depth' finding."),
        ("DK shortfall vs EU, citizen digital public services",
         f"={L('DK.GOV.DPS.CIT', 2025)}-{L('EU.GOV.DPS.CIT', 2025)}", "points",
         "Negative: Denmark scores below the EU average."),
        ("DK shortfall vs EU, ICT waste recycling",
         f"={L('DK.ENV.WEEE', 2023)}-{L('EU.ENV.WEEE', 2023)}", "pp",
         "Negative and large - candidate SDG evidence."),
        ("Trust in digital public solutions, change 2024-2025",
         f"={L('DK.TRU.DPS', 2025)}-{L('DK.TRU.DPS', 2024)}", "pp",
         "Trust rising while the mandate is in force."),
        ("Perceived security of Digital Post, change 2017-2025",
         f"={L('DK.TRU.DGP.SEC', 2025)}-{L('DK.TRU.DGP.SEC', 2017)}", "pp",
         "Trust in the mandated system over the mandate period (CLO4)."),
    ]
    r = 5
    for label, formula, unit, how in items:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill = T_BODY, F_CALC
        c.number_format = "0.0%" if unit == "%" else (
            "#,##0" if unit == "count" else "0.00")
        ws.cell(row=r, column=3, value=unit).font = T_SMALL
        h = ws.cell(row=r, column=4, value=how)
        h.font, h.alignment = T_SMALL, WRAP
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
        ws.row_dimensions[r].height = 30
        r += 1

    ws.sheet_view.showGridLines = False
    return ws


def _style_view(ws, first_row, last_row, ncols):
    for r in range(first_row, last_row + 1):
        for j in range(1, ncols + 1):
            c = ws.cell(row=r, column=j)
            c.border = BOX
            if j > 1:
                c.fill = F_CALC


def sheet_f1(wb):
    ws = wb.create_sheet("F1_BRANCHES")
    title_block(ws, "Figure 1 - Denmark's bank branch network, 2004-2024",
                "Series DK.FIN.BRCH. Values are formula lookups from 02_MASTER.")
    header_row(ws, 4, ["year", "bank branches"], [12, 16])

    years = [2004, 2006, 2010, 2016, 2021, 2024]
    for i, y in enumerate(years):
        r = 5 + i
        ws.cell(row=r, column=1, value=y).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup("DK.FIN.BRCH", y))
        c.font, c.number_format = T_BODY, "#,##0"
    _style_view(ws, 5, 4 + len(years), 2)

    last = 4 + len(years)
    ch = ScatterChart()
    ch.title = "Bank branches in Denmark, 2004-2024"
    ch.style = 2
    ch.x_axis.title = "Year"
    ch.y_axis.title = "Number of branches"
    ch.height, ch.width = 9, 17
    xs = Reference(ws, min_col=1, min_row=5, max_row=last)
    ys = Reference(ws, min_col=2, min_row=4, max_row=last)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(symbol="circle", size=7)
    s.graphicalProperties.line = LineProperties(w=22000)
    ch.series.append(s)
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 2002, 2026
    ch.y_axis.scaling.min = 0
    ws.add_chart(ch, "D4")

    source_note(ws, last + 2,
                "Source: Finans Danmark, Institutter, filialer & ansatte (FD1). "
                "Note: years are unevenly spaced, so the chart uses a numeric X axis - "
                "a category axis would imply a constant rate of decline that the data "
                "does not show.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f2(wb):
    """Two exhibits rather than one.

    A single three-series time chart was attempted first and rejected: the cash
    series has three observations, the physical-card series two and the wallet
    series one, so two-thirds of the chart would have been empty cells masquerading
    as data. Panel A plots only the series that is actually a series; Panel B shows
    the composition at the one year where all three instruments are observed.
    """
    ws = wb.create_sheet("F2_PAYMENTS")
    title_block(ws, "Figure 2 - Cash displacement in Danish physical retail",
                "Denominator throughout: share of the NUMBER of in-store payments.")

    # --- Panel A: cash share over time -------------------------------------
    ws["A4"] = "Panel A - Cash share of in-store payments"
    ws["A4"].font = T_SUB
    header_row(ws, 5, ["year", "cash (%)"], [14, 30])
    years = [2017, 2023, 2025]
    for i, y in enumerate(years):
        r = 6 + i
        ws.cell(row=r, column=1, value=y).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup("DK.PAY.CASH.POS", y))
        c.font, c.number_format = T_BODY, "0.0"
    _style_view(ws, 6, 5 + len(years), 2)
    lastA = 5 + len(years)

    chA = ScatterChart()
    chA.title = "Cash share of in-store payments, 2017-2025"
    chA.style = 2
    chA.x_axis.title = "Year"
    chA.y_axis.title = "% of number of payments"
    chA.height, chA.width = 8, 15
    xs = Reference(ws, min_col=1, min_row=6, max_row=lastA)
    ys = Reference(ws, min_col=2, min_row=5, max_row=lastA)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(symbol="circle", size=7)
    s.graphicalProperties.line = LineProperties(w=22000)
    chA.series.append(s)
    chA.x_axis.scaling.min, chA.x_axis.scaling.max = 2016, 2026
    chA.y_axis.scaling.min, chA.y_axis.scaling.max = 0, 25
    chA.legend = None
    ws.add_chart(chA, "D5")

    # --- Panel B: 2025 composition -----------------------------------------
    r = lastA + 2
    ws.cell(row=r, column=1, value="Panel B - Composition of in-store payments, 2025").font = T_SUB
    r += 1
    headB = r
    header_row(ws, headB, ["instrument", "share of payments (%)"], [30, 30])
    comp = [("Physical payment card", "DK.PAY.CRD.PHYS"),
            ("Mobile wallet (card-based)", "DK.PAY.WLT.SHR"),
            ("Cash", "DK.PAY.CASH.POS")]
    for i, (label, code) in enumerate(comp):
        rr = headB + 1 + i
        ws.cell(row=rr, column=1, value=label).font = T_BODY
        c = ws.cell(row=rr, column=2, value=lookup(code, 2025))
        c.font, c.fill, c.number_format = T_BODY, F_CALC, "0.0"
        for j in (1, 2):
            ws.cell(row=rr, column=j).border = BOX
    lastB = headB + len(comp)

    chB = BarChart()
    chB.type, chB.grouping = "bar", "clustered"
    chB.title = "Composition of in-store payments, 2025"
    chB.style = 2
    chB.x_axis.title = "% of number of payments"
    chB.height, chB.width = 7, 15
    data = Reference(ws, min_col=2, min_row=headB, max_row=lastB)
    cats = Reference(ws, min_col=1, min_row=headB + 1, max_row=lastB)
    chB.add_data(data, titles_from_data=True)
    chB.set_categories(cats)
    chB.legend = None
    ws.add_chart(chB, f"D{headB}")

    # --- Memo: different denominator ---------------------------------------
    r = lastB + 2
    ws.cell(row=r, column=1, value="MEMO - different denominator, not charted above").font = T_SUB
    r += 1
    header_row(ws, r, ["year", "citizens holding a mobile wallet (%)"], [30, 30])
    r += 1
    for y in (2019, 2023, 2025):
        ws.cell(row=r, column=1, value=y).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup("DK.PAY.WLT.OWN", y))
        c.font, c.fill, c.number_format = T_BODY, F_FLAG, "0.0"
        for j in (1, 2):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    source_note(ws, r + 1,
                "Source: Danmarks Nationalbank, Danskernes betalingsvaner (NB1). "
                "Panel B sums to 95%, not 100%: the residual is other digital "
                "instruments (chiefly account transfers and non-card mobile "
                "payments). Wallet payments ARE card payments settled through a "
                "phone, so the wallet and physical-card rows must not be added to "
                "produce a 'card' total. The memo series is excluded from both "
                "panels because its denominator is % of citizens, not % of payments. "
                "Physical card and wallet shares are observed in 2025 only, so no "
                "time series is drawn for them - a two-point line through an "
                "unobserved middle would assert a path the data does not contain.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f3(wb):
    ws = wb.create_sheet("F3_ESALES")
    title_block(ws, "Figure 3 - E-sales as a share of enterprise turnover, DK vs EU",
                "Tests the 'enterprise plateau' claim: intensity nearly doubled.")
    header_row(ws, 4, ["year", "Denmark", "EU-27"], [12, 14, 14])
    for i, y in enumerate([2014, 2024]):
        r = 5 + i
        ws.cell(row=r, column=1, value=y).font = T_BODY
        ws.cell(row=r, column=2, value=lookup("DK.ECM.ENT.TRN", y)).number_format = "0.00"
        ws.cell(row=r, column=3, value=lookup("EU.ECM.ENT.TRN", y)).number_format = "0.00"
    _style_view(ws, 5, 6, 3)

    ch = BarChart()
    ch.type, ch.grouping = "col", "clustered"
    ch.title = "E-sales as % of enterprise turnover"
    ch.style = 2
    ch.y_axis.title = "% of turnover"
    ch.x_axis.title = "Year"
    ch.height, ch.width = 9, 15
    data = Reference(ws, min_col=2, max_col=3, min_row=4, max_row=6)
    cats = Reference(ws, min_col=1, min_row=5, max_row=6)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ws.add_chart(ch, "E4")

    r = 9
    ws.cell(row=r, column=1, value="CONTEXT - breadth vs intensity, 2024").font = T_SUB
    r += 1
    header_row(ws, r, ["measure", "Denmark", "EU / leader"], [40, 14, 26])
    r += 1
    ctx = [
        ("Enterprises making e-sales (%)", lookup("DK.ECM.ENT.SHR", 2024),
         "Lithuania 43.03 (highest)"),
        ("E-sales share of turnover (%)", lookup("DK.ECM.ENT.TRN", 2024),
         "Ireland 38.25 (highest)"),
        ("EU average, e-sales share of turnover (%)", lookup("EU.ECM.ENT.TRN", 2024), ""),
    ]
    for label, formula, note in ctx:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, "0.00"
        ws.cell(row=r, column=3, value=note).font = T_SMALL
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    source_note(ws, r + 1,
                "Source: Eurostat (ES5). Reading: Denmark's e-sales share of turnover "
                "rose from 17.05% to 33.31% while the EU average moved from 16.43% to "
                "19.49%. Breadth of adoption is flat at roughly 38% of enterprises; "
                "intensity nearly doubled. The growth came from incumbents selling "
                "more online, not from new firms entering.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f4(wb):
    ws = wb.create_sheet("F4_EXCLUSION")
    title_block(ws, "Figure 4 - Five measures of digital exclusion in Denmark",
                "Same phenomenon, five definitions. The spread is the finding.")
    header_row(ws, 4, ["measure", "%", "definition basis", "source"],
               [46, 10, 34, 10])

    rows = [
        ("Formally exempt from Digital Post (Q1 2026)",
         lookup("DK.DGP.EXMP", 2026), "administrative status", "DG1"),
        ("Do not use digital public services at all",
         lookup("DK.DGX.NOUSE", 2026), "self-reported non-use", "EC1"),
        ("Face difficulties using digital public services",
         lookup("DK.DGX.DIFF", 2026), "capability estimate", "EC1"),
        ("'Digitally disadvantaged' - lower bound",
         lookup("DK.DGX.DISADV.LO", 2025), "capability estimate (range)", "DG2"),
        ("'Digitally disadvantaged' - upper bound",
         lookup("DK.DGX.DISADV.HI", 2025), "capability estimate (range)", "DG2"),
        ("'Digitally disadvantaged' - Justitia",
         lookup("DK.DGX.JUST", 2022), "broadest definition", "JU1"),
    ]
    for i, (label, formula, basis, src) in enumerate(rows):
        r = 5 + i
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, "0.0"
        ws.cell(row=r, column=3, value=basis).font = T_SMALL
        ws.cell(row=r, column=4, value=src).font = T_MONO
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
    last = 4 + len(rows)

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.title = "Measures of digital exclusion, Denmark"
    ch.style = 2
    ch.x_axis.title = "% of population"
    ch.height, ch.width = 10, 18
    data = Reference(ws, min_col=2, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.legend = None
    ws.add_chart(ch, "F4")

    r = last + 2
    ws.cell(row=r, column=1, value="AGE GRADIENT IN FORMAL EXEMPTION (2022)").font = T_SUB
    r += 1
    header_row(ws, r, ["age group", "exempt (%)"], [46, 12])
    r += 1
    for label, code in [("Age 75-84", "DK.DGP.EXMP.7584"), ("Age 85+", "DK.DGP.EXMP.85P")]:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup(code, 2022))
        c.font, c.fill, c.number_format = T_BODY, F_FLAG, "0.0"
        for j in (1, 2):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    source_note(ws, r + 1,
                "Sources: DG1, DG2, EC1, JU1. Reading: the measures are nested rather "
                "than contradictory. Formal exemption (4.7%) is an administrative "
                "status; the capability measures are three to five times larger. The "
                "statutory exemption regime therefore reaches only a minority of the "
                "citizens the state's own agency counts as struggling. Which measure "
                "is chosen determines the conclusion - so the choice must be argued, "
                "not assumed.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f5(wb):
    ws = wb.create_sheet("F5_EU8")
    title_block(ws, "Figure 5 - Individuals who bought online, 2024",
                "Verified EU countries only (8 of 27). Ranked, not a regression.")
    header_row(ws, 4, ["country", "%", "series_code"], [22, 10, 24])

    order = [("Ireland", "IE.ECM.IND.BUY"), ("Netherlands", "NL.ECM.IND.BUY"),
             ("Denmark", "DK.ECM.IND.BUY"), ("Germany", "DE.ECM.IND.BUY"),
             ("EU-27 average", "EU.ECM.IND.BUY"), ("Italy", "IT.ECM.IND.BUY"),
             ("Romania", "RO.ECM.IND.BUY"), ("Bulgaria", "BG.ECM.IND.BUY")]
    for i, (name, code) in enumerate(order):
        r = 5 + i
        ws.cell(row=r, column=1, value=name).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup(code, 2024))
        c.font, c.fill, c.number_format = T_BODY, F_CALC, "0.0"
        ws.cell(row=r, column=3, value=code).font = T_MONO
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
    last = 4 + len(order)

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.title = "Individuals who bought online in last 12 months, 2024"
    ch.style = 2
    ch.x_axis.title = "% of internet users"
    ch.height, ch.width = 10, 17
    data = Reference(ws, min_col=2, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.legend = None
    ws.add_chart(ch, "E4")

    source_note(ws, last + 2,
                "Source: Eurostat (ES4). SCOPE LIMIT: 8 of 27 member states were "
                "verified, so this sheet presents a ranking and makes no regression "
                "claim. To extend it, add the remaining member states to dataset.py "
                "using the series_code pattern XX.ECM.IND.BUY and re-run the build; "
                "this sheet and its chart will expand automatically. Denominator is "
                "% of internet users, not % of individuals.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f6(wb):
    """The adoption-to-economic-effect exhibit.

    This is the chart the assessment brief asks for: adoption on X, an economic
    magnitude on Y, one point per country, with a fitted line. It has to be a
    cross-section rather than a Danish time series because the Danish adoption
    and outcome series share almost no observation years - the best time-series
    pairing anywhere in the dataset is n=2.
    """
    ws = wb.create_sheet("F6_ADOPT_BENEFIT")
    title_block(ws, "Figure 6 - Does more digital adoption mean more economic activity?",
                "EU cross-section, 2024. X = consumer adoption. Y = share of "
                "enterprise turnover from e-sales.")

    paired, awaiting_x, awaiting_y = cross_section(2024)

    header_row(ws, 4,
               ["country", "code",
                "X: individuals buying online (%)",
                "Y: e-sales share of turnover (%)"],
               [20, 8, 30, 30])
    for i, geo in enumerate(paired):
        r = 5 + i
        ws.cell(row=r, column=1, value=COUNTRIES[geo]).font = T_BODY
        ws.cell(row=r, column=2, value=geo).font = T_MONO
        cx = ws.cell(row=r, column=3, value=lookup(f"{geo}.ECM.IND.BUY", 2024))
        cy = ws.cell(row=r, column=4, value=lookup(f"{geo}.ECM.ENT.TRN", 2024))
        for c in (cx, cy):
            c.font, c.fill, c.number_format = T_BODY, F_CALC, "0.00"
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
    first, last = 5, 4 + len(paired)

    ch = ScatterChart()
    ch.title = "Digital adoption and e-commerce turnover, EU 2024"
    ch.style = 2
    ch.x_axis.title = "Individuals who bought online (% of internet users)"
    ch.y_axis.title = "E-sales as % of enterprise turnover"
    ch.height, ch.width = 11, 18
    xs = Reference(ws, min_col=3, min_row=first, max_row=last)
    ys = Reference(ws, min_col=4, min_row=4, max_row=last)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(symbol="circle", size=9)
    s.graphicalProperties.line.noFill = True          # markers only, no join
    s.trendline = Trendline(trendlineType="linear", dispRSqr=True, dispEq=True)
    ch.series.append(s)
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 50, 100
    ch.y_axis.scaling.min = 0
    ch.legend = None
    ws.add_chart(ch, "F4")

    # --- fitted line statistics, as live formulas --------------------------
    xr = f"$C${first}:$C${last}"
    yr = f"$D${first}:$D${last}"
    r = last + 2
    ws.cell(row=r, column=1, value="FITTED LINE (ordinary least squares)").font = T_SUB
    r += 1
    header_row(ws, r, ["statistic", "value", "reading"], [26, 14, 74])
    r += 1
    stats = [
        ("n (countries)", f"=COUNT({xr})", "0",
         "Number of complete X-Y pairs. Expands automatically as data is added."),
        ("Slope", f"=SLOPE({yr},{xr})", "0.000",
         "Percentage points of enterprise turnover per percentage point of "
         "consumer adoption."),
        ("Intercept", f"=INTERCEPT({yr},{xr})", "0.00",
         "Not interpretable - no country has zero adoption, so this is far "
         "outside the observed range."),
        ("Correlation (r)", f"=CORREL({xr},{yr})", "0.000",
         "Strength and direction of the linear association."),
        ("R-squared", f"=RSQ({yr},{xr})", "0.000",
         "Share of cross-country variation in Y that moves with X."),
        ("Denmark: actual Y", lookup("DK.ECM.ENT.TRN", 2024), "0.00",
         "Denmark's observed value."),
        ("Denmark: fitted Y",
         f"=INTERCEPT({yr},{xr})+SLOPE({yr},{xr})*{lookup('DK.ECM.IND.BUY', 2024)[1:]}",
         "0.00", "What the line predicts for Denmark's adoption level."),
        ("Denmark: residual",
         f"={lookup('DK.ECM.ENT.TRN', 2024)[1:]}-(INTERCEPT({yr},{xr})"
         f"+SLOPE({yr},{xr})*{lookup('DK.ECM.IND.BUY', 2024)[1:]})",
         "+0.00;-0.00",
         "Positive: Denmark converts adoption into commercial activity better "
         "than the EU pattern predicts. Negative: worse."),
    ]
    for label, formula, fmt, reading in stats:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, fmt
        rd = ws.cell(row=r, column=3, value=reading)
        rd.font, rd.alignment = T_SMALL, WRAP
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        ws.row_dimensions[r].height = 26
        r += 1

    # --- expansion register -------------------------------------------------
    if awaiting_x or awaiting_y:
        r += 1
        ws.cell(row=r, column=1,
                value="AWAITING DATA - not plotted").font = T_SUB
        r += 1
        header_row(ws, r, ["country", "code", "missing"], [20, 8, 74])
        r += 1
        for geo in awaiting_x:
            ws.cell(row=r, column=1, value=COUNTRIES[geo]).font = T_BODY
            ws.cell(row=r, column=2, value=geo).font = T_MONO
            c = ws.cell(row=r, column=3,
                        value=f"X - add {geo}.ECM.IND.BUY for 2024 (Eurostat "
                              f"isoc_ec_ib20)")
            c.font, c.fill = T_SMALL, F_GAP
            for j in range(1, 4):
                ws.cell(row=r, column=j).border = BOX
            r += 1
        for geo in awaiting_y:
            ws.cell(row=r, column=1, value=COUNTRIES[geo]).font = T_BODY
            ws.cell(row=r, column=2, value=geo).font = T_MONO
            c = ws.cell(row=r, column=3,
                        value=f"Y - add {geo}.ECM.ENT.TRN for 2024 (Eurostat "
                              f"tin00110)")
            c.font, c.fill = T_SMALL, F_GAP
            for j in range(1, 4):
                ws.cell(row=r, column=j).border = BOX
            r += 1

    source_note(ws, r + 1,
                f"Sources: Eurostat isoc_ec_ib20 (ES4) for X; Eurostat tin00110 "
                f"(ES5, ES6) for Y. "
                f"WHY A CROSS-SECTION: the Danish adoption and outcome series "
                f"share almost no observation years - the best time-series "
                f"pairing in this dataset is n=2 - so a within-Denmark scatter "
                f"of adoption against outcome cannot be drawn from verified "
                f"data. "
                f"SAMPLE: n={len(paired)} of 27 member states. This is a small "
                f"sample; report the association descriptively and do not quote "
                f"a p-value. Adding the missing values listed above raises n "
                f"automatically on the next rebuild. "
                f"WHAT Y MEASURES: tin00110 covers all enterprises with 10+ "
                f"employees outside the financial sector, so it includes B2B and "
                f"EDI ordering across every industry, not retail alone. X is a "
                f"consumer measure. The two sit on different sides of the market, "
                f"so a positive association is evidence that digital commerce is "
                f"deep in an economy - not evidence that consumers buying online "
                f"causes enterprise turnover.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_gap(wb):
    ws = wb.create_sheet("06_RETAIL_GAP")
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 92
    title_block(ws, "Documented gap - retail trade volume index",
                "Recorded rather than silently omitted.")

    r = 4
    for k, v in [
        ("Status", "NOT RETRIEVED"),
        ("Indicator", "Retail trade turnover, volume index (mangdeindeks)"),
        ("Authority", "Danmarks Statistik; also available via Eurostat sts_trtu_a"),
        ("Filters required",
         "geo=DK; nace_r2=G47; indic_bt=VOL; s_adj=SCA; unit=I21 (2021=100)"),
        ("Why not retrieved",
         "Values are published through StatBank and the Eurostat databrowser. This "
         "session's network policy blocked direct access to both, and the figure "
         "could not be verified by search. A value that cannot be traced is not "
         "entered."),
        ("Base year caution",
         "Danmarks Statistik rebased the index from 2015=100 to 2021=100. Series "
         "retrieved on different bases must not be joined."),
        ("Effect on the analysis",
         "The e-commerce section rests on the enterprise e-sales evidence in "
         "F3_ESALES instead, which is better sourced. No conclusion in the report "
         "depends on this series."),
        ("To fill",
         "Retrieve from statistikbanken.dk, add rows to dataset.py under series_code "
         "DK.RET.VOL with unit 'index 2021=100', and re-run build_workbook.py."),
    ]:
        ws.cell(row=r, column=1, value=k).font = T_SUB
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.alignment, c.fill, c.border = T_BODY, WRAP, F_GAP, BOX
        ws.row_dimensions[r].height = 44 if len(v) > 80 else 20
        r += 1

    ws.sheet_view.showGridLines = False
    return ws


def sheet_limitations(wb):
    ws = wb.create_sheet("07_LIMITATIONS")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 92
    title_block(ws, "Data quality statement", "Read before citing any value.")

    items = [
        ("No inferential statistics",
         "The longest series here has six observations. Regression, cointegration "
         "and Granger-causality procedures require far more, and any such result on "
         "this dataset would be uninterpretable. The workbook supports description "
         "and comparison only. Co-movement between digital payment adoption and "
         "branch closures is presented as association, never as measured causation."),
        ("Unbalanced panel",
         "Observation years differ by series because the underlying sources publish "
         "on different cycles - payment habits roughly biennially, Eurostat annually, "
         "branch counts irregularly. Gaps are genuine and are not filled."),
        ("Denominator break",
         "Danish online-purchasing figures change base between 2019 (% of "
         "individuals) and 2020 onward (% of internet users). The 2019 observation "
         "carries flag 'b' and is never plotted with later years."),
        ("Verbal quantities",
         "Values flagged 'e' were published as words, not figures - 'nearly one in "
         "five', 'just under 36,000'. They are recorded as the stated approximation "
         "with the original wording in the notes column."),
        ("Confounded outcome",
         "Branch closures reflect both digitalisation and sectoral consolidation "
         "(219 institutions in 1991, 51 in 2024). The branch series alone cannot "
         "separate these, and the report should not claim that it does."),
        ("Definitional spread in exclusion measures",
         "The five exclusion measures range from 4.7% to 25% because they define "
         "the population differently. They are not competing estimates of one "
         "quantity and must not be averaged or presented as a range."),
        ("Cross-section incomplete",
         "F5 covers 8 of 27 member states. It supports a ranking, not a regression."),
        ("Figure 6 sample size",
         "The adoption-to-outcome scatter rests on 6 complete country pairs. The "
         "association is strong and positive, but 6 points cannot support a "
         "p-value, a confidence interval, or a claim about causal direction. "
         "Report the slope and R-squared descriptively and say n explicitly. "
         "Adding the missing values listed on that sheet raises n automatically."),
        ("Figure 6 measures two sides of the market",
         "X is a consumer measure (individuals buying online); Y is an "
         "all-enterprise, all-sector measure that includes B2B and EDI ordering. "
         "A positive association indicates that digital commerce runs deep in an "
         "economy. It is not evidence that consumer purchasing causes enterprise "
         "turnover, and must not be written as though it were."),
        ("Mirror-sourced column",
         "The 16 country-level e-sales turnover values flagged 'u' were retrieved "
         "via search of Eurostat tin00110 rather than from the databrowser "
         "directly. Two values in the same column (EU27 19.49 and Ireland 38.25) "
         "are independently corroborated by source ES5, which supports the "
         "column, but each value should be spot-checked against the databrowser "
         "before final submission."),
        ("Search-based verification",
         "Direct access to statistical portals was blocked in the build environment. "
         "Values were verified against the issuing authority through search results "
         "reporting those publications. This is weaker than downloading the dataset: "
         "before final submission, spot-check high-stakes figures against the source "
         "pages directly."),
        ("Discarded material",
         "An earlier candidate dataset was rejected in full after verification found "
         "fabricated values carrying authentic dataset codes and extraction dates - "
         "including a Eurostat cross-section that inverted the true EU country "
         "ranking. None of it survives in this workbook."),
    ]
    r = 4
    for k, v in items:
        ws.cell(row=r, column=1, value=k).font = T_SUB
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.alignment, c.border = T_BODY, WRAP, BOX
        c.fill = F_FLAG
        ws.row_dimensions[r].height = 62
        r += 1

    ws.sheet_view.showGridLines = False
    return ws


def sheet_ai_log(wb):
    ws = wb.create_sheet("08_AI_LOG")
    title_block(ws, "AI use and validation log",
                "Raw material for the AI Use and Validation Appendix.")
    header_row(ws, 4, ["step", "AI assistance used", "how it was validated", "outcome"],
               [28, 40, 46, 34])

    log = [
        ("Source identification",
         "AI used to identify candidate statistical sources and dataset codes.",
         "Each source opened or search-verified against the issuing authority.",
         "Source register in 03_SOURCES."),
        ("Value retrieval",
         "AI used to search for published values by authority and indicator.",
         "Each value checked against a result reporting the issuing authority's own "
         "publication.",
         "69 observations retained."),
        ("Rejection of a prior dataset",
         "A candidate dataset produced with AI assistance was reviewed.",
         "Cross-checked against Eurostat's published country ranking; the values "
         "inverted the true ranking and contained duplicated and interpolated cells.",
         "Dataset rejected in full and excluded."),
        ("Workbook construction",
         "AI wrote the Python build script that generates this workbook.",
         "Structural assertions run at build time: source_ids resolve, units and "
         "denominators present, no duplicate observations, break flags set.",
         "build_workbook.py, re-runnable."),
        ("Analytical framing",
         "AI used to interpret patterns and suggest framings.",
         "Author reviewed each interpretation against the underlying values.",
         "Interpretations appear in the report, attributed to the author."),
        ("Not delegated to AI",
         "Selection of the research question, country, industries, SDG and policy "
         "comparator; the argument; the conclusions.",
         "n/a",
         "Author's own work."),
    ]
    r = 5
    for step, used, how, outcome in log:
        for j, v in enumerate([step, used, how, outcome], start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.font, c.alignment, c.border, c.fill = T_BODY, WRAP, BOX, F_RAW
        ws.row_dimensions[r].height = 52
        r += 1

    source_note(ws, r + 1,
                "This log records assistance during data assembly. Complete it with "
                "any further AI use during drafting before submission. The assessment "
                "requires that AI-assisted content be verified and acknowledged.")
    ws.sheet_view.showGridLines = False
    return ws


def main():
    n = validate()
    wb = Workbook()
    wb.remove(wb.active)

    sheet_cover(wb)
    sheet_readme(wb)
    sheet_master(wb)
    sheet_sources(wb)
    sheet_definitions(wb)
    sheet_calc(wb)
    sheet_f1(wb)
    sheet_f2(wb)
    sheet_f3(wb)
    sheet_f4(wb)
    sheet_f5(wb)
    sheet_f6(wb)
    sheet_gap(wb)
    sheet_limitations(wb)
    sheet_ai_log(wb)

    wb.properties.title = "Denmark: Digital Adoption and Policy Outcomes"
    wb.properties.subject = COURSE
    wb.properties.creator = STUDENT_ID
    wb.properties.description = (
        f"Statistical annex, v{VERSION}, built {BUILT}. {n} verified observations."
    )

    wb.save(OUT)
    print(f"wrote {os.path.abspath(OUT)}")
    print(f"{n} observations, {len(wb.sheetnames)} sheets")


if __name__ == "__main__":
    main()
