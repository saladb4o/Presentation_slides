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
APPENDIX_DIR = DRAFT / "appendix"
FIGURES_DIR = ROOT / "report" / "figures"
RESERVED_S5 = 280        # words held for the blocked guest-lecture section

# Appendices, in order. Letter, source file stem, title.
APPENDICES = [
    ("A", "A_ai_use", "AI Use and Validation"),
    ("B", "B_data_methods", "Data, Provenance and Verification"),
    ("C", "C_regression", "Regression Diagnostics"),
    ("D", "D_exclusion", "Reconciling the Exclusion Estimates"),
    ("E", "E_cross_sections", "Full Cross-Sections and Series"),
    ("F", "F_policy_spec", "Policy Specification and Implementation Timeline"),
    ("G", "G_comparative_law", "Comparative Law on Mandatory Digital Administration"),
    ("H", "H_ombudsman", "The Parliamentary Ombudsman on Digital Post"),
]

# Appendix figures are numbered WITHIN their appendix (Figure C1, C2, ...), so
# adding one never renumbers a body figure. Body figures stay 1-8 whatever the
# appendices do.
APPENDIX_FIGURES = {
    "AF_RESID": ("figA_c1_residuals.png",
                 "Residuals against fitted values, EU 2024 regression. Workbook F6."),
    "AF_JACK": ("figA_c2_jackknife.png",
                "Leave-one-out slopes, all 18 drops. Workbook F6."),
    "AF_TAIL": ("figA_c3_tailselection.png",
                "The six tail countries against the full cross-section. Workbook F6."),
    "AF_LADDER": ("figA_d1_denominators.png",
                  "The exclusion estimates converted to people on their own bases."),
    "AF_RANK": ("figA_e1_eu27.png",
                "Individuals purchasing online, all 27 member states, 2024. Workbook F5_EU27."),
    "AF_PROD": ("figA_e3_productivity.png",
                "Danish labour productivity against the EU-27 average, 2005-2025. "
                "An index on EU27 = 100, so it shows relative position, not growth."),
    "AF_SMV": ("fig8_smvdigital.png",
               "SMV:Digital participation: self-reported by participants to the "
               "scheme's own funder. Workbook F8."),
    "AF_GANTT": ("figA_f1_gantt.png",
                 "Implementation and evaluation timeline for the SMV:Digital "
                 "scoring-threshold design proposed in Section 6."),
    "AF_PAY": ("figA_e2_payments.png",
               "Instrument shares of physical-retail payments, 2017-2025. Workbook F2_PAYMENTS."),
}

