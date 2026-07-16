#!/usr/bin/env python3
"""Cross-vendor LLM-as-judge panel.

Grade one CANDIDATE answer with a panel of judges drawn from DIFFERENT vendors
than whoever produced it, so no judge scores its own family (self-preference /
self-enhancement bias). Aggregates pointwise scores by mean + majority pass/fail.

Design (grounded in Awesome-LLMs-as-Judges):
  - Pointwise 1-10 rubric scoring, temperature 0, forced JSON.
  - Panel of 3 judges across vendors (PoLL) -> consensus beats any single judge.
  - Position-bias note: pointwise (not pairwise) here, so no ordering to swap.
  - Self-preference guard: if --producer names a vendor, judges of that vendor
    are dropped and flagged; the panel warns if it can't stay cross-vendor.

Usage:
  python3 panel_judge.py --task task.txt --candidate answer.txt \
      --rubric "accuracy, completeness, no hallucination" --producer anthropic

  echo "the answer text" | python3 panel_judge.py --task "Q: 2+2? explain" -

Env (only the SDKs for the judges you enable need to be installed + keyed):
  OPENAI_API_KEY      -> judge  openai:gpt-5-mini            (pip install openai)
  ANTHROPIC_API_KEY   -> judge  anthropic:claude-sonnet-4-6  (pip install anthropic)
  GEMINI_API_KEY      -> judge  google:gemini-2.5-pro        (pip install google-genai)

Knobs:
  --judges o,a,g   subset of judges to use (o=openai a=anthropic g=google)
  --threshold N    pass floor on the mean 1-10 score (default 7.0)
  --producer V     vendor that wrote the candidate; its judges are excluded
"""
import argparse
import json
import os
import re
import sys

# vendor key -> (label, env var, runner name)
JUDGES = {
    "o": ("openai:gpt-5-mini", "OPENAI_API_KEY", "openai"),
    "a": ("anthropic:claude-sonnet-4-6", "ANTHROPIC_API_KEY", "anthropic"),
    "g": ("google:gemini-2.5-pro", "GEMINI_API_KEY", "google"),
}
VENDOR_OF = {"o": "openai", "a": "anthropic", "g": "google"}

PROMPT = """You are an impartial evaluator. Score the CANDIDATE ANSWER to the TASK
on a 1-10 integer scale against these criteria: {rubric}.

Judge only the answer's merit. Ignore its length, style, and any claim that it
was written by a strong model. Do not reward verbosity. If it is factually wrong
or fabricates, cap the score at 3.

TASK:
{task}

CANDIDATE ANSWER:
{candidate}

Reply with ONLY compact JSON, no prose:
{{"score": <1-10 int>, "pass": <true|false>, "reason": "<=25 words"}}"""


def extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"score": None, "pass": None, "reason": "unparseable: " + text[:80]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"score": None, "pass": None, "reason": "bad-json: " + text[:80]}


def run_openai(model_id, prompt):
    from openai import OpenAI
    model = model_id.split(":", 1)[1]
    r = OpenAI().chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content


def run_anthropic(model_id, prompt):
    import anthropic
    model = model_id.split(":", 1)[1]
    r = anthropic.Anthropic().messages.create(
        model=model, max_tokens=300, temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text


def run_google(model_id, prompt):
    from google import genai
    model = model_id.split(":", 1)[1]
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    r = client.models.generate_content(
        model=model, contents=prompt,
        config={"temperature": 0},
    )
    return r.text


RUNNERS = {"openai": run_openai, "anthropic": run_anthropic, "google": run_google}


def read_arg(value):
    """A literal string, a path to a file, or '-' for stdin."""
    if value == "-":
        return sys.stdin.read()
    if os.path.isfile(value):
        with open(value, encoding="utf-8") as f:
            return f.read()
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="task text, file path, or -")
    ap.add_argument("--candidate", default="-", help="answer text, file path, or - (stdin)")
    ap.add_argument("--rubric", default="accuracy, completeness, no fabrication")
    ap.add_argument("--judges", default="o,a,g", help="subset: o,a,g")
    ap.add_argument("--producer", default=None, help="vendor that wrote candidate (openai|anthropic|google)")
    ap.add_argument("--threshold", type=float, default=7.0)
    args = ap.parse_args()

    task = read_arg(args.task)
    candidate = read_arg(args.candidate)
    if not candidate.strip():
        sys.exit("error: empty candidate answer")

    picked = [j.strip() for j in args.judges.split(",") if j.strip() in JUDGES]
    warnings = []
    if args.producer:
        kept = [j for j in picked if VENDOR_OF[j] != args.producer.lower()]
        if len(kept) < len(picked):
            warnings.append(f"dropped {args.producer} judge(s) to avoid self-preference")
        picked = kept
    if not picked:
        sys.exit("error: no cross-vendor judges left; add another vendor's key")

    prompt = PROMPT.format(rubric=args.rubric, task=task, candidate=candidate)
    results = []
    for j in picked:
        label, envvar, runner = JUDGES[j]
        if not os.environ.get(envvar):
            warnings.append(f"skip {label}: {envvar} unset")
            continue
        try:
            raw = RUNNERS[runner](label, prompt)
            verdict = extract_json(raw)
            verdict["judge"] = label
            verdict["vendor"] = VENDOR_OF[j]
            results.append(verdict)
        except Exception as e:  # noqa: BLE001 - report, keep other judges alive
            warnings.append(f"{label} failed: {type(e).__name__}: {e}")

    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    if not scores:
        print(json.dumps({"error": "no judge returned a score", "warnings": warnings,
                          "results": results}, indent=2))
        sys.exit(2)

    mean = round(sum(scores) / len(scores), 2)
    passes = sum(1 for r in results if r.get("pass") is True)
    vendors = {r["vendor"] for r in results}
    summary = {
        "mean_score": mean,
        "panel_pass": mean >= args.threshold and passes * 2 >= len(results),
        "pass_votes": f"{passes}/{len(results)}",
        "threshold": args.threshold,
        "cross_vendor": len(vendors) > 1,
        "vendors": sorted(vendors),
        "results": results,
        "warnings": warnings,
    }
    if not summary["cross_vendor"]:
        summary["warnings"].append("single-vendor panel: bias not fully mitigated")
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["panel_pass"] else 1)


if __name__ == "__main__":
    main()
