---
name: federated-knowledge-memory
category: building-agents
description: >-
  Build a shared, append-only, provenance-tracked knowledge store for a whole
  skill library or agent fleet — any contributor's LLM (any provider) writes
  CANDIDATE facts, a verification gate promotes them to TRUSTED via cross-provider
  quorum / steward sign-off / execution / evidence, and every skill reads ranked
  trusted context. Use when session knowledge keeps dying, when multiple agents
  or models should compound a common memory, or when you need bi-temporal +
  W3C-PROV provenance, PII-safe ingest, and conflict-preserving reads. Ships a
  stdlib SQLite store adapter + write/promote/query API you can run today.
when_to_use:
  - Facts learned in one session (canonical host, gotcha, decision) vanish and get relearned
  - Multiple agents or multiple model providers should share and compound one memory
  - You want a trust gate before a model-asserted fact becomes library-wide truth
  - You need provenance (who / which model / when / source) and time-travel on every fact
  - Skills need ranked shared context injected at prompt time, not ad-hoc scraping
when_not_to_use:
  - Single-agent scratch memory for one run — use a plain JSON file or mem0 local
  - Full temporal knowledge GRAPH with entity resolution — use getzep/graphiti instead
  - Vector recall over documents for RAG answers — use a rag/* retrieval skill
  - Config/settings that never need provenance or a trust gate — use a config file
keywords:
  - knowledge-base
  - append-only
  - provenance
  - w3c-prov
  - bi-temporal
  - cross-provider-quorum
  - verification-gate
  - candidate-trusted
  - dedup
  - pii-presidio
  - shared-memory
  - claim-log
  - mem0
  - graphiti
  - content-hash
similar_to:
  - autosuggestive-schema-builder
  - mcp-builder
inputs_needed: >-
  A writable store path (SQLite/JSONL); each write needs subject/predicate/object
  + who/model/provider; optional evidence URI, valid_from/valid_to, steward id.
produces: >-
  A queryable knowledge.db of provenance-tracked claims, a candidate→trusted
  promotion audit trail, and a query() helper returning ranked trusted context.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Federated Knowledge Memory

A shared brain for a skill library. Knowledge stops dying in one session: any
contributor's LLM — Claude, GPT, Gemini, Mistral — appends **candidate** facts;
a **verification gate** promotes them to **trusted**; every skill reads the
trusted set as ranked context. The trust signal that scales without a human in
the loop is **cross-provider quorum**: when models from *different companies*
independently assert the same fact, that agreement is evidence in itself.

## When to use

Reach for this the moment a second agent, a second model, or a second session
needs to build on what the first one learned — and you want that shared memory
to be auditable and trustworthy rather than a wiki anyone can poison.

## Prerequisites

- `python3` (3.9+, stdlib only — `scripts/kb.py` needs no pip install).
- Optional PROD upgrades: `presidio-analyzer` for real PII detection, an
  embedding model for semantic dedup, a vector store for scale.
- Grounding: model after `mem0` (add/search + dedup), `getzep/graphiti`
  (bi-temporal edges, episodes as ground truth, invalidate-don't-delete), and
  W3C PROV (Entity / Activity / Agent → wasGeneratedBy / wasAttributedTo).

## Mechanism / Steps

The design is an **append-only claim log**. Nothing is ever mutated in place;
trust and validity are *derived* from immutable events. Three tables:

| table | immutable row = | carries |
|-------|-----------------|---------|
| `claims` | one distinct fact, keyed by content hash | subject/predicate/object, bi-temporal `valid_from`/`valid_to`, `ingested_at`, source, skill |
| `attestations` | one independent assertion of a claim | agent, **model**, **provider** (company), evidence, at |
| `events` | a promote / retract decision | kind, reason, actor, at |

Map to W3C PROV: a claim is a **prov:Entity**, an attestation is a
**prov:Activity** `wasAttributedTo` a **prov:Agent** (the model), a promote
event is the Activity that `wasGeneratedBy` the gate.

### 1. Write (ingest a candidate) — any model, any provider

```bash
python3 scripts/kb.py --db knowledge.db write \
  --subject "vccp-mmm" --predicate "canonical-host" --object "Railway" \
  --agent buildbot --model opus-4.8 --provider anthropic --source-uri "$PR_URL"
```

On ingest the store, in order: **PII-scans** subject/predicate/object (regex
now; swap Presidio in PROD) and blocks on a hit; **content-hashes** the
normalized triple for exact dedup; falls back to a **near-dup** key
(punctuation-insensitive; PROD = embedding cosine > 0.92) so `Railway!` folds
into `Railway`; then appends the claim (if new) plus one attestation. Same fact
from a second model just adds an attestation — the claim row is written once.

### 2. Promote (the gate) — candidate → trusted

Run as a periodic job (cron) or inline after a batch. The gate passes on **any**
one of four rules, checked in order:

```bash
python3 scripts/kb.py --db knowledge.db promote --cid <cid> --quorum 2
```

1. **Cross-provider quorum** — ≥N *distinct providers* attested (default 2).
   Two Anthropic models do **not** pass; Anthropic + OpenAI do.
2. **Steward sign-off** — `--steward seb.duffy` (a trusted human/role).
3. **Execution-verified** — `--executed` (the fact was proven by running code).
4. **Evidence-linked** — an attestation carried an `--evidence` URI.

No rule passes → the claim stays `held` (candidate) and is never returned to
readers. Every promotion writes an `events` row with its reason, so trust is
fully auditable. `retract` appends a tombstone event; the claim history stays.

### 3. Query (ranked trusted context) — what skills call

```bash
python3 scripts/kb.py --db knowledge.db query --predicate canonical-host
```

Returns `trusted_only` by default, ranked by **#distinct providers, then
recency**. Conflicts are **kept, not resolved**: two trusted claims with the
same subject+predicate but different objects both come back, highest-authority
first, so the caller sees the disagreement instead of a silent overwrite
(Graphiti's invalidate-don't-delete stance). Import the helper to inject context:

```python
from kb import connect, query
ctx = query(connect("knowledge.db"), predicate="canonical-host", limit=10)
# feed `ctx` into the skill's system prompt as ranked shared facts
```

### 4. Wire it into the library

- **Write hook**: at the end of a skill run, append what it learned (decision,
  gotcha, canonical fact) as a candidate tagged with `--skill <name>`.
- **Promote job**: schedule `promote` over all `held` cids (see `schedule`/cron).
- **Read hook**: every skill calls `query()` for its domain at startup and
  prepends the trusted facts. The library's knowledge now compounds.

## Verify

```bash
cd scripts && rm -f t.db
python3 kb.py --db t.db write --subject s --predicate p --object o \
  --agent a --model opus --provider anthropic          # -> new
CID=$(python3 kb.py --db t.db query --subject s --all | \
  python3 -c "import sys,json;print(json.load(sys.stdin)[0]['cid'])")
python3 kb.py --db t.db promote --cid $CID             # -> held (1 provider)
python3 kb.py --db t.db write --subject s --predicate p --object o \
  --agent b --model gpt5 --provider openai             # -> deduped (2nd provider)
python3 kb.py --db t.db promote --cid $CID             # -> promoted:cross-provider-quorum:2
python3 kb.py --db t.db write --subject x --predicate email \
  --object me@x.com --agent a --model m --provider anthropic  # -> blocked-pii
```

Expect: single provider holds, second *distinct* provider promotes, PII blocks,
and `query` (trusted-only) returns the fact with three-way conflicts preserved.

## Pitfalls

- **Same-company quorum is not quorum.** Two of your own Claude runs agreeing
  proves nothing (correlated errors). The gate counts *distinct providers* on
  purpose — keep it that way, or quorum becomes an echo chamber.
- **Regex PII is a stopgap.** It catches emails/cards/SSNs, not names or context.
  Swap in Presidio (`AnalyzerEngine`) before ingesting anything user-facing.
- **Near-dup is punctuation-only here.** `React app` vs `React application`
  won't fold. Add embeddings for real semantic dedup at the marked PROD seam.
- **Never resolve conflicts by overwrite.** Keeping both trusted claims is the
  feature — collapsing them hides that two providers disagree.
- **Don't skip the gate for convenience.** Reading candidates as if trusted is
  how a single hallucinating model poisons the whole library.
- **Bi-temporal ≠ transaction time.** `valid_from/valid_to` is when the fact is
  true in the world; `ingested_at` is when you learned it. Don't conflate them.
- **This is a claim store, not a graph.** No entity resolution or multi-hop —
  if you need those, promote trusted claims out into `getzep/graphiti`.
