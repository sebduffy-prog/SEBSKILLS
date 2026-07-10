---
name: video-matting-rotoscope
category: media
description: >
  Pull a temporally-stable alpha matte off a person/subject across a whole video
  with RobustVideoMatting (RVM) — clean, flicker-free green-screen key, RGBA
  cutout, or composite over a new background, no chroma screen required. Use when
  the user says "green-screen this without a green screen", "matte the presenter
  out", "put them on a new background", "rotoscope this clip", "make a clean alpha
  channel for the whole video", "remove the background from this footage", or
  "the per-frame background removal flickers — make it stable". RVM keeps a
  recurrent state so edges don't shimmer frame to frame. Produces com/pha/fgr
  videos or an RGBA PNG sequence, ready to composite in ffmpeg / After Effects.
when_to_use:
  - "Matte a person/presenter/product off a moving-background clip with a clean, non-flickering alpha"
  - "Fake a green screen (no chroma required) — export a green composite or straight RGBA cutout"
  - "Put the subject on a brand-new background plate (composite fgr+pha over any image/video)"
  - "Fix per-frame still-image background removal that shimmers/flickers along edges over time"
  - "Rotoscope a talking-head / dance / product clip for a social edit or title sequence"
  - "Generate an alpha matte to hand into After Effects / Resolve / ffmpeg for grading"
when_not_to_use:
  - "Track/blur/redact a SPECIFIC clicked object (face, plate, logo) across frames → use video-object-tracking-sam2"
  - "Remove background from STILL images / a batch of photos (no temporal need) → use background-removal-batch"
  - "Just key an existing GREEN/BLUE screen you already shot → use ffmpeg-cookbook (chromakey/colorkey)"
  - "Reframe/crop to 9:16 following the speaker, not matte them → use social-video-reframe"
  - "Only need a motion/diff heatmap, not a subject alpha → use keyframe-motion-frame-diff"
keywords: [robust video matting, rvm, video matting, alpha matte, rotoscope, green screen, chroma key, background removal video, temporal stability, human matting, portrait matting, torch hub, downsample ratio, seq_chunk, rgba sequence, composite, birefnet]
similar_to: [video-object-tracking-sam2, background-removal-batch, ffmpeg-cookbook, social-video-reframe, keyframe-motion-frame-diff]
inputs_needed:
  - "Path to the source video (subject reasonably foregrounded — RVM is trained for humans/portraits)"
  - "Desired output: green composite mp4 / raw alpha (pha) / raw foreground (fgr) / RGBA PNG sequence"
  - "If compositing onto a new plate: the background image or video"
  - "Compute reality: CUDA GPU (fast, fp16) vs this Mac (MPS/CPU — works, slower, keep clips short)"
  - "Resolution (drives downsample_ratio: HD~0.25, 4K~0.125) and whether edge crispness (resnet50) matters"
produces: "com.mp4 (green-screen composite) + pha.mp4 (alpha) + fgr.mp4 (foreground), or an RGBA PNG sequence; plus an optional new-background composite"
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Video Matting & Rotoscope (RobustVideoMatting)

[RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting) (RVM) pulls a
**temporally-stable alpha matte** off a human/portrait subject across a whole clip
— no green screen, no per-frame clicking. Its recurrent architecture carries state
between frames, so the alpha doesn't shimmer or flicker the way still-image
background removal (`rembg`/BiRefNet run frame-by-frame) does. It runs in real time
on a modern GPU at 4K/HD.

Outputs, all frame-accurate to the source:
- **`pha`** — the alpha matte (grayscale, the actual deliverable for compositors)
- **`fgr`** — the estimated foreground (colour, with spill removed)
- **`com`** — a ready composite: green-screen (video) or RGBA (png sequence)

Two model variants: **`mobilenetv3`** (fast, the default) and **`resnet50`**
(crisper edges — hair, motion blur — at more compute).

## When to use

- "Green-screen the presenter without a green screen" → `rvm_matte.py --composition com.mp4`
- "Give me a clean alpha for the whole clip" → `rvm_matte.py --alpha pha.mp4 --foreground fgr.mp4`
- "Put them on a new background" → matte, then `alpha_over_bg.sh fgr.mp4 pha.mp4 plate.jpg out.mp4`
- "The frame-by-frame cutout flickers" → this is exactly what RVM fixes (temporal state)

If the user wants to isolate a **specific clicked object** (not a foregrounded human),
that's `video-object-tracking-sam2`. If it's **still photos**, that's `background-removal-batch`.

## Prerequisites (read the compute note first)

**RVM needs PyTorch and `av` (PyAV) for video I/O — and this Mac's system Python is
3.9**, so make a modern env. RVM was written against torch 1.9 but runs fine on
current torch; it is happiest on CUDA (real-time, fp16). On Apple **MPS** it works
but some ops fall back to CPU (slower) — keep clips short and use `mobilenetv3`.
For long/4K jobs, run the matte on a cloud GPU and bring `pha`/`fgr` back to
composite locally.

```bash
python3 -m venv ~/.venvs/rvm && source ~/.venvs/rvm/bin/activate
pip install --upgrade pip
pip install torch torchvision av tqdm pims          # av = PyAV, RVM's video reader/writer
python -c "import torch; print(torch.__version__)"
```

The helper loads the model **and** the bundled `convert_video` converter directly
from `torch.hub` — **no repo clone required** (weights are cached under
`~/.cache/torch/hub`, first run downloads ~20–100 MB):

```python
model         = torch.hub.load("PeterL1n/RobustVideoMatting", "mobilenetv3")  # or resnet50
convert_video = torch.hub.load("PeterL1n/RobustVideoMatting", "converter")
```

