#!/usr/bin/env python3
"""i18n QA: compare target locale files against a source-of-truth locale.

Flags: missing keys, orphan keys, placeholder mismatches, untranslated
(identical-to-source) values, and empty strings. Stdlib only; Python 3.9+.

Usage:
    python3 qa_check.py en.json fr.json de.json
    python3 qa_check.py --strict locales/en.json locales/*.json
Exit code is non-zero when any target has errors (missing key or placeholder
mismatch); orphan/untranslated are warnings unless --strict.
"""
import json, re, sys, argparse

# ICU/i18next {name} & {{name}}; printf %s %d %1$s %(name)s
PLACEHOLDER = re.compile(r"\{\{?[^{}]+\}?\}|%\(?\w*\)?[sdifgeExXoc%]|%\d+\$[sdif]")


def flatten(obj, prefix=""):
    """Flatten nested dict/list into dot-keyed {path: str}."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def placeholders(text):
    """Multiset of placeholder tokens found in a string."""
    if not isinstance(text, str):
        return {}
    counts = {}
    for m in PLACEHOLDER.findall(text):
        counts[m] = counts.get(m, 0) + 1
    return counts


def load(path):
    with open(path, encoding="utf-8") as f:
        return flatten(json.load(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--strict", action="store_true",
                    help="treat orphan/untranslated warnings as errors")
    args = ap.parse_args()

    src = load(args.source)
    had_error = False
    for tgt_path in args.targets:
        if tgt_path == args.source:
            continue
        tgt = load(tgt_path)
        missing = [k for k in src if k not in tgt]
        orphan = [k for k in tgt if k not in src]
        ph_mismatch, untranslated, empty = [], [], []
        for k in src:
            if k not in tgt:
                continue
            if placeholders(src[k]) != placeholders(tgt[k]):
                ph_mismatch.append(k)
            if isinstance(tgt[k], str) and tgt[k].strip() == "":
                empty.append(k)
            elif tgt[k] == src[k] and isinstance(src[k], str) and src[k].strip():
                untranslated.append(k)

        errors = missing or ph_mismatch or empty or (args.strict and (orphan or untranslated))
        print(f"\n=== {tgt_path} ===")
        _report("MISSING keys (in source, absent in target)", missing, True)
        _report("PLACEHOLDER mismatch (tokens differ from source)", ph_mismatch, True)
        _report("EMPTY string values", empty, True)
        _report("ORPHAN keys (in target, not in source)", orphan, args.strict)
        _report("UNTRANSLATED (identical to source)", untranslated, args.strict)
        if not errors:
            print("  OK — no blocking issues")
        had_error = had_error or errors
    sys.exit(1 if had_error else 0)


def _report(label, keys, is_error):
    if not keys:
        return
    tag = "ERROR" if is_error else "warn"
    print(f"  [{tag}] {label}: {len(keys)}")
    for k in keys[:20]:
        print(f"      - {k}")
    if len(keys) > 20:
        print(f"      ... +{len(keys) - 20} more")


if __name__ == "__main__":
    main()
