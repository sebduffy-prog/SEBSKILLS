---
name: video-object-tracking-sam2
category: media
description: >
  Track, segment and mask ONE (or several) objects across every frame of a video
  with SAM 2 / SAM 2.1 from a single click, box or point prompt — then blur, pixelate,
  black-box redact, rotoscope (alpha matte / green-screen), or draw a following
  bounding box. Use when the user says "blur this face for the whole clip", "track
  that person and pixelate them", "redact the licence plate throughout", "rotoscope
  the product out of the shot", "mask this object across all frames", "cut out the
  subject as an alpha channel", "follow this thing with a box", "segment everything
  the car does", or "GDPR-blur bystanders in this footage". Produces per-frame masks
  plus a rendered output video. SAMURAI motion-aware variant for hard/occluded tracks.
when_to_use:
  - "Blur, pixelate or black-box a face / plate / logo across an entire clip (GDPR / privacy redaction)"
  - "Track a specific object or person from one click and keep the mask locked on it every frame"
  - "Rotoscope a product / subject out of a shot — export an alpha matte or green-screen cutout"
  - "Draw a bounding box that follows a moving object through the whole video"
  - "Segment and isolate multiple objects at once (each with its own mask/colour)"
  - "Motion-aware tracking through occlusion / fast motion / similar-looking distractors (SAMURAI)"
when_not_to_use:
  - "Just remove/replace the background on stills or simple clips → use background-removal-batch"
  - "Detect scene cuts / shot boundaries, not track an object → use shot-scene-detection"
  - "Read on-screen text (OCR), not mask an object → use video-ocr-onscreen-text"
  - "Only need per-frame motion / diff heatmap, not object masks → use keyframe-motion-frame-diff"
  - "Plain ffmpeg boxblur on a FIXED region you specify by hand → use ffmpeg-cookbook"
  - "Reframe/crop to 9:16 tracking the loudest speaker, not a masked object → use social-video-reframe"
keywords: [sam2, sam 2.1, segment anything, samurai, object tracking, video segmentation, masklet, rotoscope, blur face, redact, pixelate, gdpr blur, alpha matte, green screen, mask propagation, bounding box track, video matting, meta fair, propagate_in_video]
similar_to: [background-removal-batch, shot-scene-detection, social-video-reframe, video-ocr-onscreen-text, keyframe-motion-frame-diff, ffmpeg-cookbook]
inputs_needed:
  - "Path to the source video (or a directory of JPEG frames)"
  - "The prompt: a click point, a bounding box, or 'the face/plate/person on the left' — and which frame to prompt on (usually frame 0)"
  - "Desired output: blur / pixelate / black-box redact / alpha matte (rotoscope) / following bounding box / coloured mask overlay"
  - "Compute reality: is a CUDA GPU available (cloud) or only this Mac (MPS, tiny/small model, short clips)?"
  - "Model size preference if any (tiny/small = fast, large = most accurate)"
produces: "A per-frame mask sequence (PNG/RLE) plus a rendered output video (blurred / redacted / rotoscoped / boxed)"
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video Object Tracking & Masking (SAM 2)

