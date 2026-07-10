---
name: i18n-localization-qa
category: documents
description: >
  QA a localisation before it ships. Validate that every translated string keeps its
  placeholders and ICU plural/select branches, find missing or orphaned or stale
  (identical-to-source) keys across locale files, check RTL languages and locale
  number/date/currency formatting, and enforce glossary and do-not-translate consistency.
  Use for i18next/gettext/ICU/Fluent/ARB/XLIFF/JSON message catalogs.
when_to_use:
  - A PR adds or changes translation files (JSON/YAML/PO/XLIFF/ARB) and you must gate it
  - A new locale was machine- or human-translated and needs sign-off before release
  - Runtime shows "{name}" literals, wrong plurals, mojibake, or broken RTL layout
  - You need a repeatable CI check for placeholder parity and missing keys
  - A glossary/brand term must be translated (or NOT translated) consistently everywhere
when_not_to_use:
  - You need to PRODUCE translations, not check them — use a translation service/LLM or co-op-translator
  - Extracting strings from source into a catalog — use an i18n extractor (i18next-parser, babel, formatjs extract)
  - Pure copy editing of the source language — use a proofreading/style pass, not this QA
  - Building the i18n runtime itself — use the framework docs (i18next, react-intl, next-intl)
keywords: [i18n, l10n, localization, translation-qa, icu, messageformat, plurals, placeholders, rtl, gettext, xliff, glossary, pseudolocalization, cldr, missing-strings]
similar_to: [contract-review, meeting-intelligence]
inputs_needed: Source-of-truth locale file(s) plus one or more target locale files (JSON/PO/XLIFF/ARB); optionally a glossary and do-not-translate list.
produces: A QA report listing missing/orphan/stale keys, placeholder & plural mismatches, RTL/format issues, and glossary violations — plus a CI-ready pass/fail exit code.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# i18n Localisation QA

Catch the localisation bugs that ship silently: a dropped `{count}`, a plural that only
covers English, a key present in `en` but missing in `ar`, a brand term someone
"helpfully" translated. This skill is a checklist plus a runnable validator.

## When to use

Run this whenever translated message catalogs change or a new locale is added, before it
reaches users. It complements a translation-*producing* tool like `co-op-translator` — that
tool writes the strings, this one verifies them.

## Prerequisites

- Locale files in a parseable format. The bundled script handles nested/flat **JSON**
  (i18next, react-intl, next-intl, ARB). For **.po/.pot** convert first:
  `msgcat --to-code=UTF-8 fr.po` or `python3 -c "import polib"` if `polib` is installed.
  For **XLIFF** extract `<source>`/`<target>` pairs with an XML parser.
- Python 3 (stdlib only — no pip needed for the core check).
- A source-of-truth locale (usually `en`) that defines the complete key set.

## Recipes

### 1. Placeholder parity + missing/orphan/stale keys (the core check)

`scripts/qa_check.py` flattens both files to dot-keyed strings and compares. It flags
**missing** keys, **orphan** keys (target-only), **placeholder mismatches**
(`{name}`, `{{name}}`, `%s`, `%d`, `%1$s`, `%(name)s` counted as multisets), **empty**
values, and **untranslated** values (byte-identical to source).

```bash
python3 scripts/qa_check.py en.json fr.json de.json es.json   # exit 1 on any error
python3 scripts/qa_check.py --strict en.json locales/*.json    # orphan+stale also fail
```

A placeholder mismatch is the highest-value catch: it finds `{naem}` typos, dropped
tokens, and cases where a translator "localised" `%d` into `%D`. These crash or render
literally at runtime.

### 2. ICU MessageFormat: validate plural / select branches

ICU plural categories come from **CLDR**: `zero one two few many other`, plus exact
matches `=0 =1`. `other` is mandatory; `#` prints the (offset) number. `select` is for
enumerations (e.g. gender); `selectordinal` for "1st/2nd/3rd".

```
{count, plural, =0 {No items} one {# item} other {# items}}
{gender, select, female {She} male {He} other {They}}
```

Each **target language needs the categories CLDR requires for it**, not a copy of English's
`one/other`. Arabic needs all six; Polish needs `one/few/many/other`; Japanese needs only
`other`. Validate by parsing and checking against CLDR:

```bash
# Node one-liner using the reference parser (npm i @formatjs/icu-messageformat-parser)
node -e '
const {parse}=require("@formatjs/icu-messageformat-parser");
const fs=require("fs"), msgs=JSON.parse(fs.readFileSync(process.argv[1]));
for(const [k,v] of Object.entries(msgs)){
  if(typeof v!=="string"||!v.includes("{"))continue;
  try{parse(v)}catch(e){console.log("SYNTAX",k,e.message)}
}' fr.json
```

```python
# Which plural categories does a locale legitimately need? (pip install babel)
from babel import Locale
print(Locale.parse("ar").plural_form.tags)  # {'zero','one','two','few','many','other'}
print(Locale.parse("ja").plural_form.tags)  # {'other'}
```

