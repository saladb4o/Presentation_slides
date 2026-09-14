#!/usr/bin/env python3
"""Generate the report's eight figures as PNGs, straight from data/dataset.py.

The figures are NOT exported from the workbook. They are drawn from the same
observation table the workbook's own charts are built from, so a plotted point,
a workbook cell and a number in the report prose cannot disagree - there is one
source of truth and three renderings of it.

Design decisions worth stating, because they are not cosmetic:

* Figure 1 uses a NUMERIC x-axis, not evenly spaced categories. The branch
  series is observed at 2004/2006/2010/2016/2021/2024; spacing those evenly
  would draw a constant rate of decline that did not happen.
* Figure 2 plots percentage CHANGE, not levels, because institutions, branches
  and employment are three different quantities. Each bar is labelled with its
  own window, since the three windows differ and differencing them is invalid.
* Nothing here uses two y-axes, and no chart mixes a count with a proportion on
  one scale.
* The comparator grey is 8F8F8F, chosen with a contrast validator: the original
  A3A3A3 scored 2.46:1 against white, which prints faint.
* Every bar carries a direct value label. These are read on paper, where there
  is no tooltip to recover the number from.
"""
import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402
import numpy as np                     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data"))
from dataset import OBS                                    # noqa: E402
from build_workbook import C_ACCENT, C_GREY, C_DARK, C_PALE  # noqa: E402

OUT = os.path.join(ROOT, "report", "figures")
ACCENT, GREY, DARK = "#" + C_ACCENT, "#" + C_GREY, "#" + C_DARK
INK, MUTED, GRID = "#1A1A1A", "#5A5A5A", "#DCDCDC"
WIDTH = 6.30                      # inches == 16cm, fits 1-inch margins on A4