**ffmpeg (for the composite step, runs on this Mac — no brew here):** use the
portable binary from the `imageio-ffmpeg` pip package and put it on PATH:

```bash
FF=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
ln -sf "$FF" "$(dirname "$FF")/ffmpeg"; export PATH="$(dirname "$FF"):$PATH"
```

## Recipes

### 1. Matte to green screen + alpha + foreground (the main path)

`scripts/rvm_matte.py` wraps `convert_video` with auto device selection
(CUDA→MPS→CPU) and sane defaults. Set `--downsample` to your resolution.

```bash
python scripts/rvm_matte.py input.mp4 \
  --variant mobilenetv3 \
  --downsample 0.25 --seq-chunk 12 \
  --composition com.mp4 --alpha pha.mp4 --foreground fgr.mp4
```

`--downsample` (RVM's `downsample_ratio`) is the key quality/speed knob — the model
runs its refinement at full res but the coarse pass at this ratio:

| Source | downsample |
|--------|-----------|
| SD / 512p | ~0.4 |
| HD / 1080p | ~0.25 |
| 4K | ~0.125 |

Omit it for RVM's auto mode, but setting it explicitly is more reliable. Use
`--variant resnet50` when hair/edges look soft.

### 2. RGBA PNG sequence (for After Effects / Resolve / true transparency)

```bash
python scripts/rvm_matte.py input.mp4 --png-sequence \
  --downsample 0.25 --composition out_rgba/
```

Paths become **directories**; each frame is a 4-channel RGBA PNG with true alpha
(no green to key). Import as an image sequence at the source fps.

### 3. Composite the subject onto a new background

RVM gives premultiply-friendly `fgr` + `pha`; `scripts/alpha_over_bg.sh` keys them
over any image/video with `com = fgr*pha + bg*(1-pha)` (ffmpeg `maskedmerge`,
auto-scaling the plate to match):

```bash
bash scripts/alpha_over_bg.sh fgr.mp4 pha.mp4 newplate.jpg out.mp4   # image plate
bash scripts/alpha_over_bg.sh fgr.mp4 pha.mp4 bg_clip.mp4  out.mp4   # video plate
```

Prefer this over keying the green `com.mp4` — compositing the raw `pha`+`fgr` avoids
green spill on hair edges entirely.

### 4. Manual loop (fine-grained control / custom bg colour)

When you need per-frame logic, drive the model directly (recurrent state `rec`
carries temporal info — pass it back in every step, this is why RVM is stable):

```python
from torchvision.transforms import ToTensor
from inference_utils import VideoReader, VideoWriter   # only in a cloned repo
reader = VideoReader('input.mp4', transform=ToTensor())
writer = VideoWriter('out.mp4', frame_rate=30)
bgr = torch.tensor([.47, 1, .6]).view(3, 1, 1)          # green
rec = [None] * 4                                         # <- temporal memory
with torch.no_grad():
    for src in DataLoader(reader):
        fgr, pha, *rec = model(src, *rec, downsample_ratio=0.25)
        writer.write(fgr * pha + bgr * (1 - pha))
```

## Verify

- **Alpha exists and matches length:** `ffprobe pha.mp4` frame count == source; for a
  PNG sequence `ls out_rgba/*.png | wc -l` == frames.
- **Temporal stability (the whole point):** scrub `com.mp4`/`pha.mp4` frame-by-frame
  — edges should be steady, not crawling/shimmering between frames. If they flicker,
  you're likely on a per-frame path (wrong tool) or `rec` isn't being carried.
- **Edge quality:** open the RGBA sequence over a checkerboard — hair/motion-blur
  should be soft, not a hard cardboard cutout or haloed. Re-run with `--variant
  resnet50` and/or a higher `--downsample` if edges are ragged.
- **New-bg composite:** `out.mp4` shows the subject cleanly on the plate with no
  green fringe and no bg bleeding through the body.
- **Audio preserved:** `alpha_over_bg.sh` keeps `-map 0:a?`; confirm the output isn't silent.

## Pitfalls

- **RVM is trained for humans/portraits.** It mattes people and foregrounded subjects
  well; arbitrary objects/scenes are hit-or-miss. For a specific non-human object,
  use `video-object-tracking-sam2` (SAM 2). For a per-frame BiRefNet/`rembg` cutout
  of stills, use `background-removal-batch`.
- **Set `downsample_ratio` for your resolution.** Too high on 4K wastes compute and
  can OOM; too low on HD gives mushy edges. Use the table above.
- **No CUDA on this Mac.** MPS works via `PYTORCH_ENABLE_MPS_FALLBACK=1` (the helper
  sets it) but is slow and fp32-only; keep clips short or offload the matte to a GPU.
- **fp16 is CUDA-only.** The helper only uses fp16 on CUDA — forcing half precision on
  CPU/MPS errors or corrupts output.
- **PyAV (`av`) is required** for `convert_video`'s video reader/writer; a missing/old
  `av` is the usual "it won't read my mp4" cause. `pip install av`.
- **VFR source → desynced output.** Transcode variable-frame-rate phone footage to CFR
  first (`ffmpeg -i in.mp4 -vsync cfr -r 30 cfr.mp4`) or frames drift.
- **Don't key the green composite when you have `pha`+`fgr`.** Chromakeying `com.mp4`
  reintroduces the spill RVM already removed — composite `fgr`+`pha` directly (recipe 3).
- **`torch.hub` first run needs network** to fetch code + weights into
  `~/.cache/torch/hub`; on an air-gapped box, clone the repo and load weights locally.