Prompt an object once (click / box / point), and [SAM 2](https://github.com/facebookresearch/sam2)
propagates a pixel-accurate mask across **every** frame. Then composite that mask
into the deliverable: blurred face, pixelated plate, black-box redaction,
rotoscoped alpha matte, green-screen cutout, or a following bounding box. For
tough tracks (occlusion, fast motion, look-alike distractors) use the
[SAMURAI](https://github.com/yangchris11/samurai) motion-aware memory variant,
which reuses the same SAM 2.1 weights.

Two stages, cleanly separable:
1. **Track** → SAM 2 produces a mask per frame (GPU-heavy — do this where CUDA lives).
2. **Composite** → ffmpeg turns masks into the final video (light — runs on this Mac).

## When to use

- "Blur / pixelate / redact this face-plate-logo for the whole clip" → track + `scripts/composite.sh blur|pixelate|redact`
- "Rotoscope the subject out / give me an alpha matte" → track + `composite.sh alpha` (or `greenscreen`)
- "Follow this object with a bounding box" → track, then draw box from mask bbox per frame
- "Track several objects at once" → add multiple prompts with distinct `obj_id`s

## Prerequisites (read the compute note first)

**SAM 2 needs Python ≥ 3.10 and torch ≥ 2.3.1 — this Mac's system Python is 3.9**,
so you MUST create a modern env. And SAM 2 video propagation is genuinely
GPU-hungry: on CUDA it's real-time-ish; on Apple **MPS** it runs but is slow and
lower quality (fine for short clips + tiny/small model). For anything long or
high-res, run the *track* stage on a cloud GPU (Colab / a Railway or rented
box) and bring the mask PNGs back here to composite.

**Modern Python env + SAM 2:**

```bash
# use pyenv/conda/uv to get a 3.10+ interpreter, then:
python3.11 -m venv ~/.venvs/sam2 && source ~/.venvs/sam2/bin/activate
pip install --upgrade pip
git clone https://github.com/facebookresearch/sam2.git && cd sam2
pip install -e .            # installs the sam2 package + SAM2VideoPredictor
python -c "import torch;print(torch.__version__, torch.backends.mps.is_available())"
```

**Checkpoints (SAM 2.1 — grab one; tiny is plenty for redaction, large for clean mattes):**

```bash
cd checkpoints && ./download_ckpts.sh     # all four, or curl a single one:
# sam2.1_hiera_tiny.pt  small.pt  base_plus.pt  large.pt
# configs live at sam2/configs/sam2.1/sam2.1_hiera_[t|s|b+|l].yaml
```

**ffmpeg (compositing, runs on this Mac — no brew here):** use the portable binary
from the `imageio-ffmpeg` pip package (or `_research_bank/bin`) and put it on PATH:

```bash
FF=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
ln -sf "$FF" "$(dirname "$FF")/ffmpeg"; export PATH="$(dirname "$FF"):$PATH"
```

## Recipes

### 1. Extract frames (SAM 2 video state wants JPEG frames named 0-indexed)

```bash
mkdir -p frames
ffmpeg -i input.mp4 -q:v 2 -start_number 0 'frames/%05d.jpg'
FPS=$(ffprobe -v0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate input.mp4)
```

### 2. Track one object → mask-per-frame PNGs (SAM2VideoPredictor)

Prompt with a **box** (`x0,y0,x1,y1`) or a **point** on frame 0. This script (in
`scripts/`) wraps the exact API — `build_sam2_video_predictor` →
`init_state` → `add_new_points_or_box` → `propagate_in_video` — and writes a
binary mask PNG per frame to `masks/`:

```bash
python scripts/track_sam2.py \
  --frames frames --out masks \
  --checkpoint sam2/checkpoints/sam2.1_hiera_small.pt \
  --config configs/sam2.1/sam2.1_hiera_s.yaml \
  --box 420,180,610,430          # OR: --point 512,300 --label 1
# add more prompts for more objects: --box ... --obj 2  (repeatable)
```

MPS users: export `PYTORCH_ENABLE_MPS_FALLBACK=1` before running so unsupported
ops fall back to CPU instead of erroring. Prefer `--checkpoint ...tiny/small` on MPS.

### 3. Composite the masks into the deliverable (ffmpeg, local)

`scripts/composite.sh` takes the source video + the `masks/` PNG sequence and the
effect. It builds an alpha-masked overlay so the effect is confined to the tracked
object.

```bash
bash scripts/composite.sh input.mp4 masks blur      out.mp4   # gaussian-blur the object
bash scripts/composite.sh input.mp4 masks pixelate  out.mp4   # mosaic / pixelate it
bash scripts/composite.sh input.mp4 masks redact    out.mp4   # solid black box over it
bash scripts/composite.sh input.mp4 masks alpha      out.mov   # object cut out, transparent bg (ProRes 4444)
bash scripts/composite.sh input.mp4 masks greenscreen out.mp4  # object on chroma-green
bash scripts/composite.sh input.mp4 masks overlay    out.mp4   # semi-transparent red mask (QC preview)
```

Under the hood (what `blur` runs, so you can hand-tune):

```bash
ffmpeg -i input.mp4 -framerate $FPS -i 'masks/%05d.png' -filter_complex \
 "[0:v]boxblur=20:2[bl]; \
  [1:v]format=gray,geq=lum='p(X,Y)':a='p(X,Y)'[m]; \
  [0:v][bl][m]maskedmerge[out]" \
 -map '[out]' -map 0:a? -c:a copy out.mp4
```

### 4. Following bounding box (instead of a mask overlay)

Have `track_sam2.py` also emit `boxes.csv` (`frame,x0,y0,x1,y1` = tight bbox of the
mask). Draw it with ffmpeg `drawbox` via `sendcmd`, or simplest — burn per-frame
boxes with the `--draw-box` flag on the tracker, which writes `boxed.mp4` directly.

### 5. SAMURAI (hard tracks: occlusion, fast motion, distractors)

Same weights, motion-aware memory + Kalman filtering — noticeably more robust when
plain SAM 2 drifts or swaps onto the wrong object.

```bash
git clone https://github.com/yangchris11/samurai && cd samurai
pip install -e .           # reuses SAM 2.1 checkpoints
printf 'x,y,w,h\n' > bbox.txt          # first-frame box as x,y,WIDTH,HEIGHT
echo '420,180,190,250' >> bbox.txt
python scripts/demo.py --video_path input.mp4 --txt_path bbox.txt
```

Accepts an mp4 or a frame directory. Note SAMURAI's bbox is `x,y,w,h` (top-left +
size), NOT the `x0,y0,x1,y1` corners SAM 2's API uses — convert carefully.

## Verify

- **Mask count == frame count:** `ls masks/*.png | wc -l` equals frames extracted.
- **Lock-on:** scrub `out.mp4` — the effect stays glued to the object with no
  1-frame gaps, and does NOT bleed onto the background or jump to a look-alike.
- **Redaction is airtight (GDPR):** step frame-by-frame past occlusions and quick
  turns — a single unblurred frame defeats the purpose. Dilate the mask a few px
  (`scripts/composite.sh ... --grow 6`) for a safety margin.
- **Alpha matte:** open `out.mov` over a checkerboard; edges should be clean, not
  haloed. Re-run with the `large` checkpoint if edges are ragged.
- **Coverage:** output duration and fps match the source (`ffprobe out.mp4`).

## Pitfalls

- **`python>=3.10` / `torch>=2.3.1` required** — the system 3.9 on this Mac will
  fail to install SAM 2. Always use the venv/conda step above.
- **No CUDA on this Mac.** MPS works but is slow and lossier; keep clips short and
  use tiny/small, or offload the track stage to a cloud GPU and composite locally.
- **MPS op errors** → set `PYTORCH_ENABLE_MPS_FALLBACK=1`. If masks come back empty
  or garbage on MPS, that's the known quality gap — validate on CPU/CUDA.
- **Frame naming matters:** SAM 2's video state expects `%05d.jpg` starting at 0.
  Gaps or 1-indexing silently misalign masks to frames.
- **fps drift when compositing:** pass the source fps to the mask input
  (`-framerate $FPS`) or masks and frames desync over long clips; transcode VFR
  sources to CFR first.
- **Track drifts / swaps objects** → add a correction click on a later frame
  (`--point ... --frame N`), tighten the initial box, or switch to SAMURAI.
- **SAMURAI vs SAM 2 box format:** `x,y,w,h` vs `x0,y0,x1,y1` — a silent source of
  "it tracked the wrong thing".
- **Audio dropped:** compositing recipes include `-map 0:a? -c:a copy`; keep it or
  the output goes silent.
- **Long/4K clips OOM the GPU:** `init_state(..., offload_video_to_cpu=True,
  offload_state_to_cpu=True)` (exposed as `--offload` in the tracker) trades speed
  for memory; or downscale, track, then upscale the masks with `-sws_flags neighbor`.
