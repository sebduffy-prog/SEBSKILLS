---
name: multi-touch-attribution
category: marketing-science
description: >
  Attribute conversions across the multi-touch customer journey with data-driven models,
  not just last-click. Reach for this when someone says "which channels actually drove the
  conversion", "Markov attribution", "removal effect", "Shapley attribution", "path-to-
  conversion", "MTA", "first-touch vs last-touch", "give social its fair credit", or "our
  attribution over-credits brand search". Runs ChannelAttribution's k-order Markov removal-
  effect model plus a zero-dependency Shapley-value estimator, and benchmarks both against
  rules-based baselines (first / last / linear / position / time-decay) so you can show the
  gap between naive and data-driven credit. Completes the MMM + geo measurement stack at the
  user/click-path grain.
when_to_use:
  - Reallocating credit across digital touchpoints from user-level path data (impressions/clicks → conversion)
  - Running a Markov removal-effect model to see which channel, if removed, kills the most conversions
  - Computing Shapley-value attribution to give each channel its fair coalitional credit
  - Comparing data-driven attribution against last-click / first-click / linear / time-decay baselines
  - Quantifying how much last-click over- or under-credits a channel (e.g. brand search vs upper-funnel social)
  - Building the input feature (per-channel driven conversions) that later calibrates or triangulates an MMM
when_not_to_use:
  - Channel-level budget ROI from aggregate weekly spend + sales — use the marketing-mix-modeling skill
  - Proving true incrementality with a holdout / randomised test — use the geo-incrementality-testing skill
  - You only have aggregate channel totals, not journey/path sequences — MTA needs ordered touch data
keywords:
  - attribution
  - multi-touch
  - markov
  - removal-effect
  - shapley
  - channel-attribution
  - path-to-conversion
  - last-click
  - time-decay
  - customer-journey
  - mta
  - conversion-credit
  - marketing-science
  - media-measurement
similar_to:
  - marketing-mix-modeling
  - geo-incrementality-testing
inputs_needed: >
  User/session-level journey data: for each converting (and ideally non-converting) journey, the
  ordered sequence of channels/touchpoints, a conversion count, and optionally conversion value.
  ChannelAttribution wants one row per unique path with total_conversions (+ total_null,
  total_conversion_value). Python 3.8+; a C compiler for the pip build of ChannelAttribution.
produces: >
  A per-channel attribution table comparing Markov (order-k) removal-effect credit, Shapley-value
  credit, and rules-based baselines (first/last/linear/position/time-decay), in conversions and
  value; plus removal effects and the transition matrix for narrative/QA.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Multi-Touch Attribution (Markov + Shapley vs rules-based)

Data-driven credit assignment across the touchpoint path. Two data-driven engines
(Markov removal-effect and Shapley value) benchmarked against the rules-based
baselines everyone already reports, so you can show exactly where last-click lies.

## When to use

Use when you have **ordered journey/path data** (not just channel totals) and need
to split conversion credit fairly. If you only have weekly aggregate spend and sales,
that is MMM — use `marketing-mix-modeling`. If the question is "is this media truly
incremental" you need an experiment — use `geo-incrementality-testing`. MTA answers
"given a conversion happened, which touches deserve credit"; it is correlational and
should be triangulated against those causal methods, never used alone to set budgets.

## Prerequisites

- **Python 3.8+**. On this Mac python3 is 3.9 — fine.
- **ChannelAttribution** (Markov + heuristic engine). It builds a C/Cython extension:
  ```bash
  pip install --upgrade setuptools Cython
  pip install ChannelAttribution      # current 2.2.x; needs a working C compiler
  ```
  Licensed **GPL (>=3)** — fine for internal analysis; check before redistributing.
  If the build fails (no compiler), the pure-Python `pychattr` mirrors its API, or use
  the bundled Shapley + baseline recipes below which need only pandas.
- **pandas** for data shaping (`pip install pandas`).
- The bundled `scripts/shapley_attribution.py` is **stdlib-only** — no deps at all.

