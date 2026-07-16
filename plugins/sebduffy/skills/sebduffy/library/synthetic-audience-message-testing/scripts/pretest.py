#!/usr/bin/env python3
"""Synthetic message pre-test harness.

Runs a battery of message/creative variants against a TinyTroupe persona
population, scores each reaction on a fixed rubric, and synthesises a
decision-ready readout (winner, per-variant score, objection log).

Real runs need OpenAI creds (export OPENAI_API_KEY) and `pip install
git+https://github.com/microsoft/TinyTroupe.git@main`.

`--selfcheck` exercises the config parser + scoring + synthesis on stubbed
reactions with NO network and NO TinyTroupe import, so the harness is
verifiable offline.
"""
from __future__ import annotations
import argparse, json, re, sys
from statistics import mean

# --- Scoring rubric ---------------------------------------------------------
# Deterministic lexical fallback so a readout exists even if the LLM does not
# emit a numeric field. Prefer the model's own 1-5 clarity/appeal/intent fields
# via ResultsExtractor.fields; this only backstops missing values.
POS = {"love", "great", "clear", "convincing", "want", "buy", "trust",
       "excited", "relevant", "yes", "compelling", "helpful"}
NEG = {"confusing", "boring", "vague", "gimmicky", "distrust", "expensive",
       "irrelevant", "no", "pushy", "unclear", "skeptical", "ignore"}


def lexical_sentiment(text: str) -> float:
    """Backstop 1-5 score from a free-text reaction. Never trusts input blindly."""
    if not isinstance(text, str) or not text.strip():
        return 3.0
    toks = set(re.findall(r"[a-z']+", text.lower()))
    score = 3.0 + 0.5 * len(toks & POS) - 0.5 * len(toks & NEG)
    return max(1.0, min(5.0, score))


def reaction_score(reaction: dict) -> float:
    """Prefer explicit rubric fields; fall back to lexical sentiment."""
    fields = [reaction.get(k) for k in ("clarity", "appeal", "intent")]
    nums = [float(v) for v in fields if isinstance(v, (int, float))]
    if nums:
        return round(mean(nums), 2)
    return round(lexical_sentiment(reaction.get("verbatim", "")), 2)


def synthesise(variants: list[dict]) -> dict:
    """Fold per-persona reactions into a per-variant readout + a winner."""
    rows = []
    for v in variants:
        reactions = v.get("reactions", [])
        scores = [reaction_score(r) for r in reactions]
        objections = [r.get("verbatim", "") for r in reactions
                      if reaction_score(r) < 3.0 and r.get("verbatim")]
        rows.append({
            "variant": v["id"],
            "n": len(scores),
            "mean_score": round(mean(scores), 2) if scores else 0.0,
            "top_objections": objections[:3],
        })
    rows.sort(key=lambda r: r["mean_score"], reverse=True)
    winner = rows[0]["variant"] if rows else None
    return {"winner": winner, "ranking": rows}


# --- Config -----------------------------------------------------------------
def load_config(path: str) -> dict:
    with open(path) as fh:
        cfg = json.load(fh)
    for key in ("population", "variants"):
        if key not in cfg:
            raise ValueError(f"config missing required key: {key!r}")
    if not cfg["variants"]:
        raise ValueError("config.variants must be non-empty")
    return cfg


# --- Live run (needs TinyTroupe + OPENAI_API_KEY) ---------------------------
def run_live(cfg: dict) -> dict:
    from tinytroupe.factory import TinyPersonFactory
    from tinytroupe.extraction import ResultsExtractor

    pop = cfg["population"]
    factory = TinyPersonFactory.create_factory_from_demography(
        demography_description_or_file_path=pop["demography"],
        population_size=pop.get("size", 8),
        context=cfg.get("context", "Message pre-test panel"),
    )
    people = factory.generate_people(number_of_people=pop.get("size", 8),
                                     parallelize=True)
    extractor = ResultsExtractor()

    out_variants = []
    for v in cfg["variants"]:
        reactions = []
        for person in people:
            person.listen_and_act(
                f"You just saw this ad/message. React honestly as yourself:\n\n{v['copy']}")
            r = extractor.extract_results_from_agent(
                person,
                extraction_objective=(
                    "This person's honest reaction to the message. Rate clarity, "
                    "appeal and purchase-intent each 1-5 and quote their verbatim."),
                fields=["clarity", "appeal", "intent", "verbatim"],
            )
            reactions.append(r or {})
            person.reset_prompt()  # isolate variants: no carry-over memory
        out_variants.append({"id": v["id"], "reactions": reactions})
    return synthesise(out_variants)


# --- Selfcheck --------------------------------------------------------------
def selfcheck() -> int:
    stub = [
        {"id": "A", "reactions": [
            {"clarity": 5, "appeal": 4, "intent": 4, "verbatim": "clear and convincing"},
            {"verbatim": "I love this, want to buy"}]},
        {"id": "B", "reactions": [
            {"clarity": 2, "appeal": 2, "intent": 1, "verbatim": "confusing and pushy"},
            {"verbatim": "boring, irrelevant"}]},
    ]
    out = synthesise(stub)
    assert out["winner"] == "A", out
    assert out["ranking"][0]["mean_score"] > out["ranking"][1]["mean_score"]
    assert out["ranking"][1]["top_objections"], "B should log objections"
    assert lexical_sentiment("") == 3.0
    assert reaction_score({"verbatim": "confusing and pushy no"}) < 3.0
    print("selfcheck OK:", json.dumps(out, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", help="path to pre-test config JSON")
    ap.add_argument("--selfcheck", action="store_true",
                    help="offline validation of scoring/synthesis")
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    if not args.config:
        ap.error("--config required for a live run (or use --selfcheck)")
    cfg = load_config(args.config)
    print(json.dumps(run_live(cfg), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
