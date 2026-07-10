---
name: ai-upscale-restore
category: media
description: >
  AI-upscale and restore low-res or degraded images and video, and fix damaged faces.
  Real-ESRGAN (RealESRGAN_x4plus / anime / general-v3) super-resolves a blurry logo, tiny
  product shot, screenshot, or old photo to 2x-4x; GFPGAN or CodeFormer rebuilds soft,
  blurry, or scratched faces in scanned prints. Reach for this whenever someone says
  "upscale this image", "enhance resolution", "make this HD / 4K", "de-blur", "sharpen a
  low-res logo", "restore an old photo", "fix the faces", "unblur", "super resolution",
  "enlarge without pixelation", "clean up a screenshot", or wants an old family scan
  brought back. Also upscales video frame-by-frame.
when_to_use:
  - "A logo/asset is too small or pixelated and you need it at 2x-4x for print or a deck"
  - "Restore an old scanned family photo — sharpen it and rebuild the blurry faces"
  - "Enhance a low-res screenshot, thumbnail, or product image to look crisp"
  - "Faces in a photo are soft/mushy and you want them reconstructed (GFPGAN/CodeFormer)"
  - "Upscale a small/old video clip to a higher resolution frame-by-frame"
  - "General 'make this sharper / higher resolution / HD' request on any raster image"
when_not_to_use:
  - "Just resize/pad/letterbox with no detail synthesis → use ffmpeg-cookbook scale filter"
  - "Cut out the subject / drop the background → use background-removal-batch"
  - "Generate a brand-new image from a prompt → use flux-image-gen or nano-banana-image"
  - "Only re-encode / change codec or bitrate (same resolution) → use batch-transcode-encode"
  - "Add smoother motion / more fps (not resolution) → use frame-interpolation-retiming"
  - "python/ffmpeg/torch not installed yet → run media-toolchain-bootstrap first"
keywords: [upscale, super resolution, super-resolution, real-esrgan, realesrgan, esrgan, waifu2x, gfpgan, codeformer, face restoration, restore old photo, enhance, unblur, deblur, sharpen, denoise, hd, 4k, enlarge, upsample, image restoration, scanned photo, low-res, pixelated]
similar_to: [background-removal-batch, flux-image-gen, nano-banana-image, batch-transcode-encode, frame-interpolation-retiming, ffmpeg-cookbook, comfyui-workflow-runner]
inputs_needed:
  - "Absolute path(s) to the input image(s) or video, or a folder to batch"
  - "Goal: general upscale, anime/illustration, or FACE restoration (or both)?"
  - "Target scale (2x / 3.5x / 4x) or target longest edge in px"
  - "For faces: how aggressive — natural (GFPGAN v1.4) or identity-preserving/deep repair (CodeFormer weight)?"
  - "Output folder for results"
produces: Upscaled/restored PNGs (or an upscaled MP4 for video) written to an output folder
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# AI Upscale & Restore

Two independent jobs, often combined:
- **Super-resolution** — invent real detail while enlarging (Real-ESRGAN). Use for logos,
  product shots, screenshots, whole photos, video frames.
- **Face restoration** — rebuild soft/damaged faces specifically (GFPGAN or CodeFormer).
  Faces are what breaks first in an upscale, so they get a dedicated model.

Combine them: Real-ESRGAN upscales the whole frame, `--face_enhance` runs GFPGAN on faces
in the same pass.

## When to use

Someone hands you something too small, too blurry, or too old. If they say "enhance",
"make it HD", "unblur", "restore" — this skill. If they only want a bigger canvas with no
new detail (plain resize), that's `ffmpeg -vf scale`, not this.

## Prerequisites (this Mac)

Python 3.9 here. Real-ESRGAN/GFPGAN pull in `torch`, `basicsr`, `facexlib`. A one-time
setup in a venv keeps it clean:

```bash
python3 -m venv ~/.venvs/upscale && source ~/.venvs/upscale/bin/activate
pip install --upgrade pip
pip install torch torchvision                 # CPU wheels are fine (slow but works)
pip install realesrgan gfpgan basicsr facexlib
```

Known 2026 snag: `basicsr` imports `torchvision.transforms.functional_tensor`, removed in
newer torchvision. If you hit `ModuleNotFoundError: functional_tensor`, patch the one line:

```bash
F=$(python3 -c "import basicsr.data.degradations as m; print(m.__file__)")
sed -i '' 's/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/' "$F"
```

Models auto-download on first run to `~/.cache` / a local `weights/` — allow network once.
For video you also need ffmpeg (portable binary):

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")  # or _research_bank/bin/ffmpeg
```

No GPU? Everything runs on CPU. A 4x pass on a 1080p frame is seconds-to-minutes; keep
batches small and use `-t 512` tiling to cap RAM.

## Recipes

### 1. Upscale a low-res logo / image (general, 4x)

```bash
python -m realesrgan.inference_realesrgan \
  -n RealESRGAN_x4plus -i /path/to/logo.png -o /path/to/out --outscale 4 --ext png
