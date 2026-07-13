---
name: reproducible-insight-workbench
category: verification
description: >
  Bind every headline stat and chart in a deck, report or pitch to the EXACT dataset + query/code
  that produced it, then run a reviewer pass that re-runs each binding and flags untraceable numbers,
  drifted values, and mismatched citations — emitting a JSON audit trail so a stat survives a client
  challenge. Ports the provenance + reviewer-agent pattern from Anthropic's Claude Science / AI
  Workbench into a portable Claude Code workflow. Use when a number is about to go in front of a
  client, a regulator, or a New Business panel and "where did that come from?" must have an answer.
when_to_use:
  - Locking down a pitch/QBR deck so every headline stat can be traced back to source data on demand
  - A client or auditor asks "where did this number come from?" and you need the query, dataset and rerun command
  - Before shipping a data-driven report, to prove no figure is orphaned, stale, or invented
  - Wiring a repeatable analysis so re-running it next quarter re-verifies every stat automatically
  - Catching a chart whose underlying number has silently drifted since the deck was written
when_not_to_use:
  - Just confirming cited papers/DOIs exist and resolve — use citation-integrity-check
  - Recomputing/stress-testing the statistics themselves (p-values, GRIM, denominators) — use stat-check-review
  - Verifying a standalone factual claim against sources — use claim-verifier
  - Detecting internal contradictions across an LLM's outputs with no data — use self-consistency-check
  - You want the actual hosted Claude Science beta product — that is a separate Anthropic app, not this skill
keywords: [provenance, reproducibility, audit-trail, data-lineage, headline-stat, pitch-stat, claude-science, ai-workbench, reviewer-agent, untraceable-number, citation-check, drift, rerun, verification, manifest]
similar_to: [citation-integrity-check, stat-check-review, claim-verifier, self-consistency-check, experiment-validity-audit, source-credibility-audit]
inputs_needed: The deliverable (deck/report text or exported number list), the raw dataset file(s), and the query/script or SQL that produced each headline figure. Local shell + python3 (3.9 fine). No API keys, no network.
produces: A provenance manifest binding each stat to dataset+command, plus a JSON audit trail with per-claim OK/DRIFT/ERROR verdicts, dataset sha256 hashes, and a list of untraceable numbers found in the deliverable.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Reproducible Insight Workbench

A pitch stat is only as strong as your ability to answer **"where did that come from?"** on the
spot. Anthropic's Claude Science / AI Workbench announcement frames the fix: *"Every output carries
an auditable history of how it was made, so you can validate and reproduce the results,"* and a
reviewer agent *"flags incorrect citations and untraceable numbers."* This skill ports that
pattern — **provenance binding + a reviewer pass** — into a portable Claude Code workflow you can
run on any agency deck, no beta access required.

The idea: for each headline number you (a) write a **binding** capturing the dataset, the exact
command that computes it, and a plain-language description; then (b) run a **reviewer pass** that
re-runs every binding, checks the value still reproduces, hashes the dataset, and scans the
deliverable for any number that has *no* binding. Output is a JSON audit trail you can hand to a
sceptical client.

## When to use

Reach for this the moment a number becomes load-bearing in front of an audience who can push back:
New Business pitches, QBRs, effectiveness case studies, regulator/ASA submissions, board decks.
The failure mode it kills is the orphaned stat — a "+37% reach uplift" nobody can re-derive six
weeks later because the analyst left, the sheet moved, or the source data was overwritten.

## Prerequisites

- **Local shell + `python3`.** The `scripts/audit.py` helper is stdlib-only and runs on macOS
  system python3 (3.9). No pip, no network, no API keys.
- **The three ingredients per stat:** the deliverable, the raw dataset file(s), and a *runnable*
  command (script, one-liner, or SQL wrapped in a script) that prints the number. A stat with no
  reproducing command can still be logged, but it is marked `ASSERTED`, not reproduced — be honest
  about which numbers those are.
- **Honesty about the source.** Claude Science / the AI Workbench is a **separate Anthropic beta
  product** (announced 2025; beta for Pro/Max/Team/Enterprise on macOS/Linux, 60+ science skills,
  reviewer/generalist multi-agent architecture). This skill is **not** that product and does not
  call it — it reproduces the *provenance-and-review discipline* locally. If you actually want the
  hosted workbench with HPC/Modal compute and BioNeMo tools, that is the app, not this skill.

## Recipes

### 1. Author a provenance manifest

For each headline figure, write one claim into `manifest.json`. The `command` must be a shell
command that, run from the manifest's directory, prints text containing the value.

```json
{
  "claims": [
    {
      "id": "reach-uplift",
      "value": "37%",
      "appears_as": ["37%", "37 per cent", "+37pts"],
      "dataset": "data/campaign.csv",
      "command": "python3 queries/reach.py",
      "expect_contains": "37%",
      "description": "Incremental reach uplift, exposed vs control, 6-wk window",
      "citation": "GWI wave Q2 2026, n=1504"
    }
  ]
}
```

- `appears_as` — every surface form the number takes in the deck, so the reviewer's coverage scan
  recognises it. `+37pts` and `37 per cent` are the same claim.
- `expect_contains` — the exact substring the command's stdout must contain (defaults to `value`).
  Make your query print the number in a form that matches.
