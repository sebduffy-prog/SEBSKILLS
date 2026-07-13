#!/usr/bin/env python3
"""Reproducible Insight Workbench — provenance auditor.

Binds every headline stat/figure in a deliverable to the exact dataset + command
that produced it, RE-RUNS each binding, and flags:
  - MISMATCH  : the command no longer emits the recorded value (stat has drifted)
  - ERROR     : the command failed / dataset missing (stat is unreproducible)
  - UNTRACEABLE numbers found in the deliverable with NO manifest binding

Emits a machine-readable audit trail (JSON) so a pitch stat survives a client challenge.

Stdlib only. Works on macOS system python3 (3.9). No pip, no network.

Manifest schema (JSON):
{
  "claims": [
    {
      "id": "reach-uplift",                 # required, unique
      "value": "37%",                        # the headline number as it appears
      "appears_as": ["37%", "37 per cent"],  # optional extra surface forms (default: [value])
      "dataset": "data/campaign.csv",        # optional file(s); str or list; sha256'd
      "command": "python3 queries/reach.py", # required unless value is asserted-only
      "expect_contains": "37%",              # substring the command stdout must contain
                                             #   (default: value)
      "description": "Incremental reach uplift vs control",  # plain-language provenance
      "citation": "GWI wave Q2 2026, n=1504"                 # optional source label
    }
  ]
}

Usage:
  python3 audit.py manifest.json                       # re-run + verify all bindings
  python3 audit.py manifest.json --deliverable deck.txt # + scan for untraceable numbers
  python3 audit.py manifest.json --json                # machine-readable to stdout
  python3 audit.py manifest.json --out audit_trail.json
  python3 audit.py manifest.json --timeout 120

Exit codes (CI-gateable):
  0  all bindings reproduce, no untraceable numbers
  2  untraceable number(s) in deliverable
  3  binding MISMATCH (recorded value no longer reproduces)
  4  binding ERROR (command failed / dataset missing)
  1  usage / manifest error
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

# --- number extraction: percentages, currency, decimals, thousands, plain ints ---
NUMBER_RE = re.compile(
    r"""
    (?<![\w.])                       # not mid-word / mid-decimal
    (?:[£$€]\s?)?                     # optional currency
    \d{1,3}(?:,\d{3})+(?:\.\d+)?     # 1,234 / 1,234.5
    | (?<![\w.])(?:[£$€]\s?)?\d+(?:\.\d+)?%?   # 37 / 37.5 / 37% / £5
    """,
    re.VERBOSE,
)

# tokens too generic to treat as a "headline stat" needing a binding
STOPWORDS = {"0", "1", "2", "3", "4", "5", "100"}


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as exc:
        return "ERROR:%s" % exc


def git_commit(cwd):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def normalize(tok):
    """Loose comparison form: strip currency/commas/spaces, lowercase."""
    return re.sub(r"[£$€,\s]", "", tok).lower()


def run_binding(claim, cwd, timeout):
    """Re-run a claim's command; return (status, detail, stdout)."""
    cmd = claim.get("command")
    if not cmd:
        return ("ASSERTED", "no command — value asserted, not reproduced", "")
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ("ERROR", "command timed out after %ss" % timeout, "")
    except OSError as exc:
        return ("ERROR", "could not launch command: %s" % exc, "")

    stdout = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return ("ERROR", "command exit %d: %s"
                % (proc.returncode, (proc.stderr or "").strip()[:200]), stdout)

    expect = claim.get("expect_contains", claim.get("value", ""))
    if expect and expect not in stdout and normalize(expect) not in normalize(stdout):
        return ("MISMATCH",
                "expected %r in output; not found (value has drifted)" % expect, stdout)
    return ("OK", "reproduced %r" % expect, stdout)


def audit_claims(manifest, cwd, timeout):
    results = []
    for claim in manifest.get("claims", []):
        cid = claim.get("id", "<no-id>")
        datasets = claim.get("dataset", [])
        if isinstance(datasets, str):
            datasets = [datasets]
        ds_hashes = {}
        for ds in datasets:
            p = ds if os.path.isabs(ds) else os.path.join(cwd, ds)
            ds_hashes[ds] = "MISSING" if not os.path.exists(p) else sha256_file(p)

        status, detail, _ = run_binding(claim, cwd, timeout)
        if any(v == "MISSING" for v in ds_hashes.values()) and status not in ("ERROR",):
            status, detail = "ERROR", "dataset missing: %s" % (
                ", ".join(k for k, v in ds_hashes.items() if v == "MISSING"))

        results.append({
            "id": cid,
            "value": claim.get("value"),
            "status": status,
            "detail": detail,
            "description": claim.get("description"),
            "citation": claim.get("citation"),
            "command": claim.get("command"),
            "dataset_sha256": ds_hashes,
        })
    return results


