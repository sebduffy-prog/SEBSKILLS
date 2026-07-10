---
name: background-removal-batch
category: media
description: >
  Batch-remove image backgrounds to transparent PNGs (real alpha) using rembg with BiRefNet /
  BRIA RMBG / IS-Net / U²-Net models, plus optional deck-prep (matte a solid colour, square-pad
  for consistent sizing). Use when someone says "cut out this product", "remove the background",
  "make it transparent", "knock out the background", "batch-remove backgrounds from a folder",
  "get me PNGs with no background for the deck", "clip the subject", "alpha matte", "transparent
  cutout", "rembg", or "isolate the subject on white". Runs fully local, no API key, one model
  session reused across the whole folder.
when_to_use:
  - Cut out products/people from a folder of photos into transparent PNGs for a deck or mockup
  - "Remove the background" / "make this transparent" on one image or hundreds at once
  - Need a clean solid-colour (white/brand) matte behind cut-out products for slides
  - Wispy edges (hair, fur, foliage) need high-quality alpha matting, not a hard mask
  - Want consistent square-padded cutouts so every product sits the same size on a grid
  - Local, offline, no-API-cost background removal (privacy-safe, no upload)
when_not_to_use:
  - You want to GENERATE a new image or swap in a generated background → use flux-image-gen or nano-banana-image
  - You need to upscale/restore/denoise the photo, not cut it out → use ai-upscale-restore
  - You need to remove the background of a moving subject in VIDEO → use video-object-tracking-sam2
  - You need to trace/isolate a subject as clean vector shapes → use the Adobe image_vectorize tool
  - You just want a rough per-frame mask from a clip, not still cutouts → use keyframe-motion-frame-diff
keywords: [background removal, remove background, transparent png, cutout, knockout, alpha matte, alpha matting, rembg, birefnet, bria rmbg, rmbg, isnet, u2net, product cutout, isolate subject, clipping, remove bg, make transparent, deck assets]
similar_to: [flux-image-gen, nano-banana-image, ai-upscale-restore, video-object-tracking-sam2, comfyui-workflow-runner]
inputs_needed:
  - Path to a single image OR a folder of images, and where to write the outputs
  - Whether the result should be transparent (default) or matted onto a solid colour (e.g. white for a deck)
  - Quality vs speed — birefnet-general (best) vs birefnet-general-lite / isnet-general-use (fast)
  - Whether edges are wispy (hair/fur/foliage) → turn on alpha matting
produces: Transparent (or solid-matted) PNG cutout(s) written to an output folder, mirroring the input tree
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Background Removal (Batch) — rembg + BiRefNet / RMBG

Knock out image backgrounds to **transparent PNGs with a real alpha channel**, locally and offline.
One tool covers it — `rembg` — which bundles the current best segmentation models (BiRefNet, BRIA
RMBG, IS-Net, U²-Net). No API key, nothing uploaded.

## When to use

Cutting a subject/product out of one image or a whole folder. For generating imagery, upscaling,
video subjects, or vector tracing, use the sibling skill in `when_not_to_use`.

## Prerequisites (this Mac)

- **`rembg` needs Python 3.11–3.13. The system `python3` here is 3.9 and CANNOT run it** — but
  **Python 3.12.13 and `uv` are installed**, so run everything through `uv`, which fetches a clean
  3.12 env on the fly. No global install, no venv juggling.
- **No NVIDIA GPU** (Apple Silicon) → use the CPU extra `rembg[cpu]`. Onnxruntime uses CPU/CoreML;
  BiRefNet on CPU is ~a few seconds/image, fine for decks.
- **Models auto-download on first use** to `~/.u2net` (override with `U2NET_HOME`). Pre-fetch once
  so a batch doesn't stall mid-run (below).
- No brew/LibreOffice needed. Not related to ffmpeg — this is pure image work.

Pre-fetch the model once (first run only, needs network):

```bash
uvx --python 3.12 --from "rembg[cpu,cli]" rembg d birefnet-general
```

## Models (`-m` flag) — pick one

| Model | Use it for |
|---|---|
| `birefnet-general` | **Default. Best all-round quality**, professional cutouts |
| `birefnet-general-lite` | Faster BiRefNet, slight quality drop — big batches |
| `birefnet-portrait` | People / headshots |
| `bria-rmbg` | BRIA RMBG, excellent SOTA general alternative |
| `isnet-general-use` | Fast, solid general model |
| `u2net` | Classic baseline; `u2netp` = lightweight |

Full set also includes `isnet-anime`, `birefnet-hrsod`, `birefnet-dis`, `birefnet-cod`, `sam`.

