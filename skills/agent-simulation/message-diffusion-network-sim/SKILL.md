---
name: message-diffusion-network-sim
category: agent-simulation
description: >
  Forecast how a campaign line, claim, or headline SPREADS or DIES across a synthetic
  social graph of Claude personas — not by polling isolated respondents but by modelling
  peer contagion, super-spreaders, tipping points, and message decay hop-by-hop. Use when
  someone asks "will this go viral", "how far does this message travel", "who are the
  super-spreaders for this idea", "what's the tipping point", "does this claim cascade or
  fizzle", or wants a reach-vs-spread forecast before spend. Claude scores per-persona
  adoption; a networkx independent-cascade Monte Carlo propagates it many times.
when_to_use:
  - "Forecast whether a message reaches system-wide virality or fizzles in a niche"
  - "Find the tipping point (transmissibility / seed size) where a claim goes from dud to cascade"
  - "Identify which persona archetypes are super-spreaders for THIS specific message"
  - "Compare two creative lines on spread/reach, not just standalone persona reactions"
  - "Model message decay — how the idea erodes as it travels further from the source"
when_not_to_use:
  - "You want a full agentic social-media sim with real feeds/actions and a SQLite trace — use oasis-social-media-simulation"
  - "You just want isolated persona reactions to a concept with no network contagion — use a straight synthetic-panel / persona-polling approach"
  - "You need REAL audience diffusion data (actual shares, listening) — use a GWI / Brand24 / social-listening skill"
  - "City-scale mobility/economic ABM — use agentsociety-urban-experiment"
keywords: [message diffusion, contagion, virality forecast, independent cascade, tipping point, super-spreaders, social graph, network simulation, message decay, claude personas, monte carlo, scale-free network, barabasi-albert, opinion dynamics, reach forecast, agent simulation]
similar_to: [oasis-social-media-simulation, generative-agent-architecture, agentsociety-urban-experiment]
inputs_needed:
  - "The message/claim/creative line to test (the thing that spreads)"
  - "The audience: a set of persona archetypes with rough population shares, OR just a size + topology guess"
  - "Launch shape: seeded via a few influencers (hubs) or a broad random push"
produces: A virality forecast JSON — mean/median/p90 reach + fizzle rate, a hop-by-hop diffusion curve, a tipping-point sweep (the beta where it phase-transitions), and a ranked super-spreader list. Plus the synthetic graph + per-persona adoption scores.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Message Diffusion Network Sim