def scan_untraceable(deliverable_path, manifest):
    """Find numbers in the deliverable not covered by any claim surface form."""
    with open(deliverable_path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    covered = set()
    for claim in manifest.get("claims", []):
        forms = claim.get("appears_as") or []
        if claim.get("value"):
            forms = [claim["value"]] + list(forms)
        for f in forms:
            covered.add(normalize(f))

    found = []
    seen = set()
    for m in NUMBER_RE.finditer(text):
        tok = m.group(0).strip()
        norm = normalize(tok)
        if not norm or norm in STOPWORDS:
            continue
        if norm in covered:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        # small context window for the report
        start = max(0, m.start() - 30)
        end = min(len(text), m.end() + 30)
        ctx = " ".join(text[start:end].split())
        found.append({"number": tok, "context": ctx})
    return found


def build_trail(results, untraceable, cwd):
    def count(s):
        return sum(1 for r in results if r["status"] == s)
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cwd": cwd,
        "git_commit": git_commit(cwd),
        "summary": {
            "claims": len(results),
            "ok": count("OK"),
            "mismatch": count("MISMATCH"),
            "error": count("ERROR"),
            "asserted": count("ASSERTED"),
            "untraceable_numbers": len(untraceable),
        },
        "claims": results,
        "untraceable": untraceable,
    }


def print_human(trail):
    s = trail["summary"]
    print("=" * 64)
    print("REPRODUCIBLE INSIGHT WORKBENCH — audit")
    print("generated %s  git=%s" % (trail["generated_at"], trail["git_commit"] or "n/a"))
    print("=" * 64)
    icon = {"OK": "OK  ", "MISMATCH": "DRIFT", "ERROR": "ERR ",
            "ASSERTED": "ASRT"}
    for r in trail["claims"]:
        print("[%s] %-24s %s" % (icon.get(r["status"], r["status"]), r["id"],
                                 r["value"] or ""))
        print("       %s" % r["detail"])
        if r["citation"]:
            print("       cite: %s" % r["citation"])
    if trail["untraceable"]:
        print("-" * 64)
        print("UNTRACEABLE NUMBERS (in deliverable, no binding):")
        for u in trail["untraceable"]:
            print("  ? %-10s … %s …" % (u["number"], u["context"]))
    print("-" * 64)
    print("claims=%d ok=%d drift=%d error=%d asserted=%d untraceable=%d"
          % (s["claims"], s["ok"], s["mismatch"], s["error"], s["asserted"],
             s["untraceable_numbers"]))


def exit_code(trail):
    s = trail["summary"]
    if s["error"]:
        return 4
    if s["mismatch"]:
        return 3
    if s["untraceable_numbers"]:
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser(description="Provenance auditor for headline stats.")
    ap.add_argument("manifest", help="path to manifest.json")
    ap.add_argument("--deliverable", help="text of the deck/doc to scan for untraceable numbers")
    ap.add_argument("--out", help="write full audit trail JSON here")
    ap.add_argument("--json", action="store_true", help="print audit trail JSON to stdout")
    ap.add_argument("--timeout", type=int, default=120, help="per-command timeout seconds")
    ap.add_argument("--cwd", help="dir to resolve dataset/command paths against (default: manifest dir)")
    args = ap.parse_args()

    try:
        with open(args.manifest, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("manifest error: %s" % exc, file=sys.stderr)
        return 1
    if not isinstance(manifest.get("claims"), list):
        print("manifest error: missing 'claims' array", file=sys.stderr)
        return 1

    cwd = args.cwd or os.path.dirname(os.path.abspath(args.manifest)) or "."
    results = audit_claims(manifest, cwd, args.timeout)
    untraceable = []
    if args.deliverable:
        try:
            untraceable = scan_untraceable(args.deliverable, manifest)
        except OSError as exc:
            print("deliverable error: %s" % exc, file=sys.stderr)
            return 1

    trail = build_trail(results, untraceable, cwd)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(trail, fh, indent=2)
    if args.json:
        print(json.dumps(trail, indent=2))
    else:
        print_human(trail)
    return exit_code(trail)


if __name__ == "__main__":
    sys.exit(main())
