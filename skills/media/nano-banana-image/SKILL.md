---
name: nano-banana-image
category: media
description: >
  Generate and edit images with Google's Nano Banana (Gemini Flash Image, gemini-2.5-flash-image)
  via the Gemini API — the model that actually keeps a character or product CONSISTENT across
  shots, renders LEGIBLE text inside the image, and fuses multiple reference photos into one scene.
  Use when someone says "keep this character the same across images", "put readable text in the
  image", "make a mockup / ad with my product in a scene", "composite these photos together",
  "edit this image with a prompt", "nano banana", "gemini image", "restyle this photo but keep
  the person", or "generate a branded graphic with a headline baked in". Local, scriptable, no browser.
when_to_use:
  - Keep the same character/mascot/person looking identical across a series of generated images
  - Put a product (bottle, pack, phone) into a new scene / lifestyle mockup while keeping it on-brand
  - Bake legible text — a headline, sign, label, poster copy — INTO the pixels of an image
  - Fuse 2–14 reference images (person + product + background) into one composited scene
  - Prompt-edit an existing photo (change background, outfit, lighting) without redrawing the subject
  - Batch-generate on-brand variations from a script instead of clicking around a web UI
when_not_to_use:
  - Photoreal single-shot art with no consistency/text need and you have a local GPU → use flux-image-gen
  - Node-graph pipelines, LoRAs, ControlNet, inpainting masks → use comfyui-workflow-runner
  - Generating a VIDEO (Veo / image-to-video) → use video-gen-pipeline
  - Just cutting a subject out onto transparent → use background-removal-batch
  - Upscaling / restoring an existing image → use ai-upscale-restore
keywords: [nano banana, gemini image, gemini-2.5-flash-image, gemini flash image, google image gen, character consistency, product consistency, in-image text, text rendering, multi-image fusion, image editing, image-to-image, generateContent, google-genai, synthid, image mockup, composite]
similar_to: [flux-image-gen, comfyui-workflow-runner, video-gen-pipeline, background-removal-batch, ai-upscale-restore]
inputs_needed:
  - A GEMINI_API_KEY (Google AI Studio, free tier available) exported in the shell
  - The prompt, plus any reference image paths (subject/product/background) and how many to fuse
  - Which job — pure text-to-image, edit-one-image, or fuse-many — and desired aspect ratio
produces: One or more PNG files written to disk (SynthID-watermarked), plus the raw base64 if you want it
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Nano Banana Image (Gemini Flash Image)

Google's **Nano Banana** = the Gemini Flash Image model (`gemini-2.5-flash-image`). Its edge over
generic diffusion models is three specific things: **character/product consistency** across shots,
**legible text baked into the image**, and **multi-image fusion** (drop in a person + a product +
a backdrop and get one coherent scene). Call it from the terminal, not a web tab.

## When to use

Reach for this when the deliverable needs the *same face/pack every time*, or needs *words the eye
can read* inside the artwork, or is a *composite of several photos*. If you just want one pretty
standalone render and have a local GPU, `flux-image-gen` is cheaper and offline.

## Prerequisites (this Mac)

- **API key** — get one free at aistudio.google.com, then:
  ```bash
  export GEMINI_API_KEY="AI...your-key..."
  ```
  Put it in your shell profile or a local `.env` you never commit. Never hardcode it.
- **Python SDK** (recommended path — handles base64 for you):
  ```bash
  python3 -m pip install --user google-genai pillow
  ```
  The SDK reads `GEMINI_API_KEY` from the environment automatically.
- **curl + jq** are enough for the REST path if you don't want the SDK.
- No ffmpeg/GPU needed — generation runs in Google's cloud. Output is always PNG bytes.
- **Limits worth knowing**: inline request cap ~20 MB (prompt + all images); up to ~14 reference
  images per fuse; every output carries an invisible **SynthID** watermark (it's AI-labelled — fine
  for mockups, disclose where required).

## Recipe 1 — Text-to-image (with in-image text)

Nano Banana renders short headlines/signs far more legibly than diffusion models. Ask for the exact
words in quotes.

```bash
python3 skills/media/nano-banana-image/scripts/nb_image.py \
  --prompt 'A bold vertical poster, mint-green background, a smiling barista holding a coffee cup, the headline text "MORNINGS, SORTED" in a chunky sans-serif at the top, clean flat illustration' \
  --out morning_poster.png --aspect 3:4
```