Rule of thumb: if a target catalog's plural block has *fewer* categories than
`Locale.plural_form.tags` for that locale, some counts fall through to `other` and read
wrong. Missing `other` entirely is a hard error.

### 3. RTL languages

RTL locales: **Arabic (ar), Hebrew (he), Persian/Farsi (fa), Urdu (ur)** and their
variants. Checks:

- `<html dir>` (or the framework equivalent) must switch to `rtl` for these — grep for
  hardcoded `dir="ltr"`.
- Prefer CSS **logical properties** (`margin-inline-start`, `padding-inline-end`,
  `text-align: start`) over `left`/`right`; grep the stylesheet for physical props used
  near localised content.
- Strings mixing LTR runs (URLs, numbers, code) inside RTL text may need Unicode isolates
  `⁦…⁩` (FSI/PDI) or `<bdi>` to avoid scrambled ordering.

```bash
grep -REn 'margin-(left|right)|padding-(left|right)|text-align:\s*(left|right)' src/ \
  | head   # candidates to convert to logical properties
```

### 4. Locale number / date / currency formatting

Never hardcode `,`/`.` separators or `MM/DD/YYYY`. Verify via `Intl` (or `babel`):

```python
from babel.numbers import format_currency, format_decimal
from babel.dates import format_date
import datetime as dt
for loc in ("en_US","de_DE","fr_FR","ar_EG"):
    print(loc,
          format_decimal(1234567.89, locale=loc),
          format_currency(1234.5, "EUR", locale=loc),
          format_date(dt.date(2026,7,9), format="long", locale=loc))
# de_DE -> 1.234.567,89 ;  fr_FR -> 1 234 567,89 ;  ar_EG -> ١٬٢٣٤٬٥٦٧٫٨٩
```

If the app builds these strings by concatenation instead of `Intl.NumberFormat` /
`Intl.DateTimeFormat`, flag it — that is the real bug, not the translation.

### 5. Glossary & do-not-translate consistency

Given a CSV `term,fr,de,...` glossary and a DNT list (brand names, product names, code):

```python
import csv, json, re
glossary = {r["term"]: r for r in csv.DictReader(open("glossary.csv"))}
tgt = json.load(open("fr.json")); lang = "fr"
def walk(o, p=""):
    if isinstance(o, dict):
        for k,v in o.items(): yield from walk(v, f"{p}.{k}" if p else k)
    elif isinstance(o, str): yield p, o
for key, text in walk(tgt):
    for term, row in glossary.items():
        want = row.get(lang, "").strip()
        if want and re.search(rf"\b{re.escape(term)}\b", text, re.I) \
                and want.lower() not in text.lower():
            print(f"GLOSSARY {key}: source term '{term}' should map to '{want}'")
```

For **do-not-translate** terms, assert the exact token still appears verbatim in every
target (e.g. the string still contains `Acme Cloud`, untranslated).

### 6. Pseudolocalization (pre-flight, before real translation exists)

Generate a fake locale to expose un-externalised strings and truncation early:
`Ĥéļļö` + 40% padding + brackets. If a UI string doesn't change under pseudo, it wasn't
externalised. Tools: `pseudo-localization` (npm), `pseudolocalize`, or a 20-line map.

## Verify

```bash
# Self-test the bundled validator on fixtures:
python3 scripts/qa_check.py en.json fr.json ; echo "exit=$?"   # non-zero => issues found
```

A clean run prints `OK — no blocking issues` per target and exits 0. Wire the same command
into CI as a required check so a broken placeholder can never merge.

## Pitfalls

- **Comparing against the wrong source.** The source-of-truth catalog must be complete;
  if `en` is itself missing keys the diff is meaningless. Pick the canonical locale.
- **Order/whitespace-only "differences."** Flatten and compare by key, not by raw file
  diff — reordered JSON is not a real change.
- **Copying English plural shape to every locale.** `one/other` is wrong for Arabic,
  Russian, Polish, Welsh, etc. Always check `Locale.plural_form.tags`.
- **`{{name}}` vs `{name}`.** i18next uses double braces; ICU/react-intl use single.
  Mixing them silently breaks interpolation — the validator counts the exact token, so a
  framework mismatch surfaces as a placeholder mismatch. Know which one your app uses.
- **Untranslated ≠ always wrong.** Proper nouns and short shared words (e.g. "OK",
  "Menu") legitimately match the source; keep an allow-list so `--strict` doesn't cry wolf.
- **Mojibake / BOM.** Read every file as UTF-8; a Latin-1 decode turns `é` into `Ã©`.
  Reject non-UTF-8 catalogs rather than "fixing" them downstream.
- **HTML/format-string injection in translations.** A target string that adds `<b>` or an
  extra `%s` can break rendering or crash `printf`. Placeholder-count parity catches the
  extra `%s`; scan for stray tags separately if your strings allow markup.
