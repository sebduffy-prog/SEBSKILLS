---
name: flux-image-gen
category: media
description: >
  Generate or instruction-edit images with the Flux family (FLUX.2 / FLUX.1 Kontext / Pro / dev)
  via the Black Forest Labs API, fal.ai, or Replicate — photoreal hero shots, crisp typography/poster
  text, and "change X in this image" edits that preserve the rest. Use when someone says "generate an
  image from this prompt", "make a hero image", "text-to-image with Flux", "edit this photo with an
  instruction", "change the colour/background/text in this image", "flux kontext", "inpaint with Flux",
  "flux pro / flux dev / flux 2", or "make a poster with readable text". Covers submit→poll→download,
  base64 input images, aspect ratio/size/seed, and running flux-dev locally via diffusers.
when_to_use:
  - Generate a photoreal hero/product image from a text prompt (FLUX.2 pro or FLUX1.1 pro)
  - Edit an existing image with a natural-language instruction ("change the car to teal", "remove the sign") using FLUX.1 Kontext
  - Make a poster/mockup where the on-image text/typography must be legible and correct
  - Produce reproducible variants of a prompt by fixing the seed
  - Combine multiple reference images into one composite (FLUX.2 multi-reference)
  - Run flux-dev/schnell locally on-device with diffusers instead of a hosted API
when_not_to_use:
  - You want Google's Gemini/Nano-Banana image model instead of Flux → use nano-banana-image
  - You need an animated clip or image-to-video, not a still → use video-gen-pipeline
  - You just need to cut out/replace a subject's background (no generation) → use background-removal-batch
  - You want to upscale/restore an existing image, not create one → use ai-upscale-restore
  - You need a node-graph Stable-Diffusion/Flux pipeline with custom nodes/LoRAs → use comfyui-workflow-runner
keywords: [flux, flux.2, flux 2, flux kontext, flux pro, flux1.1, flux dev, flux schnell, black forest labs, bfl, text-to-image, image editing, instruction edit, inpaint, image generation, diffusers, fal.ai, replicate, aspect ratio, seed, x-key, hero image, typography]
similar_to: [nano-banana-image, video-gen-pipeline, background-removal-batch, ai-upscale-restore, comfyui-workflow-runner]
inputs_needed:
  - The prompt (generation) or the input image path + edit instruction (editing)
  - Which provider/key you have — BFL_API_KEY (api.bfl.ai), FAL_KEY (fal.ai), or REPLICATE_API_TOKEN
  - Model tier — quality (flux-2-pro / flux-kontext-max) vs cheap/fast (flux-dev / flux-schnell)
  - Output size / aspect ratio, and whether the result must be reproducible (seed)
produces: A generated or edited image file (.jpg/.png) written locally
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Flux Image Gen (BFL / fal / Replicate + local diffusers)

Create or edit images with the Flux family. Two jobs:
- **Generate** — text → image. Reach for `flux-2-pro` (photoreal, great typography) or the cheaper
  `flux-dev`.
- **Edit** — image + instruction → image, keeping everything you didn't mention. That's
  **FLUX.1 Kontext** (`flux-kontext-pro` / `flux-kontext-max`).

The hosted BFL API is **async**: POST a request, get a `polling_url`, GET it until `status == "Ready"`,
then download the signed `result.sample` URL (valid ~10 min). The helper script does all three.

## When to use

Prompt→image, or "change X in this picture" edits. For Gemini/Nano-Banana instead, video, plain
background removal, or upscaling, use the sibling skill in `when_not_to_use`.

## Prerequisites (this Mac)

- **An API key** for one provider (pick one):
  - **BFL** (recommended, native Flux): create a key at bfl.ai, then `export BFL_API_KEY=...`.
    Base URL `https://api.bfl.ai` (or `api.eu.bfl.ai` / `api.us.bfl.ai`). Auth header is **`x-key`** (not Bearer).
  - **fal.ai**: `export FAL_KEY=...` — good for quick one-liners, auto-hosted result URLs.
  - **Replicate**: `export REPLICATE_API_TOKEN=...`.
- **Python 3.9 + `requests`** for the helper (`python3 -m pip install --user requests`). The script has a
  stdlib-only fallback if `requests` is missing, so it runs bare too.
- **Local route (no API):** `flux-dev`/`schnell` via 🤗 `diffusers` needs `torch` with MPS. Heavy
  (~24GB weights, slow on Mac GPU) — only when you must stay offline. Prefer the hosted API otherwise.
- No ffmpeg/brew needed for image gen.

## Model cheat-sheet

| Need | BFL model | fal slug | Replicate slug |
|---|---|---|---|
| Best photoreal + typography | `flux-2-pro` (or `flux-2-max`) | `fal-ai/flux-2-pro` | `black-forest-labs/flux-2-pro` |
| Solid, cheaper generate | `flux-pro-1.1` / `flux-pro-1.1-ultra` | `fal-ai/flux-pro/v1.1` | `black-forest-labs/flux-1.1-pro` |
| Cheap/fast / local | `flux-dev` (or `flux-2-klein`) | `fal-ai/flux/dev` | `black-forest-labs/flux-dev` |
| Instruction edit (keep rest) | `flux-kontext-pro` / `flux-kontext-max` | `fal-ai/flux-pro/kontext` | `black-forest-labs/flux-kontext-pro` |