```

If `python -m` can't find the entrypoint, clone the repo and run its script directly
(`python inference_realesrgan.py -n RealESRGAN_x4plus -i ...`).
Flags: `-n` model, `-i` file OR folder (batches), `-o` out folder, `-s/--outscale` final
scale (e.g. `3.5`), `-t 512` tile to save memory, `--fp32` for full precision on CPU,
`--suffix out` output name suffix.

Model picks:
- `RealESRGAN_x4plus` — default, photos/logos/general.
- `realesr-general-x4v3` — lighter general model; pair `-dn 0.5` to dial denoise strength.
- `RealESRGAN_x4plus_anime_6B` — illustrations/anime line art (kills the general model's mush).

### 2. Upscale AND fix faces in one pass (old photo)

```bash
python -m realesrgan.inference_realesrgan \
  -n RealESRGAN_x4plus -i /path/old_photo.jpg -o /path/out \
  --outscale 2 --face_enhance --ext png
```

`--face_enhance` runs GFPGAN on detected faces while Real-ESRGAN handles the background.
Good default for a single scanned print.

### 3. Face restoration only (GFPGAN, faces are the whole problem)

```bash
python -m gfpgan.inference_gfpgan \
  -i /path/inputs -o /path/results -v 1.4 -s 2 --bg_upsampler realesrgan
```

`-v` version: `1.4` = most detail/best identity (default pick), `1.3` = safest/most natural,
`1.2` = sharper no-colorize. `-s` upscale, `--bg_upsampler realesrgan` upsizes the
non-face background too (use `-bg_tile 400` if RAM-bound). Outputs land in
`results/restored_imgs/` (whole) and `results/cmp/` (before/after side-by-side).

### 4. Deeper / more controllable face repair (CodeFormer)

CodeFormer beats GFPGAN on badly degraded faces and lets you trade fidelity vs quality with
one knob. Run from a clone (`git clone https://github.com/sczhou/CodeFormer`, then its
`python scripts/download_pretrained_models.py facelib CodeFormer`):

```bash
python inference_codeformer.py -w 0.7 --input_path /path/in --output_path /path/out \
  --bg_upsampler realesrgan --face_upsample
```

`-w` (0.0-1.0) = fidelity weight: **low (0.3-0.5)** = higher quality, may drift identity;
**high (0.7-0.9)** = faithful to the original face. Start at `0.7`.

### 5. Upscale a video (frame-by-frame)

Real-ESRGAN ships `inference_realesrgan_video.py`, but the most robust path on this Mac is
explicit: split → upscale frames → reassemble with original audio.

```bash
IN=/path/clip.mp4; W=/path/work; mkdir -p "$W/frames" "$W/up"
FPS=$("$FF" -i "$IN" 2>&1 | grep -oE '[0-9.]+ fps' | head -1 | awk '{print $1}')
"$FF" -i "$IN" "$W/frames/%06d.png"                                  # 1. explode to PNGs
python -m realesrgan.inference_realesrgan -n realesr-animevideov3 \
  -i "$W/frames" -o "$W/up" --outscale 2 -t 256                      # 2. upscale every frame
"$FF" -framerate "$FPS" -i "$W/up/%06d_out.png" -i "$IN" \
  -map 0:v -map 1:a? -c:v libx264 -pix_fmt yuv420p -crf 17 \
  -c:a copy -shortest /path/clip_2x.mp4                              # 3. reassemble + audio
```

Use `realesr-animevideov3` (temporally stable) for video. Check the frame suffix Real-ESRGAN
wrote (`_out`) and match it in step 3. CPU video upscaling is slow — test on a short clip first.

## Verify

```bash
# Resolution actually grew (image):
python3 -c "from PIL import Image;print(Image.open('/path/out/logo_out.png').size)"
# Video dimensions doubled + audio still present:
"$FF" -i /path/clip_2x.mp4 2>&1 | grep -E 'Stream.*Video|Stream.*Audio'
```

Then eyeball it: open before/after. For faces, GFPGAN's `cmp/` side-by-sides and CodeFormer's
`out/final_results/` make the judgement quick. Success = sharper real detail and no
plastic/over-smoothed skin or warped features.

## Pitfalls

- **Over-smoothing / "AI plastic" faces** — dial GFPGAN down (`-v 1.3`) or raise CodeFormer
  `-w` toward 0.9 to keep the real face. There's no fully "neutral" restore.
- **Wrong model = mush** — anime/line art on the general model smears edges; use the anime
  model. Photos on the anime model flatten skin. Match model to content.
- **Text/logos with hard edges** — Real-ESRGAN can wobble crisp vector-like edges; if it's
  actually a vector, prefer re-exporting from source. For raster logos, `--outscale 2` is
  safer than 4x.
- **basicsr / torchvision import error** — apply the `functional_tensor` sed patch above.
- **Video temporal flicker** — use `realesr-animevideov3`, not `x4plus`, and keep a
  consistent `--outscale`. Frame suffix mismatch in the reassemble glob = "no such file".
- **RAM blowups on big images** — add `-t 512` (or `-t 256`) tiling; lower if it still OOMs.
- **Don't upscale then hand back JPEG** — write PNG (`--ext png`) so you don't re-compress
  the detail you just synthesised.
