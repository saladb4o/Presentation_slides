#!/usr/bin/env python3
"""Shared content model for the report.

Both renderers - the markdown assembler and the .docx builder - call build()
and get the same resolved content. Nothing about citations, figure numbers,
Table 1 or the reference list is decided in a renderer, so the two outputs
cannot drift apart.

Sections live in report/draft/ and carry TOKENS rather than typed citations or
figure numbers:

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
FIGURES_DIR = ROOT / "report" / "figures"
RESERVED_S5 = 280        # words held for the blocked guest-lecture section

# Workbook sheet -> the PNG that report/build_figures.py writes for it.
FIGURE_FILES = {
    "F1": "fig1_branches.png", "F9": "fig2_consolidation.png",
    "F6": "fig3_regression.png", "F3": "fig4_esales.png",
    "F7": "fig5_ai_firmsize.png", "F4": "fig6_exclusion.png",
    "F10": "fig7_skills.png", "F8": "fig8_smvdigital.png",
}
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




SectionContent = list        # [(kind, payload), ...]


def build():
    """Resolve every token and return the report as structured content.

    Returns a dict:
      meta        - title and identifying lines
      thesis      - the thesis statement
      sections    - ordered list of dicts: heading, paragraphs, figures
      table1      - (caption, header, rows)
      references  - alphabetised Harvard strings
      counts      - word counts, so both renderers report the same number
    """
    bodies = {}
    for name in SECTIONS:
        text = (DRAFT / f"{name}.md").read_text(encoding="utf-8")
        bodies[name] = text.split("\n---\n")[0].rstrip()
    blob = "\n".join(bodies.values())

    order, seen = [], set()
    for sheet in re.findall(r"\[\[(F\d+)\]\]", blob):
        if sheet not in seen:
            seen.add(sheet)
            order.append(sheet)
    unknown = [s for s in order if s not in CAPTIONS]
    if unknown:
        raise SystemExit(f"figure token with no caption: {unknown}")
    fignum = {sheet: i + 1 for i, sheet in enumerate(order)}

    used = []
    for sid in re.findall(r"\[\[([A-Z]+\d*)(?::[yb])?\]\]", blob):
        if sid.startswith("F") and sid[1:].isdigit():
            continue
        if sid not in SOURCES:
            raise SystemExit(f"citation token names no source: {sid}")
        if sid in REFERENCE_ONLY:
            raise SystemExit(f"{sid} is REFERENCE_ONLY but is cited in the prose")
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

    sections = []
    for name in SECTIONS:
        resolved = resolve(bodies[name])
        chunks = [c.strip() for c in resolved.split("\n\n") if c.strip()]
        heading = chunks[0].lstrip("# ").strip()
        paragraphs = [" ".join(c.split()) for c in chunks[1:]]
        sheets, local = [], set()
        for s in re.findall(r"\[\[(F\d+)\]\]", bodies[name]):
            if s not in local:
                local.add(s)
                sheets.append(s)
        figures = [{"number": fignum[s], "sheet": s,
                    "file": FIGURE_FILES[s],
                    "caption": f"Figure {fignum[s]} - {CAPTIONS[s]}"}
                   for s in sheets]
        sections.append({"key": name, "heading": heading,
                         "paragraphs": paragraphs, "figures": figures})

    events = {e[0]: e for e in POLICY_EVENTS}
    table1 = {
        "caption": ("Table 1 - The instruments this report turns on. "
                    "Full timeline in workbook sheet 09_POLICY."),
        "header": ["Date", "Instrument", "What it did"],
        "rows": [[events[d][0], events[d][3], events[d][2]] for d in TABLE1_ROWS],
    }

    counted = sum(len(" ".join(s["paragraphs"]).split()) + len(s["heading"].split())
                  for s in sections)
    caps = sum(len(f["caption"].split())
               for s in sections for f in s["figures"])
    table_words = sum(len(" ".join(r).split()) for r in table1["rows"]) \
        + len(" ".join(table1["header"]).split())

    return {
        "meta": {
            "title": "Digital Policy and Innovation Report - Denmark",
            "lines": [
                "ECON1596/ECON1597 Assessment 2 | s4040040 | "
                "Class group: [TO BE CONFIRMED]",
                "Submitted 17 September 2026",
                "Accompanying data file: "
                "ECON1596_A2_Denmark_DataWorkbook_s4040040.xlsx",
            ],
        },
        "thesis": (
            "Thesis. Danish digital adoption is near-universal among citizens "
            "and thin among firms and at the edges of the population, and the "
            "instrument that delivered the universal part - legal compulsion - "
            "is why the rest is missing."
        ),
        "placeholder": {
            "heading": "5. [Guest lecture question]",
            "text": ("NOT DRAFTED - blocked pending the guest lecture content. "
                     "280 words are reserved in the word budget."),
        },
        "sections": sections,
        "table1": table1,
        "references": references,
        "counts": {"sections": counted, "captions": caps,
                   "reserved_s5": RESERVED_S5, "table1": table_words,
                   "total": counted + caps + RESERVED_S5,
                   "total_with_table": counted + caps + RESERVED_S5 + table_words},
        "figure_count": len(fignum),
        "source_count": len(used),
    }