## Recipes

`uvx` = `uv tool run`: runs the `rembg` CLI in a throwaway 3.12 env. Every command below is
copy-pasteable.

### 1. Single image → transparent PNG

```bash
uvx --python 3.12 --from "rembg[cpu,cli]" rembg i \
  -m birefnet-general input.jpg output.png
```

### 2. Whole folder (batch)

`rembg p IN_DIR OUT_DIR` walks the folder and writes a matching PNG for each image:

```bash
uvx --python 3.12 --from "rembg[cpu,cli]" rembg p \
  -m birefnet-general ./products ./cutouts
```

### 3. Wispy edges (hair / fur / foliage) — alpha matting

```bash
uvx --python 3.12 --from "rembg[cpu,cli]" rembg i -a \
  -ae 15 -m birefnet-general portrait.jpg portrait.png
```

`-a` enables alpha matting; tune `-ae` (erode), `-af` (foreground threshold), `-ab` (background
threshold) if edges look chewed or haloed.

### 4. Deck-prep: transparent OR white-matted + square-padded (helper)

For slide-ready assets — every product cut out, centred, same square size, optional solid matte —
use the bundled helper (recursive, resumable, one reused model session):

```bash
# transparent, 1200x1200 padded, best model:
uv run --python 3.12 --with "rembg[cpu]" --with pillow \
  scripts/batch_cutout.py ./products ./cutouts --pad 1200

# matted onto brand white for a deck, wispy-edge matting on:
uv run --python 3.12 --with "rembg[cpu]" --with pillow \
  scripts/batch_cutout.py ./products ./deck --matte "#ffffff" --pad 1200 --alpha-matting
```

`--matte "#rrggbb"` composites onto a solid colour (omit for transparent). `--pad N` centres each
cutout on an NxN canvas so a product grid stays visually consistent. Existing outputs are skipped,
so a re-run resumes. Script: `scripts/batch_cutout.py`.

### 5. Just the mask (compositing yourself)

```bash
uvx --python 3.12 --from "rembg[cpu,cli]" rembg i -om -m birefnet-general in.jpg mask.png
```

## Verify

- **Alpha is real, not baked white.** Confirm the PNG has 4 channels and transparent pixels:

  ```bash
  uv run --python 3.12 --with pillow python -c \
  "from PIL import Image;i=Image.open('output.png');print(i.mode, i.getextrema()[3])"
  ```

  Expect `RGBA (0, 255)` — the alpha channel's min is 0 (fully transparent pixels exist).
- **Eyeball the edges** on a checkerboard/contrasting background (open in Preview; toggle
  Preview's transparency, or drop onto a coloured slide). Look for halos, chewed hair, or leftover
  background fringe.
- **Batch count matches**: number of PNGs in `OUT_DIR` == number of source images (the helper
  prints `done=/failed=/skipped=`).

## Pitfalls

- **`rembg: command not found` / Python 3.9 errors** — never use the system `python3`/`pip` here
  (3.9, capped). Always go through `uvx`/`uv run --python 3.12` as shown. That's non-negotiable on
  this Mac.
- **First run hangs "downloading"** — it's fetching the model to `~/.u2net`. Pre-fetch with
  `rembg d birefnet-general` (Recipe prereqs) before a big batch, and keep network on for that step.
- **Output looks white, not transparent** — you saved as `.jpg` (no alpha) or matted it. Save
  `.png`; drop `--matte` for transparency.
- **Halos / colour fringe on cutouts** — switch model (`bria-rmbg` vs `birefnet-general`) and/or
  enable `-a` alpha matting; nudge `-ae`/`-af`/`-ab`.
- **Semi-transparent glass/smoke/reflections** — segmentation models give a hard-ish subject mask;
  truly translucent materials won't matte perfectly. Prefer `birefnet-general` and accept manual
  touch-up, or use a generative edit (flux-image-gen) instead.
- **Slow on huge batches** — drop to `birefnet-general-lite` or `isnet-general-use`; the helper
  already reuses ONE model session across the folder (don't loop the CLI per file — that reloads
  the model every image).
- **Licensing** — `bria-rmbg` (BRIA RMBG) has non-commercial/commercial-licence terms upstream;
  for client/commercial deliverables prefer the BiRefNet models unless you've cleared RMBG's licence.

Sources: [danielgatis/rembg](https://github.com/danielgatis/rembg) ·
[rembg on PyPI](https://pypi.org/project/rembg/) ·
[BiRefNet](https://github.com/ZhengPeng7/BiRefNet)
