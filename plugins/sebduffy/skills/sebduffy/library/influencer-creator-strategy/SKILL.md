---
name: influencer-creator-strategy
category: strategy
description: >-
  Source, fraud-screen, cost and brief creators for a paid influencer campaign,
  then benchmark it with EMV and lock disclosure compliance. Trigger when a brief
  asks to build a creator roster, vet an influencer for fake followers, sanity-
  check a proposed fee against EMV/CPM/CPE, set engagement-rate floors, choose
  micro vs macro vs celebrity, or make sure #ad labelling passes ASA (UK) / FTC
  (US). Grounded in System1/Kantar creator-effectiveness evidence so the plan is
  built for brand impact, not just cheap reach — the desk-screen before you spend.
when_to_use:
  - A brief asks you to build or vet a creator/influencer roster for a campaign
  - You must fraud-screen a proposed creator (fake followers, bought engagement, geo mismatch)
  - Sanity-checking a creator's quoted fee against EMV, effective CPM or cost-per-engagement
  - Deciding the mix of nano/micro/macro/celebrity for a reach-vs-engagement objective
  - Writing an influencer brief that will actually build brand, not just chase views
  - Making a campaign's disclosure/labelling compliant with ASA (UK) or FTC (US) rules
  - Defending a creator line in a media plan or QBR with effectiveness evidence
when_not_to_use:
  - Sizing or profiling an audience with survey data — use audience-insight or share-of-search
  - Setting attention KPIs / aCPM for a paid media plan — use attention-planning-metrics
  - Pretesting the finished creative before airing — use creative-pretesting-framework
  - Building the whole channel media plan and budget split — use media-strategy
keywords:
  - influencer
  - creator economy
  - emv
  - earned media value
  - fake followers
  - fraud detection
  - engagement rate
  - micro influencer
  - disclosure
  - ftc
  - asa
  - cap code
  - creator brief
  - hypeauditor
  - cpm
  - cost per engagement
similar_to:
  - creative-pretesting-framework
  - attention-planning-metrics
  - media-strategy
  - audience-insight
inputs_needed: >-
  Campaign objective (awareness/consideration/conversion), target market and
  audience, budget, a shortlist of candidate creators with public metrics
  (followers, engagement rate, audience geo) or access to an audit tool, and the
  platform/regulator in scope (UK ASA vs US FTC).
produces: >-
  A screened creator roster with pass/review/reject verdicts, EMV and effective
  CPM/CPE benchmarks per creator, a tiering recommendation, a compliant creator
  brief with disclosure requirements, and a red-flag audit note for procurement.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Influencer & Creator Strategy

Turn a "let's use some influencers" brief into a screened, costed, compliant
creator plan built for brand impact. Four moves: **source → screen → cost →
brief**, with disclosure compliance baked in from the start.

## When to use

Use this when the deliverable is a creator/influencer campaign decision: who to
book, whether they are real, what a fair fee is, and how to keep it legal. It is
a defensible desk-screen and a strategy layer — it does not replace a paid audit
tool (HypeAuditor, Kolsquare, CreatorIQ) or a real brand-lift study, it makes
their outputs mean something and catches the obvious frauds before you pay.

## Prerequisites

- **No paid tools required for the desk-screen** — the helper uses public 2025
  benchmarks. For production vetting you want an audit tool (HypeAuditor
  Audience Quality Score, Kolsquare, Modash) to get real fake-follower % and
  audience geo; treat this skill's inputs as "fill from the audit export".
- `python3` (3.9+, stdlib only) for `scripts/creator_screen.py`.
- Know your regulator: **UK = ASA / CAP Code**, **US = FTC 16 CFR Part 255**.
  They differ in enforcement; both demand disclosure be prominent and up-front.

## The evidence that shapes the plan (System1 / Kantar)

Ground the strategy in what the 2025 creator-effectiveness studies actually found
— don't let a client buy reach and call it effectiveness:

- **Creators can build brands**: creator content delivered a long-term ROI index
  of ~151 (51% above the average channel) over two years, and beat industry
  norms for brand impact when done right.
- **But most creator ads underperform**: Kantar found platform engagement and
  effectiveness aligned in only ~1 in 3 pieces of creator content — engagement
  is NOT a proxy for brand-building.
- **Implication for the brief**: apply the same branding levers as any ad —
  early, distinctive brand assets; a clear message; emotional storytelling. A
  high-engagement creator with no branding discipline is a wasted spend.
- **Tier trade-off**: micro/nano creators win on engagement rate and community
  authenticity; macro/celebrity win on raw reach. Match to the objective, not to
  vanity follower counts.

## Recipe 1 — Fraud-screen a creator (do this BEFORE any fee talk)

Pull the candidate's public metrics (or the audit-tool export) and screen
against red-flag thresholds. Public 2025 benchmarks: ~81% of marketers hit
influencer fraud, and campaigns using creators with >30% fake followers saw ~58%
lower conversion.

Red flags the screen checks:

