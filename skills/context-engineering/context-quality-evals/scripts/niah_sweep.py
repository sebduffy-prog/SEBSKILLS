#!/usr/bin/env python3
"""
niah_sweep.py — a lean, dependency-light needle-in-a-haystack / lost-in-the-middle
sweep for ONE API model. Charts where a model degrades vs (context length, needle depth)
and optionally under distractors. This is a local, no-GPU alternative to NVIDIA/RULER
for quick "context quality" checks; use RULER/Chroma context-rot for the full battery.

Only stdlib is required to RUN the model calls (urllib). matplotlib is optional (heatmap).

Usage:
  export ANTHROPIC_API_KEY=sk-...
  python3 niah_sweep.py \
      --provider anthropic --model claude-sonnet-4-5 \
      --lengths 2000 8000 32000 128000 \
      --depths 0 0.25 0.5 0.75 1.0 \
      --distractors 0 \
      --out results.csv

  # OpenAI:
  export OPENAI_API_KEY=sk-...
  python3 niah_sweep.py --provider openai --model gpt-4.1 --lengths 4000 16000 64000

Outputs a CSV (length,depth,distractors,trial,correct,answer) and prints an
accuracy grid. Pass --heatmap out.png if matplotlib is installed.
"""
import argparse, csv, json, os, random, re, sys, urllib.request, urllib.error

# A neutral filler sentence pool (the "haystack"). Kept boring so the needle stands out
# only semantically, not lexically. ~approx 1 token per 0.75 words for rough sizing.
FILLER = [
    "The committee reviewed the quarterly logistics report before lunch.",
    "Rainfall in the northern valley remained steady throughout the season.",
    "A new set of guidelines was circulated to the regional offices.",
    "The archive room was reorganised to improve retrieval times.",
    "Several volunteers helped catalogue the old shipping manifests.",
    "Maintenance on the east bridge is scheduled for the following month.",
    "The library extended its opening hours during the exam period.",
    "Local vendors gathered at the market square early on Saturday.",
]

NEEDLE_TMPL = "The secret passcode for the {city} vault is {code}."
DISTRACTOR_TMPL = "The old passcode for the {city} vault was {code}."
QUESTION = "What is the secret passcode for the {city} vault? Answer with the code only."

CITIES = ["Lisbon", "Osaka", "Nairobi", "Bogota", "Helsinki", "Perth"]


def make_code(rng):
    return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))


def approx_tokens_to_words(n_tokens):
    return int(n_tokens * 0.75)


def build_context(target_tokens, depth, n_distractors, rng):
    """Assemble a haystack of ~target_tokens words with the needle at fractional `depth`."""
    city = rng.choice(CITIES)
    code = make_code(rng)
    needle = NEEDLE_TMPL.format(city=city, code=code)
    target_words = approx_tokens_to_words(target_tokens)

    filler_sents = []
    wc = 0
    while wc < target_words:
        s = rng.choice(FILLER)
        filler_sents.append(s)
        wc += len(s.split())

    # distractors: same template, wrong (old) codes for the SAME city -> competing answers
    distractors = [
        DISTRACTOR_TMPL.format(city=city, code=make_code(rng)) for _ in range(n_distractors)
    ]

    insert_at = min(int(depth * len(filler_sents)), len(filler_sents))
    body = filler_sents[:insert_at] + [needle] + filler_sents[insert_at:]
    # scatter distractors at random positions
    for d in distractors:
        body.insert(rng.randrange(len(body) + 1), d)

    context = " ".join(body)
    return context, city, code


# ---- provider adapters (stdlib urllib only) ----

def call_anthropic(model, system, user, max_tokens=32):
    key = os.environ["ANTHROPIC_API_KEY"]
    body = json.dumps({
        "model": model, "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))


def call_openai(model, system, user, max_tokens=32):
    key = os.environ["OPENAI_API_KEY"]
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_completion_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


ADAPTERS = {"anthropic": call_anthropic, "openai": call_openai}


def graded(answer, code):
    return code.upper() in re.sub(r"[^A-Za-z0-9]", "", answer).upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=ADAPTERS, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--lengths", type=int, nargs="+", default=[2000, 8000, 32000])
    ap.add_argument("--depths", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75, 1.0])
    ap.add_argument("--distractors", type=int, nargs="+", default=[0])
    ap.add_argument("--trials", type=int, default=3, help="repeats per cell (seeds)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--heatmap", default=None, help="PNG path (needs matplotlib)")
    args = ap.parse_args()

    call = ADAPTERS[args.provider]
    system = ("You are given a long document. Read it and answer the question "
              "using only information stated in the document.")
    rows = []
    grid = {}  # (length, dist) -> list of (depth, acc)

    for length in args.lengths:
        for dist in args.distractors:
            for depth in args.depths:
                correct = 0
                for t in range(args.trials):
                    rng = random.Random((args.seed, length, dist, depth, t).__hash__())
                    ctx, city, code = build_context(length, depth, dist, rng)
                    user = f"{ctx}\n\n{QUESTION.format(city=city)}"
                    try:
                        ans = call(args.model, system, user)
                    except urllib.error.HTTPError as e:
                        ans = f"<HTTP {e.code}: {e.read()[:200]}>"
                    except Exception as e:  # noqa: BLE001
                        ans = f"<ERR {e}>"
                    ok = graded(ans, code)
                    correct += ok
                    rows.append([length, depth, dist, t, int(ok), ans.strip()[:120]])
                acc = correct / args.trials
                grid.setdefault((length, dist), []).append((depth, acc))
                print(f"len={length:>7} depth={depth:<4} dist={dist} acc={acc:.2f}")

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["length", "depth", "distractors", "trial", "correct", "answer"])
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows -> {args.out}")

    if args.heatmap:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            depths = sorted(args.depths)
            keys = sorted(grid.keys())
            mat = [[dict(grid[k]).get(d, float("nan")) for k in keys] for d in depths]
            fig, ax = plt.subplots(figsize=(max(4, len(keys)), max(3, len(depths))))
            im = ax.imshow(mat, aspect="auto", vmin=0, vmax=1, cmap="RdYlGn")
            ax.set_xticks(range(len(keys)))
            ax.set_xticklabels([f"{l//1000}k/d{dd}" for l, dd in keys], rotation=45, ha="right")
            ax.set_yticks(range(len(depths)))
            ax.set_yticklabels([f"depth {d}" for d in depths])
            fig.colorbar(im, label="accuracy")
            ax.set_title(f"{args.model} NIAH sweep")
            fig.tight_layout()
            fig.savefig(args.heatmap, dpi=120)
            print(f"Wrote heatmap -> {args.heatmap}")
        except ImportError:
            print("matplotlib not installed; skipping heatmap", file=sys.stderr)


if __name__ == "__main__":
    main()
