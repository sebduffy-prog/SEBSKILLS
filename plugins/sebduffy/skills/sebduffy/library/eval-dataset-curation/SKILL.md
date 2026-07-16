---
name: eval-dataset-curation
category: verification
description: >
  Build, version and defend a golden eval set BEFORE trusting any eval number — pin an immutable frozen
  slice with a content hash, run a two-tier contamination check (fast 13-gram overlap then an
  LLM-decontaminator rephrase pass, the HELM/LMSYS method), tag every item with a difficulty band so you
  can slice pass-rate by hard/medium/easy, and hold out a private set the model has never seen. Reach for
  this whenever someone says "our eval set", "golden set", "regression suite", "is this benchmark leaked",
  "why is the score suspiciously high", or before you cite a single eval percentage to a client.
when_to_use:
  - Starting a new eval and you need a trustworthy, versioned golden set rather than an ad-hoc list of prompts
  - A model scores suspiciously high and you suspect the benchmark leaked into training (contamination)
  - You want to report pass-rate sliced by difficulty (hard/medium/easy) instead of one flattering average
  - Freezing v1 of an eval set with a content hash so results stay comparable across model versions
  - Curating a private held-out split that no vendor or crawler has seen, alongside a public dev split
when_not_to_use:
  - Running the eval and scoring model outputs against the set → use llm-judge-bias-audit or an eval harness
  - Detecting live quality drift on production traffic (not curating a fixed set) → use online-eval-drift-monitor
  - Checking whether one factual claim is true → use claim-verifier
  - Auditing experiment/benchmark methodology validity in general → use experiment-validity-audit
keywords: [eval set, golden set, benchmark, contamination, decontamination, n-gram overlap, llm-decontaminator, data leakage, held-out set, difficulty slicing, dataset versioning, content hash, regression suite, test set, helm, lmsys]
similar_to: [llm-judge-bias-audit, online-eval-drift-monitor, experiment-validity-audit, claim-verifier]
inputs_needed:
  - Candidate eval items (JSONL — question/input, expected answer or rubric, any metadata)
  - A reference corpus to check leakage against (training data, web dump, or prior eval versions) when available
  - What the eval is meant to measure, so difficulty bands and slices are meaningful
produces: A versioned golden set (frozen JSONL + manifest with content hash), a contamination report, difficulty-tagged slices, and a private held-out split
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Eval Dataset Curation

Every eval skill assumes a good set already exists. This one builds it. A curated golden set is
**versioned**, **decontaminated**, **difficulty-sliced**, and split into **public dev** vs **private
held-out**. Skip any of those and your eval numbers are decoration.

## When to use

Use this before the first eval run on a new task, and again whenever a score looks too good to be true.
The single most common cause of a suspiciously high benchmark score is contamination — the test items
leaked into pretraining. HELM found 1–6% of test instances contaminated by plain n-gram overlap; LMSYS
showed rephrased leakage can push effective contamination far higher while evading n-gram checks.

## Prerequisites

- **Python 3.9+** for `scripts/contamination_ngram.py` (pure stdlib — no installs).
- A **reference corpus** to check against. Ideal: your actual training data. Realistic fallback: prior
  versions of the eval set, public copies of the benchmark, or a web sample. No corpus at all → you can
  still version + difficulty-slice, but state "contamination: unverified" in the manifest. Never claim a
  set is clean without a check.
- For the rephrase pass (Recipe 3): an LLM API (Claude/GPT) and a sentence-embedding model. Optional but
  it's the only thing that catches paraphrased leakage.
- Reference tools if you want to go deeper: EleutherAI `lm-evaluation-harness` ships a 13-gram
  decontamination utility; `github.com/lm-sys/llm-decontaminator` is the rephrase-detection reference.

## Recipes

### Recipe 1 — Freeze and version the set (do this FIRST)

An eval number is only comparable if the set behind it is byte-identical. Freeze to canonical JSONL and
record a content hash in a manifest. Bump the version on ANY item change; never edit v1 in place.

```bash
# Canonicalise: sorted keys, one item per line, stable order by id.
python3 - <<'PY'
import json, hashlib, pathlib
items = [json.loads(l) for l in open("candidates.jsonl") if l.strip()]
items.sort(key=lambda x: x["id"])                       # stable order
blob = "\n".join(json.dumps(x, sort_keys=True) for x in items)
pathlib.Path("golden_v1.jsonl").write_text(blob + "\n")
h = hashlib.sha256(blob.encode()).hexdigest()
manifest = {"version": "v1", "n_items": len(items), "sha256": h,
            "contamination": "unverified", "created": "2026-07-10"}
pathlib.Path("golden_v1.manifest.json").write_text(json.dumps(manifest, indent=2))
print("frozen", len(items), "items  sha256", h[:16])
PY
git add golden_v1.jsonl golden_v1.manifest.json && git commit -m "eval: freeze golden set v1"
```

