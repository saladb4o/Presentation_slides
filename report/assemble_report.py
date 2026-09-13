#!/usr/bin/env python3
"""Assemble report/DRAFT_REPORT.md from the per-section drafts.

The report is never hand-edited as a whole: sections live in report/draft/ and
this script stitches them together with Table 1, the figure captions and the
reference list, both generated from data/ so they cannot drift from the workbook.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from sources import SOURCES, REFERENCE_ONLY          # noqa: E402
from dataset import POLICY_EVENTS                    # noqa: E402

DRAFT = ROOT / "report" / "draft"


def body(name, stop=None):
    t = (DRAFT / f"{name}.md").read_text().rstrip()
    return t.split(stop)[0].rstrip() if stop else t


CAPTIONS = {
    1: "*Figure 1 — Danish retail bank branches, 2004–2024. Finans Danmark. Workbook F1_BRANCHES.*",
    3: "*Figure 3 — E-sales share of enterprise turnover, Denmark and EU-27, 2014 and 2024. Eurostat. Workbook F3.*",
    4: "*Figure 4 — Five estimates of Danish digital exclusion, narrowest to widest. Workbook F4.*",
    6: "*Figure 6 — Consumer adoption and enterprise e-commerce turnover, EU 2024. Eurostat isoc_ec_ib20, tin00110. Workbook F6.*",
    7: "*Figure 7 — AI adoption by firm size, Denmark 2025. European Commission, Digital Decade. Workbook F7.*",
    8: "*Figure 8 — SMV:Digital participation, self-reported and without a control group. Workbook F8.*",
    9: "*Figure 9 — Danish banking consolidation: institutions, branches, employment. Differing base years. Finans Danmark. Workbook F9.*",
    10: "*Figure 10 — Basic digital skills by age band, Denmark and EU-27, 2025. European Commission. Workbook F10.*",
}

PRECISION = {"day": 10, "month": 7, "year": 4}
table1 = "\n".join(
    ["| Date | Event | Instrument |", "|---|---|---|"]
    + [f"| {date[:PRECISION[prec]]} | {title} | {instr} |"
       for date, prec, title, instr, _sid, _note, _series in POLICY_EVENTS]
)

references = "\n\n".join(sorted(
    v["harvard"] for k, v in SOURCES.items() if k not in REFERENCE_ONLY
))

doc = f"""# Digital Policy and Innovation Report — Denmark

**ECON1596/ECON1597 Assessment 2** · s4040040 · Class group: [TO BE CONFIRMED]
Submitted 17 September 2026 · Accompanying data file:
`ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx`

> **Thesis.** Denmark's digital transition is close to complete in breadth and
> incomplete in depth, and the instrument that delivered the breadth — legal
> compulsion — is the reason the depth is missing.

---

{body('S1_context')}

**Table 1 — Danish digital-policy instruments and dates.** Workbook sheet 09_POLICY.

{table1}

---

{body('S2_adoption_effect', chr(10) + '---' + chr(10))}

{CAPTIONS[1]}

{CAPTIONS[6]}

{CAPTIONS[9]}

---

{body('S3_eu_diffusion')}

{CAPTIONS[3]}

{CAPTIONS[7]}

---

{body('S4_left_behind')}

{CAPTIONS[4]}

{CAPTIONS[10]}

---

## 5. [Guest lecture question]

> **NOT DRAFTED — blocked pending the guest lecture content.** 280 words are
> reserved in the word budget. `report/draft/S5_guest_lecture_STUB.md` maps the
> evidence already held against each likely question theme.

---

{body('S6_recommendation')}

{CAPTIONS[8]}

---

## References

{references}
"""

(ROOT / "report" / "DRAFT_REPORT.md").write_text(doc)
print(f"wrote report/DRAFT_REPORT.md ({len(doc.split())} words incl. front matter, "
      f"Table 1 and references)")
