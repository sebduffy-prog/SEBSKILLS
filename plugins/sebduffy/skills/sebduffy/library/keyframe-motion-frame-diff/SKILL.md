---
name: keyframe-motion-frame-diff
category: media
description: >
  Frame-diff analysis for video: collapse thousands of near-identical frames
  into a handful of UNIQUE keyframes using perceptual hashing (phash/dhash), and
  auto-detect + clip only the segments where something MOVED using OpenCV
  background subtraction (MOG2). Use this to reduce a 10k-frame dump to unique
  stills, dedupe a scraped frame folder, find the "interesting" moments in CCTV
  / dashcam / trailcam / screen-recording footage, or emit motion time-ranges
  and cut them to standalone clips. Triggers on "unique frames", "dedupe frames",
  "motion detection", "clip the motion", "when did something happen", "frame
  difference", "perceptual hash", "keyframes only".
when_to_use:
  - "I extracted 10,000 frames and only want the visually unique ones"
  - "Dedupe this folder of scraped/downloaded frames, drop the near-duplicates"
  - "Find and clip only the parts of this CCTV/dashcam/trailcam clip where something moves"
  - "Give me timestamps of every motion event in this security footage"
  - "Turn a long static screen recording into just the moments where the screen changed"
  - "I need one representative still per distinct scene, cheaply, no ML model"
when_not_to_use:
  - "Split on true scene/shot boundaries (hard cuts, fades) → use shot-scene-detection"
  - "Just pull frames at N fps or at timestamps (no dedup/motion logic) → use video-frame-extraction"
  - "Cut a clip between known start/end timestamps → use video-clip-extractor"
  - "Track a specific object/person across frames → use video-object-tracking-sam2"
  - "Make a printable grid of thumbnails from the keyframes → use contact-sheet-storyboard"
  - "Remove silent gaps from talking-head audio/video → use auto-silence-cut"
keywords: [keyframe, frame diff, framediff, perceptual hash, phash, dhash, imagehash, dedupe frames, deduplicate, unique frames, motion detection, background subtraction, mog2, opencv, cctv, dashcam, trailcam, videohash, near-duplicate, hamming distance, activity detection]
similar_to: [shot-scene-detection, video-frame-extraction, video-clip-extractor, contact-sheet-storyboard, video-object-tracking-sam2, auto-silence-cut]
inputs_needed:
  - "Source: a folder of extracted frames OR a video file"
  - "For dedup: strictness (Hamming threshold, default 6 — lower keeps more)"
  - "For motion: sensitivity + min blob area, and whether to just print time-ranges or also cut clips"
produces: "A folder of unique keyframe images, and/or motion time-ranges (stdout) plus per-event stream-copied clips"
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Keyframe & Motion Frame-Diff

Two cheap, model-free frame-difference workflows:

1. **Keyframe dedup** — perceptual-hash every frame, keep only those far enough
   (Hamming distance) from all already-kept frames. 10k frames → dozens of stills.
2. **Motion clipping** — OpenCV MOG2 background subtractor flags frames where a
   blob moved; collapse those into padded, gap-merged time-ranges and optionally
   cut them with ffmpeg stream-copy.

Both scripts accept **either a frames folder or a video file** and run in seconds
per minute of footage on CPU — no GPU, no neural net.

## When to use

Reach for this when the input is dominated by redundancy: near-static timelapse,
security/trailcam footage that's 95% empty, a scraped frame dump, or a long
screen recording. You want the *signal* frames (unique looks, or moments of
change) without watching the whole thing. If you need semantic shot boundaries
(a hard cut mid-motion) use `shot-scene-detection` instead — motion detection
will happily keep filming through a cut if the subject keeps moving.

## Prerequisites (macOS, this machine)

- **Python deps** (into whatever env you use):
  ```bash
  pip install pillow imagehash opencv-python-headless numpy imageio-ffmpeg
  ```
  `opencv-python-headless` avoids the GUI/Qt baggage — we only need the algos.
- **ffmpeg**: no brew here. `imageio-ffmpeg` ships a portable binary and both
  scripts call `imageio_ffmpeg.get_ffmpeg_exe()` automatically. A copy also
  lives at `_research_bank/bin`. You only need ffmpeg when the input is a video
  (frame extraction) or when using `--cut`.
- Scripts live in this skill's `scripts/` folder; run with plain `python3`.

## Recipes