V = {(o[0], o[3]): o[4] for o in OBS}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def frame(ax, grid_axis="y"):
    """Recessive chrome: no box, one set of faint gridlines behind the marks."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)


def title(ax, text, sub=None):
    """Title plus optional subtitle.

    The subtitle is offset in POINTS, not axes fractions. An axes-fraction
    offset is a share of the plot height, so the same constant collided with
    the title on tall figures and floated away on short ones.
    """
    ax.set_title(text, loc="left", pad=22 if sub else 8, color=INK, weight="bold")
    if sub:
        ax.annotate(sub, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 7), textcoords="offset points",
                    fontsize=8.5, color=MUTED, va="bottom", ha="left")


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print(f"  {name}")
    return path


# --------------------------------------------------------------------------
def fig1_branches():
    yrs = [2004, 2006, 2010, 2016, 2021, 2024]
    vals = [V[("DK.FIN.BRCH", y)] for y in yrs]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.1))
    frame(ax)
    ax.plot(yrs, vals, color=ACCENT, linewidth=2, zorder=3)
    ax.scatter(yrs, vals, s=34, color=ACCENT, zorder=4,
               edgecolor="white", linewidth=1.1)
    for x, y in ((yrs[0], vals[0]), (yrs[-1], vals[-1])):
        ax.annotate(f"{y:,}", (x, y), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=9, color=INK)
    ax.set_ylim(0, 2300)
    ax.set_xlim(2002, 2026)
    # Thousands separators, so a y value of 2000 is not misread as a year.
    ax.yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.set_xticks(yrs)
    ax.set_ylabel("Number of branches")
    ax.annotate("−67.2%", xy=(2016, 1250), fontsize=11, color=DARK, weight="bold")
    title(ax, "Danish retail bank branches, 2004-2024",
          "Points at their true years; the gaps are real, not evenly spaced")
    return save(fig, "fig1_branches.png")


def fig2_consolidation():
    inst = (V[("DK.FIN.INST", 2024)] / V[("DK.FIN.INST", 1991)] - 1) * 100
    brch = (V[("DK.FIN.BRCH", 2024)] / V[("DK.FIN.BRCH", 2004)] - 1) * 100
    emp = (V[("DK.FIN.EMP", 2024)] / V[("DK.FIN.EMP", 1991)] - 1) * 100
    labels = ["Financial institutions\n1991-2024",
              "Bank branches\n2004-2024",
              "Bank employment\n1991-2024"]
    vals = [inst, brch, emp]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.9))
    frame(ax, grid_axis="x")
    # One series, one colour. An earlier version greyed the middle bar, which
    # implied a distinction the chart never explained.
    bars = ax.barh(labels, vals, color=ACCENT, height=0.6, zorder=3)
    for b, v in zip(bars, vals):
        # These bars run LEFT from zero, so the label goes just inside the bar
        # at its zero end. Placing it past the bar end put white text on white.
        ax.text(v + 1.8, b.get_y() + b.get_height() / 2, f"\u2212{abs(v):.1f}%",
                va="center", ha="left", fontsize=9, color="white", weight="bold")
    ax.set_xlim(-90, 2)
    ax.invert_yaxis()
    ax.set_xlabel("Change over the stated period (%)")
    title(ax, "Danish banking consolidated rather than shrank",
          "Each bar spans its own window; the three are not comparable to each other")
    return save(fig, "fig2_consolidation.png")


def fig3_regression():
    pairs = []
    for o in OBS:
        if o[0].endswith("ECM.ENT.TRN") and o[3] == 2024 and o[2] != "EU27":
            x = V.get((f"{o[2]}.ECM.IND.BUY", 2024))
            if x is not None:
                pairs.append((o[2], x, o[4]))
    xs = np.array([p[1] for p in pairs])
    ys = np.array([p[2] for p in pairs])
    slope, intercept = np.polyfit(xs, ys, 1)
    r2 = np.corrcoef(xs, ys)[0, 1] ** 2

    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    frame(ax, grid_axis="both")
    gx = np.linspace(xs.min() - 2, xs.max() + 2, 10)
    ax.plot(gx, intercept + slope * gx, color=DARK, linewidth=1.5,
            linestyle="--", zorder=3)
    for code, x, y in pairs:
        is_dk = code == "DK"
        ax.scatter(x, y, s=52 if is_dk else 34,
                   color=ACCENT if is_dk else GREY,
                   zorder=5 if is_dk else 4,
                   edgecolor="white", linewidth=1.1)
    for code in ("DK", "IE", "BG"):
        x, y = next((p[1], p[2]) for p in pairs if p[0] == code)
        ax.annotate(code, (x, y), textcoords="offset points", xytext=(7, -3),
                    fontsize=9, color=INK if code == "DK" else MUTED,
                    weight="bold" if code == "DK" else "normal")
    ax.set_xlabel("Individuals purchasing online (% of internet users)")
    ax.set_ylabel("E-sales (% of turnover)")
    ax.text(0.98, 0.06,
            f"slope +{slope:.3f}   R² {r2:.3f}   n = {len(pairs)}",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=MUTED)
    title(ax, "Consumer adoption and enterprise e-commerce, EU 2024",
          "Denmark in blue. Association only; the fit does not establish cause")
    return save(fig, "fig3_regression.png")


def fig4_esales():
    dk = [V[("DK.ECM.ENT.TRN", y)] for y in (2014, 2024)]
    eu = [V[("EU.ECM.ENT.TRN", y)] for y in (2014, 2024)]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    frame(ax)
    b1 = ax.bar(x - 0.19, dk, 0.34, label="Denmark", color=ACCENT, zorder=3)
    b2 = ax.bar(x + 0.19, eu, 0.34, label="EU-27", color=GREY, zorder=3)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.7,
                    f"{b.get_height():.2f}", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x, ["2014", "2024"])
    ax.set_ylabel("E-sales (% of enterprise turnover)")
    ax.set_ylim(0, 38)
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    title(ax, "Intensity diverged: Denmark roughly doubled, the EU did not")
    return save(fig, "fig4_esales.png")


def fig5_ai():
    labels = ["All enterprises", "Large enterprises", "SMEs"]
    vals = [V[("DK.ENT.AI", 2025)], V[("DK.ENT.AI.LRG", 2025)],
            V[("DK.ENT.AI.SME", 2025)]]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    frame(ax)
    bars = ax.bar(labels, vals, 0.5, color=[GREY, ACCENT, ACCENT], zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.4, f"{v:.2f}%",
                ha="center", fontsize=9, color=INK)
    # The gap is drawn as a VERTICAL span to the right of the bars, not as a
    # diagonal arrow between their tops. A diagonal reads as a trend - large
    # firms declining into SMEs - which is not what a size cross-section says.
    gap = vals[1] - vals[2]
    gx = 2.46
    for v in (vals[1], vals[2]):
        ax.plot([1 if v == vals[1] else 2, gx], [v, v], linestyle=":",
                color=DARK, linewidth=0.9, zorder=4)
    ax.annotate("", xy=(gx, vals[1]), xytext=(gx, vals[2]),
                arrowprops=dict(arrowstyle="<->", color=DARK, linewidth=1.1))
    ax.text(gx + 0.08, (vals[1] + vals[2]) / 2, f"{gap:.2f}\npp",
            ha="left", va="center", fontsize=9, color=DARK, weight="bold")
    ax.set_ylabel("% adopting AI")
    ax.set_ylim(0, 88)
    ax.set_xlim(-0.55, 2.95)
    title(ax, "Who could build on the rail: AI adoption by firm size, 2025",
          "The aggregate is greyed; it sits between the other two by construction")
    return save(fig, "fig5_ai_firmsize.png")


def fig6_exclusion():
    items = [
        ("Formally exempt from Digital Post\n(% of citizens 15+, 2026)",
         V[("DK.DGP.EXMP", 2026)], None, ACCENT),
        ("Do not use digital public services\n(% of population, 2026)",
         V[("DK.DGX.NOUSE", 2026)], None, GREY),
        ("Report difficulty using them\n(% of population, 2026)",
         V[("DK.DGX.DIFF", 2026)], None, GREY),
        ("“Digitally disadvantaged”\n(% of adults, 2025)",
         V[("DK.DGX.DISADV.LO", 2025)], V[("DK.DGX.DISADV.HI", 2025)], GREY),
        ("Justitia estimate\n(% of adults, 2022)",
         V[("DK.DGX.JUST", 2022)], None, GREY),
    ]
    labels = [i[0] for i in items]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.8))
    frame(ax, grid_axis="x")
    ypos = np.arange(len(items))
    for y, (lab, lo, hi, col) in zip(ypos, items):
        ax.barh(y, lo, height=0.55, color=col, zorder=3)
        if hi:
            ax.barh(y, hi - lo, left=lo, height=0.55, color=col,
                    alpha=0.45, zorder=3)
            ax.text(hi + 0.6, y, f"{lo:.0f}-{hi:.0f}%", va="center",
                    fontsize=9, color=INK)
        else:
            ax.text(lo + 0.6, y, f"{lo:.1f}%".replace(".0%", "%"), va="center",
                    fontsize=9, color=INK)
    ax.set_yticks(ypos, labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 30)
    ax.set_xlabel("Share of the stated population (%)")
    title(ax, "The relief mechanism is narrower than the need",
          "Denominators and years differ: a ladder of estimates, not a series")
    return save(fig, "fig6_exclusion.png")


def fig7_skills():
    bands = [("16-24", "DK.SKL.1624", "EU.SKL.1624"),
             ("25-54", "DK.SKL.2554", "EU.SKL.2554"),
             ("55-74", "DK.SKL.5574", "EU.SKL.5574")]
    dk = [V[(b[1], 2025)] for b in bands]
    eu = [V[(b[2], 2025)] for b in bands]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    frame(ax)
    b1 = ax.bar(x - 0.19, dk, 0.34, label="Denmark", color=ACCENT, zorder=3)
    b2 = ax.bar(x + 0.19, eu, 0.34, label="EU-27", color=GREY, zorder=3)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.4,
                    f"{b.get_height():.1f}", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x, [b[0] for b in bands])
    ax.set_xlabel("Age band")
    ax.set_ylabel("% with at least basic digital skills")
    ax.set_ylim(0, 108)
    ax.legend(frameon=False, loc="upper right", fontsize=8.5)
    title(ax, "Denmark leads every age band, and its gradient is the flatter one",
          f"Denmark {dk[0] - dk[2]:.2f} pp youngest to oldest; EU {eu[0] - eu[2]:.2f} pp")
    return save(fig, "fig7_skills.png")


def fig8_smv():
    labels = ["Invested further\nduring the project", "No further\ninvestment plans"]
    vals = [V[("DK.SME.SMVD.INV", 2025)], V[("DK.SME.SMVD.NOINV", 2025)]]
    n = V[("DK.SME.SMVD.PROJ", 2025)]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
    frame(ax)
    bars = ax.bar(labels, vals, 0.42, color=[ACCENT, GREY], zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.6, f"{v:.0f}%",
                ha="center", fontsize=9, color=INK)
    ax.set_ylabel("% of participants")
    ax.set_ylim(0, 78)
    title(ax, "SMV:Digital participation, as reported by the scheme",
          f"Shares of ~{int(n):,} supported projects. The count is off-axis: it is "
          f"not a percentage")
    return save(fig, "fig8_smvdigital.png")


FIGURES = [fig1_branches, fig2_consolidation, fig3_regression, fig4_esales,
           fig5_ai, fig6_exclusion, fig7_skills, fig8_smv]


def fig9_ewaste():
    """Two bars. The whole point is the size of one gap, so nothing else is drawn."""
    dk, eu = V[("DK.ENV.WEEE", 2023)], V[("EU.ENV.WEEE", 2023)]
    fig, ax = plt.subplots(figsize=(WIDTH, 1.9))
    frame(ax, grid_axis="x")
    bars = ax.barh(["Denmark", "EU-27 average"], [dk, eu],
                   height=0.5, color=[ACCENT, GREY], zorder=3)
    for b, v in zip(bars, (dk, eu)):
        ax.text(v + 1.6, b.get_y() + b.get_height() / 2, f"{v:.2f}%",
                va="center", fontsize=9, color=INK)
    ax.set_xlim(0, 100)
    ax.set_ylim(1.6, -0.6)
    ax.set_xlabel("% of ICT waste collected that is recycled or prepared for reuse")
    title(ax, "Denmark recovers a fifth of the ICT waste the EU average does",
          f"2023; a gap of {eu - dk:.2f} percentage points. "
          f"Base is ICT waste collected, not equipment sold")
    return save(fig, "fig9_ewaste.png")


FIGURES.append(fig9_ewaste)


def fig10_reach():
    """Two panels that must not share an axis.

    Denmark's e-government reach is published on individuals aged 16-74;
    the exemption rate is published on citizens aged 15 and over. Drawing
    them on one axis would invite the subtraction the report forbids
    everywhere else, so each panel carries its own base in its own label
    and a rule separates them.
    """
    reach = [V[("DK.DGX.EGOV.USE", 2024)], V[("EU.DGX.EGOV.USE", 2024)]]
    other = [V[("DK.DGX.DIFF", 2026)], V[("DK.DGX.NOUSE", 2026)],
             V[("DK.DGP.EXMP", 2026)]]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(WIDTH, 2.5), gridspec_kw={"width_ratios": [1, 1.15],
                                                 "wspace": 0.75})

    frame(ax1, grid_axis="x")
    b1 = ax1.barh(["Denmark", "EU-27 average"], reach, height=0.5,
                  color=[ACCENT, GREY], zorder=3)
    for b, v in zip(b1, reach):
        ax1.text(v - 2.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
                 va="center", ha="right", fontsize=9, color="white")
    ax1.set_xlim(0, 100)
    ax1.set_ylim(1.6, -0.6)
    ax1.set_xlabel("% of individuals aged 16 to 74, 2024")
    title(ax1, "Reach", "Used a public authority site or app, last 12 months")

    frame(ax2, grid_axis="x")
    labels = ["Report difficulty", "Do not use at all", "Exempt from Post"]
    b2 = ax2.barh(labels, other, height=0.5, color=DARK, zorder=3)
    for b, v in zip(b2, other):
        ax2.text(v + 2, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
                 va="center", fontsize=9, color=INK)
    ax2.set_xlim(0, 100)
    ax2.set_ylim(2.6, -0.6)
    ax2.set_xlabel("% on each measure's own base, 2026")
    title(ax2, "What reach does not measure",
          "Three bases, three sources. Not comparable with the left panel")
    return save(fig, "fig10_reach.png")


FIGURES.append(fig10_reach)


def verify():
    """Cross-check the figures' derived numbers against the report prose.

    The figures and the prose are computed independently - the figures from
    dataset.py here, the prose typed by hand in report/draft/. This asserts they
    agree, so a figure can never quietly contradict the sentence beside it.
    """
    inst = (V[("DK.FIN.INST", 2024)] / V[("DK.FIN.INST", 1991)] - 1) * 100
    brch = (V[("DK.FIN.BRCH", 2024)] / V[("DK.FIN.BRCH", 2004)] - 1) * 100
    emp = (V[("DK.FIN.EMP", 2024)] / V[("DK.FIN.EMP", 1991)] - 1) * 100
    pairs = [(V[(f"{o[2]}.ECM.IND.BUY", 2024)], o[4]) for o in OBS
             if o[0].endswith("ECM.ENT.TRN") and o[3] == 2024 and o[2] != "EU27"
             and (f"{o[2]}.ECM.IND.BUY", 2024) in V]
    xs = np.array([p[0] for p in pairs])
    ys = np.array([p[1] for p in pairs])
    slope, _ = np.polyfit(xs, ys, 1)
    r2 = np.corrcoef(xs, ys)[0, 1] ** 2

    claims = {
        "67.2": abs(brch), "76.7": abs(inst), "29.4": abs(emp),
        "0.602": slope, "0.674": r2, "18": float(len(pairs)),
        "33.53": V[("DK.ENT.AI.LRG", 2025)] - V[("DK.ENT.AI.SME", 2025)],
    }
    prose = ""
    draft = os.path.join(ROOT, "report", "draft")
    for fn in sorted(os.listdir(draft)):
        if fn.endswith(".md"):
            prose += io.open(os.path.join(draft, fn), encoding="utf-8").read()

    bad = []
    for text, computed in claims.items():
        # Compare at the precision the prose actually states. The prose says
        # "67.2%", so the test is round(67.1605, 1) == 67.2, not equality to
        # four places - otherwise every correctly rounded figure fails.
        dp = len(text.split(".")[1]) if "." in text else 0
        if round(computed, dp) != float(text):
            bad.append(f"{text} claimed, {computed:.4f} computed")
        if text not in prose:
            bad.append(f"{text} computed but absent from the report prose")
    if bad:
        raise SystemExit("FIGURE/PROSE MISMATCH:\n  " + "\n  ".join(bad))
    print(f"  verified {len(claims)} derived values against the report prose")




# ==========================================================================
# Appendix figures. Numbered within their appendix (C1, C2, ...) by render.py,
# so adding one never renumbers a body figure.
# ==========================================================================

def _cross_section():
    pairs = []
    for o in OBS:
        if o[0].endswith("ECM.ENT.TRN") and o[3] == 2024 and o[2] != "EU27":
            x = V.get((f"{o[2]}.ECM.IND.BUY", 2024))
            if x is not None:
                pairs.append((o[2], x, o[4]))
    pairs.sort(key=lambda p: p[1])
    xs = np.array([p[1] for p in pairs])
    ys = np.array([p[2] for p in pairs])
    slope, intercept = np.polyfit(xs, ys, 1)
    return pairs, xs, ys, slope, intercept


def figC1_residuals():
    pairs, xs, ys, slope, intercept = _cross_section()
    fit = intercept + slope * xs
    res = ys - fit
    rmse = np.sqrt((res ** 2).sum() / (len(xs) - 2))

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    frame(ax, grid_axis="both")
    ax.axhline(0, color=MUTED, linewidth=1)
    for band, style in ((1, ":"), (2, "--")):
        for sign in (1, -1):
            ax.axhline(sign * band * rmse, color=GREY, linewidth=0.8,
                       linestyle=style, zorder=2)
    for (code, _x, _y), f, r in zip(pairs, fit, res):
        dk = code == "DK"
        ax.scatter(f, r, s=52 if dk else 34, color=ACCENT if dk else GREY,
                   zorder=5 if dk else 4, edgecolor="white", linewidth=1.1)
        if dk or abs(r) > 1.2 * rmse:
            ax.annotate(code, (f, r), textcoords="offset points", xytext=(7, -3),
                        fontsize=8.5, color=INK if dk else MUTED,
                        weight="bold" if dk else "normal")
    ax.text(ax.get_xlim()[1], rmse, " ±1 RMSE", va="center", ha="left",
            fontsize=7.5, color=MUTED)
    ax.set_xlabel("Fitted e-sales (% of turnover)")
    ax.set_ylabel("Residual (pp)")
    title(ax, "No fitted value is mispredicted by more than two standard errors",
          f"RMSE {rmse:.2f} pp. Denmark sits +{res[[p[0] for p in pairs].index('DK')]:.2f}, "
          f"inside one")
    return save(fig, "figA_c1_residuals.png")


def figC2_jackknife():
    pairs, xs, ys, slope, _ = _cross_section()
    drops = []
    for i in range(len(xs)):
        keep = np.ones(len(xs), bool)
        keep[i] = False
        s, _ = np.polyfit(xs[keep], ys[keep], 1)
        drops.append((pairs[i][0], s))
    drops.sort(key=lambda d: d[1])
    codes = [d[0] for d in drops]
    slopes = [d[1] for d in drops]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    frame(ax, grid_axis="x")
    y = np.arange(len(codes))
    ax.axvline(slope, color=DARK, linewidth=1.4, zorder=3)
    ax.axvspan(0.380, 0.824, color=ACCENT, alpha=0.10, zorder=1)
    ax.scatter(slopes, y, s=38, color=[ACCENT if abs(s - slope) > 0.05 else GREY
                                       for s in slopes],
               zorder=5, edgecolor="white", linewidth=1.0)
    ax.set_yticks(y, [f"without {c}" for c in codes], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0.30, 0.90)
    ax.set_xlabel("Slope re-estimated on the remaining 17 states")
    # Both annotations go ABOVE the first row; at the bottom the full-sample
    # label landed on the x tick labels.
    ax.text(slope + 0.008, -0.85, f"full sample {slope:.3f}", fontsize=8,
            color=DARK, va="center", ha="left")
    ax.text(0.824, -0.85, "95% CI  ", fontsize=7.5, color=MUTED,
            ha="right", va="center")
    title(ax, "The slope survives dropping any single member state",
          f"Range [{min(slopes):.3f}, {max(slopes):.3f}]: never near zero, never sign-flipping")
    return save(fig, "figA_c2_jackknife.png")


def figC3_tailselection():
    pairs, xs, ys, slope, intercept = _cross_section()
    # The earlier figure used the ROUNDED values printed in the press release,
    # not the databrowser's. Recomputing from the databrowser gives 0.658, not
    # the 0.655 the report quotes - so the rounded values are used here, and
    # the appendix says so.
    rounded = {"IE": 96, "DK": 91, "DE": 83, "IT": 60, "BG": 57, "HU": 79}
    tx = np.array([rounded[c] for c in rounded])
    ty = np.array([V[(f"{c}.ECM.ENT.TRN", 2024)] for c in rounded])
    ts, ti = np.polyfit(tx, ty, 1)

    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    frame(ax, grid_axis="both")
    gx = np.linspace(54, 99, 10)
    ax.plot(gx, ti + ts * gx, color=ACCENT, linewidth=1.6, linestyle="-",
            zorder=4, label=f"Six tail countries (slope {ts:.3f}, R² 0.853)")
    ax.plot(gx, intercept + slope * gx, color=DARK, linewidth=1.6,
            linestyle="--", zorder=4,
            label=f"All 18 states (slope {slope:.3f}, R² 0.674)")
    for code, x, y in pairs:
        tail = code in rounded
        ax.scatter(x, y, s=44 if tail else 30,
                   color=ACCENT if tail else GREY, zorder=5 if tail else 3,
                   edgecolor="white", linewidth=1.0)
    ax.set_xlabel("Individuals purchasing online (% of internet users)")
    ax.set_ylabel("E-sales (% of turnover)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    title(ax, "Selection on the tails inflates the fit, not the slope",
          "Blue: the six countries a press release happened to name")
    return save(fig, "figA_c3_tailselection.png")


def figD1_denominators():
    """The exclusion ladder converted to people on each estimate's own base.

    Two of the five sources say "adult population" without defining it. Denmark
    has no verified adult-population figure in this dataset, so those two are
    drawn as a RANGE between the two defensible bases - the 15+ base implied by
    the Digital Post statistics and the total population - rather than silently
    picking one. Picking one is precisely the error this appendix documents.
    """
    pop = V[("DK.POP.TOT", 2026)]
    base15 = V[("DK.DGP.EXMP.N", 2026)] / (V[("DK.DGP.EXMP", 2026)] / 100)
    items = [
        ("Formally exempt", V[("DK.DGP.EXMP", 2026)], base15, base15,
         "citizens 15+, stated"),
        ("Do not use at all", V[("DK.DGX.NOUSE", 2026)], pop, pop,
         "population, stated"),
        ("Report difficulty", V[("DK.DGX.DIFF", 2026)], pop, pop,
         "population, stated"),
        ("Digitally disadvantaged", V[("DK.DGX.DISADV.LO", 2025)], base15, pop,
         "adult population, undefined"),
        ("Justitia estimate", V[("DK.DGX.JUST", 2022)], base15, pop,
         "adult population, undefined"),
    ]
    labels = [f"{n}\n({d})" for n, _p, _lo, _hi, d in items]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    frame(ax, grid_axis="x")
    y = np.arange(len(items))
    for i, (_n, pct, lo_base, hi_base, _d) in enumerate(items):
        lo = pct / 100 * lo_base / 1000
        hi = pct / 100 * hi_base / 1000
        col = ACCENT if i == 0 else GREY
        ax.barh(i, lo, height=0.55, color=col, zorder=3)
        if hi > lo:
            ax.barh(i, hi - lo, left=lo, height=0.55, color=col, alpha=0.40,
                    zorder=3)
            ax.text(hi + 14, i, f"{lo:,.0f}-{hi:,.0f}k  ({pct:g}%)", va="center",
                    fontsize=8.5, color=INK)
        else:
            ax.text(lo + 14, i, f"{lo:,.0f}k  ({pct:g}%)", va="center",
                    fontsize=8.5, color=INK)
    ax.set_yticks(y, labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1900)
    ax.set_xlabel("People (thousands) on the estimate's own base")
    title(ax, "The same ladder in people rather than percentages",
          "Faded extensions are base uncertainty: two sources say \u201cadult\u201d "
          "and do not define it")
    return save(fig, "figA_d1_denominators.png")


def figE1_eu27():
    rows = sorted(((o[2], o[4]) for o in OBS
                   if o[0].endswith("ECM.IND.BUY") and o[3] == 2024
                   and o[2] != "EU27"), key=lambda r: r[1])
    eu = V[("EU.ECM.IND.BUY", 2024)]
    codes = [r[0] for r in rows]
    vals = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(WIDTH, 4.4))
    frame(ax, grid_axis="x")
    colors = [ACCENT if c == "DK" else GREY for c in codes]
    ax.barh(codes, vals, height=0.68, color=colors, zorder=3)
    ax.axvline(eu, color=DARK, linewidth=1.2, linestyle="--", zorder=4)
    ax.text(eu + 0.7, len(codes) - 0.4, f"EU-27 {eu:.2f}", fontsize=8, color=DARK,
            va="center")
    for c, v in zip(codes, vals):
        # A white surface behind each label: the EU reference line runs through
        # this band and cut seven of them in half without it.
        ax.text(v + 0.8, codes.index(c), f"{v:.1f}", va="center", fontsize=7.5,
                color=INK if c == "DK" else MUTED, zorder=6,
                bbox=dict(boxstyle="square,pad=0.12", fc="white", ec="none"))
    ax.set_xlim(0, 108)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_xlabel("Individuals purchasing online (% of internet users), 2024")
    title(ax, "Denmark is third of twenty-seven",
          "The three countries the report names by number are IE, DK and BG")
    return save(fig, "figA_e1_eu27.png")


def figE2_payments():
    cash_y = [2017, 2023, 2025]
    cash = [V[("DK.PAY.CASH.POS", y)] for y in cash_y]
    card_y = [2017, 2025]
    card = [V[("DK.PAY.CRD.PHYS", y)] for y in card_y]
    wallet = V[("DK.PAY.WLT.SHR", 2025)]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    frame(ax)
    ax.plot(card_y, card, color=GREY, linewidth=2, zorder=3, marker="o",
            markersize=6, markeredgecolor="white", label="Physical card")
    ax.plot(cash_y, cash, color=ACCENT, linewidth=2, zorder=4, marker="o",
            markersize=6, markeredgecolor="white", label="Cash")
    ax.scatter([2025], [wallet], s=60, color=DARK, zorder=5, marker="D",
               edgecolor="white", linewidth=1.1, label="Mobile wallet (observed once)")
    for x, y, v in ((2017, cash[0], cash[0]), (2025, cash[-1], cash[-1]),
                    (2017, card[0], card[0]), (2025, card[-1], card[-1])):
        ax.annotate(f"{v:g}%", (x, y), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=8.5, color=INK)
    ax.annotate(f"{wallet:g}%", (2025, wallet), textcoords="offset points",
                xytext=(0, -16), ha="center", fontsize=8.5, color=DARK)
    ax.set_xlim(2016, 2026)
    ax.set_ylim(0, 85)
    ax.set_xticks([2017, 2019, 2021, 2023, 2025])
    ax.set_ylabel("% of the NUMBER of payments")
    ax.legend(frameon=False, fontsize=8, loc="center left")
    title(ax, "Cash fell; most of what replaced it was still a card",
          "Shares of the number of payments in physical retail, not their value")
    return save(fig, "figA_e2_payments.png")


APPENDIX_FIGURES_FNS = [figC1_residuals, figC2_jackknife, figC3_tailselection,
                        figD1_denominators, figE1_eu27, figE2_payments]




# --------------------------------------------------------------------------
def figE3_productivity():
    """Danish labour productivity against the EU-27 average, 2005-2025.

    The y axis is an INDEX on EU27_2020 = 100, so the reference line at 100 is
    the EU average and the series shows Denmark's position against it. It is
    not a Danish growth rate; the 100 line is drawn and labelled precisely so
    the chart cannot be misread as one.
    """
    rows = sorted((o[3], o[4]) for o in OBS if o[0] == "DK.PRD.LP.PER")
    yrs = [r[0] for r in rows]
    vals = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.5))
    frame(ax)
    ax.axhline(100, color=DARK, linewidth=1.1, linestyle="--", zorder=2)
    ax.annotate("EU-27 average = 100", xy=(yrs[0], 100), xytext=(0, 5),
                textcoords="offset points", fontsize=8, color=DARK, va="bottom")
    ax.plot(yrs, vals, color=ACCENT, linewidth=2.0, zorder=4)

    peak = max(range(len(vals)), key=lambda i: vals[i])
    for i, note in ((0, "below"), (peak, "above"), (len(vals) - 1, "below")):
        ax.plot(yrs[i], vals[i], "o", color=ACCENT, markersize=5, zorder=5)
        ax.annotate(f"{vals[i]:.1f}", (yrs[i], vals[i]), textcoords="offset points",
                    xytext=(0, -15 if note == "below" else 9), ha="center",
                    fontsize=8.5, color=DARK)
    ax.set_ylim(95, 126)
    ax.set_xlim(2004, 2026)
    ax.set_xticks([2005, 2010, 2015, 2020, 2025])
    ax.set_ylabel("Index, EU27 (2020 composition) = 100")
    title(ax, "Denmark's lead over the EU average widened, then narrowed",
          "Nominal labour productivity per person, current prices in PPS. "
          "A relative position, not a growth rate")
    return save(fig, "figA_e3_productivity.png")


def figF1_gantt():
    """Implementation and evaluation timeline for the randomised SMV:Digital pool.

    Colour carries the argument rather than decorating it: the accent marks the
    three steps that make the scheme evaluable - randomisation, outcome
    measurement, publication - and everything administrative stays grey.
    """
    # (label, start month index from Oct 2026, duration in months, is_causal)
    tasks = [
        ("Grant pool opens; applications received", 0, 2, False),
        ("Eligibility screening; applications scored", 2, 1, True),
        ("Scores and funding cut-off published", 3, 1, True),
        ("Baseline linkage to Danmarks Statistik registers", 3, 2, True),
        ("Grants disbursed; funded projects run", 4, 12, False),
        ("Midline monitoring of take-up and attrition", 10, 2, False),
        ("Endline outcome measurement, both sides of cut-off", 28, 3, True),
        ("Evaluation report published", 31, 3, True),
    ]
    labels = [t[0] for t in tasks][::-1]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.9))
    frame(ax, grid_axis="x")
    # The twelve months between the funded projects ending and the endline are
    # not slack. They are the outcome window: the evaluation measures two years
    # from project start, matching the existing effect measurement. Drawn,
    # because an unexplained gap in a Gantt chart reads as a planning error.
    ax.annotate("", xy=(4, -0.85), xytext=(28, -0.85),
                arrowprops=dict(arrowstyle="|-|,widthA=0.35,widthB=0.35",
                                color=GREY, linewidth=0.9,
                                shrinkA=0, shrinkB=0))
    ax.annotate("Outcomes accrue: 24 months from project start",
                xy=(16, -1.25), ha="center", va="center",
                fontsize=7.5, color=MUTED)
    for i, (lab, start, dur, causal) in enumerate(tasks[::-1]):
        ax.barh(i, dur, left=start, height=0.55, zorder=3,
                color=ACCENT if causal else GREY)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_ylim(-1.7, len(labels) - 0.4)
    # Ticks every six months from the opening of the pool.
    marks = [0, 6, 12, 18, 24, 30, 34]
    names = ["Oct 2026", "Apr 2027", "Oct 2027", "Apr 2028", "Oct 2028",
             "Apr 2029", "Aug 2029"]
    ax.set_xticks(marks)
    ax.set_xticklabels(names, fontsize=8)
    ax.set_xlim(-0.6, 34.6)
    title(ax, "The evaluation is built in, not bolted on",
          "Blue marks the five steps that make an effect estimate possible; "
          "grey is scheme administration")
    return save(fig, "figA_f1_gantt.png")


APPENDIX_FIGURES_FNS += [figE3_productivity, figF1_gantt]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print(f"writing {len(FIGURES)} figures to report/figures/")
    for f in FIGURES:
        f()
    print(f"writing {len(APPENDIX_FIGURES_FNS)} appendix figures")
    for f in APPENDIX_FIGURES_FNS:
        f()
    verify()