Most synthetic-audience work asks personas in *isolation*: "what do you think of this ad?"
But people don't form opinions alone — they're pulled by networks, norms, and each other
([Artificial Societies review, fish.dog, 2026](https://fish.dog/news/artificial-societies-review-2026-social-simulation-meets-market-research)).
This skill models the missing half: put a message into a *connected* audience and forecast
whether it **cascades or dies** — reach vs spread, tipping points, super-spreaders, decay.

The split that keeps it cheap and honest: **Claude does the semantics** (how likely is
each persona to adopt/forward THIS message), **networkx does the combinatorics** (propagate
it through the graph thousands of times). You get a mechanistic forecast, not vibes.

## When to use

Reach for this when the question is about *travel*, not *opinion*: "how far does this go,
where does it stall, who carries it, and at what point does it tip." If you only need
standalone reactions, a persona panel is simpler. If you need a full feed-level agentic
sim with 23 real actions and a DB trace, use `oasis-social-media-simulation` — this skill
is the lean, scriptable middle: a diffusion forecast you can run in seconds and sweep.

## Prerequisites

- **python3 + networkx + numpy** (already present on this Mac: networkx 3.2.1, numpy 2.0).
  If missing: `pip install networkx numpy`. No network calls; runs offline, deterministic
  with `--seed`.
- **Claude for the scoring step** — that's this session. No API key needed for the
  interactive path: you (Claude) read the persona list and write the adoption scores.
- **Optional, for large graphs (5k+ nodes):** score personas in bulk via the Anthropic
  **Message Batches API** (`/v1/messages/batches`, ~50% cheaper, async, up to 100k requests
  per batch). Only worth it when you're scoring thousands of distinct personas — for the
  usual handful of *archetypes*, score inline. This is real and GA, but treat batch as an
  optimisation, not a requirement.

Honest scope: this is a **mechanistic what-if**, not a calibrated predictor. The absolute
reach numbers are only as good as your adoption scores and topology guess. Its value is
*directional* — comparing variants, locating the tipping point, exposing which archetypes
carry the message. Validate against real listening data before betting spend.

## The model (grounded)

Diffusion runs as an **Independent Cascade Model** (Kempe, Kleinberg & Tardos, 2003), the
standard contagion model in computational social science. A just-activated node gets one
chance to activate each inactive neighbour, with probability:

```
beta  ×  p_v  ×  decay^hop
```

- **`p_v`** — Claude's adoption propensity for persona `v` given this exact message (0..1).
  This is where message-persona fit lives: a provocative claim scores high for contrarians,
  low for the risk-averse.
- **`beta`** — global transmissibility: message stickiness × channel reach. The knob you
  sweep to find the tipping point.
- **`decay^hop`** — message erosion: the idea loses salience/fidelity the further it travels
  from the source (a friend-of-a-friend-of-a-friend hears a weaker version).

Topology matters as much as the message. Default is **Barabási–Albert scale-free** (`ba`),
whose heavy-tailed degree distribution produces real hubs — the super-spreaders. `ws`
(small-world) models tight communities with bridges; `er` (random) is a no-hub null baseline.

## Recipe — forecast a campaign line

**1. Scaffold a synthetic audience graph.** Size it to your audience, pick a topology.

```bash
cd skills/agent-simulation/message-diffusion-network-sim
python3 scripts/cascade_sim.py scaffold --nodes 800 --graph ba --out run/
# writes run/graph.json, run/nodes.json (node → degree), run/adoption.json (placeholder)
```

**2. Assign each node a persona, then score adoption for THIS message.** In practice you
define a handful of **archetypes** (say 5–8: e.g. *Trend Sceptic, Culture Maven, Deal
Hunter, Brand Loyalist, Casual Scroller*) with population shares, map nodes to archetypes
(hubs → the more-connected/influential archetypes is a reasonable prior), then Claude scores
each archetype's probability of adopting *and passing on* the message. Write `run/adoption.json`
as `{"<node>": 0.0..1.0}`. Reason it out per archetype, e.g.:

> "Line: *'The only sunscreen dermatologists secretly use.'* Trend Sceptic 0.10 (smells like
> hype), Culture Maven 0.55 (loves an insider claim to share), Deal Hunter 0.20, Brand Loyalist
> 0.35, Casual Scroller 0.25." — then broadcast each score to that archetype's nodes.

Keep the *reasoning* visible in your reply; the JSON is just the compiled output.

**3. Run the forecast** — reach distribution, hop-by-hop curve, tipping sweep, spreaders.

```bash
python3 scripts/cascade_sim.py run --graph-file run/graph.json \
    --adoption run/adoption.json --seeds 3 --seed-hubs \
    --beta 0.4 --decay 0.85 --runs 2000 --top 10 --out run/forecast.json
```

`--seed-hubs` models an **influencer launch** (seed the highest-degree nodes); drop it for a
**broad random push**. Comparing the two seedings answers "is this idea better launched
top-down through big accounts, or does it spread organically from anywhere?"

**4. A/B two creative lines.** Re-score `adoption.json` for line B (same graph, same seeds),
run again to a new `--out`, and compare `mean_reach`, `fizzle_rate`, and the tipping `beta`.
Lower tipping beta = spreads under weaker conditions = the more *contagious* line, even if
peak reach is similar.

## Reading the output

- **`forecast.reach_pct` / `mean_reach`** — expected share of the network the message reaches.
- **`fizzle_rate`** — fraction of runs that died at/near the seed. High fizzle + high p90 =
  a *lottery* message (usually nothing, occasionally viral); low fizzle = reliable spread.
- **`mean_cumulative_by_hop`** — the diffusion curve. A steep early rise then flattening is a
  classic S-curve; a curve that never lifts off is a dud regardless of the seed.
- **`tipping_point_beta`** — the transmissibility at which reach phase-transitions past 15% of
  the network. Below it the message needs the audience to be *unusually* receptive; at or above
  it, it self-sustains. This is the single most decision-useful number.
- **`super_spreaders`** — nodes ranked by expected single-seed cascade size. Map them back to
  archetypes: *these are the personas worth targeting/seeding first.*

## Verify

```bash
# Deterministic smoke test on a throwaway graph (uniform adoption):
python3 scripts/cascade_sim.py scaffold --nodes 400 --graph ba --out /tmp/mdns/
python3 scripts/cascade_sim.py run --graph-file /tmp/mdns/graph.json \
    --adoption /tmp/mdns/adoption.json --seeds 3 --seed-hubs --runs 500 --top 3
```

Sanity checks: raising every adoption score should raise `reach_pct`; the `tipping_curve`
should be monotonically increasing in beta and show a visible jump (phase transition), not a flat line;
seeding hubs (`--seed-hubs`) should beat random seeding on a `ba` graph. Same `--seed` →
identical numbers.

## Pitfalls

- **Garbage-in on adoption.** The forecast is only as good as Claude's `p_v` scores. Score
  *adoption AND onward-sharing* (a message can be believed but not forwarded), reason per
  archetype in the open, and don't invent false precision — 0.1-granular scores are plenty.
- **Topology is a modelling choice, not a fact.** `ba` assumes influencer-shaped audiences;
  real B2B or tight-subculture audiences may be closer to `ws`. Run 2 topologies; if the
  conclusion flips, say so rather than reporting one number.
- **Absolute reach is not a real-world forecast.** It's a synthetic network at a made-up
  scale. Trust *comparisons and shapes* (A beats B, tips at beta≈X, fizzle-prone), not "3,412
  people will see it." The source explicitly warns social sims skew toward *visible* people —
  "who's missing" from your archetypes matters (heavy posters ≠ buyers).
- **Seeds dominate small runs.** With few seeds and low adoption almost everything fizzles;
  that's correct behaviour, not a bug. Sweep `--seeds` and `--beta` before concluding a line
  is dead.
- **This is not the agentic sim.** There are no feeds, replies, or emergent mutation of the
  message here — it's a contagion forecast. When you need real interaction dynamics and a
  queryable trace, switch to `oasis-social-media-simulation`.
