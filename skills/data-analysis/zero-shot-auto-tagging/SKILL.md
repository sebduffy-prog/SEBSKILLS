---
name: zero-shot-auto-tagging
category: data-analysis
description: >
  Auto-tag and classify a large document collection into a KNOWN taxonomy without
  labelled training data. Picks the right engine per job — HF zero-shot NLI
  (bart-large-mnli) for a handful of labels, GLiNER for span/entity extraction over
  arbitrary types, SetFit/FastFit few-shot when you can spare 8 examples per class,
  or an LLM labeller for messy nuance — then adds confidence thresholds, multi-label
  routing, and an abstain bucket. Use when the user says "tag these documents",
  "classify this corpus", "route tickets by topic", "label without training data",
  "zero-shot classification", "apply my taxonomy to N files", or "which model to
  auto-categorise text".
when_to_use:
  - "You have a fixed set of category labels (a taxonomy) and thousands of texts to sort into them with no labelled training set"
  - "Routing support tickets, emails, docs, or feedback to topics/teams by content"
  - "Extracting typed spans (products, skills, orgs, PII) where the type list is known but not a fixed gazetteer — use GLiNER"
  - "You can hand-write ~8 examples per class and want a fast, cheap CPU classifier that beats raw zero-shot — use SetFit/FastFit"
  - "Multi-label tagging where a doc can carry several tags, each with its own threshold"
  - "You need a confidence score + abstain/'other' bucket rather than a forced single label"
when_not_to_use:
  - "Labels are unknown / you want to DISCOVER themes — use embedding-corpus-clustering instead"
  - "You just need a semantic nearest-neighbour index, not discrete tags — use incremental-content-index / embedding-corpus-clustering"
  - "The text isn't extracted yet (PDFs, HTML, DOCX) — run bulk-content-extraction first, then this"
  - "You're detecting file TYPE (mime/binary) not topic — use magika-file-triage"
  - "Sentiment polarity of news specifically — news-sentiment-api is purpose-built"
keywords: [zero-shot, auto-tagging, text-classification, taxonomy, nli, bart-large-mnli, gliner, setfit, fastfit, few-shot, multi-label, confidence-threshold, ner, span-extraction, document-routing, entailment, transformers, huggingface, abstain]
similar_to: [embedding-corpus-clustering, magika-file-triage, incremental-content-index, bulk-content-extraction, news-sentiment-api]
inputs_needed: The list of category labels (the taxonomy); a sample of the texts (path/glob or column); whether single- or multi-label; per-label confidence tolerance; and whether GPU is available (else CPU-first models).
produces: A tagged dataset (JSONL/CSV) with per-row labels + confidence scores + abstain flag, plus a reusable scoring script and a chosen-engine rationale.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Zero-Shot Auto-Tagging

Sort a corpus into a **known** taxonomy without training data. The whole game is
picking the cheapest engine that clears your accuracy bar, then wrapping it in
thresholds + an abstain bucket so wrong-but-confident tags don't leak downstream.

## When to use

You already know the labels (topics, teams, entity types) and have too many texts
to label by hand. If you DON'T know the labels yet, stop — cluster first
(`embedding-corpus-clustering`) to discover them, then come back here.

## Prerequisites

- **Python 3.9+**. No GPU required for GLiNER/SetFit; NLI models are ~1.6 GB and
  CPU-slow (~1–3 docs/s on bart-large) so batch or use a distilled model.
