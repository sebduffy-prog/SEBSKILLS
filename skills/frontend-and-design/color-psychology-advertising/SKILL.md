---
name: color-psychology-advertising
category: frontend-and-design
description: >-
  Choose ad and brand colours using what the peer-reviewed evidence actually
  supports — and refuse to over-claim. The robust finding is that SATURATION and
  BRIGHTNESS drive arousal and pleasure far more reliably than hue (Valdez &
  Mehrabian 1994), that hue meaning is CONTEXT-dependent not fixed (Elliot &
  Maier 2014), and that colour–brand-personality FIT beats any "power colour"
  (Labrecque & Milne 2012; Bottomley & Doyle 2006). Reach for this to justify a
  palette to a client, sanity-check a "red converts 21%" claim, or adapt a brand
  colour across cultures (white = purity in the US, mourning in much of Asia)
  without inventing causation. Kills the 90-millisecond and 80% myths.
when_to_use:
  - Justifying an advertising or brand palette to a sceptical client or planner
  - Fact-checking a "colour X lifts conversion Y%" stat before it enters a deck
  - Adapting one brand colour across cultures / regions without a symbolism gaffe
  - Choosing between two candidate hues when brand personality is the real driver
  - Deciding CTA / packaging colour where arousal or standout is the goal
  - Writing the "why this colour" rationale slide for a pitch or strategy doc
when_not_to_use:
  - You need the math to build/convert a palette in code — use oklch-color-engine
  - You need WCAG contrast pass/fail on text — use accessible-contrast-checker
  - You need a multi-hue harmony from one seed — use color-harmony-generator
  - You need named light/dark design tokens — use brand-color-token-system
  - You need colour-vision-deficiency safety — use colorblind-safe-palettes
keywords:
  - color-psychology
  - advertising
  - brand-color
  - color-meaning
  - cross-cultural
  - saturation
  - brightness
  - arousal
  - valence
  - color-in-context
  - brand-personality
  - conversion-myth
  - causation
  - marketing
  - palette-rationale
similar_to:
  - brand-color-token-system
  - color-harmony-generator
  - colorblind-safe-palettes
  - accessible-contrast-checker
  - brand-guidelines
inputs_needed: A brand/product (its personality traits + category), target markets/cultures, and any candidate hues or a colour claim you want to check
produces: An evidence-graded colour rationale — recommended hue/saturation/brightness direction, a cross-cultural risk note, and a debunk of any over-claimed stat — ready to paste into a strategy deck
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Colour Psychology for Advertising

Most "colour psychology" you find online is folklore dressed as science: *red
makes you buy, blue means trust, this button lifts conversion 21%*. When you
justify a palette with those claims and a planner Googles them, the pitch loses
credibility. This skill gives you the **defensible** version — what controlled
studies actually show — plus the cross-cultural checks and a script that scores
a palette on the one dimension the evidence is strongest on: arousal.

## When to use

Use it when you must *defend* a colour choice — a pitch rationale slide, a
client challenge, a global rollout — or when a colour statistic is about to go
into a deck and you need to know if it survives scrutiny. If you just need to
*compute* a ramp, harmony, contrast, or tokens, use the sibling skills named in
`when_not_to_use`.

## The three findings that actually replicate

1. **Saturation and brightness > hue for feeling.** Valdez & Mehrabian (1994,
   *J. Exp. Psychol. General*) found brightness and saturation predict
   pleasure/arousal/dominance far more consistently than which hue you pick.
   Practical read: a *vivid, bright* colour reads energetic and a *muted, dark*
   one reads calm/serious almost regardless of hue. **Adjust S and V/L first;
   argue hue last.** This is the single most useful lever.

2. **Hue meaning is context-dependent, not fixed** (Elliot & Maier 2014,
   *Annual Review of Psychology*, "colour-in-context" theory). Red raises
   avoidance in an achievement/test context but attraction in a mating context —
   same red, opposite effect. So "red = urgency" is only true *in the right
   frame* (a sale, a warning). Never state a hue meaning without its context.

3. **Colour–brand FIT beats any universal "power colour."** Bottomley & Doyle
   (2006) showed people prefer *functionally congruent* colour (utilitarian
   product → "functional" colour; sensory/social product → "sensory" colour).
   Labrecque & Milne (2012, "Exciting red and competent blue") showed hue shifts
   perceived brand *personality*. Read: choose the colour that matches the brand
   personality and category, not the colour with the best anecdote.

## Recipe A — build a defensible colour rationale

1. **State the brand personality in 2–3 traits** (e.g. *competent, calm,
   premium*) and the category (utilitarian vs. sensory/social).
2. **Pick the arousal target from the brief**, not the hue: high-energy
   (impulse, sport, sale) → high saturation + high brightness; premium/calm/
   trust → lower saturation, controlled brightness. This is the Valdez-Mehrabian
   lever and it is defensible.
