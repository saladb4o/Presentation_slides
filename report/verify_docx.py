#!/usr/bin/env python3
"""Verify the built .docx against the assessment's formatting requirements.

LibreOffice in this container ships without its import/export filters - it
cannot load even a trivial .docx - so the file cannot be rendered here for a
visual check. Instead this asserts on the WordprocessingML that Word itself
reads: if these properties are present and correct, Word applies them.

What this does NOT prove: that the result looks good. Open it once before
submitting.
"""
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "report"))
from render import build, FIGURE_FILES                      # noqa: E402
from sources import REFERENCE_ONLY, SOURCES                 # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
failures, checks = [], 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        failures.append(msg)


def main():
    matches = sorted(ROOT.glob("Assignment 2 ECON1596 _*.docx"))
    if not matches:
        raise SystemExit("no built .docx found - run report/build_docx.py")
    path = matches[0]
    z = zipfile.ZipFile(path)
    doc = z.read("word/document.xml").decode("utf-8")
    styles = z.read("word/styles.xml").decode("utf-8")
    r = build()

    # --- brief's formatting requirements ---------------------------------
    normal = styles.split('w:styleId="Normal"')[1][:1200]
    check('w:ascii="Times New Roman"' in normal, "Normal style is not Times New Roman")
    check('w:sz w:val="24"' in normal, "Normal style is not 12pt (sz 24 half-points)")
    check('w:line="360"' in normal or 'w:lineRule="auto"' in normal,
          "Normal style carries no 1.5 line spacing")
    for side in ("top", "bottom", "left", "right"):
        check(f'w:{side}="1440"' in doc, f"{side} margin is not 1 inch (1440 twips)")
    justified = doc.count('w:val="both"')
    check(justified >= 15, f"only {justified} justified paragraphs")

    # --- images -----------------------------------------------------------
    embedded = [n for n in z.namelist() if n.startswith("word/media/")]
    total_figs = r["figure_count"] + r["appendix_figure_count"]
    check(len(embedded) == total_figs,
          f"{len(embedded)} images embedded, expected {total_figs}")
    sizes = {n: z.getinfo(n).file_size for n in embedded}
    check(all(s > 20000 for s in sizes.values()),
          f"an embedded image looks truncated: {sizes}")
    # 15.5cm == 5580000 EMU; allow rounding. Must stay inside the A4
    # text width of 15.92cm, or figures overhang the margin.
    widths = [int(w) for w in re.findall(r'<wp:extent cx="(\d+)"', doc)]
    check(len(widths) == total_figs,
          f"{len(widths)} sized images, expected {total_figs}")
    check(all(abs(w - 5580000) < 20000 for w in widths),
          f"a figure is not 15.5cm wide: {widths}")


    # A4, not the US Letter python-docx defaults to.
    pg = re.search(r'<w:pgSz w:w="(\d+)" w:h="(\d+)"', doc)
    check(pg and (int(pg.group(1)), int(pg.group(2))) == (11906, 16838),
          f"page size is not A4: {pg.groups() if pg else 'absent'}")

    # --- structure --------------------------------------------------------
    text = re.sub(r"<[^>]+>", "", doc)

    # Every column the renderer defines must reach the document, and every
    # date in Table 1 is a factual claim that must carry its source.
    t1 = r["table1"]
    grid = re.search(r"<w:tblGrid>(.*?)</w:tblGrid>", doc, re.S)
    cols = len(re.findall(r"<w:gridCol", grid.group(1))) if grid else 0
    check(cols == len(t1["header"]),
          f"Table 1 renders {cols} columns but the renderer defines "
          f"{len(t1['header'])}")
    for cell in t1["header"] + [c for row in t1["rows"] for c in row]:
        check(cell in text, f"Table 1 cell {cell!r} is missing from the document")
    for section in r["sections"]:
        check(section["heading"] in text, f"missing heading: {section['heading']}")
        # The rendered document carries emphasis as formatting, so the
        # asterisks the draft writes are not in the text to match against.
        first = re.sub(r"\*+", "", section["paragraphs"][0])[:60]
        check(first in text, f"missing opening prose of {section['heading']}")
    for section in r["sections"]:
        for fig in section["figures"]:
            check(fig["caption"][:40] in text,
                  f"missing caption: {fig['caption'][:40]}")
    for ref in r["references"]:
        check(ref.split(",")[0] in text, f"missing reference: {ref[:40]}")
    check(len(z.read("word/footer1.xml")) > 0 if "word/footer1.xml" in z.namelist()
          else False, "no footer part")
    footer = z.read("word/footer1.xml").decode("utf-8")
    check("PAGE" in footer, "footer carries no PAGE field")

    # --- no trace of the section 5 stub may survive -----------------------
    # While Section 5 was blocked, the renderer injected a loud placeholder AND
    # added 280 reserved words to every count. Section 5 is written now. The
    # placeholder outlived it by one build, printing a "NOT DRAFTED" heading
    # directly above the real section, and the reserve outlived it silently,
    # overstating the body by 280 words and provoking trims that were not needed.
    for stale in ("DO NOT SUBMIT", "NOT DRAFTED", "[Guest lecture question]"):
        check(stale not in text, f"section 5 stub text {stale!r} is still in the document")

    # --- citations and reference list ------------------------------------
    # A narrative citation renders "(Year)" and relies on the sentence to name
    # the author. When the sentence does not, the reader gets a bare "(2012)".
    for m in re.finditer(r"(.{0,40}?)\((?:19|20)\d{2}[a-z]?\)", text):
        before = m.group(1).rstrip()
        check(bool(re.search(r"[A-Za-z\u00C0-\u024F]$", before)),
              f"citation {m.group(0)[-7:]!r} has no author before it: ...{before[-40:]!r}")

    draft = pathlib.Path(__file__).resolve().parent / "draft"
    for f in sorted(draft.rglob("*.md")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            check(not re.search(r"Section \d", line),
                  f"{f.name}:{n} refers to a Section; the report is structured "
                  f"as Questions 1 to 5, which is what the brief marks")
            check(not re.search(r"Appendix [A-H]\b", line),
                  f"{f.name}:{n} writes an appendix letter into the prose; "
                  f"use [[AP:topic]] so the letter follows APPENDICES")

    for f in sorted(draft.rglob("*.md")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            check("]]" not in line or ":b]]" not in line or line.startswith("|"),
                  f"{f.name}:{n} uses a bare citation outside a table row, "
                  f"which renders an author and year loose in the prose")

    # Harvard orders the list letter by letter. Sorting raw strings puts every
    # capital before every lowercase letter, which is not the same thing.
    def alpha(s):
        return re.sub(r"[^a-z0-9 ]", "", s.lower())
    refs = r["references"]
    check(refs == sorted(refs, key=alpha),
          "reference list is not in letter-by-letter alphabetical order")

    # Two ids pointing at one document produce two entries for one source.
    # DG3 and DG5 did exactly that, under the same URL, as 2025b and 2025c.
    urls = [u for s in SOURCES.values() if (u := s.get("url"))]
    dupes = {u for u in urls if urls.count(u) > 1}
    check(not dupes, f"more than one source shares a URL: {sorted(dupes)}")

    # --- Table 1 ----------------------------------------------------------
    app_tables = sum(1 for a in r["appendices"]
                     for kind, _p in a["blocks"] if kind == "table")
    check(doc.count("<w:tbl>") == 1 + app_tables,
          f"expected {1 + app_tables} tables, found {doc.count('<w:tbl>')}")

    # --- appendices -------------------------------------------------------
    for app in r["appendices"]:
        check(app["heading"] in text, f"missing appendix heading: {app['heading']}")
        first = re.sub(r"\*+", "",
                       next((p for k, p in app["blocks"] if k == "para"), ""))[:60]
        check(first in text, f"missing opening prose of {app['heading']}")
        for fig in app["figures"]:
            check(fig["caption"][:35] in text,
                  f"missing appendix caption: {fig['caption'][:35]}")
    # every appendix must be pointed at from the body, or a marker never opens it
    body_text = " ".join(p for s in r["sections"] for p in s["paragraphs"])
    for app in r["appendices"]:
        letter = app["letter"]
        referenced = (f"Appendix {letter}" in body_text
                      or re.search(rf"Appendices [A-Z] to [{letter}-Z]", body_text))
        check(bool(referenced),
              f"Appendix {letter} is never referenced from the body")
    for row in r["table1"]["rows"]:
        check(row[0] in text, f"Table 1 missing row {row[0]}")

    # --- word count -------------------------------------------------------
    # Tripwire against runaway generation across the WHOLE document, not the
    # 2,000-word assessment limit - that one is enforced on the body alone by
    # assemble_report.py. Raised from 5,200 when Appendix F was added, and again
    # when Appendix G added the comparative case law, and again when H and the
    # regression-discontinuity literature were added. The appendices now run
    # well past the body; that is a judgement call for the author, not a
    # generation failure, which is all this guard is for.
    body_words = len(text.split())
    check(body_words < 9000,
          f"document body has {body_words} words, unexpectedly long")

    # The assessment limit is 2,000 words plus 10%. Tables count toward it, so
    # the ceiling is enforced on the inclusive figure. This had been checked by
    # hand each build, which is exactly how a limit drifts: adding Section 5
    # pushed the body 252 words over and nothing said so.
    counted = r["counts"]["total"]
    check(1800 <= counted <= 2200,
          f"body is {counted} words, outside the 1,800 to 2,200 band the brief "
          f"sets (2,000 plus or minus 10%, excluding references, tables and figures)")

    # REFERENCE_ONLY declares a source as supporting ARGUMENT in the report
    # rather than supplying a workbook value. The workbook verifier cannot test
    # that claim, because the report is not the workbook - so an entry could sit
    # there indefinitely describing a citation that had been edited away. Found
    # by audit: two did. The claim is testable here and now it is tested.
    cited = set(r["reference_only_cited"])
    for sid in sorted(REFERENCE_ONLY):
        check(sid in cited,
              f"{sid} is declared REFERENCE_ONLY - meaning it supports argument "
              f"in the report - but the report never cites it")

    # House style, set by the author: no em or en dashes anywhere in the
    # document. They are checked on the rendered text rather than the drafts
    # because figure titles, captions and generated reference strings also
    # reach the page and are easy to forget.
    # Remove the reference-list strings from the text first, so what remains is
    # only prose this report wrote. Counting instead of removing would let a
    # stray dash in the body hide behind a dash in a title.
    prose = text
    for ref in r["references"]:
        prose = prose.replace(ref, "")
    # A hyphen with a space either side is a dash by another name. The em and
    # en dash check below never saw the one in the thesis line because that
    # string lives in the renderer, not in a draft file.
    check(" - " not in prose,
          "a spaced hyphen is used as a dash in the report's own prose")

    for ch, name in (("\u2014", "em dash"), ("\u2013", "en dash")):
        n = prose.count(ch)
        check(n == 0,
              f"{n} {name}(s) in the report's own prose; house style is none. "
              f"Quoted source titles in the reference list are exempt")

    print(f"{checks} checks run")
    if failures:
        print(f"\n{len(failures)} FAILURES:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("all checks passed")
    print(f"  {path.name}")
    print(f"  {len(embedded)} figures, {len(r['references'])} references, "
          f"{r['counts']['total']} counted words "
          f"({r['counts']['total_with_table']} incl. Table 1)")


if __name__ == "__main__":
    main()