### Data shape

One row per unique path. Channels within a path are separated by a delimiter (`>`):

| path | total_conversions | total_null | total_conversion_value |
|------|-------------------|------------|------------------------|
| Facebook > Search > Email | 100 | 20 | 2200 |
| Search | 50 | 400 | 900 |

Include **non-converting** paths as `total_null` — the Markov model needs the failure
path to the (null) state to estimate transition probabilities correctly. Omitting them
biases removal effects.

## Recipes

### 1. Markov removal-effect + heuristics (ChannelAttribution)

```python
import pandas as pd
from ChannelAttribution import heuristic_models, markov_model

Data = pd.read_csv("journeys.csv")   # cols: path, total_conversions, total_conversion_value

# rules-based baselines: first-touch, last-touch, linear
H = heuristic_models(
    Data, var_path="path", var_conv="total_conversions",
    var_value="total_conversion_value", sep=">",
)

# data-driven: k-order Markov chain + removal effect
M = markov_model(
    Data, var_path="path", var_conv="total_conversions",
    var_value="total_conversion_value",
    var_null="total_null",   # pass non-converting paths for correct transitions
    order=1,                 # try order=2/3 and compare; higher needs more data
    nsim_start=100_000,      # random paths simulated to estimate removal effect
    max_step=None, sep=">", seed=0,
    out_more=True,           # also return removal_effects + transition_matrix
)

result = M["result"] if isinstance(M, dict) else M   # out_more=True → dict
removal = M["removal_effects"]        # channel importance before normalisation
transitions = M["transition_matrix"] # QA: does the graph look sane?

table = H.merge(result, on="channel_name")
print(table)   # first_touch / last_touch / linear_touch vs total_conversions (markov)
```

Key arguments (from the ChannelAttribution man page):
`var_path, var_conv, var_value, var_null, order=1, nsim_start=1e5, max_step=None,
out_more=False, sep=">", ncore=1, nfold=10, seed=0, conv_par=0.05, rate_step_sim=1.5`.
Raise `order` only with enough journeys — a 2nd/3rd-order chain has many more states
and over-fits on thin data; `conv_par`/`nfold` control the convergence tolerance.

**Removal effect** = the drop in total conversions when a channel is deleted from the
graph and all its paths reroute. Normalised across channels, it becomes the Markov
attribution weight. A channel with a big removal effect is a true bottleneck.

### 2. Shapley-value attribution (bundled, zero-dependency)

Shapley gives each channel its average marginal contribution across all coalitions —
the game-theoretically "fair" split, and efficient (credits sum to total conversions).
The bundled script collapses each journey to its channel *set* (order-independent) and
uses exact enumeration for <=8 channels, Monte-Carlo permutation sampling above that.

```bash
# CSV needs columns: path, conversions   (path uses the same '>' delimiter)
python3 scripts/shapley_attribution.py journeys.csv --sep ">" --nsim 20000 --seed 0
```
```
# Shapley attribution (exact); total conversions = 320.00
channel                conversions     share
Search                     111.667    34.90%
Email                      106.667    33.33%
Facebook                   101.667    31.77%
# sum check: 320.000 (should equal total 320.00)
```

Import it programmatically to join against the Markov/heuristic table:
```python
from scripts.shapley_attribution import attribute
shap, total, method = attribute("journeys.csv", sep=">", nsim=20000, seed=0)
```

### 3. Time-decay & position-based baselines (pandas, no extra deps)

ChannelAttribution gives first/last/linear; add the two other common rules yourself so
the comparison is complete:

