---
name: lottie-motion-graphics
category: media
description: >
  Generate and template Lottie JSON animations in code, then render them to MP4/GIF/WebM —
  for versioned logo stings, animated lower-thirds, and end-cards. Use when someone says
  "make a Lottie", "animated lower third", "logo sting", "data-driven motion graphic",
  "render Lottie to MP4/GIF", "300 versions of this bumper", "After Effects JSON to video",
  or "programmatic motion graphics". Covers python-lottie authoring, ${TOKEN} template
  versioning from a CSV/JSON, and the lottie_convert.py render step. Vector, resolution-free.
when_to_use:
  - Building a lower-third, logo sting, or end-card as animated vector graphics (not pixel comps)
  - Versioning ONE motion template into many variants (per-brand, per-market, per-artist) from a data file
  - Turning an After Effects / Bodymovin Lottie JSON into an MP4/GIF/WebM for delivery
  - Generating a simple shape animation programmatically in Python with keyframes and easing
  - Producing resolution-independent motion that must re-export crisply at 1080p, 4K, or square social
when_not_to_use:
  - Cutting/encoding footage, overlays on real video, or filter graphs → use ffmpeg-cookbook
  - Word-by-word burned social captions → use whisper-caption-burn
  - Pixel/AI image or video generation (Flux, video diffusion) → use flux-image-gen or video-gen-pipeline
  - Full 3D animation or rendered scenes → use a Blender workflow, not Lottie
  - Just need a static poster or vector logo, no motion → use canvas-design
keywords: [lottie, bodymovin, motion graphics, lower third, logo sting, animated json, python-lottie, lottie_convert, render lottie to mp4, gif, webm, vector animation, after effects json, data-driven video, template versioning, end card, bumper, tgs, dotlottie]
similar_to: [ffmpeg-cookbook, whisper-caption-burn, flux-image-gen, video-gen-pipeline, canvas-design, social-video-reframe]
inputs_needed:
  - Either a source Lottie JSON (from After Effects/Bodymovin, LottieFiles, or hand-authored) OR a shape spec to build from scratch
  - For versioning — a CSV/JSON of rows and which text/colour/duration tokens vary
  - Delivery target — format (MP4/GIF/WebM), resolution, and fps
produces: Lottie JSON file(s) plus optional rendered MP4/GIF/WebM per variant
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Lottie Motion Graphics

Author or template **Lottie** animations (the Bodymovin JSON that After Effects and
LottieFiles export) as **vector, resolution-free** motion — logo stings, lower-thirds,
end-cards — then render each to **MP4 / GIF / WebM**. The win over pixel workflows:
one JSON re-exports crisp at 1080p, 4K, and 1:1 social, and one template fans out to
hundreds of branded/market/artist versions from a data file.

## When to use

Reach for this when the deliverable is **shape/text motion**, not footage. If you have
an After Effects comp exported via Bodymovin, or a `.json` grabbed from LottieFiles, this
skill renders and versions it. If you have no source, it builds a simple one in Python.

## Prerequisites

