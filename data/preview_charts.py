"""Render the workbook's four charts as PNGs so they can be looked at.

Run:  python3 preview_charts.py

WHY THIS EXISTS
---------------
The previous workbook's charts were, in the project's own words, "verified
structurally and audited in the raw XML, never seen rendered" - and they were
unusable. LibreOffice's Calc filter is broken in this build environment (it
fails to load even a two-cell probe file), so the .xlsx still cannot be rendered
here.

These previews close as much of that gap as can be closed without Excel. They
read the same observations, use the same colours, the same ordering, the same
axis ranges and the same labels as the chart specs in build_workbook.py, so the
geometry and the colour decisions can be checked. They are NOT the Excel charts:
Excel will differ in fonts, in spacing and in exact tick placement. Anything
that depends on those has to be checked by opening the workbook.

WHAT THESE PREVIEWS CANNOT CATCH - demonstrated, not hypothetical
-----------------------------------------------------------------
A preview drawn by a different library cannot catch a defect that lives in how
the workbook drives XlsxWriter, because matplotlib is not asked the same
question. Two got through to Excel and were found by opening it:

  - the scatter was given subtype "markers" instead of "marker_only", so Excel
    joined all 18 countries with straight lines in row order. matplotlib's
    scatter() draws no lines, so the preview looked right.
  - every value axis was left to Excel's autoscale, which put a 57-96% series on
    a 0-120% axis. matplotlib autoscales tightly, so again the preview looked
    right.

Both are now asserted in verify_workbook.py, which reads the .xlsx rather than
redrawing it - that is the check that generalises. These previews are for
judging composition and colour, not for confirming the file is correct.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import style
from build_workbook import (EXCLUSION, PAY_SERIES, PAY_YEARS, flag_of, ols, val)
from dataset import COUNTRIES, cross_section

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "previews")

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.edgecolor": style.GRID,
    "axes.labelcolor": style.AXIS_INK,
    "text.color": style.INK,
    "xtick.color": style.AXIS_INK,
    "ytick.color": style.AXIS_INK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

PCT = FuncFormatter(lambda v, _p: f"{v:g}%")


def frame(ax, *, grid_axis="y"):
    """Recessive grid, no top or right spine. The chrome the old charts lacked
    entirely, rather than the chrome they had too much of."""
    ax.grid(axis=grid_axis, color=style.GRID, linewidth=0.75, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(style.GRID)
    ax.tick_params(length=0)


def title(ax, main, sub):
    ax.set_title(main, fontsize=12, fontweight="bold", color=style.NAVY,
                 loc="left", pad=18)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9,
            color=style.AXIS_INK, va="bottom")


def c1_payments(path):
    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=130)
    width = 0.26
    for i, (code, label, colour) in enumerate(PAY_SERIES):
        xs, ys = [], []
        for j, year in enumerate(PAY_YEARS):
            try:
                v = val(code, year)
            except KeyError:
                continue          # a gap stays a gap; nothing is drawn
            xs.append(j + (i - 1) * width)
            ys.append(v)
        bars = ax.bar(xs, ys, width * 0.92, label=label, color=colour, zorder=3)
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:g}%",
                    ha="center", va="bottom", fontsize=8.5,
                    color=style.AXIS_INK)

    ax.set_xticks(range(len(PAY_YEARS)))
    ax.set_xticklabels([str(y) for y in PAY_YEARS])
    ax.set_xlabel("Year")
    ax.set_ylabel("% of the number of payments")
    ax.set_ylim(0, 80)
    ax.yaxis.set_major_formatter(PCT)
    frame(ax)
    title(ax, "Cash gave up 14 points of retail payments in eight years",
          "Share of the number of physical-retail payments, Denmark")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=3, fontsize=9)
    fig.text(0.01, 0.005, "The mobile wallet was not separately reported in "
                          "2017; the absent column is a gap, not a zero.",
             fontsize=7.5, color=style.MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def c2_exclusion(path):
    rows = sorted(EXCLUSION, key=lambda e: val(e[0], e[1]))
    labels = [f"{lab}\n({year}, {basis})" for _c, year, lab, basis in rows]
    values = [val(c, y) for c, y, _l, _b in rows]
    colours = [style.ACCENT_LIGHT if flag_of(c, y) == "e" else style.ACCENT
               for c, y, _l, _b in rows]

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=130)
    pos = range(len(rows))
    ax.barh(list(pos), values, 0.62, color=colours, zorder=3)
    for i, v in enumerate(values):
        ax.text(v + 0.4, i, f"{v:g}%", va="center", fontsize=8.5,
                color=style.AXIS_INK)

    ax.set_yticks(list(pos))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()              # narrowest at the top, so the ladder reads down
    ax.set_xlabel("% of the stated population base")
    ax.set_xlim(0, 28)
    ax.xaxis.set_major_formatter(PCT)
    frame(ax, grid_axis="x")
    title(ax, "Exclusion is four to five times wider than exemption",
          "Denmark. The lighter bars are estimates, not published counts.")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def c3_eu27(path):
    rows = sorted([(g, val(f"{g}.ECM.IND.BUY", 2024)) for g in COUNTRIES],
                  key=lambda t: -t[1])
    geos = [g for g, _ in rows]
    values = [v for _g, v in rows]
    colours = [style.ACCENT if g == "DK" else style.CONTEXT for g in geos]
    eu = val("EU.ECM.IND.BUY", 2024)

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=130)
    ax.bar(range(len(rows)), values, 0.74, color=colours, zorder=3)
    ax.axhline(eu, color=style.NAVY, linewidth=1.1, linestyle="--", zorder=4)
    ax.text(len(rows) - 0.4, eu + 1.2, f"EU-27 average {eu:.1f}%", ha="right",
            fontsize=8.5, color=style.NAVY)

    # Left-aligned off the bar rather than centred on it: centred, the label
    # ran back across the Netherlands column beside it.
    dk = geos.index("DK")
    ax.text(dk + 0.5, values[dk] + 2.0, f"Denmark {values[dk]:.1f}%",
            ha="left", fontsize=8.5, fontweight="bold", color=style.ACCENT)

    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(geos, fontsize=8)
    ax.set_xlabel("Member state")
    ax.set_ylabel("% of internet users")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(PCT)
    frame(ax)
    title(ax, f"Denmark ranks {dk + 1} of {len(rows)} on online purchasing",
          "Individuals who bought online, % of internet users, 2024")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def c4_adopt_benefit(path):
    paired, _ax_, awaiting_y = cross_section(2024)
    xs = [val(f"{g}.ECM.IND.BUY", 2024) for g in paired]
    ys = [val(f"{g}.ECM.ENT.TRN", 2024) for g in paired]
    slope, intercept, r2 = ols(xs, ys)

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=130)
    for g, x, y in zip(paired, xs, ys):
        is_dk = g == "DK"
        ax.scatter(x, y, s=90 if is_dk else 60,
                   color=style.ACCENT if is_dk else style.CONTEXT,
                   edgecolors="white", linewidths=1.25,
                   zorder=5 if is_dk else 3)
    dk = paired.index("DK")
    ax.annotate("Denmark", (xs[dk], ys[dk]), textcoords="offset points",
                xytext=(9, 5), fontsize=9, fontweight="bold",
                color=style.ACCENT)

    lo, hi = min(xs) - 2, max(xs) + 2
    ax.plot([lo, hi], [intercept + slope * lo, intercept + slope * hi],
            color=style.NAVY, linewidth=1.25, linestyle="--", zorder=2)
    # Same bounds the Excel chart sets, so the two correspond.
    ax.set_xlim(50, 100)
    ax.set_ylim(0, 40)

    ax.set_xlabel("Individuals who bought online (% of internet users)")
    ax.set_ylabel("E-sales (% of enterprise turnover)")
    ax.xaxis.set_major_formatter(PCT)
    ax.yaxis.set_major_formatter(PCT)
    frame(ax, grid_axis="both")
    title(ax, "Adoption explains part of the outcome, not all of it",
          f"EU, 2024. n = {len(paired)}, slope {slope:+.3f}, "
          f"R-squared {r2:.3f}")
    fig.text(0.01, 0.005,
             f"Holding adoption but not the outcome measure, so absent: "
             f"{', '.join(awaiting_y)}.", fontsize=7.5, color=style.MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    jobs = [
        ("C1_F2_PAYMENTS.png", c1_payments),
        ("C2_F4_EXCLUSION.png", c2_exclusion),
        ("C3_F5_EU27.png", c3_eu27),
        ("C4_F6_ADOPT_BENEFIT.png", c4_adopt_benefit),
    ]
    for name, fn in jobs:
        path = os.path.join(OUTDIR, name)
        fn(path)
        print("wrote previews/" + name)


if __name__ == "__main__":
    main()