# Workbook sheet -> the PNG that report/build_figures.py writes for it.
FIGURE_FILES = {
    "F1": "fig1_branches.png", "F9": "fig2_consolidation.png",
    "F6": "fig3_regression.png", "F3": "fig4_esales.png",
    "F7": "fig5_ai_firmsize.png", "F4": "fig6_exclusion.png",
    "F10": "fig7_skills.png",
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
            # Personal authors are listed "Surname, Initials" in the reference
            # list but cited "Surname" in text, and four or more authors become
            # "et al." A source may therefore carry an explicit in-text name;
            # organisational authors, which are the great majority here, need
            # none because the two forms coincide.
            intext = SOURCES[sid].get("intext", author)
            cite[sid] = (intext, f"{year}{suffix}")
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
    reference_only_cited = []
    bodies = {}
    for name in SECTIONS:
        text = (DRAFT / f"{name}.md").read_text(encoding="utf-8")
        bodies[name] = text.split("\n---\n")[0].rstrip()

    # Appendices are optional: absent files are simply skipped, so the report
    # builds at any stage of drafting them.
    app_bodies = {}
    for letter, stem, _title in APPENDICES:
        path = APPENDIX_DIR / f"{stem}.md"
        if path.exists():
            app_bodies[letter] = path.read_text(encoding="utf-8").split(
                "\n---\n")[0].rstrip()

    blob = "\n".join(list(bodies.values()) + list(app_bodies.values()))

    order, seen = [], set()
    for sheet in re.findall(r"\[\[(F\d+)\]\]", blob):
        if sheet not in seen:
            seen.add(sheet)
            order.append(sheet)
    unknown = [s for s in order if s not in CAPTIONS]
    if unknown:
        raise SystemExit(f"figure token with no caption: {unknown}")
    fignum = {sheet: i + 1 for i, sheet in enumerate(order)}

    # Appendix figures numbered within their own appendix: C1, C2, ...
    appfig = {}
    for letter, _stem, _title in APPENDICES:
        body = app_bodies.get(letter, "")
        seen_local, n = set(), 0
        for key in re.findall(r"\[\[(AF_[A-Z]+)\]\]", body):
            if key in seen_local:
                continue
            if key not in APPENDIX_FIGURES:
                raise SystemExit(f"appendix figure token with no entry: {key}")
            seen_local.add(key)
            n += 1
            appfig[key] = (f"{letter}{n}", letter)

    used = []
    for sid in re.findall(r"\[\[([A-Z]+\d*)(?::[yb])?\]\]", blob):
        if sid.startswith("AF_"):
            continue
        if sid.startswith("F") and sid[1:].isdigit():
            continue
        if sid not in SOURCES:
            raise SystemExit(f"citation token names no source: {sid}")
        # REFERENCE_ONLY sources support argument but supply no workbook value.
        # Citing them in prose is legitimate - that is what they are for. The
        # rule they must still obey is that no figure or numeric claim rests on
        # them, which is why they are named here rather than silently allowed.
        if sid in REFERENCE_ONLY:
            reference_only_cited.append(sid)
        if sid not in used:
            used.append(sid)
    cite, references = build_citations(used)

    def resolve(text):
        def sub(m):
            tok, form = m.group(1), m.group(2)
            if tok in appfig:
                return f"Figure {appfig[tok][0]}"
            if tok in fignum:
                return f"Figure {fignum[tok]}"
            author, year = cite[tok]
            if form == ":y":
                return f"({year})"
            if form == ":b":
                return f"{author} {year}"
            return f"({author} {year})"
        return re.sub(r"\[\[(AF_[A-Z]+|[A-Za-z]+\d*)(:[yb])?\]\]", sub, text)

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

    appendices = []
    for letter, stem, title in APPENDICES:
        if letter not in app_bodies:
            continue
        resolved = resolve(app_bodies[letter])
        chunks = [c.strip() for c in resolved.split("\n\n") if c.strip()]
        blocks = []
        for chunk in chunks:
            if chunk.startswith("### "):
                blocks.append(("subheading", chunk[4:].strip()))
            elif chunk.startswith("## "):
                continue                       # the title comes from APPENDICES
            elif chunk.lstrip().startswith("|"):
                rows = [[c.strip() for c in line.strip().strip("|").split("|")]
                        for line in chunk.splitlines()
                        if line.strip().startswith("|")
                        and not set(line.replace("|", "").strip()) <= set("-: ")]
                blocks.append(("table", rows))
            elif chunk.startswith("- "):
                blocks.append(("bullets", [l[2:].strip()
                                           for l in chunk.splitlines()
                                           if l.startswith("- ")]))
            else:
                blocks.append(("para", " ".join(chunk.split())))
        figures = []
        seen_local = set()
        for key in re.findall(r"\[\[(AF_[A-Z]+)\]\]", app_bodies[letter]):
            if key in seen_local:
                continue
            seen_local.add(key)
            number, _ = appfig[key]
            filename, caption = APPENDIX_FIGURES[key]
            figures.append({"key": key, "number": number, "file": filename,
                            "caption": f"Figure {number} - {caption}"})
        appendices.append({"letter": letter, "title": title,
                           "heading": f"Appendix {letter}. {title}",
                           "blocks": blocks, "figures": figures,
                           "words": len(" ".join(
                               b[1] for b in blocks
                               if b[0] in ("para", "subheading")).split())})

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
        "appendices": appendices,
        "appendix_words": sum(a["words"] for a in appendices),
        "reference_only_cited": sorted(set(reference_only_cited)),
        "figure_count": len(fignum),
        "appendix_figure_count": sum(len(a["figures"]) for a in appendices),
        "source_count": len(used),
    }
