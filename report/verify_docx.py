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
    # 16cm == 5760000 EMU; allow rounding
    widths = [int(w) for w in re.findall(r'<wp:extent cx="(\d+)"', doc)]
    check(len(widths) == total_figs,
          f"{len(widths)} sized images, expected {total_figs}")
    check(all(abs(w - 5760000) < 20000 for w in widths),
          f"a figure is not 16cm wide: {widths}")

    # --- structure --------------------------------------------------------
    text = re.sub(r"<[^>]+>", "", doc)
    for section in r["sections"]:
        check(section["heading"] in text, f"missing heading: {section['heading']}")
        first = section["paragraphs"][0][:60]
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

    # --- the placeholder must be impossible to miss -----------------------
    check("DO NOT SUBMIT" in text, "section 5 placeholder is not marked")

    # --- Table 1 ----------------------------------------------------------
    app_tables = sum(1 for a in r["appendices"]
                     for kind, _p in a["blocks"] if kind == "table")
    check(doc.count("<w:tbl>") == 1 + app_tables,
          f"expected {1 + app_tables} tables, found {doc.count('<w:tbl>')}")

    # --- appendices -------------------------------------------------------
    for app in r["appendices"]:
        check(app["heading"] in text, f"missing appendix heading: {app['heading']}")
        first = next((p for k, p in app["blocks"] if k == "para"), "")[:60]
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
    # assemble_report.py. Raised from 5,200 when Appendix F was added.
    body_words = len(text.split())
    check(body_words < 6500,
          f"document body has {body_words} words, unexpectedly long")

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
