---
name: creative-pretesting-framework
category: strategy
description: >-
  Design a real-world creative pretest (System1 Test Your Ad, Kantar LINK+,
  Neurons Predict AI) and interpret the scores into a hard go/refine/kill gate
  BEFORE media commit. Use to spec a test brief, pick the right vendor for the
  question, read a Star/Spike/Fluency or LINK+ percentile readout without
  fooling yourself, or build a benchmark gate for a creative review. Turns a
  vendor PDF into a defensible spend decision — not a replacement for the test
  itself, the layer that makes its numbers mean something.
when_to_use:
  - You have finished or animatic creative and need a real pretest specced before it airs
  - A System1, Kantar LINK+, or Neurons readout landed and you must interpret it into a decision
  - Someone asks "is this ad good enough to run" and you need a benchmark gate, not a vibe
  - Choosing which pretest vendor/method fits the question (long-term brand vs short-term sales vs attention)
  - Setting a pass bar for a creative gate deck or client sign-off before budget release
  - Reconciling a strong emotional score with weak branding, or a good ad that mis-attributes
when_not_to_use:
  - You want a fast directional pre-screen with no vendor/budget — use synthetic-audience-message-testing
  - You want an open moderated discussion of the creative — use synthetic-focus-group
  - You need to build the audience/personas first — use persona-population-builder
  - You are writing or diagnosing the ad copy itself — use advertising-strategy-copy
keywords:
  - creative pretesting
  - ad testing
  - system1
  - test your ad
  - kantar link
  - neurons predict
  - star rating
  - spike rating
  - fluency
  - copy testing
  - creative effectiveness
  - pre-flight
  - benchmark gate
  - esov
  - emotional response
  - go no-go
similar_to:
  - synthetic-audience-message-testing
  - synthetic-focus-group
  - effectiveness-case
  - advertising-strategy-copy
inputs_needed: The creative (finished film, animatic, key frame, or static); the decision at stake (air / refine / kill, or pick between cuts); target audience + market; a vendor readout PDF if a test already ran; budget/ESOV context if judging short-term.
produces: A pretest brief (vendor, method, cells, sample, KPIs, pass bar) OR a scored gate readout — verdict (GO / REFINE / KILL), per-metric band, and the reasons — plus a one-line recommendation for the spend decision.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Creative Pretesting Framework

Spec a **real** creative pretest and read its scores into a spend decision. This
skill covers the three vendors an agency actually commissions — **System1 Test
Your Ad**, **Kantar LINK+**, and **Neurons Predict AI** — plus a gate script
that classifies scores the same way every time so a strategist and a client read
the same PDF and reach the same verdict.

This is the interpretation and gating layer. It does not run the test (that is a
paid vendor panel or AI model) and it does not invent scores. If no test has run
yet, it produces the brief; if a readout exists, it produces the gate.

## When to use

Reach for this when finished or animatic creative is heading toward a spend
decision and someone needs a defensible answer to "is it good enough, and how do
we know". Also use it to pick the right method: the vendors answer different
questions, and testing the wrong thing wastes the fee.

## Prerequisites

- **No API/keys required** for the framework itself — the gate script is stdlib
  Python and runs offline.
- **A vendor account** to actually run a test: System1 (system1group.com), Kantar
  Marketplace, or Neurons (neuronsinc.com). These are paid. This skill assumes
  either you are commissioning one or a readout already exists.
- macOS `python3` (3.9) for `scripts/interpret_scores.py`. No pip installs.
- Honesty gate: never fabricate a score. If a number is missing, say so and mark
  the readout INCOMPLETE — the script does this for you.

## Vendor selection — test the right question

| Question you're answering | Vendor / method | Core output |
|---|---|---|
| Will this build the brand long-term? | **System1 Test Your Ad** | Star Rating 1.0–5.0 (emotional response of real people) |
| Will it drive sales in 8–10 weeks? | **System1 Spike** (or LINK+ STSL) | Spike 1.00–1.33+; LINK+ Short-Term Sales Likelihood |
| Is branding strong enough to get credit? | **System1 Fluency** / LINK+ Branding | Fluency 0–100 |
| Full validated diagnostic (branding, persuasion, engagement, LT equity) | **Kantar LINK+** | Percentile vs channel norm (0–30 / 30–70 / 70–100) |
| Where will the eye go in the first seconds? | **Neurons Predict AI** | Attention heatmap + Focus / Cognitive Demand / Clarity / Engagement |

Rule of thumb: **System1** for the emotional/long-term growth question on film;
**LINK+** when you need a deep validated diagnostic and channel-specific norms
(260k+ test database); **Neurons** for pre-human, fast attention screening of
static/thumbnail/key-frame and early cutdowns. They are complementary, not rival
— a common agency stack is Neurons early (cheap, instant), System1 or LINK+ on
the finished film.

## Recipe A — write the pretest brief (no test yet)

1. **State the decision.** Air / refine / kill, or "pick between cut A and B".
   The decision picks the vendor (table above) and the pass bar.
