---
name: video-frame-extraction
category: media
description: >
  Extract video frames to PNG/JPG with ffmpeg — pull every frame, every Nth
  frame, one per second, keyframes only, or a single frame at an exact
  timestamp. Also runs the full extract → per-frame process → re-encode harness
  that rebuilds a video from processed frames while keeping the original audio
  in sync. Use when someone says "grab frames from this video", "export frames
  as images", "pull every 10th frame", "screenshot at 00:01:23", "dump all
  frames", "process each frame then rebuild the video with audio", or "turn a
  folder of frames back into an mp4".
when_to_use:
  - "Pull every Nth frame of a clip out as numbered PNGs/JPGs"
  - "Grab one frame per second (or per N seconds) for sampling/thumbnails"
  - "Save a single still at an exact timestamp (e.g. 00:01:23.500)"
  - "Extract only keyframes (I-frames) fast, without decoding everything"
  - "Run frames through an image step (upscale, mask, filter) then rebuild the video keeping audio"
  - "Rebuild an mp4 from an existing folder of image frames and re-mux the original audio"
when_not_to_use:
  - "Want AI shot/scene boundaries, not fixed intervals → use shot-scene-detection"
  - "Want frame-diff / motion keyframe detection → use keyframe-motion-frame-diff"
  - "Want a laid-out grid/contact sheet of thumbnails → use contact-sheet-storyboard"
  - "General transcode / codec change, no frame export → use batch-transcode-encode or ffmpeg-cookbook"
  - "Just need to download the source video first → use youtube-download"
keywords: [ffmpeg, extract frames, frames to png, every nth frame, select filter, fps filter, thumbnail, keyframe, i-frame, frame at timestamp, image2, re-mux audio, rebuild video from frames, frame sequence, dump frames, screenshot video, fps_mode]
similar_to: [ffmpeg-cookbook, shot-scene-detection, keyframe-motion-frame-diff, contact-sheet-storyboard, frame-interpolation-retiming, batch-transcode-encode]
inputs_needed:
  - "Path to the source video"
  - "Sampling rule: every frame / every Nth frame / N per second / keyframes only / single timestamp"
  - "Output format (png lossless vs jpg smaller) and output folder"
  - "If rebuilding: the per-frame processing step and the target output fps"
produces: A numbered image sequence (PNG/JPG) in a folder, and optionally a re-encoded video rebuilt from processed frames with original audio intact.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video Frame Extraction

Extract frames from a video as images, and (optionally) run the full
extract → process → re-encode loop that rebuilds the video from processed
frames while keeping the original audio in sync.

## When to use

- Export frames as images at a chosen cadence (all / every Nth / per-second / keyframes).
- Grab a single still at a precise timestamp.
- Do per-frame work (mask, upscale, filter, annotate) and reassemble a video
  with the original audio re-muxed back on top.

## Prerequisites (this Mac)

No brew ffmpeg here. Use the portable binary from the pip `imageio-ffmpeg` wheel:

```bash
FF=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())")
echo "$FF"          # cache this path; reuse as "$FF" below
"$FF" -version | head -1
```

If the import fails: `python3 -m pip install --user imageio-ffmpeg`. A build
also lives at `_research_bank/bin`. There is no separate `ffprobe`; get metadata
from `ffmpeg` itself (see Verify) or via `imageio_ffmpeg`.

Newer builds (5.1+, which this wheel ships) prefer `-fps_mode` over the legacy
`-vsync`. Commands below use `-fps_mode`; if you hit an old binary, swap
`-fps_mode vfr` → `-vsync vfr` and `-fps_mode passthrough` → `-vsync 0`.

## Recipes

Set once per session:

```bash
FF=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())")
IN=input.mp4
OUT=frames && mkdir -p "$OUT"
```

### 1. Every frame → PNG sequence

```bash
"$FF" -i "$IN" -start_number 0 "$OUT/frame_%06d.png"
```

`%06d` zero-pads to 6 digits so files sort correctly. Use `.jpg` + `-q:v 2`
(2 = best, 31 = worst) for far smaller files when lossless isn't needed.

### 2. Every Nth frame

Keep 1 of every N frames. `n` is the 0-based frame index; `not(mod(n,N))` is true
on 0, N, 2N, … Escape the comma as `\,` inside the filter expression.

```bash
N=10
"$FF" -i "$IN" -vf "select='not(mod(n\,$N))'" -fps_mode passthrough "$OUT/frame_%05d.png"
```

`-fps_mode passthrough` (a.k.a. `-vsync 0`) stops ffmpeg re-timing/duplicating so
you get exactly the selected frames — one file per kept frame.

### 3. Sample at a frame rate (per-second thumbnails)

`fps=1` = one frame per second; `fps=1/5` = one every 5s; `fps=2` = two/sec.
The `fps` filter resamples on the timeline, so it's the right tool for even
time-spacing (unlike `select`, which counts source frames):