### 1. Dedupe an existing frame folder → unique keyframes
```bash
python3 scripts/keyframe_dedup.py ./frames --out ./unique --threshold 6
# 10240 frames -> 37 unique keyframes (phash, threshold=6) in ./unique
```
- `--threshold` is the min Hamming distance (over a 64-bit hash) to count a frame
  as *new*. **Lower = stricter = more keyframes kept.** Start at 6; use 8-10 for
  aggressive collapse, 3-4 to catch subtle changes.
- `--hash phash` (default, DCT — robust to scale/compression), `dhash` (fast
  gradient), `ahash`, `whash` (wavelet). phash is the safe default.

### 2. Dedupe straight from a video (no pre-extraction)
```bash
python3 scripts/keyframe_dedup.py talk.mp4 --out ./unique --fps 2 --threshold 6
```
Samples at `--fps` via ffmpeg into a temp dir, then dedups. Handy for "one still
per distinct slide" from a screen recording.

### 3. Motion time-ranges from CCTV (print only)
```bash
python3 scripts/motion_clips.py cctv.mp4 --min-area 800 --sensitivity 25
# 12.400 18.900
# 143.100 151.700
# 4 events, 47.3s active / 3600.0s total   (to stderr)
```
Each stdout line is `start end` in seconds. Tune:
- `--min-area` — minimum moving-blob pixel area. Raise to ignore leaves/rain/
  small critters; lower to catch a distant figure.
- `--sensitivity` — MOG2 `varThreshold`; **lower = more sensitive**.
- `--pad` seconds of lead/tail per event (default 1.5), `--gap` merges events
  closer than N s (default 1.0), `--min-dur` drops blips (default 0.5s).

### 4. Motion → cut standalone clips
```bash
python3 scripts/motion_clips.py trailcam.mp4 --min-area 1200 --cut ./events
# writes events/motion_000_12.4-18.9.mp4 ...
```
Clips are ffmpeg `-c copy` (stream copy → instant, lossless, but cuts land on the
nearest keyframe; re-encode if you need frame-exact starts).

### 5. Whole-video near-duplicate check (different job)
To ask "are these two *videos* the same/near-dup" (not per-frame), use
`videohash` (akamhy/videohash) — one 64-bit wavelet hash per whole video:
```python
from videohash import VideoHash
a, b = VideoHash(path="a.mp4"), VideoHash(path="b.mp4")
print(a - b, a.is_similar(b))   # Hamming distance, bool
```
Note: videohash is lightly maintained (last release 2022) and needs ffmpeg on
PATH — fine for one-off dedup, but for per-frame keyframing use recipe 1.

## Verify

- **Dedup sanity**: `ls ./unique | wc -l` should be « input count. Eyeball the
  keyframes — no two should look identical; if you see dups, *lower* `--threshold`.
  If distinct scenes got merged into one keyframe, *raise* it.
- **Motion sanity**: sum of `(end-start)` (printed to stderr) should be a small
  fraction of total duration for sparse footage. Spot-check one clip actually
  contains movement; if empty clips appear, raise `--min-area`/`--min-dur`; if
  real events are missed, lower `--sensitivity` or `--min-area`.
- Re-run with a tweaked threshold — both scripts are idempotent (dedup overwrites
  `key_*`, motion re-emits ranges), so iterate freely.

## Pitfalls

- **Threshold direction is counter-intuitive.** For dedup, *lower* threshold
  keeps *more* frames (stricter about calling things duplicates). For motion,
  *lower* sensitivity means *more* motion detected.
- **Lighting flicker / auto-exposure / compression noise** trips both: phash may
  treat an exposure shift as a new keyframe; MOG2 may flag a global brightness
  change as motion. The morphology open+dilate in `motion_clips.py` mutes most
  speckle; for exposure churn raise `--min-area` and `--sensitivity`.
- **Camera motion breaks background subtraction.** MOG2 assumes a static camera.
  For handheld/dashcam pans, nearly every frame reads as motion — use keyframe
  dedup (recipe 1/2) instead, which is camera-motion tolerant.
- **MOG2 warm-up**: the first ~dozen frames build the background model and may
  false-positive; `--pad`/`--min-dur` usually absorb this, but for a hard cut at
  t=0 discard the first event if it starts at 0.0.
- **Stream-copy cut offset**: `--cut` snaps starts to the nearest keyframe, so a
  clip can begin up to a GOP early. Acceptable for review; re-encode (drop
  `-c copy`) for frame-accurate deliverables.
- **`opencv-python` vs `-headless`**: install only one. The headless build is
  correct here and avoids Qt/plugin errors in a headless/CI context.
