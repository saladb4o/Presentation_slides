#!/usr/bin/env python3
"""Render report/DRAFT_REPORT.md from the shared content model.

This is a renderer only. Citations, figure numbers, Table 1, the reference list
and the word counts are all decided in render.py, which report/build_docx.py
also calls - so the markdown preview and the submitted .docx cannot disagree.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "report"))
from render import build                                   # noqa: E402


def main():
    r = build()
    out = [f"# {r['meta']['title']}", ""]
    out += ["  \n".join(r["meta"]["lines"]), ""]
    out += [f"> **{r['thesis'].split('.', 1)[0]}.**"
            f"{r['thesis'].split('.', 1)[1]}", "", "---", ""]

    for section in r["sections"]:
        out += [f"## {section['heading']}", ""]
        for para in section["paragraphs"]:
            out += [para, ""]
        if section["key"] == "S1_context":
            t = r["table1"]
            out += [f"**{t['caption']}**", ""]
            out += ["| " + " | ".join(t["header"]) + " |",
                    "|" + "---|" * len(t["header"])]
            out += ["| " + " | ".join(row) + " |" for row in t["rows"]]
            out += [""]
        for fig in section["figures"]:
            out += [f"![{fig['caption']}](figures/{fig['file']})", "",
                    f"*{fig['caption']}*", ""]
        out += ["---", ""]
        if section["key"] == "S4_left_behind":
            p = r["placeholder"]
            out += [f"## {p['heading']}", "", f"> **{p['text']}**", "", "---", ""]

    out += ["## References", ""]
    out += ["\n\n".join(r["references"]), ""]

    path = ROOT / "report" / "DRAFT_REPORT.md"
    path.write_text("\n".join(out), encoding="utf-8")
    c = r["counts"]
    print(f"wrote {path.relative_to(ROOT)}")
    print(f"  sections {c['sections']} + captions {c['captions']} "
          f"+ reserved section 5 {c['reserved_s5']} = {c['total']}")
    print(f"  Table 1 {c['table1']} words -> {c['total_with_table']} "
          f"if tables count")
    print(f"  {r['source_count']} sources cited, {len(r['references'])} "
          f"references, {r['figure_count']} figures numbered "
          f"1-{r['figure_count']}")


if __name__ == "__main__":
    main()
