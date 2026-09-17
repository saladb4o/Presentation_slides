"""Workbook styling: the palette, the formats, and the per-sheet furniture.

Kept apart from build_workbook.py so that "how it looks" can be reviewed without
reading "what it says".

PALETTE PROVENANCE
------------------
Two schemes, used for different jobs, because they answer different questions.

1. CATEGORICAL (chart C1, where three payment instruments must be told apart).
   Slots 1-3 of the validated default data-viz palette:

       blue #2a78d6 . orange #eb6834 . aqua #1baf7a

   Validated with the palette checker, light mode, adjacent pairlist:
   lightness band PASS, chroma floor PASS, CVD separation PASS (worst adjacent
   dE 9.2 deutan), normal-vision floor PASS (worst adjacent dE 27.6).
   Aqua carries a contrast WARN at 2.74:1 against a near-white surface, so the
   relief rule applies and C1 ships visible direct labels on every column.

2. HIGHLIGHT / CONTEXT (charts C3 and C4, where one country is the subject and
   the rest are background). Accent blue against neutral grey:

       accent #2a78d6 . context #8F8F8F

   This deliberately fails the checker's chroma floor, and the failure is the
   point: the checker scores categorical palettes, where every slot must read as
   its own identity, whereas grey here means "not the subject". The pair clears
   the separation gates that do apply - CVD dE 11.7 tritan, normal-vision dE
   17.9 - and both clear 3:1 contrast against the surface.

Charts take bare RGB with a leading '#', which is what XlsxWriter expects.
"""

import math

# --- chart colour ----------------------------------------------------------
CAT_1 = "#2a78d6"      # categorical slot 1 - blue
CAT_2 = "#eb6834"      # categorical slot 2 - orange
CAT_3 = "#1baf7a"      # categorical slot 3 - aqua

ACCENT = "#2a78d6"     # the subject of a highlight chart
CONTEXT = "#8F8F8F"    # everything that is not the subject
ACCENT_LIGHT = "#9FC3EC"  # same hue, lighter - marks an estimate rather than a
                          # published figure, and is legended wherever it appears
GRID = "#D9D9D9"       # recessive gridlines
AXIS_INK = "#52514E"   # axis and tick text

# --- document colour -------------------------------------------------------
NAVY = "#1F3A5F"       # titles, header bands
INK = "#1A1A1A"
MUTED = "#5A5A5A"

FILL_DERIVED = "#EAF1F8"   # value produced by a formula
FILL_FLAGGED = "#FDF3E3"   # break, estimate or provisional
FILL_GAP = "#F9ECEC"       # documented gap
# A retrieved value carries no fill at all. White is the default state, and the
# default state should be the commonest one.

# --- tab colour, by sheet family -------------------------------------------
TAB_REFERENCE = NAVY
TAB_CHART = "#2E6DB4"
TAB_SUPPORT = "#7A7A7A"
TAB_CAUTION = "#C8912F"

FONT = "Calibri"


