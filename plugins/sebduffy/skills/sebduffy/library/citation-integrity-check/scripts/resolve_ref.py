#!/usr/bin/env python3
"""Resolve a reference by DOI and flag retraction/correction status.

Cross-checks three free, no-key sources:
  - Crossref REST API  (metadata + Retraction Watch `updated-by` links)
  - OpenAlex           (`is_retracted` boolean)
  - PubMed E-utilities (PublicationType "Retracted Publication")

Stdlib only (urllib/json) so it runs on the system python3.9 with no pip.
Set CONTACT_EMAIL below (or env MAILTO) to join each API's polite pool.

Usage:
  python3 resolve_ref.py 10.1016/S0140-6736(97)11096-0
  python3 resolve_ref.py --json 10.1371/journal.pone.0000308
Exit code: 0 clean, 3 retracted, 2 not found, 1 error.
"""
import json, os, sys, urllib.parse, urllib.request

CONTACT_EMAIL = os.environ.get("MAILTO", "you@example.com")
UA = f"citation-integrity-check/1.0 (mailto:{CONTACT_EMAIL})"
TIMEOUT = 30


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def crossref(doi):
    """Return (metadata dict, list-of-update-notices) or (None, []) if 404."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="") + "?mailto=" + CONTACT_EMAIL
    try:
        m = _get(url)["message"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, []
        raise
    meta = {
        "title": (m.get("title") or [""])[0],
        "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                    for a in m.get("author", [])],
        "container": (m.get("container-title") or [""])[0],
        "year": (m.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0],
        "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"),
    }
    # `updated-by` on a retracted/corrected work points to the notice.
    notices = [{"type": u.get("type"), "label": u.get("label"),
                "doi": u.get("DOI"), "source": u.get("source")}
               for u in m.get("updated-by", [])]
    return meta, notices


def openalex(doi):
    url = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe="") + \
          "?mailto=" + CONTACT_EMAIL
    try:
        w = _get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return bool(w.get("is_retracted"))


def pubmed(doi):
    """Return (pmid, is_retracted) or (None, None)."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    q = urllib.parse.urlencode({"db": "pubmed", "term": f"{doi}[doi]",
                                "retmode": "json", "email": CONTACT_EMAIL})
    ids = _get(base + "esearch.fcgi?" + q).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None, None
    pmid = ids[0]
    s = urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json",
                                "email": CONTACT_EMAIL})
    rec = _get(base + "esummary.fcgi?" + s).get("result", {}).get(pmid, {})
    pubtypes = rec.get("pubtype", [])
    return pmid, ("Retracted Publication" in pubtypes)


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    doi = args[0].strip().replace("https://doi.org/", "")

    meta, notices = crossref(doi)
    if meta is None:
        out = {"doi": doi, "status": "NOT_FOUND"}
        print(json.dumps(out) if as_json else f"NOT FOUND in Crossref: {doi}")
        sys.exit(2)

    try:
        oa_retracted = openalex(doi)
    except Exception:
        oa_retracted = None
    try:
        pmid, pm_retracted = pubmed(doi)
    except Exception:
        pmid, pm_retracted = None, None

    cr_retracted = any(n["type"] == "retraction" for n in notices)
    retracted = bool(cr_retracted or oa_retracted or pm_retracted)
    result = {
        "doi": doi, "status": "RETRACTED" if retracted else "OK",
        "metadata": meta, "notices": notices,
        "signals": {"crossref_retraction": cr_retracted,
                    "openalex_is_retracted": oa_retracted,
                    "pubmed_retracted": pm_retracted, "pmid": pmid},
    }
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{'!! RETRACTED' if retracted else 'OK'}: {doi}")
        print(f"  {meta['title']}  ({meta['year']}) — {meta['container']}")
        for n in notices:
            print(f"  {n['label']}: {n['doi']}  [{n['source']}]")
        print(f"  signals: crossref={cr_retracted} openalex={oa_retracted} "
              f"pubmed={pm_retracted} pmid={pmid}")
    sys.exit(3 if retracted else 0)


if __name__ == "__main__":
    main()
