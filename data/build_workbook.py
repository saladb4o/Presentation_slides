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
from openpyxl.chart.series import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.trendline import Trendline
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from dataset import (COUNTRIES, OBS, POLICY_EVENTS, cross_section,
                     policy_events_for, validate)
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

# --- chart palette --------------------------------------------------------
# Four steps, ordered as a value ramp rather than a categorical set. Grey
# carries the series the reader is not meant to look at; the accent carries the
# one they are. Nothing is coloured for variety - colour routes attention.
#
# Chart colours are bare RGB (no leading alpha byte), unlike the cell fills
# above, because DrawingML and the styles API disagree about the format.
C_PALE = "E8E8E8"     # context, furthest back
C_GREY = "A3A3A3"     # context
C_ACCENT = "2E6DB4"   # focus - Denmark, or the single series in view
C_DARK = "1F3A5F"     # emphasis - matches NAVY

# Number formats, four-part: positive; negative; zero; text.
#
# The fourth section is the one that earns its place. lookup() returns "" for an
# observation that does not exist, which lands in the text section - so a gap
# renders as an en-dash instead of an empty cell. A gap should look like a gap,
# not like an oversight.
#
# CAVEAT, recorded on 01_README: a genuine zero also renders as an en-dash.
# No series in this dataset has a meaningful zero, so this is safe here; it
# would not be safe in a workbook that did.
N_DEC = '_(#,##0.00_);\\(#,##0.00\\);_("–"_);_("–"_)'
N_INT = '_(#,##0_);\\(#,##0\\);_("–"_);_("–"_)'
N_ONE = '_(#,##0.0_);\\(#,##0.0\\);_("–"_);_("–"_)'
N_THREE = '_(#,##0.000_);\\(#,##0.000\\);_("–"_);_("–"_)'
N_SIGNED = '_(+#,##0.00_);_(-#,##0.00_);_("–"_);_("–"_)'

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


def L(series, year):
    """`lookup` with the leading '=' stripped, for embedding inside a formula."""
    return lookup(series, year)[1:]


def style_chart(ch, legend="b"):
    """Strip Excel's default chart chrome.

    openpyxl's `style` presets produce the look everyone recognises as a default
    Excel chart. Removing the preset, the gridlines and the axis lines leaves the
    data as the only thing drawn, which is the point: every pixel that is not a
    value is competing with one that is.

    The axis LINES are hidden while the axes themselves are kept - tick labels
    still render, so the chart loses its frame without losing its scale.

    Pass legend=None for a single-series chart, where a legend restates the
    title and earns nothing.
    """
    ch.style = None
    for ax in (ch.x_axis, ch.y_axis):
        if ax is None:
            continue
        ax.majorGridlines = None
        ax.spPr = GraphicalProperties(ln=LineProperties(noFill=True))

    if legend is None:
        ch.legend = None
    elif ch.legend is not None:
        # Bottom, never right: a right-hand legend eats horizontal plot width,
        # which is the axis carrying the comparison in every chart here.
        ch.legend.position = legend
        ch.legend.overlay = False

    if isinstance(ch, BarChart):
        # Excel defaults to gapWidth 150, which leaves bars thinner than the
        # space between them and makes the whitespace the dominant shape.
        ch.gapWidth = 80
        if ch.grouping == "stacked":
            ch.overlap = 100
        elif ch.grouping == "clustered" and len(ch.series) > 1:
            ch.overlap = -27
    return ch


def paint(series, rgb, line=False):
    """Solid-fill a series in one palette colour."""
    series.graphicalProperties = GraphicalProperties(solidFill=rgb)
    if not line:
        series.graphicalProperties.ln = LineProperties(noFill=True)
    return series


def highlight_points(series, n_points, focus, base=C_GREY, accent=C_ACCENT):
    """Grey every bar except the ones named in `focus`.

    `focus` maps a zero-based point index to a colour. This is what turns a
    ranked bar chart from eight identically coloured bars into a chart with a
    subject: Denmark in the accent, the EU average in navy, everyone else
    receding into grey.
    """
    paint(series, base)
    series.data_points = [
        DataPoint(idx=i,
                  spPr=GraphicalProperties(
                      solidFill=focus.get(i, base),
                      ln=LineProperties(noFill=True)))
        for i in range(n_points)
    ]
    return series


