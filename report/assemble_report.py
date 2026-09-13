#!/usr/bin/env python3
"""Assemble report/DRAFT_REPORT.md from the per-section drafts.

The report is never hand-edited as a whole. Sections live in report/draft/ and
carry TOKENS rather than typed citations or figure numbers:

    [[RR1]]     -> "(Rigsrevisionen 2016)"      full author-date citation
    [[RR1:y]]   -> "(2016)"                     year only, for narrative citation
    [[RR1:b]]   -> "Rigsrevisionen 2016"        bare, for use inside existing parens
    [[F6]]      -> "Figure 3"                   report figure number

Both are resolved here, which buys three structural guarantees that the first
draft failed on:

  * every in-text citation resolves to a source in data/sources.py;
  * the reference list contains exactly the sources actually cited - no padding;
  * same-author-same-year references get 2025a/2025b/... suffixes assigned by
    title, consistently in the citation and the reference list;
  * report figures are numbered 1..n by order of first appearance, so the
    workbook's sheet names (F1, F3, F6, ...) never leak their gaps into the
    report. The caption still names the workbook sheet.
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from sources import SOURCES, REFERENCE_ONLY          # noqa: E402
from dataset import POLICY_EVENTS                    # noqa: E402

DRAFT = ROOT / "report" / "draft"
SECTIONS = ["S1_context", "S2_adoption_effect", "S3_eu_diffusion",
            "S4_left_behind", "S6_recommendation"]

# Workbook sheet -> caption. The report figure NUMBER is assigned by first
# appearance, so it never appears in this table.
CAPTIONS = {
    "F1":  "Danish retail bank branches, 2004-2024. Finans Danmark; workbook F1_BRANCHES.",
    "F9":  "Danish banking consolidation: institutions, branches, employment; differing base years. Finans Danmark; workbook F9.",
    "F6":  "Consumer adoption and enterprise e-commerce turnover, EU 2024. Eurostat; workbook F6.",
    "F3":  "E-sales share of enterprise turnover, Denmark and EU-27, 2014 and 2024. Eurostat; workbook F3.",
    "F7":  "AI adoption by firm size, Denmark 2025. European Commission; workbook F7.",
    "F4":  "Five estimates of Danish digital exclusion; denominators and years differ. Workbook F4.",
    "F10": "Basic digital skills by age band, Denmark and EU-27, 2025. European Commission; workbook F10.",
    "F8":  "SMV:Digital participation: self-reported, no control group. Workbook F8.",
}

# Table 1 is trimmed to the instruments the argument actually turns on; the full
# timeline stays in workbook sheet 09_POLICY.
# Rigsrevisionen's 2016 audit is deliberately NOT here: it is a finding, not an
# instrument, and sections 1 and 6 both cite it in prose.
TABLE1_ROWS = ["2012-06-11", "2014-11-01", "2022-07-01", "2023-10-31"]


def author_year(harvard):
    """Split a Harvard string into its author and year, e.g. ('Eurostat', '2025')."""
    m = re.match(r"^(.*?) (\d{4}), (.*)$", harvard, re.S)
    if not m:
        raise ValueError(f"unparsable Harvard string: {harvard[:60]}")
    return m.group(1), m.group(2), m.group(3)


def build_citations(used_ids):
    """Assign a/b/c suffixes within each (author, year) group, ordered by title."""
    groups = {}
    for sid in used_ids:
        author, year, title = author_year(SOURCES[sid]["harvard"])
        groups.setdefault((author, year), []).append((title, sid))
    cite, refs = {}, []
    for (author, year), entries in groups.items():
        entries.sort()
        multiple = len(entries) > 1
        for i, (title, sid) in enumerate(entries):
            suffix = chr(ord("a") + i) if multiple else ""
            cite[sid] = (author, f"{year}{suffix}")
            harvard = SOURCES[sid]["harvard"]
            refs.append(harvard.replace(f"{author} {year},",
                                        f"{author} {year}{suffix},", 1))
    return cite, sorted(refs)


def main():
    bodies = {}
    for name in SECTIONS:
        text = (DRAFT / f"{name}.md").read_text(encoding="utf-8")
        bodies[name] = text.split("\n---\n")[0].rstrip()
    blob = "\n".join(bodies.values())

    # --- resolve figure numbers by order of first appearance -----------------
    order, seen = [], set()
    for sheet in re.findall(r"\[\[(F\d+)\]\]", blob):
        if sheet not in seen:
            seen.add(sheet)
            order.append(sheet)
    unknown = [s for s in order if s not in CAPTIONS]
    if unknown:
        raise SystemExit(f"figure token with no caption: {unknown}")
    fignum = {sheet: i + 1 for i, sheet in enumerate(order)}

    # --- resolve citations ---------------------------------------------------
    used = []
    for sid in re.findall(r"\[\[([A-Z]+\d*)(?::[yb])?\]\]", blob):
        if sid.startswith("F") and sid[1:].isdigit():
            continue
        if sid not in SOURCES:
            raise SystemExit(f"citation token names no source: {sid}")
        if sid in REFERENCE_ONLY:
            raise SystemExit(f"{sid} is REFERENCE_ONLY but is cited in the prose; "
                             "either drop the citation or reclassify the source")
        if sid not in used:
            used.append(sid)
    cite, references = build_citations(used)

    def resolve(text):
        def sub(m):
            tok, form = m.group(1), m.group(2)
            if tok in fignum:
                return f"Figure {fignum[tok]}"
            author, year = cite[tok]
            if form == ":y":
                return f"({year})"
            if form == ":b":
                return f"{author} {year}"
            return f"({author} {year})"
        return re.sub(r"\[\[([A-Za-z]+\d*)(:[yb])?\]\]", sub, text)

    caption_block = {}
    for sheet, num in fignum.items():
        caption_block.setdefault(sheet, f"*Figure {num} - {CAPTIONS[sheet]}*")

    def figures_for(name):
        sheets, seen_local = [], set()
        for s in re.findall(r"\[\[(F\d+)\]\]", bodies[name]):
            if s not in seen_local:
                seen_local.add(s)
                sheets.append(s)
        return "\n\n".join(caption_block[s] for s in sheets)

    events = {e[0]: e for e in POLICY_EVENTS}
    table1 = "\n".join(
        ["| Date | Instrument | What it did |", "|---|---|---|"]
        + [f"| {events[d][0]} | {events[d][3]} | {events[d][2]} |" for d in TABLE1_ROWS]
    )

    doc = f"""# Digital Policy and Innovation Report - Denmark

