---
name: frame-interpolation-retiming
category: media
description: >
  Generate synthetic in-between frames to make video smoother — buttery slow-motion from
  ordinary 30fps footage, or up-convert a clip's frame rate (24/30 → 60/120fps) so it looks
  fluid. Two engines: fast ffmpeg minterpolate (mi_mode=mci optical flow, no GPU) for a quick
  pass, and RIFE (hzwer/Practical-RIFE) neural interpolation for cleaner 2x/4x results on
  hard motion. Reach for this whenever someone says "make this slow-mo smooth", "interpolate
  frames", "boost to 60fps", "fake slow motion", "fps up-conversion", "60fps this clip",
  "smooth motion", "motion interpolation", or "in-between frames".
when_to_use:
  - "Turn normal 30fps footage into smooth slow-motion instead of stuttery frame-doubling"
  - "Up-convert a 24/30fps clip to 60fps (or 120fps) so it plays fluid"
  - "A slowed-down clip judders and you want interpolated in-between frames"
  - "Need a quick CPU-only smoothing pass with ffmpeg (no model download)"
  - "Want the highest-quality result on fast/complex motion → RIFE 2x/4x"
when_not_to_use:
  - "Just change playback speed with NO new frames (choppy is fine) → use ffmpeg-cookbook setpts"
  - "Pull still frames out of a video → use video-frame-extraction"
  - "Upscale resolution / denoise / restore old footage → use ai-upscale-restore"
  - "ffmpeg / python not set up yet → run media-toolchain-bootstrap first"
  - "Re-encode / change codec/bitrate only → use batch-transcode-encode"
keywords: [frame interpolation, minterpolate, mci, optical flow, rife, practical-rife, slow motion, slowmo, slow-mo, fps up-conversion, 60fps, 120fps, motion interpolation, setpts, in-between frames, tweening, smooth video, retiming, mc_mode, aobmc]
similar_to: [ffmpeg-cookbook, ai-upscale-restore, batch-transcode-encode, video-frame-extraction, social-video-reframe]
inputs_needed:
  - "Absolute path to the input clip"
  - "Goal: smooth SLOW-MO (keep duration slower) or FPS UP-CONVERSION (same duration, higher fps)?"
  - "Target output fps (e.g. 60), and slow-mo factor if slowing (e.g. 2x = half speed)"
  - "Quality vs speed: quick ffmpeg pass, or best-quality RIFE (needs one-time model download + a GPU helps)?"
  - "Source fps (check with ffprobe) so the maths is right"
produces: A single interpolated MP4 with synthetic in-between frames (smoother slow-mo or higher fps)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Frame Interpolation & Retiming

Two ways to invent in-between frames: **ffmpeg minterpolate** (fast, CPU, zero setup) and
**RIFE** (neural, cleaner on hard motion, one-time model download). Pick by quality bar.

## When to use

The footage is real time but you want it **slower and still smooth**, or it's a low frame
rate and you want it **fluid (60/120fps)**. Interpolation synthesises new frames between the
real ones — unlike plain `setpts`, which just holds/drops existing frames and stutters.

Decide the intent first, it changes the maths:
- **Smooth slow-mo** — output is LONGER (half speed = 2x duration). Slow down + interpolate.
- **FPS up-conversion** — output is SAME duration, just more frames per second.

## Prerequisites (this Mac)

No brew ffmpeg. Use the portable binary from `imageio-ffmpeg`:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
# also mirrored at _research_bank/bin/ffmpeg
"$FF" -hide_banner -filters | grep minterpolate   # confirm the filter exists
```

Check the source fps before you compute anything (ffprobe is NOT bundled with imageio-ffmpeg;
use a portable one if present, else read fps from the clip's metadata in any player):

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate \
  -of csv=p=0 "$IN"        # e.g. 30000/1001 ≈ 29.97
```

RIFE path only: `git clone https://github.com/hzwer/Practical-RIFE`, `pip3 install -r
requirements.txt` (needs **Python ≤ 3.11** + torch — the system 3.9 works, or a venv),
then download a model release and unzip it into `train_log/`. GPU (CUDA/MPS) is much faster
but CPU works for short clips.

---

## Recipe A — ffmpeg minterpolate (fast, no setup)

`mi_mode=mci` = motion-compensated interpolation (optical flow). `mc_mode=aobmc` +
`vsbmc=1` give the smoothest, least-blocky output.

### A1. FPS up-conversion (same duration, e.g. 30 → 60fps)

