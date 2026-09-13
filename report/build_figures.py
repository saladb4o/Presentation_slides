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
from build_workbook import C_ACCENT, C_GREY, C_DARK        # noqa: E402

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
    title(ax, "Danish retail bank branches, 2004–2024",
          "Points at their true years; the gaps are real, not evenly spaced")
    return save(fig, "fig1_branches.png")


def fig2_consolidation():
    inst = (V[("DK.FIN.INST", 2024)] / V[("DK.FIN.INST", 1991)] - 1) * 100
    brch = (V[("DK.FIN.BRCH", 2024)] / V[("DK.FIN.BRCH", 2004)] - 1) * 100
    emp = (V[("DK.FIN.EMP", 2024)] / V[("DK.FIN.EMP", 1991)] - 1) * 100
    labels = ["Financial institutions\n1991–2024",
              "Bank branches\n2004–2024",
              "Bank employment\n1991–2024"]
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
          "Each bar spans its own window — the three are not comparable to each other")
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
          "Denmark in blue. Association only — the fit does not establish cause")
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
          "The aggregate is greyed — it sits between the other two by construction")
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
            ax.text(hi + 0.6, y, f"{lo:.0f}–{hi:.0f}%", va="center",
                    fontsize=9, color=INK)
        else:
            ax.text(lo + 0.6, y, f"{lo:.1f}%".replace(".0%", "%"), va="center",
                    fontsize=9, color=INK)
    ax.set_yticks(ypos, labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 30)
    ax.set_xlabel("Share of the stated population (%)")
    title(ax, "The relief mechanism is narrower than the need",
          "Denominators and years differ — a ladder of estimates, not a series")
    return save(fig, "fig6_exclusion.png")


def fig7_skills():
    bands = [("16–24", "DK.SKL.1624", "EU.SKL.1624"),
             ("25–54", "DK.SKL.2554", "EU.SKL.2554"),
             ("55–74", "DK.SKL.5574", "EU.SKL.5574")]
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
    title(ax, "SMV:Digital participation — self-reported, no control group",
          f"Shares of ~{int(n):,} supported projects. The count is off-axis: it is "
          f"not a percentage")
    return save(fig, "fig8_smvdigital.png")


FIGURES = [fig1_branches, fig2_consolidation, fig3_regression, fig4_esales,
           fig5_ai, fig6_exclusion, fig7_skills, fig8_smv]


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
        "24.25": V[("DK.SKL.1624", 2025)] - V[("DK.SKL.5574", 2025)],
        "31.95": V[("EU.SKL.1624", 2025)] - V[("EU.SKL.5574", 2025)],
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


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print(f"writing {len(FIGURES)} figures to report/figures/")
    for f in FIGURES:
        f()
    verify()