`flux-kontext-max` is rate-limited harder (≈6 concurrent tasks → 429s). FLUX.2 supports up to ~4MP and
multi-reference (combine several source images).

## Recipe 1 — Generate a hero image (BFL, helper script)

```bash
export BFL_API_KEY=...
python3 scripts/flux_bfl.py gen \
  "cinematic hero shot of a matte-red sports car on a rain-slick city street at night, \
   neon reflections, shallow depth of field, 35mm" \
  --model flux-2-pro --width 1536 --height 864 --seed 42 -o hero.jpg
# prints: hero.jpg
```

Landscape 16:9 here is `1536x864`. Reuse `--seed` to get the same image; drop it for variety.

## Recipe 2 — Instruction edit with FLUX.1 Kontext (keep everything else)

```bash
python3 scripts/flux_bfl.py edit input.jpg \
  "change the car colour to metallic teal, keep the background and lighting identical" \
  --model flux-kontext-pro --aspect 16:9 -o edited.jpg
```

Kontext takes the source as `input_image` (base64 or URL). Good instructions name **only** what to
change ("replace the billboard text with 'SALE'", "remove the person on the left") so the rest is
preserved. `--aspect` from `3:7`…`7:3`, default `1:1`.

## Recipe 3 — Raw BFL API (no script, curl + jq)

```bash
# 1. submit
resp=$(curl -s -X POST https://api.bfl.ai/v1/flux-2-pro \
  -H "x-key: $BFL_API_KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"a golden retriever puppy in a field of tulips, soft morning light","width":1024,"height":1024}')
poll=$(echo "$resp" | jq -r .polling_url)
# 2. poll until Ready
while :; do r=$(curl -s "$poll" -H "x-key: $BFL_API_KEY"); s=$(echo "$r" | jq -r .status);
  echo "$s"; [ "$s" = "Ready" ] && break; [ "$s" = "Error" -o "$s" = "Failed" ] && { echo "$r"; exit 1; }; sleep 2; done
# 3. download the signed sample URL
curl -s "$(echo "$r" | jq -r .result.sample)" -o out.jpg
```

## Recipe 4 — fal.ai one-liner (Python SDK)

```bash
python3 -m pip install --user fal-client
```
```python
import fal_client, urllib.request
r = fal_client.run("fal-ai/flux-2-pro", arguments={
    "prompt": "a bold retro travel poster of Tokyo at dusk, the word TOKYO in clean sans-serif",
    "image_size": "landscape_16_9"})           # fal returns hosted image URLs
urllib.request.urlretrieve(r["images"][0]["url"], "poster.jpg")
```
Editing on fal: model `fal-ai/flux-pro/kontext` with `{"prompt": ..., "image_url": <url-or-data-uri>}`.

## Recipe 5 — Local flux-dev via diffusers (offline, slow)

```python
import torch
from diffusers import FluxPipeline
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()          # fits in less VRAM/unified memory
img = pipe("an astronaut riding a horse on mars, photorealistic",
           height=1024, width=1024, guidance_scale=3.5, num_inference_steps=28,
           generator=torch.Generator("cpu").manual_seed(0)).images[0]
img.save("local.png")
```
Needs a HF token + accepted licence for `FLUX.1-dev`. `FLUX.1-schnell` is faster (≈4 steps, Apache-2.0).

## Verify

- **File exists & is a real image:** `file out.jpg` → `JPEG image data …`; open it (`open out.jpg`).
- **Right dimensions:** `python3 -c "from PIL import Image;print(Image.open('out.jpg').size)"`.
- **Edit actually preserved the scene:** eyeball input vs output — only the requested thing changed.
- **Reproducibility:** same `--seed` + prompt + model → same image (hosted; local diffusers needs the same generator seed).

## Pitfalls

- **Wrong auth header.** BFL uses `x-key: <key>`, *not* `Authorization: Bearer`. Bearer → 401/403.
- **Signed result URL expires (~10 min).** Download immediately after `Ready`; don't stash the URL.
- **Forgetting to poll.** The POST returns only an `id`/`polling_url`, never the image. You must GET the poll URL until `Ready`.
- **Editing needs the image inline.** `input_image` is base64 (or a public URL). The helper base64-encodes local files for you; raw curl must send the base64 string.
- **Over-specified edit prompts drift the whole image.** Name only what changes; add "keep everything else identical" for Kontext.
- **`flux-kontext-max` 429s** under load (≈6 concurrent) — back off / retry, or use `flux-kontext-pro`.
- **Wrong region base URL / data residency.** EU-only keys must hit `api.eu.bfl.ai`; a mismatch 401s.
- **Local diffusers is heavy on this Mac.** ~24GB download + slow MPS inference — use only when offline; the hosted API is faster and cheaper for one-offs.
- **Content filters** can `Error`/`Failed` a request (e.g. real public figures, unsafe prompts). Rephrase rather than retry blindly.

Sources: [BFL API docs](https://docs.bfl.ai/) · [black-forest-labs/flux](https://github.com/black-forest-labs/flux) · [fal.ai FLUX](https://fal.ai/flux) · [🤗 diffusers Flux](https://huggingface.co/docs/diffusers/api/pipelines/flux)