- `dataset` — one path or a list; each file is sha256-hashed into the audit trail so you can prove
  which snapshot the number came from.
- Omit `command` for numbers you can only assert (e.g. a third-party topline you can't recompute) —
  they log as `ASSERTED` so reviewers know they are un-reproduced, not verified.

### 2. Run the reviewer pass

```bash
python3 scripts/audit.py manifest.json --deliverable deck.txt --out audit_trail.json
```

`deck.txt` is your deliverable as plain text — export/paste the deck or report copy. Use the
`pptx` skill (`markitdown`) to extract slide text, or `pdf` for a PDF, then point `--deliverable`
at the result. The pass:

1. **Re-runs every binding** and checks `expect_contains` is still in the output → `OK` / `DRIFT`.
2. **Hashes each dataset**; a missing file → `ERROR` (unreproducible).
3. **Scans the deliverable** for numbers (percentages, currency, decimals, thousands) and flags any
   whose normalized form matches no claim → **untraceable**.

Per-claim verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `OK` | Command re-ran and the value still reproduces | Ship it |
| `DRIFT` | Command ran but no longer emits the recorded value | Number is stale — re-derive before the meeting |
| `ERROR` | Command failed / dataset missing | Stat is currently unreproducible — do not present |
| `ASSERTED` | No command; value logged but not reproduced | Label its true source; consider recomputing |

### 3. Gate on the exit code (CI / pre-send hook)

```bash
python3 scripts/audit.py manifest.json --deliverable deck.txt
echo "exit=$?"
```

Exit codes: `0` clean · `2` untraceable number(s) · `3` DRIFT · `4` ERROR · `1` manifest/usage
error. Wire it into a pre-send check so a deck literally cannot be exported while a headline number
is orphaned or stale.

### 4. Chart provenance, not just numbers

A chart is a stat with a picture. Give the plotting script its own claim: `command` regenerates the
figure **and** prints its key value (e.g. the peak or the delta), `expect_contains` pins that value,
and `description` records the axis/transform decisions. Now the image and its underlying number are
bound together — regenerate and you re-verify both. Mirrors the Workbench behaviour where a figure
carries its exact code, environment, and a plain-language description of how it was made.

### 5. Handoff pack for the challenge

Ship `audit_trail.json` alongside the deck (or into the project repo). It records, per claim: the
value, verdict, dataset sha256(s), the exact command, the citation, and the git commit of the repo
at audit time. When a client challenges a number, you open the trail, show the dataset hash and the
one-line rerun command, and re-derive it live. That is the whole point.

## Verify

Reproduce the smoke test that ships with this skill:

```bash
cd /tmp && rm -rf riw && mkdir -p riw/queries riw/data && cd riw
printf 'group,reached\ncontrol,100\nexposed,137\n' > data/campaign.csv
cat > queries/reach.py <<'PY'
import csv
r={x['group']:int(x['reached']) for x in csv.DictReader(open('data/campaign.csv'))}
print(f"uplift: {round((r['exposed']-r['control'])/r['control']*100)}%")
PY
echo '{"claims":[{"id":"reach","value":"37%","dataset":"data/campaign.csv","command":"python3 queries/reach.py","expect_contains":"37%"}]}' > m.json
printf 'A 37%% reach uplift and a 12%% sales lift.\n' > deck.txt
python3 /path/to/scripts/audit.py m.json --deliverable deck.txt; echo "exit=$?"
```

Expect: `reach` → `OK`, an untraceable `12%` flagged, `exit=2`. Then edit `exposed,137` → `145`
and re-run: the binding flips to `DRIFT`, `exit=3` — the stat drifted and the pass caught it. A
manifest whose every claim is `OK` with no untraceable numbers exits `0`.

## Pitfalls

- **`ASSERTED` is not verified.** A number with no command is logged, not reproduced. Do not let an
  `ASSERTED` topline masquerade as audited — either recompute it or cite its external source plainly.
- **The coverage scan is lexical, not semantic.** It matches number *strings*, so add every surface
  form (`37%`, `37 per cent`, `0.37`, `+37pts`) to `appears_as`, or it will flag your own bound stat
  as untraceable. Conversely, it can't tell a page number or a footnote year from a headline stat —
  eyeball the untraceable list; `STOPWORDS` and small integers are skipped by default.
- **`command` runs real shell.** Only audit manifests you wrote or trust — a claim's command executes
  with your permissions. Keep commands to read-only queries; never put a destructive command in a
  binding.
- **`expect_contains` is a substring match.** `"3%"` matches inside `"137%"`. Pin the fuller string
  (`"uplift: 37%"`) when a bare number could collide, and make your query print a distinctive label.
- **Rounding drift.** If the deck says `37%` but the query prints `36.8%`, it reads as `DRIFT`. Decide
  the canonical rounding, print it that way, and pin it — don't round differently in deck vs query.
- **Datasets move.** The sha256 proves *which snapshot* produced the number; if the file is later
  overwritten the hash changes and the story falls apart. Freeze the source data (copy into the repo)
  before you audit, so the trail points at an immutable artefact.
- **This skill checks reproducibility, not truth.** A stat can reproduce perfectly from a biased or
  mis-specified analysis. Pair with stat-check-review (are the numbers sound?) and
  citation-integrity-check (do the cited sources exist and support the point?) for the full defence.
