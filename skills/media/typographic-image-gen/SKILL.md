---
name: typographic-image-gen
category: media
description: >
  Generate ad comps where the IN-IMAGE TEXT is legible, correctly spelled, and on-brand — OOH/billboard
  posters, pack shots, price flashes, menus, infographics — using the 2026 text step-change models:
  Nano Banana Pro (Gemini 3 Pro Image), FLUX.2, Seedream 5.0 Pro, GPT Image 2. Use when someone says
  "billboard/poster with this headline baked in", "text must say EXACTLY…", "readable copy in the
  image", "packaging comp", "which model renders text best", or gets garbled words from a generic model.
  Covers the model-picker, verbatim text-locking prompts, OOH aspect ratios, and a unified fal runner.
when_to_use:
  - A comp needs a headline, tagline, price, or pack copy rendered LEGIBLY and spelled EXACTLY right
  - Deciding which model to reach for when text accuracy is the deciding factor (Nano Banana Pro vs FLUX.2 vs Seedream 5 vs GPT Image 2)
  - OOH/DOOH layouts — 48-sheet, 6-sheet, bus-side, digital screen — where copy placement and hierarchy matter
  - Packaging / pack-shot comps where the label, variant name, and claims must read correctly
  - Infographics, menus, price lists, or offer flashes with multiple exact text elements
  - You got misspelled or gibberish words from a generic diffusion model and need a fix
when_not_to_use:
  - Photoreal art/edit with no critical text, and you want the native Flux workflow → use flux-image-gen
  - You specifically want Google's native Gemini workflow (character/product consistency) → use nano-banana-image
  - The final layout should be editable vector text over a plate, not baked pixels → use canvas-design (or set type in the design tool)
  - You need an animated/video version, not a still → use video-gen-pipeline
  - You just need a subject cut out or background swapped, no generation → use background-removal-batch
keywords: [typographic image, in-image text, legible text, ooh, billboard, poster, packaging comp, pack shot, price point, offer flash, infographic, nano banana pro, gemini 3 pro image, flux.2, seedream 5, gpt image 2, text rendering, fal, aspect ratio, headline]
similar_to: [flux-image-gen, nano-banana-image, canvas-design, video-gen-pipeline, background-removal-batch]
inputs_needed:
  - The EXACT text strings (headline, subhead, price, legal, pack copy) — verbatim, with correct casing
  - The format/aspect ratio (48-sheet 3:1, 6-sheet portrait, 1:1 social, A-series pack) and any brand colours/fonts to describe
  - A FAL_KEY (fal.ai) for FLUX.2 / Seedream / GPT Image 2, or a GEMINI_API_KEY for Nano Banana Pro
  - Any reference image(s) — product pack, logo, style plate — to keep on-brand
produces: A flattened comp image (.png/.jpg) with baked-in text, at the chosen aspect ratio/resolution
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Typographic Image Gen (legible in-image text for comps)

Generic diffusion models garble words. The 2026 text step-change models don't — reliably enough for
client-facing OOH and packaging **comps** (not final print). This skill is the *craft* on top of the
raw model APIs: the model-picker, the prompt discipline that locks text verbatim, the right aspect
ratios, and a single runner that drives every fal-hosted text model. For the native BFL/Gemini
mechanics it defers to the sibling skills in `when_not_to_use`.

> Comps, not artwork. Baked pixel-text can still slip a character. Always proof against the brief and,
> for anything going to print, rebuild the type as editable vector in the design tool.

## When to use

Any deliverable where the words inside the image have to be **right** — spelled correctly, legible at
the viewing distance, and placed in a sensible hierarchy. If text isn't the deciding factor, the
sibling image skills are simpler.

## Prerequisites (this Mac)

- **A key for one provider:**
  - `export FAL_KEY=...` — one door to FLUX.2, Seedream, GPT Image 2 (used by the runner below).
  - `export GEMINI_API_KEY=...` — for **Nano Banana Pro** (`gemini-3-pro-image-preview`); drive it
    via the `nano-banana-image` sibling skill (native Gemini `generateContent`).
