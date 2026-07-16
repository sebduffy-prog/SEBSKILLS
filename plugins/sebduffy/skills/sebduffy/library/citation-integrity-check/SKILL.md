---
name: citation-integrity-check
category: verification
description: >
  Verify every reference in a manuscript, report, or LLM output actually EXISTS and says
  what it is cited for. Resolve each DOI/PMID against Crossref, OpenAlex, and PubMed;
  confirm title/authors/year/pages match; flag retractions and corrections via the Retraction
  Watch data now baked into Crossref's API; catch hallucinated, mismatched, or discredited
  citations before they ship. Use when checking a bibliography, reference list, or any
  AI-generated citations.
when_to_use:
  - Auditing a bibliography or reference list before submission, publication, or client delivery
  - Checking citations produced by an LLM (real DOI? real paper? says what's claimed?)
  - Screening a manuscript's references for retracted or corrected papers
  - Confirming a quoted passage or page number actually appears in the cited source
  - Building a clean, resolvable, retraction-free reference set for a report or deck
when_not_to_use:
  - Judging whether a source is trustworthy/biased in the first place — use source-credibility-audit
  - Checking a factual/empirical claim regardless of citation — use claim-verifier
  - Auditing statistics/p-values/effect sizes inside a paper — use stat-check-review
  - Evaluating study design or methods quality — use research-methodology-review
keywords: [citation, doi, crossref, openalex, pubmed, retraction, retraction-watch, reference-check, bibliography, hallucinated-citation, pmid, verification, quote-check, page-number]
similar_to: [claim-verifier, stat-check-review, source-credibility-audit, research-methodology-review, adversarial-argument-review, self-consistency-check]
inputs_needed: A bibliography / reference list / manuscript with in-text citations, or a list of DOIs/PMIDs/titles. Network access. No API keys required.
produces: A per-reference verdict table (EXISTS / METADATA-MISMATCH / NOT-FOUND / RETRACTED) with resolved metadata, retraction notices, and the specific fields that disagree.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Citation Integrity Check

Every reference makes three implicit claims: **it exists**, **its metadata is right**, and **it
supports what it's cited for**. Hallucinated LLM citations fail the first, sloppy human
bibliographies fail the second, and even careful authors fail the third when they cite a
paper that was later retracted. This skill checks all three against free, no-key scholarly
APIs, with Retraction Watch coverage built in.

## When to use

Run this whenever a reference list is load-bearing: journal submissions, litigation exhibits,
policy briefs, client decks, and above all **any citations an LLM generated** — fabricated
DOIs that resolve to a *different* real paper are the most dangerous failure mode, because a
DOI that resolves looks trustworthy until you compare the metadata.

## Prerequisites

- **Network access.** No API keys. All three sources are free.
- **Python 3.9+** (the system `python3` on macOS is fine — the helper is stdlib-only, no pip).
- **Polite pool:** set a contact email so APIs give you priority and won't rate-limit:
  `export MAILTO="you@example.com"` before running the helper. Crossref, OpenAlex, and
  PubMed all reward a real `mailto`; anonymous traffic can be throttled.
- Sources of truth:
  - **Crossref REST** — `https://api.crossref.org/works/{DOI}` — canonical publisher metadata
    **and** Retraction Watch links (the Labs endpoint is deprecated; data is now in production).
  - **OpenAlex** — `https://api.openalex.org/works/https://doi.org/{DOI}` — has an
    `is_retracted` boolean.
  - **PubMed E-utilities** — biomedical coverage + PublicationType `"Retracted Publication"`.

## Recipes

### 1. Resolve + retraction-screen one reference (the helper)

```bash
export MAILTO="you@example.com"
cd scripts
python3 resolve_ref.py 10.1016/S0140-6736(97)11096-0        # human-readable
python3 resolve_ref.py --json 10.1371/journal.pone.0000308  # machine-readable
```

Exit codes: `0` clean · `3` retracted · `2` not found · `1` error — so you can gate a CI/batch
job on them. The tool queries all three sources, unions the retraction signals (any one is
enough to flag), and prints the resolved title/year/venue so you can eyeball the match.

### 2. Batch-check a whole bibliography

Extract DOIs (one per line into `dois.txt`), then:

```bash
while read -r doi; do
  [ -z "$doi" ] && continue
  python3 scripts/resolve_ref.py "$doi" || true      # keep going past non-zero exits
  echo "---"
done < dois.txt | tee citation_report.txt
```

To pull DOIs out of messy text (handles most modern DOIs):

```bash
grep -oiE '10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+' manuscript.txt | sort -u > dois.txt
```

### 3. Metadata match — is the DOI the paper they *think* it is?

An LLM will happily cite `10.1234/foo` with a plausible-looking author and year that belong to
a *different* paper. Resolve the DOI, then compare the claimed vs. resolved fields:

| Field | Rule |
|-------|------|
| First-author surname | Must match (allow transliteration variants) |
| Year | Must match exactly — off-by-one usually means wrong DOI |
| Title | Compare normalized (lowercase, strip punctuation); flag if not a clear match |
| Venue / journal | Must be consistent; a Nature cite resolving to a predatory journal is a red flag |
| Volume / issue / pages | Compare when present; mismatched pages break quote/page-number claims |

Verdict per reference: **EXISTS-AND-MATCHES** / **METADATA-MISMATCH** (resolves, wrong paper) /
**NOT-FOUND** (likely hallucinated) / **RETRACTED**.

### 4. Retraction & correction screen (what's under the hood)

On a retracted work, Crossref exposes an `updated-by` array. Each entry is a notice:

```json
"updated-by": [
  { "type": "retraction", "label": "Retraction",
    "DOI": "10.1016/s0140-6736(10)60175-4", "source": "retraction-watch",
    "updated": { "date-parts": [[2010, 2, 6]] } }
]
```

`type` is `retraction`, `correction`, `expression_of_concern`, `withdrawal`, etc.; `source` is
`retraction-watch` or `publisher`. To pull the *whole* current retraction firehose:

```bash
curl -s "https://api.crossref.org/works?filter=update-type:retraction&rows=5&mailto=$MAILTO" \
  | python3 -m json.tool | head -40
```

Coverage is not identical across sources — that's exactly why the helper checks all three and
flags on any positive. Corrections/EoCs are not the same as retractions: report them, but don't
treat a corrected paper as invalid unless the correction undermines the cited claim.

### 5. Quote & page-number verification

Resolving metadata does **not** prove the quoted sentence is in the source. For that:

1. Get the open-access PDF/HTML: check OpenAlex `best_oa_location.pdf_url` /
   `primary_location.landing_page_url`, or Unpaywall (`https://api.unpaywall.org/v2/{DOI}?email=$MAILTO`).
2. Fetch it (WebFetch, or the `pdf` skill for local PDFs) and search for the quoted string.
3. Confirm the quote is verbatim (allow `[...]` elisions) **and** the cited page number lands on
   the passage. Paraphrases attributed as direct quotes, and quotes lifted out of a context that
   reverses their meaning, both count as integrity failures — report them.

## Verify

- Run the two smoke cases and confirm the verdicts and exit codes:
  ```bash
  python3 scripts/resolve_ref.py 10.1016/S0140-6736(97)11096-0; echo "exit=$?"  # RETRACTED, exit 3
  python3 scripts/resolve_ref.py 10.1371/journal.pone.0000308;  echo "exit=$?"  # OK, exit 0
  ```
  The first (Wakefield 1998) must show a Retraction notice with `source: retraction-watch` and
  `crossref=True openalex=True pubmed=True`. A bogus DOI must print NOT FOUND, exit 2.
- Spot-check one flagged retraction against the public record at
  `https://retractionwatch.com` or the retraction-notice DOI in a browser.
- For a clean bibliography every reference should end EXISTS-AND-MATCHES with no retractions.

## Pitfalls

- **A resolving DOI is not a matching DOI.** The single most common LLM failure is a real DOI
  pointing at the *wrong* paper. Always compare metadata (recipe 3) — never stop at "it resolves".
- **Not everything has a DOI.** Books, preprints, grey literature, and older papers may lack one.
  Fall back to title search (Crossref `?query.bibliographic=`) or a PMID, and verify manually.
- **DOI encoding.** DOIs contain `/`, `(`, `)`, `;`, `:` — always URL-encode before putting one
  in a path (the helper does this with `urllib.parse.quote(..., safe="")`).
- **Rate limits.** Without a `mailto` you can get throttled or dropped into a slow pool. Set
  `MAILTO`, and for large batches add a small sleep between calls to be a good citizen.
- **Retraction lag.** A very recent retraction may not have propagated to all three sources yet;
  the union check mitigates this but cannot eliminate it. When stakes are high, also eyeball
  Retraction Watch directly.
- **Correction ≠ retraction.** Don't discard a paper over a routine erratum. Report the notice
  type accurately and judge relevance to the specific claim being cited.
- **Don't trust the abstract as the whole paper.** Quote/page checks (recipe 5) require the full
  text, not the abstract or a metadata snippet.
