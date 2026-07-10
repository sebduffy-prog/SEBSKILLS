---
name: contact-sheet-storyboard
category: media
description: >
  Turn a video into a single contact-sheet / storyboard grid — evenly-spaced
  thumbnails tiled into rows and columns with the source timecode burned onto
  each cell — using ffmpeg's fps + drawtext + tile filters. Handles fixed-grid
  (e.g. a 5x6 sheet of the whole clip), one-thumb-per-N-seconds, one-thumb-per-scene
  storyboards, and multi-page sheets for long footage. Use when someone says
  "make a thumbnail grid of this video", "contact sheet", "storyboard every
  scene", "montage of screenshots", "overview grid with timestamps", "proof
  sheet", "vidcaps grid", or "one image summarising the whole video".
when_to_use:
  - "Make a single overview image of a whole video as a grid of thumbnails"
  - "Storyboard a clip — one tile per scene/beat, with timecodes visible"
  - "Proof/contact sheet with the timestamp burned under each frame for logging"
  - "One-thumbnail-per-N-seconds strip to eyeball pacing at a glance"
  - "Multi-page sheets for a long video (auto-split across several PNGs)"
  - "Quick QC montage to spot black frames, glitches, or repeated shots"
when_not_to_use:
  - "Need frames as separate numbered image files, not a laid-out grid → use video-frame-extraction"
  - "Want AI-detected scene cut timestamps first → use shot-scene-detection, then feed them here"
  - "Want an animated GIF preview, not a static grid → use slack-gif-creator or ffmpeg-cookbook"
  - "General transcode / filter recipe unrelated to grids → use ffmpeg-cookbook"
  - "Just need one still at a timestamp → use video-frame-extraction"
keywords: [contact sheet, storyboard, thumbnail grid, montage, tile filter, ffmpeg tile, proof sheet, vidcaps, drawtext timecode, burn timecode, mosaic, screenshot grid, overview image, filmstrip, scene grid, storyboard grid]
similar_to: [video-frame-extraction, shot-scene-detection, ffmpeg-cookbook, keyframe-motion-frame-diff, batch-transcode-encode]
inputs_needed:
  - "Path to the source video"
  - "Grid shape: either a fixed CxR (e.g. 5x6) or a cadence (one thumb every N seconds / per scene)"
  - "Thumbnail width in px (height auto), and whether to burn timecodes (default yes)"
  - "Output path (.png sharp, .jpg smaller) and output folder"
produces: A single contact-sheet / storyboard PNG (or JPG), or a numbered set of sheet pages for long videos, each cell showing the frame with its source timecode.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Contact Sheet / Storyboard

Collapse a whole video into one image: a grid of evenly-spaced thumbnails, each
stamped with the timecode it came from. `fps` (or `select`) samples the frames,
`drawtext` burns the timecode onto each thumb, `tile` lays them out.

## When to use

- One image that summarises an entire clip (grid of stills + timecodes).
- Storyboard: one tile per scene or per beat, timecodes visible for logging.
- QC montage to eyeball pacing, black frames, dupes, or glitches fast.

## Prerequisites (this Mac)

No brew ffmpeg here. Use the portable binary from the pip `imageio-ffmpeg`
wheel — it is a full build with **libfreetype + fontconfig**, so `drawtext`,
`tile`, `fps` and `select` all work:

```bash
FF=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())")
FP=$(python3 -c "import imageio_ffmpeg,sys,os; sys.stdout.write(os.path.join(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()),'ffprobe'))" 2>/dev/null)
"$FF" -version | head -1
"$FF" -hide_banner -filters | grep -E ' (tile|drawtext) '   # confirm both present
```

Font for `drawtext` (portable ffmpeg lacks a default) — use an explicit file
that exists on macOS. Reference it as `${FONT}` (with braces): this Mac's shell
is **zsh**, where a bare `$FONT:text` triggers the `:t` history modifier and
silently mangles the path to `Arial.ttf` → drawtext then errors "text must be
provided".

```bash
FONT=/System/Library/Fonts/Supplemental/Arial.ttf
```

`ffprobe` may not ship beside the imageio binary. Where a recipe needs duration,
the one-liner below derives it from `ffmpeg` stderr instead — no ffprobe needed.

## Recipes

`drawtext` is applied **before** `tile`, so each thumbnail carries its own
source timecode. `%{pts\:hms}` renders that frame's presentation time as
`HH:MM:SS.mmm`. Reusable timecode drawtext snippet:

```bash
TC="drawtext=fontfile=${FONT}:text='%{pts\\:hms}':x=6:y=h-th-6:fontcolor=white:fontsize=20:box=1:boxcolor=black@0.55:boxborderw=5"
```

### 1. One thumbnail every N seconds (variable rows)

Best default for "give me an overview". Here: 1 thumb / 5 s, 320px wide, 5 cols.
`tile` auto-fills as many rows as needed for the frames it receives.

```bash
"$FF" -y -i in.mp4 \
  -vf "fps=1/5,$TC,scale=320:-1,tile=5x100:margin=8:padding=6:color=black" \
  -frames:v 1 -update 1 sheet.png
```

