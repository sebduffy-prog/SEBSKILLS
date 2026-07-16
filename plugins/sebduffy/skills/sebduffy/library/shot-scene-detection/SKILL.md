---
name: shot-scene-detection
category: media
description: >
  Detect every shot boundary / scene cut in a video and produce a timecoded shot
  list plus split clips. Use when the user says "find all the cuts", "split this
  video at every scene change", "give me a shot list", "detect scene boundaries",
  "cut this into clips per scene", "export an EDL / cut list", "one file per shot",
  or "timecodes for each camera cut". Runs PySceneDetect (content/adaptive
  detectors) locally, exports CSV / EDL / FCPXML / HTML cut lists, splits into
  per-shot clips, and saves preview thumbnails per scene. TransNetV2 fallback for
  gradual dissolves. Not silence-based, not reframing.
when_to_use:
  - "Split a long video into one clip per scene/shot at every hard cut"
  - "Get a timecoded shot list (start/end TC + frame numbers) as CSV"
  - "Export an EDL or Final Cut Pro XML cut list to hand to an editor"
  - "Count how many distinct shots / camera cuts are in a video"
  - "Save a preview thumbnail for each detected scene"
  - "Detect soft dissolves / fades that a simple threshold misses (TransNetV2)"
when_not_to_use:
  - "Cut on speech/silence gaps, not visual cuts → use auto-silence-cut"
  - "Pull one known in/out segment out of a video → use video-clip-extractor"
  - "Reframe/crop a clip to 9:16 or 1:1 → use social-video-reframe"
  - "General ffmpeg trim/concat/mux you already know the timecodes for → use ffmpeg-cookbook"
  - "Extract N frames or 1 fps stills, not scene-aware → use video-frame-extraction"
  - "Build a storyboard/contact sheet grid image → use contact-sheet-storyboard"
keywords: [scene detection, shot detection, shot boundary, cut detection, pyscenedetect, scenedetect, transnetv2, split video, cut list, edl, fcpxml, shot list, timecodes, scene cuts, detect-content, detect-adaptive]
similar_to: [ffmpeg-cookbook, video-clip-extractor, auto-silence-cut, video-frame-extraction, contact-sheet-storyboard, long-video-to-shorts]
inputs_needed:
  - "Path to the source video"
  - "What you want out: split clips, CSV shot list, EDL/FCPXML, thumbnails (or all)"
  - "Sensitivity if known: lower threshold = more cuts (default is fine to start)"
  - "Output directory (defaults to alongside the source)"
produces: "Per-shot clips and/or a timecoded cut list (CSV/EDL/FCPXML/HTML) + per-scene thumbnails"
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Shot / Scene Detection