2. **Pick cells.** One finished ad = one cell. Comparing cuts = one cell each,
   same sample frame. A/B a single element (end-frame, VO) = matched cells.
3. **Set the pass bar UP FRONT, before you see results.** e.g. "Ship only if
   Star >= 3.0 AND Fluency >= 83." Pre-committing the bar is what stops
   post-hoc rationalisation of a weak ad.
4. **Sample & audience.** System1 runs ~150 nationally representative per ad by
   default; match the buying audience where the platform allows. Neurons needs
   no sample (AI model). LINK+ sample is quote-dependent.
5. **Diagnostics.** Add only what changes a decision — Right Brain Richness /
   fluent devices (System1), persuasion + branding diagnostics (LINK+), heatmap
   + Focus (Neurons). Every extra diagnostic is spend and dilution.
6. **Hand over** the brief: vendor, method, cells, sample, KPIs, and the
   pre-agreed pass bar. That last line is the whole point.

## Recipe B — interpret a readout into a gate (test done)

1. **Pull the headline numbers** from the vendor PDF. For System1: Star, Spike,
   Fluency. For LINK+: the percentile band per metric (0–30 low, 30–70 mid,
   70–100 high) and STSL. For Neurons: Focus / Cognitive Demand / Clarity /
   Engagement (each 0–100) and the heatmap.
2. **Run the gate** for System1-shape scores:

   ```bash
   echo '{"vendor":"system1","star":3.4,"spike":1.12,"fluency":88}' \
     | python3 scripts/interpret_scores.py
   # -> {"verdict":"GO", ... "reasons":["Star 3.4 (Good) clears the 3.0 bar."]}
   ```

   Or pass flags: `python3 scripts/interpret_scores.py --star 2.1 --spike 0.95 --fluency 70`.
3. **Read the bands, not just the number.** Published System1 bands:
   - **Star (long-term growth):** 1.0 Low · 2.0 Modest · 3.0 Good · 4.0 Strong · 5.0 Exceptional.
   - **Spike (short-term sales):** <=1.00 Low · 1.00–1.09 Modest · 1.10–1.18 Good · 1.19–1.32 Strong · >=1.33 Exceptional.
   - **Fluency (branding):** <=72 Low · 73–82 Modest · 83–90 Good · 91–94 Strong · >=95 Exceptional.
   The UK all-ads average sits around 2 Stars, so a 3.0 is genuinely above the
   crowd — most ads are 1–2 Stars. Do not treat 3.0 as mediocre.
4. **Cross-check the contradictions** (the real skill):
   - **High Star, low Fluency** → emotionally powerful but the brand won't get
     credit. Fix distinctive assets/branding moments; don't just re-shoot.
   - **High Spike, low Star** → sales bump now, no equity built. Fine for a
     promo burst, wrong for a brand campaign.
   - **Good scores, weak Neurons Focus on the logo/pack** → attention is
     landing everywhere but the brand. Re-edit for the branded moment.
5. **Factor ESOV, don't skip it.** System1 states Star combined with media spend
   (ESOV) predicts up to ~48% of brand growth — a 3-Star ad under-funded still
   underperforms a 2-Star ad with share-of-voice behind it. Report the verdict
   *and* the spend condition. Deep equity work belongs in effectiveness-case.
6. **Write the recommendation** in one line: verdict, the binding reason, and
   the condition ("GO if ESOV positive; branding is the only soft spot").

## Verify

- Script smoke test (offline, no deps):
  ```bash
  python3 scripts/interpret_scores.py --star 3.4 --spike 1.12 --fluency 88   # GO
  python3 scripts/interpret_scores.py --star 1.4 --fluency 60                # KILL / REWORK
  ```
- Sanity-check bands against the live source if in doubt:
  system1group.com/uncategorized/our-metrics-explained.
- Confirm the pass bar was set *before* results were seen — if it wasn't, flag
  the readout as post-hoc and lower your confidence.

## Pitfalls

- **Never fabricate or "estimate" a vendor score.** If the PDF doesn't state it,
  it's missing — mark INCOMPLETE. Synthetic guesses belong in
  synthetic-audience-message-testing, clearly labelled as directional.
- **Don't compare across vendors on a shared scale.** A System1 3-Star and a
  LINK+ 70th-percentile are not the same currency; benchmark each to its own norm.
- **Star measures long-term, Spike short-term — reporting one as "the score" is
  the classic error.** Always report both when the brief needs sales *and* brand.
- **Neurons predicts attention, not persuasion or emotion.** Great for the first
  few seconds and static assets; it does not replace human emotional testing.
- **A single 150-person test cell is directional at the margins.** Treat a
  0.2-Star gap between cuts as a tie, not a winner; look for meaningful gaps.
- **Testing the wrong question wastes the fee.** Pick the vendor from the
  decision (table), not from whichever account you already have open.
- **Thresholds in the script are defensible defaults, not gospel.** Override
  `STAR_GO` / `FLUENCY_MIN` per brief and category, and say so in the readout.