- No pip installs needed for the runner — it's stdlib `urllib` only (py3.9 fine).
- The **exact copy** written down verbatim. Garbage in = garbled out.

## Model picker (2026)

| Model | fal endpoint / access | Text superpower | Reach for it when |
|---|---|---|---|
| **Nano Banana Pro** (Gemini 3 Pro Image) | `gemini-3-pro-image-preview` (native Gemini) | Best-in-class long/paragraph text, infographics, multilingual; 1K/2K/4K | Dense copy, real infographics, diagrams-from-notes, Search-grounded facts |
| **FLUX.2 [pro]** | `fal-ai/flux-2-pro` | Complex typography, UI/poster layouts, up to 4 MP; `[flex]` tuned for text-heavy design | Poster/OOH layouts, UI mockups, when you want the BFL look |
| **Seedream 5.0 Pro** | `fal-ai/bytedance/seedream/v4/text-to-image` (v4 stable; 5.0 Pro rolling out) | Poster/layout composition, 10+ languages, layer/pixel editing, up to 4K | Multilingual packs, high-density infographics, up to 15 images/prompt |
| **GPT Image 2** | `openai/gpt-image-2` | ~99% text accuracy, native 4K, CJK/curved/small type | The hardest exact-text jobs; legal lines, tiny type, curved pack surfaces |

Rule of thumb: **exact tiny/legal or curved-surface text → GPT Image 2**; **rich infographic/paragraph
→ Nano Banana Pro**; **poster/OOH art direction → FLUX.2**; **multilingual pack density → Seedream**.
When text accuracy is critical, generate the same prompt on two of them and pick the clean take.

## The verbatim text-locking prompt discipline

This is what separates a usable comp from mush. Every prompt should:

1. **Quote text literally, once, in double quotes.** `The headline reads exactly "GET GOING".`
   Don't paraphrase or repeat the string in different casing — models render what they see.
2. **State casing and punctuation explicitly** — "all caps, no full stop", "sentence case".
3. **Name each text element and its role/position**: headline, subhead, price flash, legal line,
   logo lockup — and where each sits (top-left, lower third, bottom strip).
4. **Give hierarchy in words**: "dominant headline, small legal line at the very bottom".
5. **Describe type feel, not a font file**: "bold grotesque sans, tight tracking" — models can't load
   your licensed font, so approximate then replace vector-side later.
6. **Keep total distinct strings low** (≤3–4 for one pass). More strings = more error surface; split
   into elements you composite, or use a model's editing pass to add each.
7. **Leave deliberate empty space** ("clean sky upper third for the headline") so text has room.
8. **Negative-guard** where supported: "no extra text, no watermark, no lorem ipsum, no duplicated
   letters".

## Recipes

### 1. OOH poster with a locked headline (FLUX.2 via the runner)

```bash
export FAL_KEY=...   # fal.ai key
python3 scripts/fal_text_image.py \
  --endpoint fal-ai/flux-2-pro \
  --size 2048x683 \
  --prompt 'Landscape 48-sheet billboard comp, 3:1. Sunlit empty coastal road.
Dominant headline top-left reads exactly "GET GOING" in bold condensed grotesque
sans, all caps, tight tracking, warm off-white. Small brand logo lockup bottom-right.
Tiny legal line along the very bottom edge reads exactly "Terms apply." Clean
composition, generous negative space for the headline, no extra text, no watermark.' \
  --seed 7 --out ooh_getgoing.png
```

`3:1 ≈ 2048x683` (48-sheet). Other UK OOH: **6-sheet** portrait ~`1200x1800` (2:3), **bus-side**
~`2048x585`, **1:1 social** `1536x1536`, **9:16 DOOH** `1080x1920`. Fix `--seed` to iterate copy
without redrawing the whole scene.

### 2. Hardest exact-text job → GPT Image 2