def formats(wb):
    """Build every cell format once, and hand them back by name.

    One typeface throughout. Sizes carry the hierarchy: 16 for a sheet title,
    11 for prose, 10 for data. No monospace anywhere - in a spreadsheet it reads
    as a code dump rather than as a figure.
    """
    def f(**kw):
        kw.setdefault("font_name", FONT)
        return wb.add_format(kw)

    return {
        "title": f(font_size=16, bold=True, font_color=NAVY),
        "subtitle": f(font_size=11, font_color=MUTED, italic=True),
        "section": f(font_size=11, bold=True, font_color=NAVY),
        "prose": f(font_size=11, font_color=INK, text_wrap=True, valign="top"),
        "prose_n": f(font_size=11, font_color=INK, valign="top"),
        "small": f(font_size=9, font_color=MUTED, text_wrap=True, valign="top"),

        "head": f(font_size=10, bold=True, font_color="#FFFFFF", bg_color=NAVY,
                  text_wrap=True, valign="bottom", border=0),
        "label": f(font_size=10, bold=True, font_color=INK, valign="top"),
        # Same, but wrapping. A row-label column narrower than its longest
        # label clips it against the occupied cell to its right; wrapping
        # costs nothing where the row height is computed from the label too.
        "label_wrap": f(font_size=10, bold=True, font_color=INK,
                        valign="top", text_wrap=True),

        "text": f(font_size=10, font_color=INK, valign="top", text_wrap=True),
        "text_n": f(font_size=10, font_color=INK, valign="top"),
        "code": f(font_size=10, font_color=INK, valign="top"),

        "year": f(font_size=10, font_color=INK, num_format="0", align="center"),
        "num": f(font_size=10, font_color=INK, num_format="#,##0.0;-#,##0.0;0;@"),
        "int": f(font_size=10, font_color=INK, num_format="#,##0;-#,##0;0;@"),
        "pct1": f(font_size=10, font_color=INK, num_format='#,##0.0"%";-#,##0.0"%";0;@'),

        "derived": f(font_size=10, font_color=INK, bg_color=FILL_DERIVED,
                     num_format="#,##0.0;-#,##0.0;0;@"),
        "derived_int": f(font_size=10, font_color=INK, bg_color=FILL_DERIVED,
                         num_format="#,##0;-#,##0;0;@"),
        "derived_txt": f(font_size=10, font_color=INK, bg_color=FILL_DERIVED,
                         valign="top", text_wrap=True),
        "flagged": f(font_size=10, font_color=INK, bg_color=FILL_FLAGGED,
                     num_format="#,##0.0;-#,##0.0;0;@"),
        "gap": f(font_size=10, font_color=INK, bg_color=FILL_GAP, valign="top",
                 text_wrap=True),

        "swatch_derived": f(bg_color=FILL_DERIVED, border=1, border_color="#C8C8C8"),
        "swatch_flagged": f(bg_color=FILL_FLAGGED, border=1, border_color="#C8C8C8"),
        "swatch_gap": f(bg_color=FILL_GAP, border=1, border_color="#C8C8C8"),
        "swatch_plain": f(bg_color="#FFFFFF", border=1, border_color="#C8C8C8"),

        "link": f(font_size=10, font_color="#1155CC", underline=1, valign="top"),
    }


def finish(ws, widths, freeze=None, hide_grid=True, landscape=True,
           header_row=None, tab=None):
    """Apply the furniture every sheet gets and the old workbook gave almost none.

    widths: list of (first_col, last_col, width) triples.
    header_row: 0-based row holding the column headings, repeated at the top of
        every printed page. It is passed explicitly rather than assumed to be
        row 0, because most sheets here open with a title and a subtitle and put
        their headings on row 3. 06_SERIES repeated row 0 for exactly that
        reason and printed its sheet title above page 2 instead of its columns.
    """
    for first, last, width in widths:
        ws.set_column(first, last, width)
    if freeze:
        ws.freeze_panes(*freeze)
    if hide_grid:
        ws.hide_gridlines(2)
    if tab:
        ws.set_tab_color(tab)

    # Print setup. Absent from all 22 sheets of the previous workbook, which is
    # why printing it produced confetti.
    if landscape:
        ws.set_landscape()
    else:
        ws.set_portrait()
    ws.set_paper(9)              # A4
    ws.set_margins(0.5, 0.5, 0.6, 0.6)
    ws.fit_to_pages(1, 0)        # one page wide, as many down as it takes
    if header_row is not None:
        ws.repeat_rows(header_row)
    ws.set_footer("&L&A&C&D&R Page &P of &N")


def prose_row_height(cells, minimum=14.0):
    """Height in points for a row of wrapped prose.

    cells: (text, column_width) for every wrapped cell in the row.

    Excel does not re-fit a row whose height the file sets, so a height that is
    too small silently truncates - it does not scroll, and it does not print.
    The previous formula was ``11 * (len(text) // 95 + 1)`` with a fixed 95
    regardless of how wide the column actually was, and it clipped 34 cells on
    07_LIMITATIONS, among them the whole validation column of the AI use log.

    Two corrections. The line count comes from the column's real width, and
    CHARS_PER_UNIT stays deliberately below what Calibri usually fits, so the
    estimate errs long: a row a line too tall costs nothing, a row a line too
    short loses text. PT_PER_LINE is the 10pt line box, not the 11pt guess.
    """
    CHARS_PER_UNIT = 1.0         # conservative; Calibri averages nearer 1.15
    PT_PER_LINE = 13.5
    lines = 1
    for text, width in cells:
        if not text:
            continue
        per_line = max(1.0, width * CHARS_PER_UNIT)
        lines = max(lines, math.ceil(len(text) / per_line))
    return max(minimum, lines * PT_PER_LINE + 2)
