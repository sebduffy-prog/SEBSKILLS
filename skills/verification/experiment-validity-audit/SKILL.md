---
name: experiment-validity-audit
category: verification
description: >
  Gate an A/B test result before anyone calls a winner — run the four integrity checks that catch most false
  positives: Sample Ratio Mismatch (chi-square, Fabijan et al. threshold p<0.0005), peeking / repeated-looks alpha
  inflation, power & minimum-detectable-effect (was the test even big enough?), and novelty/primacy decay via early-
  vs-late windows. Use this whenever someone says "the test won", "ship the variant", "is this significant",
  "the uplift is X%", or hands you a dashboard screenshot. Pushy on purpose: no result ships past this gate un-audited.
when_to_use:
  - An experiment/A-B/multivariate test is being declared a winner and about to inform a spend or creative decision
  - You need to confirm traffic split is clean (SRM) before trusting ANY metric in the readout
  - Someone peeked daily / stopped early and you must judge whether the significance is real
  - Checking a test was adequately powered, or sizing one before launch (n per arm / MDE)
  - An early uplift looks too good — suspect novelty or primacy effect and want the early-vs-late split
when_not_to_use:
  - Recomputing t/F/chi2/p consistency or GRIM/GRIMMER on already-reported stats → use stat-check-review
  - Appraising overall study DESIGN quality / confounds beyond validity gates → use research-methodology-review
  - Verifying non-numeric factual claims or quotes in the readout → use claim-verifier
  - Building or running the analysis pipeline on raw event data from scratch → use data-analysis skills
keywords: [srm, sample ratio mismatch, ab test, a/b testing, chi-square, peeking, alpha spending, statistical power, mde, minimum detectable effect, novelty effect, primacy effect, false positive, experiment, conversion rate, sequential testing]
similar_to: [stat-check-review, research-methodology-review, claim-verifier, self-consistency-check]
inputs_needed:
  - Per-arm counts (users/sessions assigned) and the intended split (e.g. 50/50)
  - The metric readout — baseline rate, observed lift, claimed p-value or confidence
  - How many times the result was looked at / whether it was stopped early
  - If available, the metric split by an early window vs a later window (for novelty)
produces: A GO / NO-GO integrity verdict per gate (SRM, peeking, power/MDE, novelty) with the recomputed numbers and the fix
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Experiment Validity Audit

Four gates every A/B result must clear before it's trusted. A "significant winner" that fails
**any** gate is not a winner — it's an artifact. Run the gates in order; a failed SRM check
invalidates every downstream metric, so start there.

The helper `scripts/validity_audit.py` runs on macOS system `python3` (3.9) with **no
third-party deps** — it uses `scipy` if present and falls back to exact stdlib math otherwise.

## When to use

Reach for this the moment a test is being called. Advertising/media context: variant creative,
landing pages, bidding strategies, email subject lines, audience splits — all routinely shipped on
false positives because nobody checked the split was clean or the test was long enough.

## Prerequisites

- `python3` (3.9+). `scipy` optional (auto-detected); everything works without it.
- The four inputs above. You can run any gate independently — partial data still audits partially.
- No API keys. Nothing leaves the machine.

## Gate 1 — Sample Ratio Mismatch (run first, always)

If the *observed* assignment split deviates from the *intended* split more than chance allows, the
randomisation or logging is broken and **no metric can be trusted**. Test with a chi-square
goodness-of-fit; alarm at **p < 0.0005** (Fabijan et al., KDD '19 — a stricter bar than 0.05
because SRM is common and catastrophic).

```bash
# 50/50 test, 50120 vs 49880 assigned:
python3 scripts/validity_audit.py srm --counts 50120 49880
#   p: 0.4479  srm: False   -> split is clean, proceed

# Same magnitude gap but real breakage:
python3 scripts/validity_audit.py srm --counts 52000 48000
#   p: 1.1e-36  srm: True    -> STOP. Do not read the metrics.

# Unequal / multi-arm: pass expected ratios (auto-normalised):
python3 scripts/validity_audit.py srm --counts 9100 4900 --expected 0.65 0.35
python3 scripts/validity_audit.py srm --counts 33500 33200 33990   # 3 equal arms
```

**If SRM fires:** do not debug the metric — debug the pipeline. Common causes: redirect/latency
bias (one arm loads slower and users bounce before assignment logs), bot filtering applied to one
arm, a broken randomisation hash, or assignment logged at a different point than exposure.