```python
import pandas as pd
from collections import defaultdict

HALF_LIFE = 7.0            # days; time-decay weight = 0.5 ** (days_before_conv / half_life)
U_FIRST, U_LAST = 0.40, 0.40   # position-based (U-shaped) end weights; middle shares the rest

def rule_based(journeys):   # journeys: list[(channels:list[str], conv:float)]
    time_decay, u_shaped = defaultdict(float), defaultdict(float)
    for chans, conv in journeys:
        n = len(chans)
        # time-decay: later touches weighted more (assume 1 step == 1 unit here)
        w = [0.5 ** ((n - 1 - i)) for i in range(n)]
        s = sum(w)
        for c, wi in zip(chans, w):
            time_decay[c] += conv * wi / s
        # position-based U-shape
        if n == 1:
            u_shaped[chans[0]] += conv
        else:
            mid = (1 - U_FIRST - U_LAST) / max(n - 2, 1) if n > 2 else 0
            for i, c in enumerate(chans):
                if i == 0:      u_shaped[c] += conv * U_FIRST
                elif i == n-1:  u_shaped[c] += conv * U_LAST
                else:           u_shaped[c] += conv * mid
    return dict(time_decay), dict(u_shaped)
```

### 4. The money slide — naive vs data-driven gap

Merge every model into one table and compute the delta a data-driven model would move:
`markov_credit - last_click_credit`. Positive = last-click *under*-credits (usually
upper-funnel social/display/video); negative = last-click *over*-credits (usually brand
search and retargeting that sit last in the path). That delta is the reallocation story.

## Verify

- **Efficiency**: Shapley credits (and normalised Markov credits) must sum to total
  conversions. The bundled script prints a sum check — it must match `total`.
- **Sanity vs baselines**: on a single-channel-per-path dataset, all models collapse to
  the same answer. Confirm they do before trusting multi-touch numbers.
- **Order stability**: rerun `markov_model` with `order=1,2,3`. If credits swing wildly,
  you lack data for the higher order — report order=1.
- **Seed stability**: fix `seed`; Monte-Carlo (Markov `nsim_start`, Shapley `--nsim`)
  answers should be stable to ~1% across seeds. If not, raise the simulation count.
- **Transition matrix QA** (`out_more=True`): probabilities out of each state sum to 1;
  spot-check that dominant transitions match how the funnel really flows.
- Smoke-test the script offline:
  ```bash
  python3 -c "import ast; ast.parse(open('scripts/shapley_attribution.py').read()); print('ok')"
  ```

## Pitfalls

- **Correlation, not causation.** MTA re-slices credit among touches that *co-occur* with
  conversions; it cannot see holdout/counterfactual demand. Never set budgets on MTA alone
  — triangulate with `geo-incrementality-testing` and `marketing-mix-modeling`.
- **Dropping non-converting paths.** Without `var_null`/failure paths the Markov transition
  matrix is wrong and removal effects inflate. Always feed the nulls.
- **Order explosion.** `order=3` on a 10-channel funnel is thousands of states; it overfits
  and slows to a crawl. Start at 1, raise only with volume, cross-check with `nfold`.
- **Shapley cost.** Exact Shapley is O(n!·paths). The script auto-switches to sampling above
  8 channels — for 20+ channels keep `--nsim` high enough that the sum check is exact and
  ranks are stable, and consider grouping rare channels into "Other".
- **Cookie/consent gaps & walled gardens.** Post-iOS-14 and cookieless paths are truncated;
  a channel absent from observable paths gets zero MTA credit even if it drove demand. State
  the observability caveat with every MTA deck.
- **View-through vs click.** Decide up front whether impressions count as touches; mixing
  click and view touches without a rule silently double-credits display/social.
- **GPL licence.** ChannelAttribution is GPL(>=3). Fine for internal reports; get sign-off
  before shipping it inside a redistributed product. The bundled Shapley script has no such
  constraint.

## Sources

- ChannelAttribution — https://github.com/DavideAltomare/ChannelAttribution · https://pypi.org/project/ChannelAttribution/
- `markov_model` reference — https://rdrr.io/cran/ChannelAttribution/man/markov_model.html
- pychattr (pure-Python mirror) — https://github.com/jmwoloso/pychattr