```bash
"$FF" -i "$IN" -vf "fps=1" "$OUT/thumb_%04d.png"
```

Prefer the perceptually "best" frame in each interval (sharp, non-blurry) with
the `thumbnail` filter — great for previews/contact-sheet feeds:

```bash
"$FF" -i "$IN" -vf "thumbnail=n=100" -fps_mode passthrough "$OUT/best_%03d.png"
```

### 4. Keyframes (I-frames) only — fast

Decode-skip everything but keyframes; near-instant on long files:

```bash
"$FF" -skip_frame nokey -i "$IN" -vf "select='eq(pict_type\,I)'" -fps_mode passthrough "$OUT/key_%04d.png"
```

### 5. Single frame at an exact timestamp

Put `-ss` **before** `-i` for a fast input seek, then take one frame:

```bash
"$FF" -ss 00:01:23.500 -i "$IN" -frames:v 1 -q:v 2 still.jpg
```

For a frame-accurate grab on codecs where input-seek lands on the nearest
keyframe, seek slightly early and refine after decode:

```bash
"$FF" -ss 00:01:20 -i "$IN" -vf "select='gte(t\,83.5)'" -frames:v 1 still.png
```

### 6. Full harness: extract → process → rebuild with audio

The critical part is re-muxing: read the **original** video as a second input and
map only its audio, so voice/music stays perfectly aligned.

```bash
# a) know the source fps (needed so the rebuilt video plays at the right speed)
FPS=$("$FF" -i "$IN" 2>&1 | grep -oE '[0-9.]+ fps' | head -1 | awk '{print $1}')
echo "source fps = $FPS"

# b) extract EVERY frame (rebuild needs a 1:1 sequence)
mkdir -p proc/in proc/out
"$FF" -i "$IN" -start_number 0 "proc/in/f_%06d.png"

# c) process each frame — swap in your real step (PIL, ImageMagick, an upscaler…)
#    Example: greyscale via ffmpeg per file. Keep the SAME numbering in proc/out.
for f in proc/in/f_*.png; do
  b=$(basename "$f")
  "$FF" -y -i "$f" -vf "format=gray" "proc/out/$b"
done

# d) rebuild: frames → video, then map audio from the ORIGINAL input (input #1)
"$FF" -framerate "$FPS" -start_number 0 -i "proc/out/f_%06d.png" \
      -i "$IN" \
      -map 0:v -map 1:a? \
      -c:v libx264 -pix_fmt yuv420p -crf 18 \
      -c:a copy -shortest processed.mp4
```

Notes:
- `-map 1:a?` — the `?` makes audio optional so a silent source doesn't error.
- `-pix_fmt yuv420p` guarantees the PNGs re-encode to a widely-playable H.264.
- `-shortest` trims to whichever stream ends first, avoiding a hanging tail.
- If your process step drops/reorders frames, the video will desync — keep a
  strict 1:1 mapping and identical zero-padded numbering in and out.

### Rebuild from an existing frame folder

```bash
"$FF" -framerate 25 -pattern_type glob -i "frames/*.png" \
      -i original.mp4 -map 0:v -map 1:a? \
      -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a copy -shortest out.mp4
```

## Verify

```bash
ls "$OUT" | head && echo "count: $(ls "$OUT" | wc -l)"        # frames landed & sorted
"$FF" -i still.jpg 2>&1 | grep -E 'Video:|Stream'              # a still decodes
# rebuilt video has BOTH streams and expected duration:
"$FF" -i processed.mp4 2>&1 | grep -E 'Duration|Stream #0'
```

Confirm A/V sync by eye: play `processed.mp4` and check dialogue matches lips;
compare its `Duration` line to the source.

## Pitfalls

- **`-ss` placement.** Before `-i` = fast (keyframe) seek; after `-i` = slow but
  frame-accurate decode-seek. For single stills, before `-i` is usually right.
- **`select` vs `fps`.** `select`/`mod(n,N)` counts *source frames* (uneven in
  wall-clock time on VFR footage); `fps=` resamples to even *time* spacing. Pick
  by whether you mean "every Nth frame" or "every N seconds".
- **Missing `-fps_mode passthrough` with `select`.** Without it ffmpeg may
  duplicate/drop to hit a CFR target, giving more or fewer files than you selected.
- **Comma escaping.** Inside a `-vf` expression, commas separating filter args
  must be `\,` or the filtergraph mis-parses.
- **Padding width.** Match `%06d` to your frame count (6 digits ≈ up to ~1M
  frames). Too-narrow padding breaks lexical sort at the rollover.
- **Rebuild desync.** Dropped/renumbered frames or a wrong `-framerate` shift
  audio out of sync — the source fps from step (a) and 1:1 numbering are load-bearing.
- **Huge output.** Every-frame PNGs of a long clip is gigabytes; prefer `.jpg -q:v 2`
  or sample (recipe 2/3) unless you truly need every lossless frame.