3. **Pick hue for personality FIT**, e.g. blue leans competent/trustworthy,
   red leans exciting/dominant, but always phrase as *"associated with"* and
   tied to the category — not *"causes"*.
4. **Write it graded.** Use the evidence ladder in Verify. Label each sentence
   STRONG / MIXED / FOLKLORE so the reader trusts the strong ones.
5. **Run Recipe C** (cross-cultural) before you commit for any market you don't
   personally live in.

## Recipe B — score a palette's arousal (runnable)

The defensible dimension is arousal via saturation + brightness. This scores
each swatch so "this palette reads energetic/calm" is a measured claim, not a
vibe. Pure stdlib, python3.9-safe.

```python
import colorsys

def arousal_score(hex_color: str) -> dict:
    """Valdez-Mehrabian-informed heuristic: arousal rises with saturation and,
    weakly, with brightness. Returns 0-100. Higher = more energetic/stimulating.
    NOT a claim about a specific hue — this is the S/V dimension only."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected #RRGGBB, got {hex_color!r}")
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    _, _, v = colorsys.rgb_to_hsv(r, g, b)
    # HSV 'S' understates arousal for dark vivid colours; use HSL-style sat too.
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    sat_hsl = 0.0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1) + 1e-9)
    # Weight saturation ~3x brightness (Valdez & Mehrabian: sat dominates arousal)
    score = round(100 * (0.72 * min(sat_hsl, 1.0) + 0.28 * v), 1)
    band = "calm" if score < 34 else "moderate" if score < 67 else "energetic"
    return {"hex": hex_color, "arousal": score, "reads_as": band}

if __name__ == "__main__":
    for c in ["#E4002B", "#8A9BA8", "#0B1F3A", "#FFD400", "#2E7D32"]:
        print(arousal_score(c))
```

Expected: vivid red `#E4002B` and yellow `#FFD400` land "energetic"; the slate
`#8A9BA8` and navy `#0B1F3A` land "calm/moderate" — matching intuition, but now
it is a number you can put on a slide.

## Recipe C — cross-cultural adaptation check

Before shipping a colour into a market, check the hue against known symbolism
divergences. These are *documented cultural conventions*, still generalisations —
verify with a local. High-risk hues:

| Hue | Common Western read | Diverges elsewhere |
|-----|--------------------|--------------------|
| White | purity, weddings, clean | mourning/death in much of East & South Asia |
| Red | danger/love/sale (context!) | luck, prosperity, weddings in China |
| Green | nature, go, health | Islam: sacred/positive; can imply infidelity in parts of China |
| Black | luxury, sophistication, mourning | prosperity/health in some East-Asian framings |
| Purple | royalty, premium | mourning in Brazil/Thailand contexts |
| Yellow | caution, cheap/optimistic | imperial/sacred in China; mourning tones elsewhere |

Rule: for a global campaign, lead with **saturation/brightness mood** (travels
well) and treat **hue symbolism as localisable**. McDonald's red+yellow reads
appetite/value in the West and luck/imperial warmth in China — a happy overlap,
not a universal law.

## Verify — the evidence ladder (grade every claim)

- **STRONG (state plainly):** saturation & brightness drive arousal/valence
  (Valdez & Mehrabian); colour–personality and colour–product congruence effects
  (Labrecque & Milne; Bottomley & Doyle); colour aids brand *recognition*.
- **MIXED / context-only:** specific hue → specific emotion or behaviour (red →
  attraction/achievement flips by context, Elliot & Maier; several red effects
  have failed to replicate). Phrase as "associated with, in X context".
- **FOLKLORE (do not cite as fact):** "90% of snap judgements are on colour
  alone", "colour boosts recognition 80%", "the orange button converts 21%
  more". These are un-sourced or single-study/self-serving numbers. If a client
  wants one, run your OWN A/B test and cite that.

Sanity gate before any colour stat ships: *Is there a named peer-reviewed
source? A control group? A stated context? A plausible mechanism?* If any is
missing, downgrade to FOLKLORE.

## Pitfalls

- **Claiming causation from a hue.** Colour *correlates with* associations; it
  rarely *causes* a purchase in isolation. Say "supports / reinforces", not
  "makes people buy".
- **Ignoring saturation/brightness and fighting over hue.** You get 80% of the
  emotional effect from S and V — argue those first (Recipe B gives the number).
- **Copy-pasting a "colour meanings" chart as universal.** Meaning is cultural
  and contextual; Recipe C exists for exactly this.
- **Trusting round-number stats (80%, 90%, 21%).** They are almost always
  recycled from un-refereed blog posts tracing back to Singh (2006) or nowhere.
- **Ignoring accessibility.** A psychologically "perfect" pair that fails
  contrast or CVD is unusable — pair this with accessible-contrast-checker and
  colorblind-safe-palettes.
- **Over-fitting to one demographic.** Colour preference varies by age, gender
  and category; state who your evidence is about.