`tile=5x100` = 5 columns, up to 100 rows (a ceiling; unused rows are trimmed).
Raise the row cap if the clip is long. `-frames:v 1 -update 1` forces a single
output image.

### 2. Fixed grid across the WHOLE clip (e.g. exactly 5x6 = 30 thumbs)

Compute an fps that spreads exactly `cols*rows` samples over the duration.
Derives duration from ffmpeg stderr (no ffprobe):

```bash
IN=in.mp4; COLS=5; ROWS=6; W=320
DUR=$("$FF" -i "$IN" 2>&1 | awk -F'[:,]' '/Duration/{print $2*3600+$3*60+$4; exit}')
N=$((COLS*ROWS))
FPS=$(python3 -c "print($N/max($DUR,0.001))")
"$FF" -y -i "$IN" \
  -vf "fps=$FPS,$TC,scale=$W:-1,tile=${COLS}x${ROWS}:margin=8:padding=6:color=black" \
  -frames:v 1 -update 1 -pix_fmt rgb24 sheet.png
```

The `fps` filter picks the frame nearest each 1/FPS interval, so the 30 tiles
are evenly spread start→end.

### 3. Storyboard: one tile per scene cut

Sample only frames where a scene change is detected (threshold 0.3), then tile.
Great for "storyboard every scene" without a separate detector.

```bash
"$FF" -y -i in.mp4 \
  -vf "select='gt(scene,0.3)',$TC,scale=360:-1,tile=4x100:margin=8:padding=6,setpts=N/TB" \
  -frames:v 1 -update 1 -vsync vfr storyboard.png
```

Tune `0.3` (lower = more cuts). If you already have precise cut timestamps from
**shot-scene-detection**, use `select='eq(n,123)+eq(n,456)+...'` with the frame
numbers instead for exact tiles.

### 4. JPG output + a header title strip

Smaller file, with a caption bar drawn over the finished sheet:

```bash
"$FF" -y -i in.mp4 \
  -vf "fps=1/10,$TC,scale=280:-1,tile=6x100:margin=8:padding=6:color=black,\
drawtext=fontfile=${FONT}:text='in.mp4 — contact sheet':x=8:y=8:fontcolor=yellow:fontsize=22:box=1:boxcolor=black@0.6:boxborderw=6" \
  -frames:v 1 -update 1 -q:v 3 sheet.jpg
```

### 5. Long video → multi-page sheets

For a 2-hour talk a single sheet gets unwieldy. The helper splits the grid
across numbered pages (`sheet-001.png`, `sheet-002.png`, …):

```bash
python3 scripts/contact_sheet.py in.mp4 --cols 5 --rows 6 --every 15 --width 320 --out sheets/
# --every N  : one thumb per N seconds (omit to fill each page edge-to-edge)
# --cols/--rows: tiles per page   --no-timecode: skip the burn-in
```

The helper wraps the same ffmpeg filter chain, computes how many pages the
requested cadence needs, and offsets each page with `-ss` so pages don't overlap.

## Verify

```bash
# It exists and has real dimensions (grid should be cols*W wide-ish):
"$FF" -i sheet.png 2>&1 | grep -E 'Video:|Stream'
# Or open it:
open sheet.png
```

Sanity checks:
- Tile count matches expectation (count cells; for recipe 2 it must be COLS*ROWS).
- Timecodes increase left→right, top→bottom and span 00:00 → end of clip.
- No large block of identical/black tiles (means over-sampling a static section
  or the fps/duration math was off).

## Pitfalls

- **`No such filter: 'drawtext'`** — the ffmpeg build lacks libfreetype. The
  imageio-ffmpeg binary above has it; a stripped custom build may not. Confirm
  with the `grep drawtext` check in Prerequisites.
- **`Cannot find a valid font` / fontconfig errors** — always pass
  `fontfile=$FONT` with a real path (`Arial.ttf` above). Bare `font=Arial`
  needs a fontconfig config the portable build may not resolve.
- **Escaping in filtergraphs** — inside `-vf` the colon in `%{pts\:hms}` must be
  backslash-escaped, and commas separate filters. Keep the `$TC` variable
  unquoted where shown so its own commas chain filters correctly; if you inline
  it, mind the escaping.
- **Only one tile / blank sheet** — you forgot `-frames:v 1 -update 1`, so
  ffmpeg wrote every completed tile as a separate frame or refused to overwrite.
- **Tiles clipped or rows missing** — the `tile` row count is a hard ceiling.
  If `fps` yields more frames than `cols*rows`, extra frames are dropped; raise
  the row cap (recipe 1) or lower the sampling rate.
- **Scene-select gives too many/few tiles** — `scene` threshold is content
  dependent; 0.2–0.4 is a sane range. Add `-vsync vfr` so duplicated PTS from
  `setpts` don't drop tiles.
- **Portrait/rotated video looks squashed** — `scale=W:-1` preserves aspect;
  don't hardcode both dimensions unless you want letterbox/stretch.
