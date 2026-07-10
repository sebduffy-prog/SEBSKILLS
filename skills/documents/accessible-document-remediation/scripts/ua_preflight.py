#!/usr/bin/env python3
"""PDF/UA machine-checkable preflight audit (no Java, no license).

Checks the structural PDF/UA-1 (ISO 14289-1) requirements that a screen
reader relies on and that veraPDF also enforces, but which are cheap to read
straight from the document catalog with pypdf. This is a *triage* tool: a
clean report here does NOT mean full PDF/UA conformance (alt-text quality,
reading order and the human WCAG checks still need review) -- but any FAIL
here is a definite blocker worth fixing before you run veraPDF or ship.

Usage:
    python3 ua_preflight.py FILE.pdf [FILE2.pdf ...]

Exit code 0 = every file passed all hard checks; 1 = at least one FAIL.
Requires: pypdf >= 3 (pip install pypdf).
"""
import sys

try:
    from pypdf import PdfReader
    from pypdf.generic import IndirectObject
except ImportError:
    sys.stderr.write("pypdf is required: pip install pypdf\n")
    sys.exit(2)


def _deref(obj):
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def audit(path):
    """Return (list_of_results, hard_fail_count) for one PDF.

    Each result is (level, label, detail) where level is PASS/FAIL/WARN.
    """
    results = []
    try:
        reader = PdfReader(path)
    except Exception as exc:  # noqa: BLE001 - report, do not crash the batch
        return [("FAIL", "readable", f"cannot open: {exc}")], 1

    root = _deref(reader.trailer["/Root"])

    # 1. Tagged: /MarkInfo << /Marked true >>
    mark_info = _deref(root.get("/MarkInfo"))
    marked = bool(mark_info and _deref(mark_info.get("/Marked")))
    results.append(("PASS" if marked else "FAIL", "tagged",
                    "/MarkInfo /Marked true" if marked
                    else "not tagged - add a logical structure tree"))

    # 2. Structure tree present
    has_struct = root.get("/StructTreeRoot") is not None
    results.append(("PASS" if has_struct else "FAIL", "struct-tree",
                    "/StructTreeRoot present" if has_struct
                    else "no /StructTreeRoot - no semantic structure"))

    # 3. Natural language declared on the catalog
    lang = _deref(root.get("/Lang"))
    has_lang = bool(lang and str(lang).strip())
    results.append(("PASS" if has_lang else "FAIL", "lang",
                    f"/Lang = {lang}" if has_lang
                    else "no document /Lang - screen readers can't pick a voice"))

    # 4. Document title + DisplayDocTitle so the title (not the filename) shows
    info = _deref(reader.trailer.get("/Info")) or {}
    title = _deref(info.get("/Title")) if info else None
    has_title = bool(title and str(title).strip())
    vp = _deref(root.get("/ViewerPreferences")) or {}
    show_title = bool(vp and _deref(vp.get("/DisplayDocTitle")))
    if has_title and show_title:
        results.append(("PASS", "title", f"/Title set, DisplayDocTitle true"))
    elif has_title and not show_title:
        results.append(("FAIL", "title",
                        "/Title set but ViewerPreferences/DisplayDocTitle "
                        "missing/false - viewers show the filename"))
    else:
        results.append(("FAIL", "title", "no document /Title in metadata"))

    # 5. Every page should force structure tab order: /Tabs /S
    bad_tabs = []
    for idx, page in enumerate(reader.pages, start=1):
        tabs = _deref(page.get("/Tabs"))
        if str(tabs) != "/S":
            bad_tabs.append(idx)
    if not reader.pages:
        results.append(("WARN", "tab-order", "document has no pages"))
    elif bad_tabs:
        results.append(("FAIL", "tab-order",
                        f"{len(bad_tabs)} page(s) missing /Tabs /S "
                        f"(first: p{bad_tabs[0]})"))
    else:
        results.append(("PASS", "tab-order", "all pages use /Tabs /S"))

    # 6. XMP metadata stream (PDF/UA identifier lives here) -- soft check
    has_xmp = root.get("/Metadata") is not None
    results.append(("PASS" if has_xmp else "WARN", "xmp",
                    "/Metadata stream present" if has_xmp
                    else "no XMP metadata - PDF/UA identifier can't be embedded"))

    hard_fails = sum(1 for level, _, _ in results if level == "FAIL")
    return results, hard_fails


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    total_fail = 0
    for path in argv[1:]:
        print(f"\n=== {path} ===")
        results, hard = audit(path)
        for level, label, detail in results:
            print(f"  [{level:4}] {label:12} {detail}")
        total_fail += hard
        verdict = "BLOCKERS FOUND" if hard else "no structural blockers"
        print(f"  -> {verdict} ({hard} hard fail(s))")
    print(f"\nTotal hard fails across {len(argv) - 1} file(s): {total_fail}")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