**ECON1596/ECON1597 Assessment 2** * s4040040 * Class group: [TO BE CONFIRMED]
Submitted 17 September 2026 * Accompanying data file:
`ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx`

> **Thesis.** Danish digital adoption is near-universal among citizens and thin
> among firms and at the edges of the population, and the instrument that
> delivered the universal part - legal compulsion - is why the rest is missing.

---

{resolve(bodies['S1_context'])}

**Table 1 - The instruments this report turns on.** Full timeline in workbook sheet 09_POLICY.

{table1}

---

{resolve(bodies['S2_adoption_effect'])}

{figures_for('S2_adoption_effect')}

---

{resolve(bodies['S3_eu_diffusion'])}

{figures_for('S3_eu_diffusion')}

---

{resolve(bodies['S4_left_behind'])}

{figures_for('S4_left_behind')}

---

## 5. [Guest lecture question]

> **NOT DRAFTED - blocked pending the guest lecture content.** 280 words are
> reserved in the word budget. `report/draft/S5_guest_lecture_STUB.md` maps the
> evidence already held against each likely question theme.

---

{resolve(bodies['S6_recommendation'])}

{figures_for('S6_recommendation')}

---

## References

{chr(10) + chr(10)}{(chr(10) + chr(10)).join(references)}
"""
    out = ROOT / "report" / "DRAFT_REPORT.md"
    out.write_text(doc, encoding="utf-8")

    counted = sum(len(resolve(b).split()) for b in bodies.values())
    caps = sum(len(c.split()) for c in caption_block.values())
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  sections {counted} + captions {caps} + reserved section 5 280 "
          f"= {counted + caps + 280}")
    print(f"  Table 1 {len(table1.split())} words "
          f"-> {counted + caps + 280 + len(table1.split())} if tables count")
    print(f"  {len(used)} sources cited, {len(references)} references, "
          f"{len(fignum)} figures numbered 1-{len(fignum)}")


if __name__ == "__main__":
    main()
