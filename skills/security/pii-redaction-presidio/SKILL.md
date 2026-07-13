---
name: pii-redaction-presidio
category: security
description: >-
  Detect, redact and anonymize PII/PHI in text at scale with Microsoft Presidio.
  Use when you must strip names, emails, phones, SSNs, credit cards, IPs or PHI
  from logs, datasets, tickets, or LLM prompts before storage or sharing. Wires
  AnalyzerEngine + AnonymizerEngine with per-entity operators (replace/mask/hash/
  encrypt/redact), custom regex + deny-list recognizers, batch processing, and a
  recall evaluation so nothing leaks silently. Reversible pseudonymization via
  encrypt/decrypt included.
when_to_use:
  - Scrubbing PII/PHI from free-text logs, support tickets, chat transcripts, or CSV columns before storage or analytics
  - De-identifying prompts/outputs going to or from an LLM so raw user data never leaves your boundary
  - Building a reversible pseudonymization pipeline (encrypt then decrypt on authorised read-back)
  - Adding org-specific detectors (employee IDs, internal account numbers, project codenames) via regex/deny-list
  - Proving redaction quality with a labelled test set and a recall/leak report before shipping
when_not_to_use:
  - Removing secrets/API keys from a git repo or code — use secrets-hygiene-and-remediation
  - Scanning source for injection/vuln patterns — use sast-semgrep-opengrep
  - Redacting faces/text baked into images or PDFs — use Presidio Image Redactor (out of scope here) or the pdf skill
  - Auditing third-party dependency risk — use supply-chain-sca-audit
keywords:
  - pii
  - phi
  - redaction
  - anonymization
  - presidio
  - de-identification
  - pseudonymization
  - masking
  - hashing
  - gdpr
  - hipaa
  - ner
  - spacy
  - recall
  - data-privacy
similar_to:
  - secrets-hygiene-and-remediation
  - sast-semgrep-opengrep
  - supply-chain-sca-audit
  - container-iac-hardening
  - llm-red-team
inputs_needed: Text corpus / column to scrub (str, list, or CSV); target entity list; per-entity redaction policy; optional labelled sample for evaluation; optional encryption key for reversible mode.
produces: De-identified text with per-entity operators applied; an entity findings report; optional reversible ciphertext + decrypt path; a recall/leak evaluation table.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# PII Redaction with Microsoft Presidio

Two engines do the work: **AnalyzerEngine** finds PII spans (spaCy NER + regex
recognizers + context words), and **AnonymizerEngine** applies a per-entity
*operator* to each span. Golden rule: **never trust default coverage** — pick
entities explicitly, choose an operator each, then run the recall check.

## When to use

Text must be de-identified before storage, sharing, an LLM call, or analytics.
Works on strings, lists, and tabular columns. Non-text PII (image/PDF pixels) or
repo secrets → see `when_not_to_use`.

## Prerequisites

