---
name: brand-kontext-studio
category: recipes
description: >-
  Recreate FLUX.1 Kontext / Nano-Banana style in-context brand image editing as a named combo.
  Chain flux-image-gen or nano-banana-image to generate or instruction-edit the scene, then
  background-removal-batch to cut the subject, then brand-color-token-system + oklch-color-engine
  to grade everything to an exact brand palette, and finish by compositing onto a branded layout.
  Reach for this to drop a product or person into a new on-brand scene, swap a background, or
  colour-grade a shoot to house colours without a designer round-trip.
when_to_use:
  - You want FLUX.1 Kontext / Nano-Banana "edit this image in context" behaviour but wired into a repeatable brand pipeline
  - You need to place a product or subject into a new generated scene, or swap/replace its background, and land it on-brand
  - You are grading a photo or render to an exact brand palette (hex ramp + OKLCH) rather than eyeballing curves
  - You want the generate/edit step to be swappable between Flux and Nano-Banana depending on which key you hold
  - You need a final composited, brand-graded PNG/PDF suitable for a deck, ad, or social post
when_not_to_use:
  - You only need one text-to-image generation or a single in-context edit — use flux-image-gen or nano-banana-image alone
  - You only need to knock out a background across a folder of images — use background-removal-batch alone
  - You only need a tonal ramp or semantic tokens from a brand hex — use brand-color-token-system alone
  - You only need perceptual colour maths (contrast, lightness, gamut) — use oklch-color-engine alone
  - You have no image-gen key/GPU and only need local retouch — skip the amber step and just grade/compose
keywords:
  - flux kontext
  - nano banana
  - in-context editing
  - brand image editing
  - background swap
  - colour grade
  - brand palette
  - oklch
  - product placement
  - image generation
  - retouch
  - compositing
  - gemini flash image
  - recipe
  - combo
  - amber
similar_to:
  - flux-image-gen
  - nano-banana-image
  - background-removal-batch
  - brand-color-token-system
  - oklch-color-engine
inputs_needed: >-
  A source image (product/subject/scene) or a text prompt for the scene, an edit instruction
  ("put this on a marble counter", "swap the sky"), and ONE brand hex (or full palette) to grade to.
  For the generative step you need a Flux key (FAL/Replicate/BFL) or a Gemini key for Nano-Banana,
  or a local GPU running ComfyUI. The grade + compose steps are pure local (Node/Python + a browser).
produces: >-
  A brand-graded, composited image (PNG, plus optional PDF/layout) of the subject in the new
  on-brand scene, the cut-out subject with alpha, and a reusable brand token/OKLCH grade spec
  so the same look can be re-applied to future shots.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Brand Kontext Studio

Recreate the headline trick of **FLUX.1 Kontext** and **Google Nano-Banana** — "edit this image in
context, keep everything else, change the one thing I asked for" — but wired into a repeatable brand
pipeline so the output lands on your exact house colours and layout instead of a raw model dump.
Everything downstream of the generative edit runs locally; only that one step needs a model.

## What it recreates

Black Forest Labs' **FLUX.1 Kontext** and Google's **Nano-Banana (Gemini 2.5 Flash Image)** —
instruction-driven, in-context image editing: place a product in a new scene, swap a background,
restyle a shot, or restage a subject while preserving identity and composition. Commercial versions
bundle the "make it on-brand" polish; this recipe rebuilds that polish from library skills so the
brand grade and layout are yours, deterministic, and re-runnable.

## Feasibility

**Rating: amber.**

- Green — background cut-out, brand-palette derivation, OKLCH grading, and final compositing are
  all fully local and deterministic (Node/Python + a browser). No key, no GPU.
- Amber — the one generative/in-context edit step (Step 1) needs an external image model: a hosted
  Flux key (FAL / Replicate / BFL) or a Gemini key for Nano-Banana, or a local GPU running ComfyUI.
  That step is the only thing you cannot reproduce offline on a stock laptop.
- Not red — nothing here is faked or oversold. If you have the key, the in-context edit is genuinely
  Kontext/Nano-Banana; if you don't, you still get real local grade + compose on an image you supply.

The honest split: the *editing intelligence* is wrapped (it's the model's), the *brand fidelity* is
genuinely reproduced by this library.

## The combo

An ordered chain of skills that already exist in this library:

1. **flux-image-gen** *(or)* **nano-banana-image** — the amber step. Generate the new scene from a
   prompt, or run the in-context edit ("put this bottle on a sunlit marble counter, keep the label").
   Use `flux-image-gen` when you hold a Flux/FAL/Replicate/BFL key or want FLUX.1 Kontext behaviour;
   use `nano-banana-image` when you hold a Gemini key and want Nano-Banana's identity-preserving edits.
   Pick one — they are interchangeable at this slot.
2. **background-removal-batch** — cut the edited subject cleanly from its plate, producing an alpha
   PNG. Runs locally; batch-capable if the model returned several candidates.
3. **brand-color-token-system** — turn ONE brand hex into the full 50→950 tonal ramp + semantic
   tokens that define what "on-brand" means for the grade and the layout.
4. **oklch-color-engine** — do the actual perceptual grade: map the image's dominant tones toward
   the brand ramp in OKLCH (lightness/chroma/hue), check contrast and gamut, keep skin/product tones
   sane. This is where the shot stops looking like a stock render and starts looking like your brand.
5. **compose** *(via* **canvas-design***)* — composite the graded cut-out onto a brand background /
   layout and export the final PNG (and PDF if it's going in a deck). canvas-design is the local
   compositing + layout skill; the token ramp from Step 3 drives its colours.

## Prerequisites

- One generative credential for Step 1: a Flux key (FAL/Replicate/BFL) **or** a Gemini key **or** a
  local GPU with ComfyUI. Without any of these you can only enter the chain at Step 2 with an image
  you already have.
- Node and/or Python locally for Steps 2–5, plus a browser (canvas-design renders through one).
- Your source image(s) and the brand hex (or existing palette/token file).

## Run it

1. **Decide the editing engine.** Holding a Flux key → invoke **flux-image-gen**. Holding a Gemini
   key → invoke **nano-banana-image**. Give it the source image + a single, specific in-context
   instruction (name what changes, name what to preserve). Save the best candidate.
2. **Cut the subject.** Invoke **background-removal-batch** on that candidate → alpha PNG of the
   subject (or of several candidates at once). Keep the original plate around in case you want the
   generated background too.
3. **Define the brand.** Invoke **brand-color-token-system** with your brand hex → 50→950 ramp +
   semantic tokens. If you already have a token file, load it and skip generation.
4. **Grade to brand.** Invoke **oklch-color-engine** to shift the image's tones toward the ramp in
   OKLCH — set target lightness/chroma/hue anchors from the tokens, verify contrast and that no
   channel clips out of gamut, and protect subject/skin tones from over-shift.
5. **Compose + export.** Invoke **canvas-design** to lay the graded cut-out onto a brand background
   built from the same tokens, add any lockup/type, and export the final PNG (and PDF for decks).
6. **Re-run cheaply.** Steps 2–5 are deterministic — rerun them on new shots with the saved token
   file and grade spec to keep a whole campaign consistent without touching the model again.

## Verify

- **Preservation:** the in-context edit changed only what you asked — identity, label text, and
  composition survived. If not, tighten the Step 1 instruction and regenerate.
- **Clean alpha:** no halo/fringe around the cut-out at 100% zoom; hair/edges intact.
- **On-brand grade:** sample the graded image's dominant hues and confirm they sit on the brand ramp
  (oklch-color-engine can report deltas); check foreground/background contrast passes.
- **Composite integrity:** subject sits believably on the brand background — consistent light
  direction and edge softness, no obvious paste look. Export opens correctly as PNG/PDF.
- **Reproducibility:** rerun Steps 2–5 on the same input and confirm byte-stable (or visually
  identical) output — the local half must be deterministic.

## Pitfalls

- **Treating the model output as final.** Kontext/Nano-Banana give you a *plausible* scene, not an
  on-brand asset. The whole point of this recipe is Steps 3–5; skipping the grade defeats it.
- **Grading in sRGB by eye.** Do the grade in OKLCH via oklch-color-engine — sRGB curve-tweaks drift
  hue and crush chroma. Anchor to the token ramp, don't freehand.
- **Over-grading skin/product.** Push the background hard toward brand, protect the subject. An
  aggressive global shift makes people look ill and products look wrong.
- **Halo from a lazy cut.** A soft or fringed mask from Step 2 shows immediately once composited on a
  contrasting brand background. Fix the alpha before compositing, not after.
- **Believing it's fully local.** It isn't — Step 1 needs a key or GPU. State that up front; don't
  promise an offline Kontext clone. If the user has no key, enter at Step 2 with their own image.
- **Locking to one vendor.** Step 1 is deliberately swappable between flux-image-gen and
  nano-banana-image. If one refuses a prompt or lacks a key, switch to the other — the rest of the
  chain is identical.