Prompt tips for text: keep the copy short, put it in `"double quotes"`, and name the font *feel*
("chunky sans-serif", "elegant serif") rather than a specific typeface.

## Recipe 2 — Edit / restyle one image (keep the subject)

Pass the original as a reference and describe the change. The subject stays recognisable.

```bash
python3 skills/media/nano-banana-image/scripts/nb_image.py \
  --prompt 'Keep this exact person and their face unchanged. Change the background to a sunlit Tokyo street at golden hour, add a light film grain.' \
  --image portrait.jpg --out portrait_tokyo.png
```

Say **"keep this exact person/product unchanged"** explicitly — it's the phrasing that drives
consistency. For product shots: "keep the label, shape and colour of this bottle identical".

## Recipe 3 — Character/product consistency across a series

Feed one canonical reference and generate each scene against it, reusing the same reference every call:

```bash
for scene in "ordering at a food truck" "reading on a park bench" "waving at a train station"; do
  python3 skills/media/nano-banana-image/scripts/nb_image.py \
    --prompt "The SAME character as the reference, identical face, hair and outfit. Now: $scene. Consistent flat-illustration style." \
    --image mascot_ref.png \
    --out "mascot_${scene// /_}.png"
done
```

## Recipe 4 — Multi-image fusion (person + product + background)

Pass several `--image` flags; the model composites them into one scene.

```bash
python3 skills/media/nano-banana-image/scripts/nb_image.py \
  --prompt 'Place the person from image 1 holding the product from image 2, standing in the environment from image 3. Match lighting to the background. Keep the product label sharp and legible.' \
  --image model.jpg --image bottle.png --image cafe_bg.jpg \
  --out fused_ad.png --aspect 4:5
```

## Raw REST (no SDK)

The classic `generateContent` endpoint — image bytes come back base64 in
`candidates[0].content.parts[].inlineData.data`:

```bash
IMG_B64=$(base64 -i portrait.jpg)   # macOS base64: -i for input file, no line wraps by default
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d "{
    \"contents\": [{\"parts\": [
      {\"text\": \"Change the background to a snowy mountain. Keep the person identical.\"},
      {\"inline_data\": {\"mime_type\": \"image/jpeg\", \"data\": \"$IMG_B64\"}}
    ]}]
  }" \
  | jq -r '.candidates[0].content.parts[] | select(.inlineData) | .inlineData.data' \
  | base64 -d > edited.png
```

Text-to-image is the same request minus the `inline_data` part. Add more `inline_data` parts to fuse.

## Verify

- `file out.png` reports `PNG image data`, and it opens: `open out.png`.
- Non-zero size and sane dimensions: `python3 -c "from PIL import Image;i=Image.open('out.png');print(i.size,i.mode)"`.
- If the script prints refusal/safety text instead of writing a file, the model returned **text, not an
  image** — inspect the printed message (see Pitfalls).
- For consistency work, eyeball the series side by side — build a quick contact sheet with the
  `contact-sheet-storyboard` skill.

## Pitfalls

- **Model returned text, no image.** Safety filters, an ambiguous prompt, or a "describe" verb.
  Re-read the printed response; rephrase as a concrete *generate/edit* instruction ("Create an
  image where…", "Edit this photo to…").
- **Consistency drifts.** You didn't pass the reference every call, or didn't say "keep identical".
  Always re-feed the canonical reference image and use explicit "same person/product, unchanged" language.
- **Garbled in-image text.** Copy too long, or no quotes. Keep headlines to a few words in
  `"quotes"`; the model isn't a layout engine for paragraphs.
- **413 / request too large.** Inline images push you past ~20 MB. Downscale references first
  (`sips -Z 1600 ref.jpg --out ref_small.jpg` on macOS) or use the Gemini Files API to upload.
- **Aspect ratio ignored.** On the classic `generateContent` path, state the framing in the prompt
  ("tall 3:4 vertical poster"); precise `aspect_ratio` control lives on the newer Interactions API /
  Gemini 3.x Flash Image models — swap the model ID if you need exact sizes/2K–4K output.
- **Key leaks.** `GEMINI_API_KEY` is a live billing credential — env var only, never in a committed file.
- **Watermark.** Every output is SynthID-tagged as AI-generated. Expected; disclose per client/platform rules.