def chart_title(ws, cell, text, note=None):
    """Write a chart's title into a cell instead of onto the chart.

    openpyxl renders chart titles inconsistently and they cannot be aligned to
    the sheet grid. A title in a cell aligns with everything else, stays
    editable by the reader, and can carry a units caption beneath it.
    """
    c = ws[cell]
    c.value = text
    c.font = Font(name="Calibri", size=11, bold=True, color=NAVY)
    c.fill = PatternFill("solid", fgColor="FFE7F2FF")
    c.alignment = Alignment(vertical="center")
    if note:
        below = ws.cell(row=c.row + 1, column=c.column, value=note)
        below.font = T_SMALL
    return c


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
        ("F5_EU27", "Figure 5 - online purchasing, all 27 member states, 2024"),
        ("F6_ADOPT_BENEFIT", "Figure 6 - adoption vs economic effect, EU 2024"),
        ("F7_QUALITY", "Figure 7 - DK vs EU: leads on adoption, trails on "
                       "service quality"),
        ("F8_SMVDIGITAL", "Figure 8 - SMV:Digital, the one policy with a "
                          "control group"),
        ("09_POLICY", "Policy events - dated instruments with legal citations"),
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

        # --- the fiscal case, and how much of it was ever verified ---------
        ("Digital Post: projected annual saving",
         lookup("DK.GOV.DGP.SAVE.PLAN", 2016), "mDKK/yr",
         "Ministry of Finance business case for the mandate (RR1)."),
        ("Digital Post: saving verifiable by audit",
         lookup("DK.GOV.DGP.SAVE.VERIF", 2016), "mDKK/yr",
         "Postage, paper and envelopes only (RR1)."),
        ("Digital Post: unverified share of the business case",
         f"=1-({L('DK.GOV.DGP.SAVE.VERIF', 2016)}"
         f"/{L('DK.GOV.DGP.SAVE.PLAN', 2016)})", "%",
         "Over half the projected saving - the wage and overhead component - was "
         "never substantiated. The cross-government study intended to test it was "
         "abandoned. The strongest cost-side finding in this workbook."),
        ("Digital Post: cost per formally exempt citizen, if the shortfall is real",
         f"=(({L('DK.GOV.DGP.SAVE.PLAN', 2016)}"
         f"-{L('DK.GOV.DGP.SAVE.VERIF', 2016)})*1000000)"
         f"/{L('DK.DGP.EXMP.N', 2026)}", "DKK",
         "ILLUSTRATIVE ONLY, and not a real unit cost: it divides an unverified "
         "saving shortfall by an unrelated headcount. Included because the "
         "comparison of magnitudes is informative; it must not be quoted as a "
         "cost per person."),

        # --- magnitudes ----------------------------------------------------
        ("Resident population, 1 January 2026",
         lookup("DK.POP.TOT", 2026), "count",
         "Direct lookup. The only population level in the workbook (DST2)."),
        ("Citizens formally exempt from Digital Post, Q1 2026",
         lookup("DK.DGP.EXMP.N", 2026), "count",
         "Headcount behind the 4.7% rate (DG1)."),
        ("Change in exempt headcount, 2025 to 2026",
         f"={L('DK.DGP.EXMP.N', 2026)}-{L('DK.DGP.EXMP.N', 2025)}", "count",
         "Falling. Note the 2025 figure is an 'approximately' value, so this "
         "difference is not precise."),
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