- **Python 3.8+** (this Mac's 3.9 is fine). Use a venv. No API key — all local.
- Install packages + the spaCy model (~560 MB, a SEPARATE step, not a pip dep):
  ```sh
  python3 -m venv .venv && source .venv/bin/activate
  pip install presidio-analyzer presidio-anonymizer
  python -m spacy download en_core_web_lg     # default NER model
  ```
  Missing model = `OSError: [E050] Can't find model 'en_core_web_lg'`. The smaller
  `en_core_web_sm` works but has weaker PERSON/LOCATION recall.
- GPU is optional and unavailable on Apple Silicon (MPS unsupported → CPU).
- Higher accuracy (optional): `pip install "presidio-analyzer[transformers]"` +
  a `TransformersNlpEngine` (e.g. `dslim/bert-base-NER`). Heavier, slower.

## Recipes

### 1. Analyze then anonymize (the core loop)

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

analyzer = AnalyzerEngine()      # loads spaCy model + built-in recognizers once
anonymizer = AnonymizerEngine()

text = "Jane Doe emailed jane@acme.io from 10.0.0.4; card 4095-2609-9393-4932."

# Pick the entities explicitly — don't rely on "detect everything".
results = analyzer.analyze(
    text=text,
    entities=["PERSON", "EMAIL_ADDRESS", "IP_ADDRESS", "CREDIT_CARD"],
    language="en",
)
# results: list[RecognizerResult] each with entity_type, start, end, score

clean = anonymizer.anonymize(text=text, analyzer_results=results)
print(clean.text)
# Jane Doe -> <PERSON>, jane@acme.io -> <EMAIL_ADDRESS>, etc. (default = replace)
```

Omit `entities` to run every recognizer (more recall, more false positives);
filter with `score_threshold=0.4`. Common built-ins: `PERSON`, `EMAIL_ADDRESS`,
`PHONE_NUMBER`, `CREDIT_CARD` (Luhn-checked), `US_SSN`, `IBAN_CODE`, `IP_ADDRESS`,
`LOCATION`, `DATE_TIME`, `URL`, `US_BANK_NUMBER`, `MEDICAL_LICENSE`, `CRYPTO`,
`NRP`. Live list: `analyzer.get_supported_entities(language="en")`.

### 2. Per-entity operators (mask / hash / replace / redact / keep)

This is the payoff — a different policy per entity type:

```python
from presidio_anonymizer.entities import OperatorConfig

operators = {
    "PERSON":        OperatorConfig("replace", {"new_value": "<REDACTED>"}),
    # star the first 12 chars, keep last 4 (from_end=False masks from the start)
    "CREDIT_CARD":   OperatorConfig("mask",
                        {"masking_char": "*", "chars_to_mask": 12, "from_end": False}),
    # consistent pseudonym for joins/dedupe — SAME salt = SAME hash
    "EMAIL_ADDRESS": OperatorConfig("hash", {"hash_type": "sha256", "salt": "PROJECT_PEPPER"}),
    "IP_ADDRESS":    OperatorConfig("redact", {}),
    "DEFAULT":       OperatorConfig("replace", {"new_value": "<PII>"}),  # fallthrough
}

clean = anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
print(clean.text)
```

Operator cheat sheet (from Presidio docs):

| Operator | Effect | Key params |
|----------|--------|-----------|
| `replace` | swap span for a literal | `new_value` (defaults to `<ENTITY_TYPE>`) |
| `redact`  | delete the span | — |
| `mask`    | overwrite chars with a symbol | `masking_char`, `chars_to_mask`, `from_end` |
| `hash`    | salted one-way hash | `hash_type` (`sha256`/`sha512`/`md5`), `salt` |
| `encrypt` | reversible AES ciphertext | `key` (16/24/32-byte string) |
| `keep`    | leave PII untouched | — |

**Referential integrity gotcha:** `hash` now uses a *random* salt by default, so
the same email hashes differently each run. To join records across runs you MUST
pass a fixed `salt`. Store that salt as a secret, not in code.

### 3. Reversible pseudonymization (encrypt → decrypt)

When an authorised reader must recover the original later. `enc.items` carries the
spans needed to reverse; `KEY` is a 16/24/32-byte AES key from a secret store —
never hardcoded. Lost key = unrecoverable; leaked key = redaction is worthless.

```python
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from presidio_anonymizer.entities import OperatorConfig
import os
KEY = os.environ["PRESIDIO_KEY"]

enc = AnonymizerEngine().anonymize(text=text, analyzer_results=results,
        operators={"DEFAULT": OperatorConfig("encrypt", {"key": KEY})})
back = DeanonymizeEngine().deanonymize(text=enc.text, entities=enc.items,
        operators={"DEFAULT": OperatorConfig("decrypt", {"key": KEY})})
assert text == back.text
```

### 4. Custom recognizers (org-specific PII)

Built-ins miss internal identifiers. Add regex (`context` words boost score) and
deny-list recognizers, then register them:

```python
from presidio_analyzer import Pattern, PatternRecognizer

emp_id = PatternRecognizer(supported_entity="EMPLOYEE_ID",
    patterns=[Pattern(name="emp_id", regex=r"\bEMP-\d{5}\b", score=0.85)],
    context=["employee", "staff", "badge"])
codenames = PatternRecognizer(supported_entity="PROJECT_CODENAME",
    deny_list=["Bluejay", "Redstone", "Orchid"])

analyzer.registry.add_recognizer(emp_id)
analyzer.registry.add_recognizer(codenames)
results = analyzer.analyze(text="Badge EMP-48213 works on Orchid.",
    entities=["EMPLOYEE_ID", "PROJECT_CODENAME"], language="en")
```

### 5. At scale — batch + CSV columns

Use `BatchAnalyzerEngine` / `BatchAnonymizerEngine` so the model loads once and
iterates, instead of re-instantiating per row:

```python
from presidio_analyzer import BatchAnalyzerEngine
from presidio_anonymizer import BatchAnonymizerEngine

batch_analyzer = BatchAnalyzerEngine(analyzer_engine=analyzer)
texts = ["Call Bob at 212-555-5555", "ssn 078-05-1120", "..."]

results = batch_analyzer.analyze_iterator(texts, language="en")   # generator
clean = BatchAnonymizerEngine().anonymize_list(
    texts=texts, recognizer_results_list=list(results),
    operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<PII>"})},
)
```

Map DataFrame cells through the batch iterator, not a `for` loop with fresh
engines. For huge corpora run it as a Docker service using the official
`mcr.microsoft.com/presidio-analyzer` / `presidio-anonymizer` images (check the
tag list for the most recent release before pinning):

```sh
docker run -d -p 5002:3000 mcr.microsoft.com/presidio-analyzer:latest
curl -s localhost:5002/analyze -H 'content-type: application/json' \
  -d '{"text":"Bob at 212-555-5555","language":"en"}'
```

### 6. Recall evaluation — prove nothing leaks

Redaction quality is judged by **recall** (fraction of true PII caught). A missed
span is a leak, so recall matters more than precision here. Build a tiny labelled
set of `(text, [char spans that ARE PII])` and measure token-level catch rate:

```python
def measure_recall(analyzer, samples, entities, language="en"):
    hit = total = 0; misses = []
    for text, gold in samples:                  # gold: list[(start, end)]
        covered = [(r.start, r.end)
                   for r in analyzer.analyze(text=text, entities=entities, language=language)]
        for gs, ge in gold:
            total += 1
            if any(fs <= gs and ge <= fe for fs, fe in covered): hit += 1
            else: misses.append(text[gs:ge])
    return (hit / total if total else 1.0), misses

samples = [
    ("Reach Priya Nair at priya@acme.io", [(6, 16), (20, 33)]),   # PERSON, EMAIL
    ("SSN 078-05-1120 on file", [(4, 15)]),
]
recall, leaks = measure_recall(analyzer, samples, ["PERSON", "EMAIL_ADDRESS", "US_SSN"])
print(f"recall={recall:.1%}  leaked={leaks}")
```

Ship only when recall clears your bar (e.g. 0.95) **and** `leaks` is empty for the
promised entity types. Raise recall by lowering `score_threshold`, adding custom
recognizers (Recipe 4), or the transformers engine. For a rigorous benchmark, the
`presidio-evaluator` package generates synthetic labelled data and per-entity P/R/F.

## Verify

```sh
python - <<'PY'
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
a, an = AnalyzerEngine(), AnonymizerEngine()
t = "I am John Smith, ssn 078-05-1120, john@x.io"
r = a.analyze(text=t, entities=["PERSON","US_SSN","EMAIL_ADDRESS"], language="en")
out = an.anonymize(text=t, analyzer_results=r).text
assert "078-05-1120" not in out and "john@x.io" not in out, "LEAK: "+out
print("OK ->", out)
PY
```
Passing = the SSN and email are absent from the output. If it errors on model
load, re-run `python -m spacy download en_core_web_lg`.

## Pitfalls

- **Trusting defaults = silent leaks.** spaCy misses unusual names, foreign
  formats, and typo'd emails. Always run Recipe 6 on a representative sample.
- **Overlapping spans.** When two recognizers hit the same text Presidio keeps the
  higher-confidence one; a low-score custom regex gets dropped. Bump its `score`
  or add `context` words.
- **Random hash salt.** Default `hash` salts randomly — same input hashes
  differently each run. Pass a fixed (secret) `salt` whenever you need joins.
- **Offsets shift after anonymization.** `replace`/`redact` change string length,
  so original `start/end` no longer map to the clean text. Re-analyze the cleaned
  text if you need positions; keep `result.items` for reversibility.
- **Encryption key handling.** `encrypt` needs a 16/24/32-byte key from env/secret
  manager — never hardcode it. Lost key = unrecoverable data; leaked key = no
  protection.
- **Redaction ≠ anonymity.** Quasi-identifiers (title + city + DOB) can
  re-identify after direct PII is gone. Legal anonymity may also need
  k-anonymity/generalization, which Presidio does not provide.
- **CSV structure is invisible to it.** Presidio scans free text, not schema. Feed
  it cell values (Recipe 5) or hard-mask known-sensitive columns directly.