`python-lottie` (import name `lottie`, CLI `lottie_convert.py`). This Mac has **no
Homebrew** and **python3 is 3.9** — install into a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "lottie[all]"     # cairosvg + pillow + numpy + fonttools + glaxnimate
```

Honest dependency notes (from the package's extras):
- **JSON / SVG / TGS** export works with the base install — no extras.
- **GIF / animated WebP** needs `[gif]` (pulls `cairosvg`, `pillow`).
- **MP4 / WebM / AVI** needs `[video]` (`cairosvg`, `numpy`, `opencv`). Rendering rasterises
  each frame through Cairo, so `cairosvg` must import cleanly — that is the usual failure point.
- **Text as real shapes / custom fonts** needs `[text]` (`fonttools`); otherwise text layers
  fall back to system font metrics and may not render.
- `[all]` grabs everything and is the safe choice on a workstation.

Verify the CLI is on PATH: `lottie_convert.py --version`.

## Recipes

### 1. Render an existing Lottie JSON to video

The CLI auto-detects formats from file extensions:

```bash
lottie_convert.py sting.json sting.mp4                 # AE/Bodymovin export -> MP4
lottie_convert.py sting.json sting.gif --fps 30        # social GIF, capped fps
lottie_convert.py sting.json sting.webm                # alpha-friendly WebM
lottie_convert.py logo.json  logo_4k.png --width 3840  # single still frame, upscaled
```

Lottie is vector, so `--width` re-rasterises without quality loss. For a transparent
sting to overlay in an edit, prefer WebM (VP9 alpha) or a PNG sequence, then composite
with **ffmpeg-cookbook**.

### 2. Version ONE template into many (the core use case)

Author or export a base Lottie, then replace the values that vary with `${TOKEN}`
placeholders **inside JSON string values** — the text of a title layer, a fill colour,
a duration. `scripts/version_lottie.py` fills them from a CSV/JSON, one output per row,
and (optionally) renders each. A lone `"${DURATION}"` string coerces back to a JSON
number, so keyframe times and positions can vary too.

Template `lowerthird.json` (fragment): `"t": "${TITLE}"`, an `"op": "${DURATION}"`,
and a colour token you keep as a string. Rows:

```csv
SLUG,TITLE,ACCENT,DURATION
warner-holly,Holly Humberstone — Live,#E4002B,90
warner-erin,Erin LeCount — In Session,#0072CE,90
```

```bash
python3 scripts/version_lottie.py lowerthird.json rows.csv --out out/ --render mp4
# -> out/warner-holly.json + out/warner-holly.mp4, one pair per row
```

`SLUG` names each output; a missing token fails loud (never a silent blank). rows can
also be a JSON array of objects. This is the "300 branded bumpers overnight" workflow.

### 3. Build a lower-third from scratch in Python

When there is no AE source, the `lottie` Python API composes shapes and keyframes
directly. Verified API surface (v0.7.x):

```python
from lottie import objects, Point, Color
from lottie.utils import script

an = objects.Animation(60)          # 60 frames; default 60 fps -> ~1s
an.width, an.height = 1920, 1080

layer = objects.ShapeLayer()
an.add_layer(layer)

bar = layer.add_shape(objects.Rect(Point(480, 980), Point(760, 90)))  # centre, size
layer.add_shape(objects.Fill(Color(0, 0.45, 0.81)))                   # VCCP-ish blue

# slide the bar in: keyframe the group/layer transform position
layer.transform.position.add_keyframe(0,  Point(-400, 0))
layer.transform.position.add_keyframe(15, Point(0, 0))                # ease handled by tangents

# export JSON (base install) then render via the CLI, or hand `an` to script_main:
from lottie.exporters.core import export_lottie
export_lottie(an, "lowerthird.json")
# script.script_main(an)   # alt: gives this file its own convert CLI (out format by extension)
```

Then render with Recipe 1, or feed the JSON into Recipe 2 for versioning. Keep hand-built
scenes simple — for anything elaborate, design in After Effects, export via Bodymovin,
and version here.

## Verify

```bash
# 1. templating works with no lottie install (pure stdlib):
python3 scripts/version_lottie.py --help

# 2. round-trip a rendered file has real duration + frames:
lottie_convert.py sting.json sting.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 sting.mp4   # > 0

# 3. tokens all resolved — no stray ${...} left in output JSON:
grep -o '\${[A-Z0-9_]*}' out/*.json && echo "UNRESOLVED TOKENS" || echo "clean"
```

Open a rendered variant and confirm the swapped text/colour is correct before batching
the full set — a wrong token maps silently to the wrong brand across every version.

## Pitfalls

- **`cairosvg` import errors** are the #1 render failure. `pip install "lottie[all]"`
  inside the venv; on a bare install JSON/SVG export works but MP4/GIF will not.
- **Fonts.** Text layers need the `[text]` extra AND the font available, or glyphs render
  with wrong metrics / go missing. Safest cross-machine path: convert text to outlines in
  AE before export, or drive text via `${TOKEN}` over a template whose font is embedded.
- **GIF is lossy and heavy.** 256-colour, no alpha, big files. Use it only for chat/email;
  deliver WebM or MP4 (or a PNG sequence for compositing) everywhere else.
- **fps vs frames.** Lottie stores `ip`/`op` in *frames* at the comp `fr`. Changing only
  `--fps` on render can speed up or slow motion — scale `op` in the same ratio if you want
  the same wall-clock duration.
- **Bodymovin feature gaps.** python-lottie doesn't render every AE effect (some
  expressions, complex mattes, layer styles). Sanity-render one frame after export; if it
  looks wrong, simplify the comp rather than fighting the renderer.
- **Don't hand-edit raw keyframe arrays** in the JSON by eye — use `${TOKEN}` swaps or the
  Python API so easing tangents stay coherent.