- Installs (pick per engine — don't install all four):
  ```bash
  pip install -U transformers torch            # NLI zero-shot (bart-large-mnli)
  pip install -U gliner                         # span/entity extraction
  pip install -U setfit                         # few-shot (needs ~8 examples/class)
  # LLM labeller: use your existing Claude/OpenAI SDK — no extra install
  ```
- First run downloads weights from the HF hub (needs network; then cached in
  `~/.cache/huggingface`). Set `HF_HUB_OFFLINE=1` to pin to cache afterwards.

## Choose the engine (decision rule)

| Situation | Engine | Why |
|---|---|---|
| ≤ ~15 whole-document labels, no examples | **NLI zero-shot** (`bart-large-mnli`) | True zero-shot, just pass label names |
| Extract typed **spans** (any type list) | **GLiNER** | Entity-level, CPU-fast, arbitrary labels |
| You can write ~8 examples/class | **SetFit** (or FastFit >10 classes) | 5×+ faster inference, beats raw zero-shot |
| Nuance, sarcasm, long context, rationale | **LLM labeller** | Highest quality, priciest; cache prompts |

Rule of thumb: prototype with NLI to prove the taxonomy works, then, if it's too
slow or borderline, promote to SetFit (label a few) or an LLM for the hard classes.

## Recipe A — NLI zero-shot, multi-label + threshold + abstain

```python
from transformers import pipeline

clf = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
LABELS = ["billing", "bug report", "feature request", "account access", "praise"]
THRESHOLD, MULTI = 0.60, True   # per-label prob cut; True = independent scores

def tag(text):
    out = clf(text, LABELS, multi_label=MULTI)
    pairs = list(zip(out["labels"], out["scores"]))          # sorted desc
    kept = [{"label": l, "score": round(s, 3)} for l, s in pairs if s >= THRESHOLD]
    return {"text": text, "tags": kept, "abstain": not kept, "top": pairs[0][0]}

print(tag("I was charged twice this month and can't log in"))
```

- `multi_label=True` scores each label independently (a doc can be billing AND
  account-access). `False` softmaxes across labels → forced single winner.
- **Abstain** (`kept == []`) is a feature: route those to human review, don't force.
- Batch by passing a list of texts; set `batch_size=8` and `device=0` if you have a
  GPU. For speed on CPU swap in `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` (smaller,
  often more accurate than bart-large-mnli).

## Recipe B — GLiNER for span/entity extraction

Use when you want the *spans* ("Acme Corp", "Series B") not a whole-doc label.

```python
from gliner import GLiNER

model = GLiNER.from_pretrained("gliner-community/gliner_medium-v2.5")
labels = ["company", "funding round", "person", "product", "location"]
text = "Acme Corp raised a Series B led by Jane Doe in Berlin."

for e in model.predict_entities(text, labels, threshold=0.5):
    print(e["label"], "->", e["text"], round(e["score"], 3))
```

- Labels are arbitrary natural-language type names — no retraining. `threshold`
  trades recall for precision. CPU-friendly; medium model ~0.5 GB.
- For PII specifically use `knowledgator/gliner-pii-large-v1.0`.

## Recipe C — SetFit few-shot (when zero-shot is borderline)

SetFit turns your label names into synthetic examples, so you can start with **zero**
real data and improve by adding a handful of real ones.

```python
from datasets import Dataset
from setfit import SetFitModel, Trainer, get_templated_dataset

candidate_labels = ["sadness", "joy", "love", "anger", "fear", "surprise"]
# Synthesises sample_size examples/class from the label names (template-based)
train_ds = get_templated_dataset(Dataset.from_dict({}),
                                 candidate_labels=candidate_labels, sample_size=8)

model = SetFitModel.from_pretrained("sentence-transformers/paraphrase-mpnet-base-v2")
Trainer(model=model, train_dataset=train_ds).train()

preds = model.predict(["I can't stop smiling today"])   # -> ['joy']
probs = model.predict_proba(["I can't stop smiling today"])  # confidence per class
```

- Add real labelled rows to `train_ds` as you get them — accuracy climbs fast.
- **FastFit** (`pip install fast-fit`) is the better pick when you have **>10
  classes** (SetFit gets intractable to train at that scale).

## Recipe D — LLM labeller (hardest classes / nuance)

Cheapest reliable pattern: constrain output to your taxonomy + a confidence + an
`"other"` escape hatch, and **prompt-cache** the taxonomy block (see `claude-api`).

```
System (cache this): "You tag support messages. Allowed tags ONLY: [billing, bug,
feature, access, praise, other]. Return JSON {tags:[...], confidence:0-1}. Use
'other' if none fit. Never invent a tag."
User: <the message>
```

Validate every response against the allowed set before writing it — an LLM will
occasionally hallucinate a tag; reject and re-ask or fall back to `other`.

## Batch a whole corpus → JSONL

```python
import json, glob
rows = (open(p).read() for p in glob.glob("corpus/*.txt"))
with open("tagged.jsonl", "w") as out:
    for r in rows:
        out.write(json.dumps(tag(r)) + "\n")   # tag() from Recipe A
```

Keep the raw scores in the output — downstream you'll want to re-threshold without
re-running the model.

## Verify

- **Eyeball a stratified sample**: pull 20 rows per tag + 20 abstains and read them.
  Precision problems show up as confident-but-wrong; recall problems hide in abstain.
- **Sanity numbers**: tag distribution shouldn't be ~uniform (a sign the model is
  guessing) nor 95% one class (a sign of a dominant-prior collapse — raise threshold).
- **Threshold sweep**: if you have even 50 hand-labelled rows, plot precision/recall
  across thresholds and pick the knee — don't hardcode 0.5 blindly.
- **Multi-label leakage**: check the mean tags-per-doc; if every doc gets 4 tags your
  threshold is too low.

## Pitfalls

- **Label wording matters in zero-shot.** "feature request" beats "feat"; the model
  reads the label as English. Rephrase vague labels into a short hypothesis-friendly
  phrase and re-test — it can swing accuracy 10–20 pts.
- **`multi_label=False` forces a winner even for off-taxonomy text.** Always add an
  abstain rule (top score < threshold → "other"), else garbage gets a confident tag.
- **bart-large-mnli is slow on CPU.** For big corpora use a deberta-v3 zeroshot
  distilled model or move to SetFit — don't grind bart-large over 100k docs.
- **GLiNER labels ≠ NLI labels.** GLiNER extracts spans; if you feed it whole-doc
  topic labels you'll get nonsense. Match the engine to the granularity.
- **Cache the model, not just weights.** Instantiate the pipeline/model ONCE and reuse
  it across the batch; re-creating it per doc is the #1 speed bug.
- **Never fabricate tags to fill gaps.** Abstain is correct output — route it to a human
  queue rather than forcing a label the model didn't support.
- **Extract text first.** These models want clean text; feed them raw PDF/HTML bytes and
  they'll tag boilerplate. Run `bulk-content-extraction` upstream.