Rule: results are only citable next to the manifest `sha256`. Different hash → different set → not
comparable.

### Recipe 2 — Fast contamination screen (13-gram overlap)

The HELM/GPT-3 default. Catches verbatim and near-verbatim leakage cheaply. Run it against every
reference corpus you have.

```bash
python3 scripts/contamination_ngram.py \
  --eval golden_v1.jsonl --ref training_sample.txt \
  --n 13 --field question --out flagged.jsonl
# exits 1 if anything is flagged — drop it straight into CI as a gate.
```

- `--n 13` is the GPT-3 threshold (GPT-4 report used 50 characters; 13 words ≈ that). Lower `n` → more
  false positives, higher → misses short leaks.
- `--threshold` raises the number of shared n-grams needed to flag (use 2–3 for very large web corpora to
  cut noise).
- Review `flagged.jsonl`, **remove or rewrite** the leaked items, re-freeze as v2, update the manifest to
  `"contamination": "13gram-clean vs <corpus>"`.

### Recipe 3 — Rephrase pass (the leakage n-gram misses)

N-gram overlap flagged <1% of *rephrased* contamination in the LMSYS study. If the stakes are high, add
the two-step LLM-decontaminator method:

1. Embed every eval item and every reference doc (e.g. sentence-transformers / an embedding API).
2. For each eval item, retrieve top-k (k≈20) nearest reference docs by cosine similarity.
3. Ask a strong LLM per pair: *"Are these two the same question, possibly reworded/translated? yes/no."*
4. Any `yes` → contaminated; remove or replace.

This catches translation, paraphrase and format-shift leakage. It is more expensive, so run Recipe 2
first and only rephrase-check what survives.

### Recipe 4 — Difficulty banding and slices

One average hides everything. Tag each item `hard | medium | easy` so pass-rate can be sliced. Good
difficulty signals, in order of trust:

- **Empirical**: fraction of a panel of models (or humans) that get it right. <33% right → hard. This is
  the gold standard — derive it once, store it on the item.
- **Proxy** when you have no panel yet: input length, reasoning-step count, rubric strictness, or
  domain-expert tag. Label these `difficulty_source: proxy` so you don't overtrust them.

Store `difficulty` and `difficulty_source` fields on each item. Always report the hard-slice pass-rate
separately — a model can ace easy items and still be useless on the ones that matter.

### Recipe 5 — Public dev vs private held-out split

Anything you publish, paste into a prompt, or send to a vendor is contaminated for next quarter. Split:

- **Dev (public)**: iterate freely, share, tune prompts against it. Expect it to leak.
- **Held-out (private)**: never published, never pasted whole into a model, stored access-controlled.
  Only ever report headline numbers from here. Stratify the split so difficulty and category mix match
  across both (a random split can skew all the hard items into one side).

## Verify

- **Frozen set is reproducible**: re-run Recipe 1's hash on the committed file — it must equal the
  manifest `sha256`.
- **Contamination gate runs**: `python3 scripts/contamination_ngram.py --eval golden_v1.jsonl --ref
  <corpus>` exits 0 only when clean. Confirm it *does* flag a deliberately-injected leaked item (planting
  a known corpus sentence should light up).
- **Slices are non-degenerate**: every difficulty band has enough items to be meaningful (rule of thumb
  ≥30 per band, or report bands as indicative only).
- **Held-out really is held out**: grep your prompts/commits/tickets for held-out item text — zero hits.

## Pitfalls

- **Reporting one flat average.** Always publish the hard-slice number. A 92% that is 99% easy / 40% hard
  is a lie of omission.
- **Trusting n-gram alone.** It misses rephrased/translated leakage (LMSYS: <1% caught). For high-stakes
  claims add Recipe 3.
- **Editing the golden set in place.** Any item change invalidates every prior comparison. Bump the
  version and re-freeze; keep old versions in git.
- **Leaking your own held-out set.** Pasting it into a chat, a PR, or a vendor eval burns it. Treat it
  like a credential.
- **Checking against the wrong corpus.** Contamination is model-specific — a set clean for one model's
  training data may be leaked for another. State *which corpus* the "clean" claim is against.
- **Proxy difficulty as fact.** Length ≠ hardness. Prefer empirical pass-rate; label proxies honestly.
- **Tiny bands.** A "hard" slice of 6 items has a pass-rate that swings 17% per item. Size bands before
  quoting their scores.