Find every shot boundary in a video, then split it into per-shot clips and/or
export a timecoded cut list (CSV, EDL, FCPXML, HTML). Primary engine is
[PySceneDetect](https://www.scenedetect.com/) (Breakthrough). For hard cases
(slow dissolves, cross-fades) fall back to
[TransNetV2](https://github.com/soCzech/TransNetV2).

## When to use

- "Split this at every scene cut" → `split-video`
- "Give me a shot list with timecodes" → `list-scenes` (CSV)
- "Export a cut list for the editor" → `save-edl` / `save-fcp`
- "How many shots are in this?" → `list-scenes`, count rows
- "Thumbnail per scene" → `save-images`

## Prerequisites

**PySceneDetect** (pip, works on this Mac's Python 3.9):

```bash
python3 -m pip install --user 'scenedetect[opencv]'
scenedetect version   # confirm CLI is on PATH
```

If `scenedetect` isn't on PATH after `--user` install, invoke via
`python3 -m scenedetect ...`.

**ffmpeg** — required for `split-video` and `save-images`. This Mac has NO brew
ffmpeg; use the portable one from the `imageio-ffmpeg` pip package and put it on
PATH so PySceneDetect can find it:

```bash
FFDIR="$(python3 -c 'import imageio_ffmpeg,os;print(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()))')"
# the binary is named ffmpeg-<ver>-macos... — symlink it to plain "ffmpeg"
ln -sf "$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" "$FFDIR/ffmpeg"
export PATH="$FFDIR:$PATH"
```

Or use `_research_bank/bin` if ffmpeg already lives there. The helper
`scripts/detect.sh` does this PATH wiring for you.

**TransNetV2 (optional, only for gradual transitions):**

```bash
python3 -m pip install --user tensorflow ffmpeg-python pillow
git clone https://github.com/soCzech/TransNetV2   # weights in inference/transnetv2-weights/
```

## Recipes

All commands follow the pattern: `scenedetect -i INPUT [global opts] DETECTOR [detector opts] COMMAND [command opts] ...`. Commands chain — you can list, save an EDL, split, and save images in one pass.

### 1. Timecoded shot list → CSV (most common)

```bash
scenedetect -i input.mp4 -o out/ detect-adaptive list-scenes
# -> out/input-Scenes.csv  (Scene #, Start/End timecode, Start/End frame, length)
```

`detect-adaptive` handles camera motion well (default). Use `detect-content` for
fast MTV-style cutting. Add `-s out/stats.csv` to cache frame scores for fast
re-tuning.

### 2. Split into one clip per shot

```bash
scenedetect -i input.mp4 -o out/ detect-adaptive split-video
# -> out/input-Scene-001.mp4, -Scene-002.mp4, ...  (re-encoded, frame-accurate)
```

Add `--copy` for fast stream-copy splits (keyframe-aligned, less precise; needs
mkvmerge or falls back to ffmpeg `-c copy`). Use `-f '$VIDEO_NAME-$SCENE_NUMBER.mp4'`
to control filenames.

### 3. Export an editor cut list (EDL / FCPXML / HTML)

```bash
scenedetect -i input.mp4 -o out/ detect-content save-edl          # CMX 3600 .edl
scenedetect -i input.mp4 -o out/ detect-content save-fcp          # FCP7 xmeml
scenedetect -i input.mp4 -o out/ detect-content save-html         # visual scene list
```

### 4. Preview thumbnail per scene

```bash
scenedetect -i input.mp4 -o out/ detect-adaptive save-images -n 1   # 1 image per scene
```

### 5. Tune sensitivity

Fewer/more cuts is controlled by threshold. Lower = more sensitive = more cuts.

```bash
scenedetect -i input.mp4 detect-content -t 27 list-scenes    # content default ~27
scenedetect -i input.mp4 detect-adaptive -t 3.0 list-scenes  # adaptive default ~3.0
```

Speed up long files with `-d 2` (downscale) or `--frame-skip 1`. Ignore short
blips with `-m 15` (min-scene-len frames) on the detector.

### 6. Everything at once

```bash
scenedetect -i input.mp4 -o out/ detect-adaptive -m 15 \
  list-scenes save-edl save-images -n 1 split-video
```

### 7. Helper script (handles ffmpeg PATH for you)

```bash
bash scripts/detect.sh input.mp4 out/            # CSV + EDL + thumbnails
bash scripts/detect.sh input.mp4 out/ --split    # also split into clips
```

### 8. TransNetV2 fallback (gradual dissolves)

When PySceneDetect misses soft transitions, run TransNetV2's frame-level model:

```bash
python3 TransNetV2/inference/transnetv2.py input.mp4
# writes input.mp4.scenes.txt (start_frame end_frame per line) + .predictions.txt
```

Convert frame ranges to timecodes with the source fps (`ffprobe -show_streams`),
then split with ffmpeg using the recipes in ffmpeg-cookbook.

## Verify

- CSV: `head out/input-Scenes.csv` — confirm rows have monotonically increasing
  start timecodes and the last End TC ≈ full duration.
- Clip count: `ls out/*-Scene-*.mp4 | wc -l` should equal CSV scene rows.
- Spot-check a boundary: open two adjacent clips; the last frame of clip N and
  first frame of clip N+1 should straddle a real cut, not mid-shot.
- Split coverage: sum of clip durations ≈ source duration (no gaps/overlaps).

## Pitfalls

- **`split-video`/`save-images` fail silently or error "ffmpeg not found"** →
  ffmpeg isn't on PATH. Run the Prerequisites symlink step; the portable binary
  from `imageio-ffmpeg` is not named plain `ffmpeg`, so PySceneDetect won't
  auto-detect it until symlinked.
- **Too many tiny scenes** (flashing, handheld shake) → raise `-m`
  (min-scene-len) and/or raise threshold `-t`.
- **Missed cuts across similar-colored shots** → lower `-t`, or switch
  `detect-content` → `detect-adaptive`, or use TransNetV2.
- **Fades to/from black not caught** → use `detect-threshold` (fade detector),
  not content/adaptive.
- **Slow on long 4K files** → add `-d 2` (downscale) and cache with `-s stats.csv`
  so re-runs at new thresholds skip re-decoding.
- **`--copy` splits land on keyframes, not exact cuts** → drop `--copy` for
  frame-accurate (re-encoded) clips when precision matters.
- **Timecodes vs frames**: EDL/FCPXML use the source frame rate; VFR footage can
  drift — transcode to CFR first (`ffmpeg -i in.mp4 -vsync cfr -r 25 cfr.mp4`).