def policy_block(ws, row, series_code, heading="POLICY EVENTS ON THIS SERIES"):
    """Write the dated instruments bearing on `series_code` beneath a figure.

    openpyxl cannot draw a vertical rule on a chart plot area, so the events are
    rendered as a dated table directly under the data the chart reads. A reader
    can line the dates up against the series by eye, and - unlike an annotation
    burned into a chart image - each row carries its own legal citation and
    source_id, so the claim that an instrument took effect on a given date is
    auditable on the same terms as every value in the workbook.

    Returns the next free row.
    """
    events = policy_events_for(series_code)
    if not events:
        return row

    ws.cell(row=row, column=1, value=heading).font = T_SUB
    row += 1
    header_row(ws, row, ["date", "precision", "instrument", "citation", "source"],
               [14, 11, 46, 34, 10])
    row += 1
    for when, precision, name, citation, src, _desc, _rel in events:
        vals = [when, precision, name, citation, src]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=row, column=j, value=v)
            c.font = T_MONO if j in (1, 5) else T_BODY
            c.border, c.alignment, c.fill = BOX, WRAP, F_RAW
        row += 1
    return row + 1


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
        c.font, c.number_format = T_BODY, N_INT
    _style_view(ws, 5, 4 + len(years), 2)

    last = 4 + len(years)
    ch = ScatterChart()
    ch.x_axis.title = "Year"
    ch.y_axis.title = "Number of branches"
    ch.height, ch.width = 9, 17
    xs = Reference(ws, min_col=1, min_row=5, max_row=last)
    ys = Reference(ws, min_col=2, min_row=4, max_row=last)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(symbol="circle", size=7,
                      spPr=GraphicalProperties(
                          solidFill=C_ACCENT,
                          ln=LineProperties(noFill=True)))
    s.graphicalProperties.line = LineProperties(w=22000, solidFill=C_ACCENT)
    ch.series.append(s)
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 2002, 2026
    ch.y_axis.scaling.min = 0
    style_chart(ch, legend=None)
    chart_title(ws, "D3", "Bank branches in Denmark, 2004-2024",
                "Count of retail branches. Uneven year spacing, numeric X axis.")
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
        c.font, c.number_format = T_BODY, N_ONE
    _style_view(ws, 6, 5 + len(years), 2)
    lastA = 5 + len(years)

    chA = ScatterChart()
    chA.x_axis.title = "Year"
    chA.y_axis.title = "% of number of payments"
    chA.height, chA.width = 8, 15
    xs = Reference(ws, min_col=1, min_row=6, max_row=lastA)
    ys = Reference(ws, min_col=2, min_row=5, max_row=lastA)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(symbol="circle", size=7,
                      spPr=GraphicalProperties(
                          solidFill=C_ACCENT,
                          ln=LineProperties(noFill=True)))
    s.graphicalProperties.line = LineProperties(w=22000, solidFill=C_ACCENT)
    chA.series.append(s)
    chA.x_axis.scaling.min, chA.x_axis.scaling.max = 2016, 2026
    chA.y_axis.scaling.min, chA.y_axis.scaling.max = 0, 25
    style_chart(chA, legend=None)
    chart_title(ws, "D4", "Cash share of in-store payments, 2017-2025",
                "% of the number of payments made in physical retail.")
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
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_ONE
        for j in (1, 2):
            ws.cell(row=rr, column=j).border = BOX
    lastB = headB + len(comp)

    chB = BarChart()
    chB.type, chB.grouping = "bar", "clustered"
    chB.x_axis.title = "% of number of payments"
    chB.height, chB.width = 7, 15
    data = Reference(ws, min_col=2, min_row=headB, max_row=lastB)
    cats = Reference(ws, min_col=1, min_row=headB + 1, max_row=lastB)
    chB.add_data(data, titles_from_data=True)
    chB.set_categories(cats)
    # Cash is the subject of this figure, so cash is the only coloured bar.
    highlight_points(chB.series[0], len(comp), {2: C_ACCENT})
    style_chart(chB, legend=None)
    chart_title(ws, f"D{headB - 1}", "Composition of in-store payments, 2025",
                "Sums to 95%; the residual is other digital instruments.")
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
        c.font, c.fill, c.number_format = T_BODY, F_FLAG, N_ONE
        for j in (1, 2):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    r = policy_block(ws, r + 2, "DK.PAY.CASH.POS")

    source_note(ws, r,
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
        ws.cell(row=r, column=2, value=lookup("DK.ECM.ENT.TRN", y)).number_format = N_DEC
        ws.cell(row=r, column=3, value=lookup("EU.ECM.ENT.TRN", y)).number_format = N_DEC
    _style_view(ws, 5, 6, 3)

    ch = BarChart()
    ch.type, ch.grouping = "col", "clustered"
    ch.y_axis.title = "% of turnover"
    ch.x_axis.title = "Year"
    ch.height, ch.width = 9, 15
    data = Reference(ws, min_col=2, max_col=3, min_row=4, max_row=6)
    cats = Reference(ws, min_col=1, min_row=5, max_row=6)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    paint(ch.series[0], C_ACCENT)   # Denmark
    paint(ch.series[1], C_GREY)     # EU-27, context
    style_chart(ch)
    chart_title(ws, "E3", "E-sales as % of enterprise turnover, DK vs EU-27",
                "Denmark in blue; the EU average in grey.")
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
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        ws.cell(row=r, column=3, value=note).font = T_SMALL
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    r = policy_block(ws, r + 2, "DK.ECM.ENT.TRN")

    source_note(ws, r,
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
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_ONE
        ws.cell(row=r, column=3, value=basis).font = T_SMALL
        ws.cell(row=r, column=4, value=src).font = T_MONO
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
    last = 4 + len(rows)

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.x_axis.title = "% of population"
    ch.height, ch.width = 10, 18
    data = Reference(ws, min_col=2, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    paint(ch.series[0], C_ACCENT)
    style_chart(ch, legend=None)
    chart_title(ws, "F3", "Measures of digital exclusion, Denmark",
                "Five definitions of the same phenomenon; they are nested, "
                "not contradictory.")
    ws.add_chart(ch, "F4")

    r = last + 2
    ws.cell(row=r, column=1, value="AGE GRADIENT IN FORMAL EXEMPTION (2022)").font = T_SUB
    r += 1
    header_row(ws, r, ["age group", "exempt (%)"], [46, 12])
    r += 1
    for label, code in [("Age 75-84", "DK.DGP.EXMP.7584"), ("Age 85+", "DK.DGP.EXMP.85P")]:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup(code, 2022))
        c.font, c.fill, c.number_format = T_BODY, F_FLAG, N_ONE
        for j in (1, 2):
            ws.cell(row=r, column=j).border = BOX
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="HEADCOUNTS, NOT SHARES").font = T_SUB
    r += 1
    header_row(ws, r, ["quantity", "persons", "basis"], [46, 14, 74])
    r += 1
    heads = [
        ("Citizens formally exempt, Q1 2026", lookup("DK.DGP.EXMP.N", 2026),
         "Reported directly by the Agency for Digital Government (DG1)."),
        ("Citizens formally exempt, April 2025", lookup("DK.DGP.EXMP.N", 2025),
         "Reported as approximately 256,000 (DG1)."),
        ("Implied population aged 15+",
         f"={L('DK.DGP.EXMP.N', 2026)}/({L('DK.DGP.EXMP', 2026)}/100)",
         "DERIVED, not retrieved: the exempt headcount divided by the exemption "
         "rate. Used only to convert the capability shares below into orders of "
         "magnitude. A published 15+ population figure was not verifiable in this "
         "session; see 06_RETAIL_GAP."),
        ("Implied persons who do not use digital public services at all",
         f"=({L('DK.DGX.NOUSE', 2026)}/100)*({L('DK.DGP.EXMP.N', 2026)}"
         f"/({L('DK.DGP.EXMP', 2026)}/100))",
         "ORDER OF MAGNITUDE ONLY. Applies a share measured on 'the population' "
         "to a 15+ base; the denominators are not identical."),
        ("Implied persons facing difficulty with digital public services",
         f"=({L('DK.DGX.DIFF', 2026)}/100)*({L('DK.DGP.EXMP.N', 2026)}"
         f"/({L('DK.DGP.EXMP', 2026)}/100))",
         "ORDER OF MAGNITUDE ONLY, same caveat."),
    ]
    for label, formula, note in heads:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_INT
        ws.cell(row=r, column=3, value=note).font = T_SMALL
        ws.cell(row=r, column=3).alignment = WRAP
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        ws.row_dimensions[r].height = 40
        r += 1

    r = policy_block(ws, r + 1, "DK.DGP.EXMP")

    source_note(ws, r,
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
    """Complete EU ranking on the consumer adoption measure.

    The order is computed from OBS at build time rather than typed, so the
    ranking cannot drift out of step with the data. The EU-27 aggregate is
    ranked alongside the member states as a reference marker; it is not an
    observation and is excluded from every calculation on F6.
    """
    ws = wb.create_sheet("F5_EU27")
    title_block(ws, "Figure 5 - Individuals who bought online, 2024",
                "All 27 member states and the EU-27 aggregate, ranked. "
                "Denominator: % of internet users.")
    header_row(ws, 4, ["country", "%", "series_code"], [22, 10, 24])

    # Ranked descending on the observed value. Built from OBS, not typed.
    rows = [(("EU-27 average" if geo == "EU27" else COUNTRIES[geo]),
             f"{code.split('.')[0]}.ECM.IND.BUY", val)
            for code, _ind, geo, yr, val, *_ in OBS
            if yr == 2024 and code.endswith(".ECM.IND.BUY")]
    order = [(n, c) for n, c, _v in sorted(rows, key=lambda t: -t[2])]

    for i, (name, code) in enumerate(order):
        r = 5 + i
        ws.cell(row=r, column=1, value=name).font = T_BODY
        c = ws.cell(row=r, column=2, value=lookup(code, 2024))
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        ws.cell(row=r, column=3, value=code).font = T_MONO
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
    last = 4 + len(order)

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.x_axis.title = "% of internet users"
    ch.height, ch.width = 18, 17          # 28 bars need the vertical room
    data = Reference(ws, min_col=2, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    # The subject of this chart is Denmark's position in the distribution, not
    # 28 values. Denmark takes the accent, the EU aggregate takes navy as the
    # reference marker, and every member state recedes to grey so the
    # comparison reads at a glance.
    focus = {i: (C_ACCENT if code.startswith("DK") else C_DARK)
             for i, (_name, code) in enumerate(order)
             if code.startswith(("DK", "EU"))}
    highlight_points(ch.series[0], len(order), focus)
    style_chart(ch, legend=None)
    chart_title(ws, "E3", "Individuals who bought online, 2024",
                "Denmark in blue, EU-27 aggregate in navy, member states in "
                "grey. Ranked descending.")
    ws.add_chart(ch, "E4")

    source_note(ws, last + 2,
                "Source: Eurostat isoc_ec_ib20, complete databrowser extract for "
                "2024 (ES7), unrounded. This replaces an earlier 8-country version "
                "built from rounded press-release figures; on those the Italian and "
                "Romanian values both read 60% and appeared tied, while unrounded "
                "Italy is second lowest at 59.60 and Romania is above it at 59.73. "
                "Bulgaria remains the lowest of the 27 at 57.18. The ranking above "
                "is computed from the data at build time, "
                "so it cannot fall out of step with 02_MASTER. Denominator is % of "
                "internet users, not % of individuals - see 04_DEFINITIONS.")
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
            c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
    first, last = 5, 4 + len(paired)

    ch = ScatterChart()
    ch.x_axis.title = "Individuals who bought online (% of internet users)"
    ch.y_axis.title = "E-sales as % of enterprise turnover"
    ch.height, ch.width = 11, 18
    xs = Reference(ws, min_col=3, min_row=first, max_row=last)
    ys = Reference(ws, min_col=4, min_row=4, max_row=last)
    s = Series(ys, xs, title_from_data=True)
    s.marker = Marker(
        symbol="circle", size=9,
        spPr=GraphicalProperties(solidFill=C_ACCENT,
                                 ln=LineProperties(noFill=True)))
    s.graphicalProperties.line.noFill = True          # markers only, no join
    # R-squared is now displayed. It was withheld while the X column was a
    # tail-selected sample assembled from a press release; the column is now the
    # complete isoc_ec_ib20 databrowser extract for all 27 member states, so the
    # fit is estimated on every paired country rather than on the extremes, and
    # the statistic has been earned. The SAMPLE block below records what the
    # selected sample had reported, because the difference is itself a finding.
    s.trendline = Trendline(trendlineType="linear", dispRSqr=True, dispEq=True)
    ch.series.append(s)
    # The fitted line is drawn in the dark emphasis colour rather than grey. It
    # is still an interpretation laid over the observations, so it does not take
    # the accent, but on a complete cross-section of 18 countries with a slope
    # over five standard errors from zero it is no longer the weaker of the two.
    s.trendline.spPr = GraphicalProperties(
        ln=LineProperties(solidFill=C_DARK, w=16000))
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 50, 100
    ch.y_axis.scaling.min = 0
    style_chart(ch, legend=None)
    chart_title(ws, "F3", "Digital adoption and e-commerce turnover, EU 2024",
                "One point per member state with both measures. Fitted by "
                "ordinary least squares; see the statistics below.")
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
        ("n (countries)", f"=COUNT({xr})", N_INT,
         "Number of complete X-Y pairs. Expands automatically as data is added."),
        ("Slope", f"=SLOPE({yr},{xr})", N_THREE,
         "Percentage points of enterprise turnover per percentage point of "
         "consumer adoption."),
        ("Intercept", f"=INTERCEPT({yr},{xr})", N_DEC,
         "Not interpretable - no country has zero adoption, so this is far "
         "outside the observed range."),
        ("Correlation (r)", f"=CORREL({xr},{yr})", N_THREE,
         "Strength and direction of the linear association."),
        ("R-squared", f"=RSQ({yr},{xr})", N_THREE,
         "Share of cross-country variation in Y that moves with X. Estimated on "
         "the complete set of paired member states, so it is quotable - see the "
         "SAMPLE block below for what the earlier tail-selected sample claimed."),
        ("Slope standard error",
         f"=STEYX({yr},{xr})/SQRT(DEVSQ({xr}))", N_THREE,
         "Precision of the slope estimate."),
        ("Slope t-statistic",
         f"=SLOPE({yr},{xr})/(STEYX({yr},{xr})/SQRT(DEVSQ({xr})))", N_DEC,
         "Slope divided by its standard error, on n-2 degrees of freedom. "
         "Above about 2.1 the slope is distinguishable from zero at the 5% "
         "level on this sample size."),
        ("Denmark: actual Y", lookup("DK.ECM.ENT.TRN", 2024), N_DEC,
         "Denmark's observed value."),
        ("Denmark: fitted Y",
         f"=INTERCEPT({yr},{xr})+SLOPE({yr},{xr})*{lookup('DK.ECM.IND.BUY', 2024)[1:]}",
         N_DEC, "What the line predicts for Denmark's adoption level."),
        ("Denmark: residual",
         f"={lookup('DK.ECM.ENT.TRN', 2024)[1:]}-(INTERCEPT({yr},{xr})"
         f"+SLOPE({yr},{xr})*{lookup('DK.ECM.IND.BUY', 2024)[1:]})",
         N_SIGNED,
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

    # --- sample provenance -------------------------------------------------
    # This block used to be a SELECTION WARNING. The X column had been assembled
    # from a Eurostat press release, which names the countries that make a story:
    # the top of the ranking, the bottom, and a couple of large movers. That is a
    # sample drawn from the tails, and truncating a distribution at both ends
    # while discarding the middle raises the correlation coefficient largely
    # independently of the underlying relationship.
    #
    # The column is now the complete isoc_ec_ib20 databrowser extract for 2024,
    # all 27 member states, unrounded. The warning is therefore replaced - but
    # the numbers it was warning about are kept, because the comparison measures
    # the bias rather than merely asserting it: the slope barely moved while the
    # fit fell by nearly two tenths. That is what tail selection does, shown
    # rather than claimed.
    r += 1
    ws.cell(row=r, column=1,
            value="SAMPLE - how these points were obtained").font = T_SUB
    r += 1
    for line in [
        f"COMPLETE FOR 2024: the X column is the full Eurostat isoc_ec_ib20 "
        f"extract for all 27 member states, unrounded, taken from the "
        f"databrowser. Every member state holding both measures is plotted - "
        f"{len(paired)} of them. No country with both values is excluded, so the "
        "fit is no longer conditioned on where a country sits in the ranking.",
        "WHAT THE EARLIER SAMPLE CLAIMED: an earlier version of this figure drew "
        "X from a Eurostat press release, which named only the three highest "
        "countries, the three lowest and two large movers. On those 6 tail "
        "countries the fit was R-squared 0.853 with a slope of +0.655. On the "
        "complete cross-section it is R-squared 0.674 with a slope of +0.602.",
        "READING THAT COMPARISON: the slope moved by about 8% while R-squared "
        "fell by 0.18. This is the signature of selection on the tails - it "
        "widens the spread in X relative to the scatter around the line, which "
        "flatters the fit while leaving the estimated relationship roughly "
        "intact. The earlier R-squared was an upper bound, as the warning it "
        "replaced said; this one is an estimate.",
        "STILL NOT A COMPLETE CROSS-SECTION OF THE EU: nine member states hold "
        "the adoption measure but not the enterprise turnover measure and are "
        "listed below. The sample is complete with respect to X and incomplete "
        "with respect to Y, so it is 18 countries rather than 27 - but the "
        "countries dropped are dropped by data availability, not by their "
        "position on either axis.",
        "DIRECTION OF CAUSATION IS NOT ESTABLISHED AND CANNOT BE. X measures "
        "consumers; Y measures enterprises, including business-to-business sales "
        "that no consumer touches. Both plausibly rise with national income, "
        "which is in neither axis. This figure shows that digital commerce runs "
        "deep in the same economies where consumers buy online. It does not show "
        "that the one produces the other.",
    ]:
        c = ws.cell(row=r, column=1, value=line)
        c.font, c.alignment, c.fill = T_SMALL, WRAP, F_FLAG
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
        ws.row_dimensions[r].height = 46
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


def sheet_policy(wb):
    """The instruments themselves, dated and cited.

    A workbook of outcomes cannot show policy impact, because impact is a
    statement about what happened relative to something. This sheet supplies the
    something. Each row is an instrument with a commencement date, a legal
    citation, a source_id and the series it bears on; the figure sheets render
    the same rows beneath their data.

    The `precision` column exists because two of these dates are known only to
    the year. Recording them as if they were known to the day would be the same
    class of error as recording an interpolated value as a retrieved one.
    """
    ws = wb.create_sheet("09_POLICY")
    title_block(ws, "Policy events",
                "Dated instruments, with the series each one bears on. "
                "Rendered as event tables beneath the figures they affect.")
    header_row(ws, 4,
               ["date", "precision", "instrument", "legal citation", "source_id",
                "what it does", "series affected"],
               [13, 11, 44, 32, 10, 74, 24])

    r = 5
    for when, precision, name, citation, src, desc, related in POLICY_EVENTS:
        vals = [when, precision, name, citation, src, desc, related]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.font = T_MONO if j in (1, 5, 7) else T_BODY
            c.border, c.alignment, c.fill = BOX, WRAP, F_RAW
        ws.row_dimensions[r].height = 46
        r += 1

    source_note(ws, r + 1,
                "Reading: the mandate date of 1 November 2014 is the hinge of this "
                "workbook. Digital Post was not adopted by citizens choosing it; "
                "citizens were enrolled automatically, and exemption is available "
                "only against statutory criteria. Adoption rates after that date "
                "therefore measure compliance with a legal obligation, not revealed "
                "preference, and no figure in this workbook should be read as though "
                "they measured preference.")
    source_note(ws, r + 3,
                "CORRECTION RECORDED: an earlier draft of this workbook stated that "
                "SMV:Digital was being defunded. That claim could not be verified, "
                "and the scheme's own 2026 grant-pool page (SMV1) documents pools "
                "still open, with a further pool opening on 26 October 2026. The "
                "claim has been withdrawn from the dataset and from the report's "
                "argument. See 07_LIMITATIONS and 08_AI_LOG.")
    ws.freeze_panes = "C5"
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f7(wb):
    """Adoption is not the same thing as service quality, and Denmark proves it.

    Denmark leads the EU on every adoption and capability measure in this
    workbook, and sits BELOW the EU average on the eGovernment Benchmark score
    for citizen services - 82.2 against 84.64 - and far below on cross-border
    services. That pairing is the strongest finding in the dataset: near-universal
    use of public digital services was achieved by statute, and universal use has
    not produced above-average services.

    The chart is a grouped bar rather than a scatter because these are six
    different indicators on three different denominators; plotting them against
    each other would imply a relationship that does not exist. What is being
    compared is Denmark against the EU average, indicator by indicator.
    """
    ws = wb.create_sheet("F7_QUALITY")
    title_block(ws, "Figure 7 - Denmark vs the EU: adoption and capability, then quality",
                "Leads on every capability measure. Below average on citizen "
                "service quality.")
    header_row(ws, 4, ["indicator", "Denmark", "EU-27", "unit"], [46, 14, 14, 30])

    rows = [
        ("SMEs with at least basic digital intensity",
         lookup("DK.ENT.DII", 2025), lookup("EU.ENT.DII", 2025), "% of SMEs"),
        ("Enterprises adopting AI",
         lookup("DK.ENT.AI", 2025), "", "% of enterprises (EU avg 19.95)"),
        ("Digital public services for citizens",
         lookup("DK.GOV.DPS.CIT", 2025), lookup("EU.GOV.DPS.CIT", 2025),
         "eGovernment Benchmark score 0-100"),
        ("Cross-border digital public services",
         lookup("DK.GOV.DPS.XB", 2025), "", "score 0-100 (EU avg 75.28)"),
    ]
    r = 5
    for label, dk, eu, unit in rows:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=dk)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        if eu:
            c = ws.cell(row=r, column=3, value=eu)
            c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        ws.cell(row=r, column=4, value=unit).font = T_SMALL
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = BOX
        r += 1
    last = r - 1

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.x_axis.title = "% or benchmark score"
    ch.height, ch.width = 10, 18
    data = Reference(ws, min_col=2, max_col=3, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    paint(ch.series[0], C_ACCENT)   # Denmark
    paint(ch.series[1], C_GREY)     # EU-27, context
    style_chart(ch)
    chart_title(ws, "F3", "Denmark vs EU-27 average",
                "Denmark in blue, EU average in grey. Note the direction "
                "reverses on the bottom two rows.")
    ws.add_chart(ch, "F4")

    r = last + 2
    ws.cell(row=r, column=1,
            value="THE GAP THAT MATTERS - service quality, not capability").font = T_SUB
    r += 1
    header_row(ws, r, ["quantity", "value", "reading"], [46, 14, 74])
    r += 1
    gaps = [
        ("Digital public services, DK minus EU average",
         f"={L('DK.GOV.DPS.CIT', 2025)}-{L('EU.GOV.DPS.CIT', 2025)}",
         "Negative. The most digitalised population in the EU receives "
         "below-average digital public services."),
        ("Digital skills gap within Denmark, 16-24 minus 55-74",
         f"={L('DK.SKL.1624', 2025)}-{L('DK.SKL.5574', 2025)}",
         "The within-country spread. Note that Denmark's WEAKEST age group "
         "(67.81%) still beats the EU average (42.60%) by 25pp, so Danish "
         "exclusion is not a skills deficit relative to Europe - it is a mandate "
         "calibrated above the bottom of its own distribution."),
        ("AI adoption gap within Denmark, large firms minus SMEs",
         f"={L('DK.ENT.AI.LRG', 2025)}-{L('DK.ENT.AI.SME', 2025)}",
         "Breadth without depth, restated for AI."),
    ]
    for label, formula, note in gaps:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill, c.number_format = T_BODY, F_CALC, N_DEC
        ws.cell(row=r, column=3, value=note).font = T_SMALL
        ws.cell(row=r, column=3).alignment = WRAP
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        ws.row_dimensions[r].height = 44
        r += 1

    source_note(ws, r + 1,
                "Source: European Commission, Digital Decade 2026 country report for "
                "Denmark (EC1). CAUTION: the eGovernment Benchmark is a scored "
                "assessment, not a survey proportion, and a 2.4-point difference "
                "between two scores should not be read as a precisely measured gap. "
                "The direction is the finding; the magnitude is not.")
    ws.sheet_view.showGridLines = False
    return ws


def sheet_f8(wb):
    """The only control-group evidence in the workbook.

    Every other adoption-and-outcome pairing here is correlational. The June 2025
    Effektmaaling, prepared by Danmarks Statistik, compared SMV:Digital
    participants against comparable non-participating firms and found higher
    revenue and higher employment. A comparison group is worth more, evidentially,
    than any cross-section of countries in this file - which is why this sheet
    exists and why Figure 6 should be read as support for it rather than the
    other way round.

    No effect size is plotted because none was verified. Plotting the
    participation shares as though they were an effect would repeat exactly the
    error this workbook was rebuilt to avoid.
    """
    ws = wb.create_sheet("F8_SMVDIGITAL")
    title_block(ws, "Figure 8 - SMV:Digital, the one policy with a control group",
                "Danmarks Statistik matched-comparison evaluation, June 2025.")
    header_row(ws, 4, ["measure", "value", "unit"], [52, 14, 30])

    rows = [
        ("Digitalisation projects supported since 2018",
         lookup("DK.SME.SMVD.PROJ", 2025), "count"),
        ("Participants investing further during the project",
         lookup("DK.SME.SMVD.INV", 2025), "% of participants"),
        ("Participants with no further investment plans",
         lookup("DK.SME.SMVD.NOINV", 2025), "% of participants"),
    ]
    r = 5
    for label, formula, unit in rows:
        ws.cell(row=r, column=1, value=label).font = T_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.fill = T_BODY, F_CALC
        c.number_format = N_INT if unit == "count" else N_ONE
        ws.cell(row=r, column=3, value=unit).font = T_SMALL
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        r += 1
    last = r - 1

    ch = BarChart()
    ch.type, ch.grouping = "bar", "clustered"
    ch.x_axis.title = "% of participating enterprises / count"
    ch.height, ch.width = 8, 16
    data = Reference(ws, min_col=2, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    paint(ch.series[0], C_ACCENT)
    style_chart(ch, legend=None)
    chart_title(ws, "E3", "SMV:Digital participant outcomes",
                "Participation measures only. No effect size is plotted "
                "because none was verified.")
    ws.add_chart(ch, "E4")

    r = last + 2
    ws.cell(row=r, column=1,
            value="WHY THIS IS THE STRONGEST EVIDENCE IN THE WORKBOOK").font = T_SUB
    r += 1
    for line in [
        "The evaluation was carried out by Danmarks Statistik, which compared "
        "participating firms against comparable firms that did not participate. "
        "Participants showed higher revenue AND higher employment.",
        "That is a comparison group. Nothing else in this workbook has one. "
        "Figure 6's cross-section can show that adoption and commercial activity "
        "move together across countries; it cannot rule out that richer countries "
        "simply do more of both. A matched comparison can.",
        "LIMIT: the effect sizes are not reproduced here because they were not "
        "verified against the evaluation itself. The direction of the finding is "
        "sourced; the magnitude is not, and must not be invented.",
        "LIMIT: participation is voluntary, so selection into the programme by "
        "more capable or more ambitious firms is not excluded by matching alone.",
    ]:
        c = ws.cell(row=r, column=1, value=line)
        c.font, c.alignment = T_SMALL, WRAP
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        ws.row_dimensions[r].height = 34
        r += 1

    r = policy_block(ws, r + 1, "DK.SME.SMVD.PROJ")

    source_note(ws, r,
                "Source: Effektmaaling af SMV:Digital, Danmarks Statistik for the "
                "Agency for Digital Government, June 2025 (DG3); scheme status from "
                "SMV:Digital's 2026 grant-pool page (SMV1).")
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
        ("Figure 6 tail selection - RESOLVED, and what it cost",
         "The adoption column in Figure 6 was originally assembled from a "
         "Eurostat press release naming the highest three countries, the lowest "
         "three and two large movers, so most plotted points came from the ends "
         "of the EU distribution. Selecting on the extremes of X inflates the "
         "correlation coefficient regardless of the underlying relationship, and "
         "R-squared was withheld from the chart face for that reason. The column "
         "is now the complete isoc_ec_ib20 databrowser extract for all 27 member "
         "states, unrounded, so the selection is gone and R-squared is displayed. "
         "The measured cost of the bias is retained on F6 because it is "
         "informative: on the 6 tail countries the fit was R-squared 0.853 with a "
         "slope of +0.655; on the complete cross-section it is R-squared 0.674 "
         "with a slope of +0.602. Tail selection barely moved the slope and "
         "flattered the fit by 0.18."),
        ("No price deflator on the turnover series",
         "E-sales as a share of enterprise turnover runs 2014 to 2024, spanning "
         "the pandemic and the 2022 inflation episode. Turnover is nominal, and "
         "online and physical retail did not face the same price path. Part of the "
         "measured rise in the e-sales share is therefore relative price movement "
         "rather than real reallocation of activity. No deflator was available in "
         "this session and none has been applied, so the doubling of intensity "
         "should be read as nominal."),
        ("Banking series use different base years",
         "Branch counts begin in 2004; institution counts and employment begin in "
         "1991. A 2004-2024 branch change and a 1991-2024 employment change are "
         "not comparable, and placing the two percentages side by side in prose "
         "would misrepresent both. 05_CALC labels every window explicitly. Either "
         "state both windows or do not draw the comparison."),
        ("No sampling error is reported anywhere",
         "The Eurostat, Nationalbank and Agency for Digital Government figures are "
         "survey estimates and carry sampling error that the issuing authorities "
         "publish but this workbook does not reproduce. Small differences should "
         "not be treated as established: a 2-3 point gap between two survey "
         "proportions, or between two eGovernment Benchmark scores, may not be "
         "distinguishable from zero. Directions are more robust than magnitudes "
         "throughout."),
        ("Headcount conversions rest on an implied denominator",
         "A published figure for the Danish population aged 15 and over could not "
         "be verified in this session. F4 therefore derives an implied 15+ base by "
         "dividing the exempt headcount by the exemption rate, both from the same "
         "source. Persons-affected figures built on it are orders of magnitude, "
         "not counts, and the capability shares they scale are measured on 'the "
         "population' rather than on the 15+ base - the denominators are not "
         "identical. Every such cell is marked in place."),
        ("A withdrawn claim about SMV:Digital",
         "An earlier draft of this workbook asserted that SMV:Digital was being "
         "defunded, and an argument was built on the contrast between a programme "
         "that works and a programme being cut. The claim could not be verified. "
         "The scheme's own 2026 grant-pool page documents pools still open and a "
         "further pool opening on 26 October 2026. The claim has been removed from "
         "the dataset and from the report's argument, and the correction is "
         "recorded in 09_POLICY and 08_AI_LOG rather than silently erased."),
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
        ("Cross-section complete on adoption, incomplete on outcome",
         "The adoption measure now covers all 27 member states for 2024, so F5 is "
         "a complete EU ranking. The enterprise-turnover measure does not: nine "
         "member states hold adoption but not turnover and cannot enter Figure 6. "
         "Those nine are dropped by data availability rather than by their "
         "position on either axis, which is why the remaining 18 are treated as a "
         "usable cross-section."),
        ("Figure 6 sample size",
         "The adoption-to-outcome scatter rests on 18 complete country pairs, up "
         "from 6. That is enough to report a slope with a standard error and a "
         "t-statistic, all three of which are on the sheet as live formulas. It "
         "is not enough, and no sample size would be enough here, to support a "
         "claim about causal direction: this is one year of cross-sectional data "
         "with no control for national income. Say n explicitly, report the "
         "slope with its standard error, and keep the language associational."),
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
         "Every retained observation carries a source_id."),
        ("Rejection of a prior dataset",
         "A candidate dataset produced with AI assistance was reviewed.",
         "Cross-checked against Eurostat's published country ranking; the values "
         "inverted the true ranking and contained duplicated and interpolated cells.",
         "Dataset rejected in full and excluded."),
        ("Withdrawal of an AI-suggested claim",
         "An AI-assisted draft asserted that the SMV:Digital grant scheme was "
         "being defunded, and an argument was built on the contrast between a "
         "programme with measured positive effects and a programme being cut.",
         "Searched for the scheme's funding status. The scheme's own 2026 "
         "grant-pool page documents pools still open and a further pool opening "
         "26 October 2026. No source supported the defunding claim.",
         "Claim withdrawn from the dataset and the argument; the withdrawal is "
         "recorded in 09_POLICY and 07_LIMITATIONS rather than erased."),
        ("Statistical self-audit",
         "AI was asked to audit its own workbook as a macroeconomic policy "
         "reviewer would.",
         "The audit found that Figure 6's adoption column had been assembled "
         "from a press release naming only the top three, bottom three and three "
         "large movers - a sample drawn from the tails, which inflates R-squared "
         "by construction.",
         "R-squared removed from the chart face; a selection warning added to "
         "F6; the limitation recorded in 07_LIMITATIONS. Later resolved - see "
         "the two rows below."),
        ("Failed verification attempt",
         "AI was asked to retrieve Eurostat isoc_ec_ib20 for 2024 for the twelve "
         "member states missing from Figure 6, so the tail selection could be "
         "removed.",
         "Eurostat and the national statistical offices are unreachable from the "
         "build environment. Web search returned only the press release naming "
         "the same tails, two country values with no attributable source, and one "
         "answer mixing the '% of internet users' and '% of individuals' "
         "denominators in a single paragraph.",
         "No values accepted. Recorded because the honest outcome of a "
         "verification attempt is sometimes that it failed."),
        ("Author-supplied authoritative extract",
         "The author retrieved the complete isoc_ec_ib20 table from the Eurostat "
         "databrowser and supplied it as a spreadsheet; AI parsed it into the "
         "dataset.",
         "The extract carries its own provenance header - dataset code, "
         "extraction timestamp, last-update date, and an explicit unit of "
         "'percentage of individuals who used internet within the last year'. "
         "The ten values it overlapped with were compared against the rounded "
         "press-release figures already held; all ten agreed to rounding.",
         "All 27 member states plus the EU-27 aggregate added under source ES7. "
         "Figure 6 went from n=6 to n=18 and R-squared was restored to the chart "
         "face. The superseded rounded values are recorded in each row's note."),
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
    sheet_f7(wb)
    sheet_f8(wb)
    sheet_policy(wb)
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