## Gate 2 — Peeking / repeated looks

A fixed-horizon p<0.05 test is only valid if you look **once**, at the pre-planned end. Each extra
peek at "is it significant yet?" inflates the false-positive rate. Five daily looks at nominal 0.05
turns the real error rate into ~0.23.

```bash
python3 scripts/validity_audit.py peek --looks 5
#   naive_actual_fpr_if_uncorrected: 0.226   <- what you actually risked
#   bonferroni_alpha_per_look: 0.010         <- corrected threshold (conservative)
#   sidak_alpha_per_look: 0.0102
```

**Fix:** either (a) pre-register one analysis at a fixed n and honour it, (b) use the corrected
per-look alpha above, or (c) adopt an always-valid method (mSPRT / sequential testing, alpha-
spending like O'Brien-Fleming) that is designed for continuous monitoring. If the win only appears
at one mid-experiment peek and evaporates later, it was noise.

## Gate 3 — Power / MDE (was it big enough?)

An underpowered test that shows "no significant difference" proves nothing, and one that squeaks
over the line on tiny n is fragile. Size before launch; sanity-check after.

```bash
# How many users per arm to detect a 5% relative lift on a 10% baseline?
python3 scripts/validity_audit.py power --baseline 0.10 --mde-rel 0.05
#   n_per_arm: 57763   total_n: 115526

# You only have 40k/arm — what's the smallest lift you could actually detect?
python3 scripts/validity_audit.py power --baseline 0.10 --n 40000
#   detectable_mde_rel: 0.060   -> anything smaller than a 6% lift is invisible

# Absolute MDE and custom alpha/power also supported:
python3 scripts/validity_audit.py power --baseline 0.10 --mde-abs 0.01 --alpha 0.05 --power 0.9
```

**Read it as:** if the observed lift is *below* the detectable MDE for the n you ran, "not
significant" means "underpowered", not "no effect". If a "winner" needed the full sample to reach
p<0.05, expect it to regress.

## Gate 4 — Novelty / primacy decay

Early uplift is often users reacting to *change*, not *quality* (novelty), or a temporary dip as
regulars relearn (primacy). Split the metric into an early window and a later window and compare
the lift.

```bash
# early (ctrl trt) vs late (ctrl trt) conversion rates:
python3 scripts/validity_audit.py novelty --early 0.112 0.101 --late 0.104 0.103
#   early_lift_rel, late_lift_rel, lift_decay_rel, novelty_suspected: True/False
```

**If novelty is suspected** (late lift < ~50% of early lift): re-read on a fresh later window,
segment by new vs returning users, or hold the variant out to a small control for a few more weeks
before rolling out. Decisions made on week-1 numbers routinely reverse by week 4.

## Verify

```bash
python3 -c "import ast; ast.parse(open('scripts/validity_audit.py').read()); print('syntax ok')"
python3 scripts/validity_audit.py srm --counts 52000 48000     # expect srm: True
python3 scripts/validity_audit.py power --baseline 0.10 --mde-rel 0.05  # expect ~57763/arm
```
Cross-check one SRM by hand: chi2 = sum((obs-exp)^2/exp); for 52000/48000 vs 50000/50000 that's
(2000^2/50000)*2 = 160, p(df=1) ~ 1e-36. Matches.

## Pitfalls

- **Reading metrics before clearing SRM.** The single most common mistake. SRM first, every time.
- **SRM on tiny samples.** Chi-square needs reasonable expected counts (>~5 per cell). With a few
  hundred users a real mismatch may not reach p<0.0005 yet — re-check as the test fills.
- **Treating p<0.0005 as arbitrary.** It's deliberately strict: SRM is frequent and poisons
  everything, so the community tolerates a higher miss rate to avoid crying wolf. Don't relax it.
- **One-sided vs two-sided.** The power calc here is two-sided (`alpha/2`); match your test's tails
  or the n will be wrong.
- **Proportions only.** The power/MDE math is for binary/conversion metrics. Continuous metrics
  (revenue, time-on-site) need a variance estimate and a different formula — don't reuse these n's.
- **Ratio metrics (per-session within user).** SRM and naive t-tests assume independent units;
  clustered/ratio metrics need the delta method or bootstrap, not this.
- **Novelty flag is a heuristic**, not a test — use it to decide whether to *keep running*, not to
  overturn a clean, powered, peek-corrected result on its own.