| Signal | Flag threshold | Why |
| --- | --- | --- |
| Engagement rate | below tier floor (nano 3% / micro 2% / macro 1%) | dead or bought audience |
| Suspicious followers | > 25% | fake-follower purchase |
| 7-day growth spike | > 15% with no viral post/press | bot injection |
| Generic comments | > 15% emoji/one-word/copy-paste | engagement pods |
| Audience geo gap | > 20pt vs target market | irrelevant / bought reach |
| HypeAuditor AQS | < 60 | low overall audience quality |

```bash
python3 scripts/creator_screen.py screen --tier micro \
    --er 2.4 --fake-pct 12 --growth-spike 8 \
    --generic-comment-pct 10 --audience-geo-gap 9 --aqs 78
# -> {"verdict": "PASS", "flag_count": 0, ...}
```

Verdict rule: **0 flags = PASS, 1–2 = REVIEW (ask the creator to explain), 3+ =
REJECT.** Any single flag on fake-follower % or AQS should trigger a full audit
regardless of the count.

## Recipe 2 — Cost sanity-check with EMV / CPM / CPE

EMV has no universal formula (Ayzenberg's index is the de-facto standard), so use
it as a **directional benchmark against the quoted fee**, never as the number you
promise a client. Formula used: `EMV = likes×$0.10 + comments×$1.00 +
(impressions/1000)×$8 CPM`. Tune the constants to your own paid-media CPM.

```bash
python3 scripts/creator_screen.py emv \
    --impressions 120000 --likes 8000 --comments 300 --fee 4000
# -> emv_to_fee_ratio, effective_cpm, effective_cpe
```

Read it like this:
- **emv_to_fee_ratio < 1** → you're paying more than the earned value; negotiate
  or justify with a strategic reason (audience fit, content usage rights).
- **effective_cpm** vs your paid-social CPM → is the creator premium worth it?
- **effective_cpe** → compare like-for-like across the roster to rank value.

Do not confuse EMV with ROI or sales — it is a media-value proxy for comparison
only. For real outcome measurement you need a brand-lift study or MMM.

## Recipe 3 — Tier the roster to the objective

- **Awareness / reach at scale** → 1–2 macro or celebrity anchors + a micro tail.
- **Consideration / trust / niche** → weight to micro (2–5% ER) and nano (3–8%
  ER); more creators, more authentic reach, lower unit cost.
- **Conversion / performance** → whitelist/boost the best-screened creators as
  paid social (Spark Ads etc.); creator content as the creative, your targeting.
- Always over-weight **audience fit and brand-safety** over follower count.

## Recipe 4 — Lock disclosure compliance into the brief

Non-negotiable, and a 2026 zero-tolerance enforcement area. Put this in the
contract and the brief, not just a verbal ask:

- **UK (ASA / CAP Code)**: any paid promotion or gifted-for-content post must be
  "obviously identifiable" as advertising. Use `#ad` (or "Ad") **prominently and
  up-front** — first thing seen, before "…see more". `#sp`, `#spon`, `#ambassador`
  or a hidden tag at the end are NOT sufficient.
- **US (FTC 16 CFR 255)**: disclosure must be "clear and conspicuous", in the same
  medium as the claim, and hard to miss; platform-only tools (e.g. "paid
  partnership" label) are recommended but not on their own sufficient.
- **Both**: disclose any material connection (payment, free product, affiliate,
  family/employee relationship); creators must not claim to have used a product
  they haven't; health/finance claims carry extra rules.
- Brief must also state: deliverables, usage/whitelisting rights and term,
  exclusivity window, approval workflow, and brand-asset/message requirements
  (from the System1/Kantar branding-lever point above).

## Verify

```bash
python3 scripts/creator_screen.py screen --tier micro --er 0.9 --fake-pct 34 --aqs 55
# expect verdict REJECT with multiple flags
python3 -c "import ast; ast.parse(open('scripts/creator_screen.py').read()); print('parse ok')"
```

Before sign-off, confirm: every rostered creator PASSED (or REVIEW-cleared) the
screen; each fee has an emv_to_fee_ratio you can defend; the brief names the exact
disclosure hashtag and placement for the campaign's regulator; and the brief
carries at least one branding lever, not just an engagement target.

## Pitfalls

- **Engagement ≠ effectiveness.** Kantar showed the two align only ~1/3 of the
  time. A viral, high-ER creator with no brand assets on screen builds nothing.
- **EMV is a benchmark, not a promise.** Never present EMV as ROI or as revenue;
  it is fee-negotiation and roster-ranking ammunition only.
- **A clean platform "paid partnership" tag is not full compliance** under ASA or
  FTC — you still need the in-caption disclosure, up-front.
- **Desk-screen ≠ audit.** The helper's thresholds catch obvious fraud; a REVIEW
  or a big campaign still needs a paid audit tool for real fake-follower % and
  audience geography.
- **Follower count is a vanity input.** Book on audience fit, engagement quality
  and brand safety; a smaller, screened, on-target creator usually out-converts a
  big bought one.
- **Tune the EMV constants.** The default $0.10/like, $1/comment, $8 CPM are
  generic — replace with your own paid-media costs or the numbers are meaningless.