```bash
"$FF" -i "$IN" \
  -vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out_60fps.mp4
```

### A2. Smooth slow-motion (e.g. 2x slower, silky at 60fps)

Slow down with `setpts`, THEN interpolate to the target fps. Audio can't stretch cleanly,
so drop it with `-an` (or handle separately). `setpts=2.0*PTS` = half speed = 2x longer.

```bash
"$FF" -i "$IN" \
  -vf "setpts=2.0*PTS,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -an slowmo_2x.mp4
```

Speed factor → `setpts` multiplier: 2x slower = `2.0*PTS`, 4x slower = `4.0*PTS`,
1.5x = `1.5*PTS`. Keep `fps=` at the smooth playback rate you want (usually 60).

Tips: minterpolate is single-threaded and slow on big frames — downscale first for a
preview (`scale=1280:-2,` before `minterpolate`). Fast/occluded motion can smear; if it
tears badly, drop to `me_mode=bidir` alone or switch to RIFE.

---

## Recipe B — RIFE (best quality, neural)

RIFE doubles frame count per pass. `--multi=2` = 2x frames, `--multi=4` = 4x
(`--exp=N` is the log form: `--exp=2` == `--multi=4`).

### B1. Smooth 2x / 4x (more frames, engine keeps output fps sensible)

```bash
cd Practical-RIFE
python3 inference_video.py --multi=2 --video="$IN"      # → INPUT_2X_<fps>fps.mp4
python3 inference_video.py --multi=4 --video="$IN"      # 4x frames
python3 inference_video.py --multi=2 --UHD --video="$IN"  # --UHD == --scale=0.5 for 4K
```

### B2. Force an output fps (up-conversion) or a PNG sequence

```bash
python3 inference_video.py --multi=4 --fps=60 --video="$IN"
python3 inference_video.py --multi=2 --img=frames_dir/    # numbered 0.png,1.png,...
```

### B3. RIFE for TRUE slow-mo (retime after interpolating)

RIFE adds frames but doesn't slow playback. For, say, 4x slow-mo from 30fps: interpolate
4x (→120 frames worth), then reinterpret at the original 30fps so it plays 4x longer:

```bash
python3 inference_video.py --multi=4 --fps=120 --video="$IN"   # → clip_4X_120fps.mp4
"$FF" -i clip_4X_120fps.mp4 -r 30 -c:v libx264 -crf 18 -pix_fmt yuv420p -an slowmo_4x.mp4
```

`--montage` splices the original beside the result for an easy before/after check.

---

## Verify

```bash
# 1. New fps / frame count is what you asked for:
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,nb_frames \
  -of default=nw=1 out.mp4

# 2. Duration matches intent (slow-mo should be LONGER; up-conversion same):
ffprobe -v error -show_entries format=duration -of csv=p=0 out.mp4

# 3. Eyeball a few interpolated frames for smearing/ghosting on fast motion:
"$FF" -i out.mp4 -vf "select='not(mod(n,15))'" -vsync vfr /tmp/chk_%03d.png
```

Smooth playback with no obvious stutter = success. Halos/warping around fast edges = the
interpolator struggled (see pitfalls).

## Pitfalls

- **Slow-mo vs up-conversion confusion.** Up-conversion keeps duration; slow-mo lengthens
  it. If duration didn't change but you wanted slow-mo, you forgot the `setpts`/retime step.
- **Audio.** You can't stretch audio to match slowed video without pitch artefacts — use
  `-an` for slow-mo, or process audio separately (`atempo`). For pure up-conversion, `-c:a copy`.
- **minterpolate is CPU-bound and single-threaded** — a 1080p minute can take many minutes.
  Downscale for previews; reserve full-res for the final render.
- **Interpolation artefacts** (ghosting, warped edges, smeared occlusions) show up on fast
  or complex motion. RIFE handles these far better than minterpolate. Neither invents
  detail hidden behind objects.
- **RIFE Python cap.** Practical-RIFE needs Python ≤ 3.11 and torch; wrong torch/CUDA
  combo = import errors. Use a venv. Forgetting to unzip a model into `train_log/` is the
  #1 first-run failure.
- **Don't over-interpolate.** 4x/8x on already-smooth footage rarely helps and multiplies
  artefacts + file size. Match the target fps to the delivery format (usually 60fps).
- **Always re-encode with `-pix_fmt yuv420p`** so the result plays everywhere (QuickTime/web).