Swap the endpoint; same runner and prompt discipline. Best for legal lines, tiny type, curved surfaces.

```bash
python3 scripts/fal_text_image.py --endpoint openai/gpt-image-2 \
  --size 1536x1536 \
  --prompt 'Square pack-shot comp. A matte drinks can, front label reads exactly
"CITRUS SURGE", variant strip below reads exactly "Zero Sugar". Small side-of-can
claim in tiny type reads exactly "150ml e". Studio light, seamless background.
Sharp legible label, correct spelling, no duplicated letters, no extra text.' \
  --out pack_citrus.png
```

### 3. Multilingual / high-density → Seedream

```bash
python3 scripts/fal_text_image.py \
  --endpoint fal-ai/bytedance/seedream/v4/text-to-image \
  --size auto_4K \
  --prompt 'Menu-board comp with three price rows, left column dish names, right
column prices reading exactly "£3.50", "£4.20", "£5.00". Header reads exactly
"TODAY". Clean grid, legible, no invented items, no extra text.' \
  --out menu.png
```

### 4. Dense infographic or paragraph copy → Nano Banana Pro

Nano Banana Pro leads on long/paragraph text and real infographics. Drive it via the
**`nano-banana-image`** sibling skill (native Gemini, model `gemini-3-pro-image-preview`), reusing the
same verbatim discipline above. Ask for 2K/4K and a specified aspect ratio in the prompt.

### 5. Add or fix one text element on an existing comp

Every model here also has an **edit** endpoint (e.g. `fal-ai/flux-2-pro/edit`, Seedream v4 `/edit`).
Prefer editing to re-rolling: generate the clean scene once, then add the price flash / legal line as a
second pass so each string gets the model's full attention. For instruction edits that preserve the
rest of the frame, `flux-image-gen` (FLUX.1 Kontext) is the sibling to use.

## Verify

- **Read every word out loud** against the brief. Zoom to 100%. Check the legal line character by
  character — that's where slips hide.
- **Casing / punctuation** match the copy deck exactly.
- **Legibility at distance**: for OOH, shrink the comp to thumbnail — the headline must still read.
- **No phantom text**: scan corners/edges for invented words, duplicated letters, watermarks.
- **Colour/hierarchy** on-brief. If the licensed font matters, note "type to be reset" and rebuild
  vector-side for anything past comp stage.
- Runner exits non-zero and prints `ERROR:` on any API/timeout failure — it never writes a fake image.

## Pitfalls

- **Baked text can still misspell** — even 99%-accurate models miss ~1 in 100. Never ship pixel-text
  to print; comp only, then reset as vector. Proof every string.
- **Too many strings in one prompt** multiplies errors — keep to ≤3–4 per pass; add the rest by edit.
- **Paraphrasing the copy** or repeating it in mixed casing confuses the model — quote it once, literally.
- **Licensed fonts don't load** — you're describing a look, not loading a .otf. Approximate, then reset.
- **Seedream 5.0 Pro is rolling out** — the verified stable fal endpoint is the v4 id above; check
  fal.ai for the exact `seedream/v5` path before hardcoding it, and don't invent an endpoint string.
- **Provider drift**: model ids and params change fast. If the runner 404s, open the model's fal page
  and confirm the current endpoint id and `image_size` presets — don't guess.
- **Rights**: these are AI comps. Don't pass them as final artwork, and clear usage/likeness per the
  agency's AI-content policy before anything client-facing goes out.

## Sources

- Nano Banana Pro / Gemini 3 Pro Image — blog.google, deepmind.google/models/gemini-image/pro
- FLUX.2 — bfl.ai/blog/flux-2, fal.ai/models/fal-ai/flux-2-pro (endpoint `fal-ai/flux-2-pro`)
- Seedream 5.0 Pro — seed.bytedance.com; fal `fal-ai/bytedance/seedream/v4/text-to-image`
- GPT Image 2 — openai.com (ChatGPT Images 2.0); fal `openai/gpt-image-2`
